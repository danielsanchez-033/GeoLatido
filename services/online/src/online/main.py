"""Procesado en línea de la zona buscada (2026-11-15).

Al buscar un lugar sin veredictos, la interfaz pide aquí su procesado. Pasos, cada uno con su estado:

1. `zone`: crea la zona en ZONES_DIR (un YAML como los de config/aois), centrada en el lugar y de MAX_SPAN_DEG como
   mucho por lado, con una ventana de WINDOW_DAYS días. catalog la lee de esa carpeta sin reiniciarse.
2. `series`: pide a catalog las series comparables y elige la que tiene HH y HV (processor no procesa otras),
   contiene la zona y más fechas. Si no hay ninguna, termina en `no_processable_series` y dice qué hay.
3. `process`: `python -m processor run-remote --last MAX_DATES`: abre cada fecha en NASA por HTTPS (token de
   Earthdata) y lee en memoria solo la ventana de la zona; **no guarda recortes en disco**, solo los artefactos del
   veredicto en `data/artifacts/<zona>`, que verdicts y tiles ven sin reiniciarse. Medido el 2026-11-15: unos 18 MB y
   35 s por fecha en Delicias, frente a los 8,7 GB que había recibido la copia de ingest sin terminar dos fechas.

Un trabajo a la vez (memoria del equipo de 16 GB); los demás esperan en cola. Todo es dato real: aquí no se genera
nada sintético.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import queue
import re
import shutil
import subprocess
import threading
import time
import unicodedata
from pathlib import Path

import httpx
import yaml
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator

COLLECTION = "NISAR_L2_GCOV_PROVISIONAL_V1"
PROCESSABLE = ("DH", "QP")  # processor necesita HH y HV (gcov.py, _NEEDED)
STEPS = ("zone", "series", "process")


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def slug(text: str) -> str:
    t = unicodedata.normalize("NFKD", text.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:24] or "zona"


def clamp_bbox(bbox: list[float], max_span: float) -> list[float]:
    """Centra la caja en el lugar y la limita a max_span grados por lado: cada fecha de una zona como Parral
    (0,55° × 0,45°) pesa unos 310 MB y tarda 2-6 min; una de 0,3° pesa menos de la mitad."""
    w, s, e, n = bbox
    cx, cy = (w + e) / 2, (s + n) / 2
    hx, hy = min((e - w) / 2, max_span / 2), min((n - s) / 2, max_span / 2)
    # Un punto o una caja diminuta (un edificio) se amplía a 0,1° para que haya algo que medir.
    hx, hy = max(hx, 0.05), max(hy, 0.05)
    return [round(cx - hx, 5), round(cy - hy, 5), round(cx + hx, 5), round(cy + hy, 5)]


def zone_id(name: str, bbox: list[float]) -> str:
    h = hashlib.sha1(",".join(f"{v:.3f}" for v in bbox).encode()).hexdigest()[:6]
    return f"z-{slug(name)}-{h}"


# Copia de services/verdicts/src/verdicts/rules.py (los servicios no importan código entre sí; processor/cells.py
# hace lo mismo). Solo sirve para el resumen ligero que la interfaz enseña al terminar, antes de pedir a verdicts el
# veredicto completo, que es el que manda. Si Balanza cambia los umbrales, hay que cambiarlos aquí.
MIN_OBSERVED_FRACTION = 0.5
MIN_CHANGED_FRACTION = 0.05
UNOBSERVABLE_CAUSES = ("outside_scene", "invalid_or_partial", "input_exception", "low_looks", "no_data", "terrain")


def summarize_manifest(manifest: dict) -> dict:
    """Resumen por par sacado del manifiesto de processor: fechas, estado y fracción de cambio, con la misma regla
    que verdicts (`decide`). Declara que es provisional y sin calibrar; el veredicto de verdicts es el que vale."""
    pairs = []
    for p in manifest.get("pairs", []):
        counts = p.get("stats", {}).get("counts", {})
        observed = counts.get("no_change", 0) + counts.get("change_probable", 0)
        total = sum(counts.values())
        observed_fraction = observed / total if total else 0.0
        changed_fraction = counts.get("change_probable", 0) / observed if observed else 0.0
        cause = None
        if observed_fraction < MIN_OBSERVED_FRACTION:
            state = "not_observable"
            cause = max(UNOBSERVABLE_CAUSES, key=lambda name: counts.get(name, 0))
        else:
            state = "change_probable" if changed_fraction >= MIN_CHANGED_FRACTION else "no_detectable_change"
        frm, to = p["from"], p["to"]
        pairs.append({
            "id": p["id"], "from": frm, "to": to, "kind": p.get("kind"),
            "interval_days": (dt.date.fromisoformat(to[:10]) - dt.date.fromisoformat(frm[:10])).days,
            "state": state, "cause": cause,
            "observed_fraction": round(observed_fraction, 4), "changed_fraction": round(changed_fraction, 4),
        })
    return {
        "series": manifest.get("series", {}).get("id"), "data_kind": manifest.get("data_kind"),
        "dates": [d["date"] for d in manifest.get("dates", [])], "pairs": pairs,
        "rules": {"min_observed_fraction": MIN_OBSERVED_FRACTION, "min_changed_fraction": MIN_CHANGED_FRACTION,
                  "calibrated": False, "source": "manifest"},
    }


def series_config_id(s: dict) -> str:
    return f"T{int(s['track']):03d}{s['direction']}-F{int(s['frame']):03d}"


# Gránulos en modo mixto: la letra tras la polarización es M (…_DHDH_M_2026…; la habitual es A). processor los
# rechaza (gcov.py, isMixedMode), así que no cuentan para elegir serie. Visto en Venecia el 2026-11-15.
MIXED = re.compile(r"_[A-Z]{4}_M_\d{8}T")


def usable(granules: list[dict]) -> list[dict]:
    return [g for g in granules if not MIXED.search(g.get("id", ""))]


def choose_series(available: list[dict]) -> tuple[dict | None, list[dict]]:
    """La serie con HH y HV que contiene la zona y tiene más fechas utilizables (sin modo mixto); si ninguna la
    contiene, la de más fechas."""
    resumen = [
        {"id": s["id"], "polarization": s["polarization"], "dates": len(s["granules"]), "usable_dates": len(usable(s["granules"])),
         "contains_aoi": s["contains_aoi"]}
        for s in available
    ]
    ok = [s for s in available if s["polarization"][:2] in PROCESSABLE and len(usable(s["granules"])) >= 2]
    if not ok:
        return None, resumen
    ok.sort(key=lambda s: (s["contains_aoi"], len(usable(s["granules"]))), reverse=True)
    return ok[0], resumen


class ZoneIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    bbox: list[float] = Field(..., description="[oeste, sur, este, norte] del lugar buscado, WGS84.")

    @field_validator("bbox")
    @classmethod
    def _bbox(cls, v):
        if len(v) != 4:
            raise ValueError("bbox necesita 4 números")
        w, s, e, n = v
        if not (-180 <= w <= e <= 180 and -90 <= s <= n <= 90):
            raise ValueError("bbox fuera de rango o invertida (no se admite cruzar el antimeridiano)")
        return v


class Runner:
    def __init__(self, zones_dir: Path, data_dir: Path, catalog_url: str, max_dates: int, window_days: int,
                 run=None, client: httpx.Client | None = None):
        self.zones_dir = zones_dir
        self.data_dir = data_dir
        self.catalog_url = catalog_url.rstrip("/")
        self.max_dates = max_dates
        self.window_days = window_days
        self.client = client or httpx.Client(timeout=120)
        self.run_cmd = run or self._subprocess
        self.q: queue.Queue[str] = queue.Queue()
        self._proc: subprocess.Popen | None = None
        self._cancel: set[str] = set()
        self._lock = threading.Lock()
        # Lecturas y escrituras del estado bajo el mismo cerrojo: en Windows, reemplazar un archivo abierto falla.
        self._io = threading.RLock()
        zones_dir.mkdir(parents=True, exist_ok=True)
        # Un reinicio corta los trabajos en marcha: quedan como fallidos y se pueden volver a pedir.
        for job in self.list():
            if job["state"] in ("queued", "running"):
                job.update(state="failed", error="Interrumpido por un reinicio del servicio; vuelve a buscar el lugar.")
                self._save(job)
        threading.Thread(target=self._worker, daemon=True).start()

    # --- estado en disco ------------------------------------------------------------------------------------------
    def _job_path(self, zid: str) -> Path:
        return self.zones_dir / f"{zid}.job.json"

    def get(self, zid: str) -> dict | None:
        p = self._job_path(zid)
        with self._io:
            return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None

    def _save(self, job: dict) -> dict:
        job["updated_at"] = now()
        with self._io:
            tmp = self._job_path(job["id"]).with_suffix(".part")
            tmp.write_text(json.dumps(job, ensure_ascii=False, indent=1), encoding="utf-8")
            tmp.replace(self._job_path(job["id"]))
        return job

    def list(self) -> list[dict]:
        with self._io:
            out = [json.loads(p.read_text(encoding="utf-8")) for p in self.zones_dir.glob("*.job.json")]
        return sorted(out, key=lambda j: j.get("created_at", ""), reverse=True)

    # --- API ----------------------------------------------------------------------------------------------------------
    def submit(self, name: str, bbox: list[float], max_span: float) -> dict:
        area = clamp_bbox(bbox, max_span)
        zid = zone_id(name, area)
        with self._lock:
            job = self.get(zid)
            if job and job["state"] in ("queued", "running", "done"):
                return job
            job = {"id": zid, "name": name, "requested_bbox": bbox, "bbox": area, "state": "queued", "step": None,
                   "steps": {s: "pending" for s in STEPS}, "series": None, "series_found": [], "log": [], "error": None,
                   "created_at": now(), "max_dates": self.max_dates}
            self._save(job)
        self.q.put(zid)
        return job

    def regenerate(self, zid: str) -> dict | None:
        """Vuelve a procesar una zona ya creada (2026-11-15): elige de nuevo la serie y lee las fechas más recientes.
        None si la zona no existe; si ya está en cola o en marcha, devuelve el trabajo tal cual."""
        with self._lock:
            job = self.get(zid)
            if not job:
                return None
            if job["state"] in ("queued", "running"):
                return job
            job.update(state="queued", step=None, steps={s: "pending" for s in STEPS}, series=None, series_found=[], log=[],
                       error=None, summary=None, subsidence=None, regenerated_at=now())
            self._save(job)
        self.q.put(zid)
        return job

    def cancel(self, zid: str) -> bool:
        job = self.get(zid)
        if not job or job["state"] not in ("queued", "running"):
            return False
        self._cancel.add(zid)
        if self._proc and self._proc.poll() is None and job["state"] == "running":
            self._proc.terminate()
        return True

    # --- trabajo ------------------------------------------------------------------------------------------------
    def _worker(self):
        while True:
            zid = self.q.get()
            try:
                self._run(zid)
            except Exception as e:  # noqa: BLE001 - el estado del trabajo lleva el error
                job = self.get(zid) or {"id": zid}
                job.update(state="failed", error=f"{type(e).__name__}: {e}"[:500], finished_at=now())
                self._save(job)

    def _subprocess(self, args: list[str], job: dict) -> int:
        # Sin búfer: ingest y processor escriben su progreso al momento y la interfaz lo ve.
        env = {**os.environ, "CATALOG_URL": self.catalog_url, "PYTHONUNBUFFERED": "1"}
        self._proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
        for line in self._proc.stdout:  # type: ignore[union-attr]
            job["log"] = (job["log"] + [line.rstrip()[:300]])[-40:]
            self._save(job)
        return self._proc.wait()

    def _start_subsidence(self, zid: str):
        """Hundimiento con NISAR GUNW (processor subsidence) en paralelo al procesado de GCOV: es otra lectura de
        NASA, pequeña, y no debe alargar la espera. Solo con el lanzador real; en las pruebas no se lanza."""
        if self.run_cmd != self._subprocess:
            return None
        env = {**os.environ, "PYTHONUNBUFFERED": "1"}
        args = ["python", "-m", "processor", "--aoi-dir", str(self.zones_dir), "--data-dir", str(self.data_dir),
                "subsidence", "--aoi", zid, "--pairs", "6"]
        try:
            return subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
        except OSError:
            return None

    def _finish_subsidence(self, proc, zid: str, job: dict, wait_s: float = 240.0) -> None:
        """Espera al hundimiento como mucho `wait_s` tras el GCOV y deja su resumen en el trabajo. Nunca hace fallar
        el trabajo: si no termina o falla, la zona queda sin dato de hundimiento y se dice."""
        if proc is None:
            return
        try:
            proc.wait(timeout=wait_s)
        except subprocess.TimeoutExpired:
            proc.kill()
            job["subsidence"] = {"status": "timeout"}
            return
        path = self.data_dir / "artifacts" / zid / "subsidence" / "subsidence.json"
        if proc.returncode == 0 and path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            job["subsidence"] = {k: data.get(k) for k in ("status", "sinking_fraction", "max_rate_mm_yr", "noise_mm_yr", "days")}
        else:
            job["subsidence"] = {"status": "failed"}

    def _step(self, job: dict, step: str, fn) -> bool:
        if job["id"] in self._cancel:
            raise InterruptedError()
        job["step"] = step
        job["steps"][step] = "running"
        self._save(job)
        t = time.monotonic()
        ok = fn()
        job["steps"][step] = ("done" if ok else "failed") + f" ({time.monotonic() - t:.0f} s)"
        self._save(job)
        return ok

    def _run(self, zid: str):
        job = self.get(zid)
        job.update(state="running", started_at=now())
        self._save(job)
        aoi_yaml = self.zones_dir / f"{zid}.yaml"
        today = dt.date.today()
        aoi = {
            "id": zid, "name": job["name"], "bbox": job["bbox"], "city_bbox": job["bbox"], "collection": COLLECTION,
            "maturity": "PROVISIONAL",
            "window": {"start": (today - dt.timedelta(days=self.window_days)).isoformat(), "end": today.isoformat()},
            "series": [], "origin": "online", "created_at": job["created_at"],
        }
        try:
            self._step(job, "zone", lambda: aoi_yaml.write_text(yaml.safe_dump(aoi, allow_unicode=True, sort_keys=False), encoding="utf-8") > 0)

            def series() -> bool:
                r = self.client.get(f"{self.catalog_url}/aois/{zid}/series")
                r.raise_for_status()
                chosen, found = choose_series(r.json())
                job["series_found"] = found
                if not chosen:
                    return False
                sid = series_config_id(chosen)
                job["series"] = {"id": sid, "catalog_id": chosen["id"], "polarization": chosen["polarization"],
                                 "dates": len(usable(chosen["granules"])), "contains_aoi": chosen["contains_aoi"]}
                aoi["series"] = [{"id": sid, "track": chosen["track"], "direction": chosen["direction"], "frame": chosen["frame"]}]
                aoi_yaml.write_text(yaml.safe_dump(aoi, allow_unicode=True, sort_keys=False), encoding="utf-8")
                return True

            if not self._step(job, "series", series):
                job.update(state="no_processable_series", step=None, finished_at=now(),
                           error="Ninguna serie NISAR con HH y HV y al menos dos fechas sin modo mixto cubre esta zona en "
                           "la ventana; processor necesita las dos polarizaciones. Las pasadas se pueden ver igual.")
                self._save(job)
                return
            sid = job["series"]["id"]
            run = ["python", "-m", "processor", "--aoi-dir", str(self.zones_dir), "--data-dir", str(self.data_dir), "run-remote",
                   "--aoi", zid, "--series", sid, "--last", str(self.max_dates), "--catalog-url", self.catalog_url,
                   "--catalog-series", job["series"]["catalog_id"]]
            hundimiento = self._start_subsidence(zid)
            if not self._step(job, "process", lambda: self.run_cmd(run, job) == 0):
                if hundimiento is not None:
                    hundimiento.kill()
                if zid in self._cancel:
                    raise InterruptedError()
                causa = next((line for line in reversed(job["log"]) if line.startswith("Error:")), "")
                raise RuntimeError(f"processor no pudo leer o procesar las fechas. {causa or 'Revisa EARTHDATA_TOKEN y la conexión.'}")
            # Respuesta ligera: el resumen por par sale del manifiesto y llega con el estado `done`, antes de que la
            # interfaz pida teselas o veredictos a verdicts.
            manifest_path = self.data_dir / "artifacts" / zid / sid / "manifest.json"
            if manifest_path.exists():
                job["summary"] = summarize_manifest(json.loads(manifest_path.read_text(encoding="utf-8")))
            self._finish_subsidence(hundimiento, zid, job)
            # Al regenerar puede salir otra serie: las anteriores de esta zona en línea se quitan para no duplicarla.
            zona = self.data_dir / "artifacts" / zid
            if zid.startswith("z-") and zona.is_dir():
                for d in zona.iterdir():
                    if d.is_dir() and d.name not in (sid, "subsidence"):
                        shutil.rmtree(d, ignore_errors=True)
            job.update(state="done", step=None, finished_at=now(), aoi=zid)
            self._save(job)
        except InterruptedError:
            job.update(state="cancelled", finished_at=now())
            self._save(job)
        finally:
            self._cancel.discard(zid)


def create_app(runner: Runner | None = None) -> FastAPI:
    app = FastAPI(title="Dancing with the SAR — procesado en línea", version="0.1.0",
                  description="Procesa la zona buscada con ingest y processor. Un trabajo a la vez; datos reales.")
    max_span = float(os.environ.get("ONLINE_MAX_SPAN_DEG", "0.3"))
    r = runner or Runner(
        Path(os.environ.get("ZONES_DIR", "/data/aois-online")),
        Path(os.environ.get("DATA_DIR", "/data")),
        os.environ.get("CATALOG_URL", "http://catalog:8000"),
        int(os.environ.get("ONLINE_MAX_DATES", "4")),
        int(os.environ.get("ONLINE_WINDOW_DAYS", "150")),
    )
    token_ok = bool(os.environ.get("EARTHDATA_TOKEN"))

    @app.get("/health")
    def health():
        return {"status": "ok", "earthdata_token": token_ok}

    @app.get("/zones")
    def zones():
        return r.list()

    @app.post("/zones", status_code=202)
    def create(body: ZoneIn):
        if not token_ok:
            raise HTTPException(503, "Falta EARTHDATA_TOKEN en el .env: sin él no se pueden leer los gránulos de NASA.")
        return r.submit(body.name, body.bbox, max_span)

    @app.get("/zones/{zid}")
    def get(zid: str):
        job = r.get(zid)
        if not job:
            raise HTTPException(404, "Zona inexistente")
        return job

    @app.post("/zones/{zid}/regenerate", status_code=202)
    def regenerate(zid: str) -> dict:
        """Regenera los veredictos de una zona en línea con sus fechas más recientes."""
        if not token_ok:
            raise HTTPException(503, "Falta EARTHDATA_TOKEN en el .env: sin él no se pueden leer los gránulos de NASA.")
        job = r.regenerate(zid)
        if job is None:
            raise HTTPException(404, "Zona desconocida: solo se regeneran las zonas procesadas en línea")
        return job

    @app.post("/zones/{zid}/cancel")
    def cancel(zid: str) -> dict:
        return {"cancel_requested": r.cancel(zid)}

    @app.get("/limits")
    def limits() -> dict:
        return {"max_span_deg": max_span, "max_dates": r.max_dates, "window_days": r.window_days, "processable_polarizations": list(PROCESSABLE)}

    return app

