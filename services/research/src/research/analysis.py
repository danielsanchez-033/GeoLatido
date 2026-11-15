"""Detección de cambios y análisis temporal sobre lo que ya procesó la cadena del proyecto.

No se reprocesa nada aquí: la retrodispersión, el umbral y el desplazamiento de escena salen de `verdicts` (HTTP) y
de su manifiesto (contrato de Eco). Este módulo agrupa los veredictos por serie, mide su evolución y convierte cada
par con cambio o con anomalía estadística en un hallazgo con su evidencia y sus límites.
"""
from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
from typing import Protocol

import httpx

from . import temporal

ASF_GAPS = [(dt.date(2026, 7, 27), dt.date(2026, 8, 10))]  # hueco permanente de adquisición declarado por ASF


class VerdictsSource(Protocol):
    def aois(self) -> list[str]: ...
    def series(self, aoi: str) -> list[dict]: ...
    def verdicts(self, aoi: str, series: str, lang: str) -> list[dict]: ...
    def event(self, aoi: str, date: str, params: dict) -> dict: ...


class HttpVerdicts:
    def __init__(self, base: str | None = None, client: httpx.Client | None = None):
        self.base = (base or os.environ.get("VERDICTS_URL", "http://verdicts:8000")).rstrip("/")
        self.client = client or httpx.Client(timeout=200)

    def _get(self, path: str, params: dict | None = None):
        r = self.client.get(self.base + path, params=params)
        r.raise_for_status()
        return r.json()

    def aois(self):
        return self._get("/aois")

    def series(self, aoi):
        return self._get(f"/aois/{aoi}/series")

    def verdicts(self, aoi, series, lang):
        return self._get(f"/aois/{aoi}/series/{series}/verdicts", {"lang": lang})

    def event(self, aoi, date, params):
        return self._get(f"/aois/{aoi}/events", {"date": date, **params})


def intersects(a: list[float], b: list[float]) -> bool:
    return a[0] < b[2] and a[2] > b[0] and a[1] < b[3] and a[3] > b[1]


def bbox_polygon(b: list[float]) -> dict:
    w, s, e, n = b
    return {"type": "Polygon", "coordinates": [[[w, s], [e, s], [e, n], [w, n], [w, s]]]}


def confidence(v: dict) -> tuple[str, list[str]]:
    """Confianza descriptiva de un hallazgo: nunca 'alta', porque ningún umbral está calibrado con verdad de campo."""
    reasons: list[str] = []
    ev = v["evidence"]
    if ev.get("observed_fraction", 0) < 0.9:
        reasons.append("menos del 90 % de la zona observable")
    ss = ev.get("scene_shift") or {}
    if ss.get("exceeds_threshold"):
        reasons.append("desplazamiento de toda la escena por encima del umbral")
    noise = ev.get("noise") or {}
    if (noise.get("hh_db") or 0) >= 1.2:
        reasons.append("dispersión de la diferencia HH ≥ 1,2 dB (par ruidoso)")
    if v["receipt"].get("spans_data_gap"):
        reasons.append("el par cruza un hueco de adquisición")
    q = v["receipt"].get("quality") or {}
    if any((side or {}).get("flags") for side in (q.get("before"), q.get("after"))):
        reasons.append("alguna fecha con bandera de calidad")
    margin = ev["changed_fraction"] - ev["decision_rule"]["min_changed_fraction"]
    if 0 <= margin < 0.01:
        reasons.append("a menos de 1 punto del umbral de decisión")
    return ("low" if reasons else "medium"), reasons


def _cells(artifact_root: Path | None, aoi: str, series: str, pair_id: str) -> dict | None:
    """Celdas de 1 km con cambio, del manifiesto (T-ECO-12). None si la serie no las trae."""
    if not artifact_root:
        return None
    mpath = artifact_root / aoi / series / "manifest.json"
    if not mpath.exists():
        return None
    try:
        manifest = json.loads(mpath.read_text(encoding="utf-8"))
        pair = next((p for p in manifest.get("pairs", []) if p["id"] == pair_id), None)
        if not pair or not pair.get("cells"):
            return None
        gj = json.loads((artifact_root / pair["cells"]).read_text(encoding="utf-8"))
    except (OSError, ValueError, KeyError):
        return None
    feats = [f for f in gj.get("features", []) if (f.get("properties") or {}).get("state") == "change_probable"]
    if not feats:
        return None
    return {"type": "FeatureCollection", "features": feats}


def analyze_area(src: VerdictsSource, area: dict, start: str, end: str, lang: str = "es", artifact_root: Path | None = None) -> dict:
    out: dict = {"area": area["id"], "processed": [], "series": [], "findings": [], "limitations": [], "errors": []}
    s0, e0 = dt.date.fromisoformat(start), dt.date.fromisoformat(end)
    try:
        aois = src.aois()
    except Exception as e:  # noqa: BLE001
        out["errors"].append({"source": "verdicts", "error": type(e).__name__, "detail": str(e)[:200]})
        out["limitations"].append("El servicio de veredictos no respondió: no hay análisis de cambio para esta área.")
        return out
    for aoi in aois:
        try:
            series_list = src.series(aoi)
        except Exception as e:  # noqa: BLE001
            out["errors"].append({"source": f"verdicts/{aoi}", "error": type(e).__name__, "detail": str(e)[:200]})
            continue
        for s in series_list:
            if not intersects(area["bbox"], s["bbox"]):
                continue
            try:
                vs = src.verdicts(aoi, s["id"], lang)
            except Exception as e:  # noqa: BLE001
                out["errors"].append({"source": f"verdicts/{aoi}/{s['id']}", "error": type(e).__name__, "detail": str(e)[:200]})
                continue
            vs = [v for v in vs if dt.date.fromisoformat(v["from_date"]) >= s0 and dt.date.fromisoformat(v["to_date"]) <= e0]
            out["processed"].append({"aoi": aoi, "series": s["id"], "data_kind": s["data_kind"], "bbox": s["bbox"], "dates": s["dates"], "relief": s.get("relief") is not None})
            out["series"].append(_series_block(aoi, s, vs))
            out["findings"] += _findings(aoi, s, vs, out["series"][-1], artifact_root)
    if not out["processed"]:
        out["limitations"].append(
            "Ninguna serie procesada por este proyecto cubre esta área en el periodo: solo hay disponibilidad de "
            "datos (catálogo), no medición de cambio. Ausencia de análisis no es ausencia de cambio."
        )
    return out


def _series_block(aoi: str, s: dict, vs: list[dict]) -> dict:
    cons = sorted([v for v in vs if v["kind"] == "consecutive"], key=lambda v: v["to_date"])
    observed = [v for v in cons if v["state"] != "not_observable"]
    pts = [(dt.date.fromisoformat(v["to_date"]), v["evidence"]["changed_fraction"]) for v in observed]
    analysis = temporal.analyze_series(pts, ASF_GAPS) if pts else None
    return {
        "aoi": aoi,
        "series": s["id"],
        "data_kind": s["data_kind"],
        "variable": "changed_fraction",
        "variable_label": "Fracción de lo observado con cambio probable (HH/HV, umbral por par, desplazamiento de escena restado)",
        "points": [
            {
                "pair_id": v["id"],
                "from": v["from_date"],
                "to": v["to_date"],
                "state": v["state"],
                "changed_fraction": v["evidence"]["changed_fraction"],
                "observed_fraction": v["evidence"]["observed_fraction"],
                "mean_change_hh_db": v["evidence"].get("mean_change_hh_db"),
                "mean_change_hv_db": v["evidence"].get("mean_change_hv_db"),
                "scene_shift_hh_db": (v["evidence"].get("scene_shift") or {}).get("hh_db"),
                "noise_hh_db": (v["evidence"].get("noise") or {}).get("hh_db"),
                "spans_data_gap": v["receipt"].get("spans_data_gap"),
                "granules": v["receipt"].get("granules", []),
            }
            for v in cons
        ],
        "not_observable_pairs": [v["id"] for v in cons if v["state"] == "not_observable"],
        "full_window": [
            {"pair_id": v["id"], "from": v["from_date"], "to": v["to_date"], "state": v["state"], "changed_fraction": v["evidence"]["changed_fraction"]}
            for v in vs
            if v["kind"] == "full_window"
        ],
        "analysis": analysis,
        "decision_rule": cons[0]["evidence"]["decision_rule"] if cons else None,
    }


def _findings(aoi: str, s: dict, vs: list[dict], block: dict, artifact_root: Path | None) -> list[dict]:
    anomalous_dates = {a["date"] for a in ((block["analysis"] or {}).get("anomalies") or [])}
    out = []
    for v in vs:
        if v["kind"] != "consecutive":
            continue
        stat = v["to_date"] in anomalous_dates
        if v["state"] != "change_probable" and not stat:
            continue
        conf, reasons = confidence(v)
        cells = _cells(artifact_root, aoi, s["id"], v["id"])
        ev = v["evidence"]
        out.append({
            "id": f"F-{aoi}-{s['id']}-{v['id']}",
            "aoi": aoi,
            "series": s["id"],
            "pair_id": v["id"],
            "geometry": cells or bbox_polygon(s["bbox"]),
            "geometry_kind": "cells_1km" if cells else "aoi_bbox",
            "start": v["from_date"],
            "end": v["to_date"],
            "sensor": "NISAR L-SAR",
            "product": "NISAR_L2_GCOV_PROVISIONAL_V1",
            "data_kind": v["receipt"]["data_kind"],
            "variables": ["HH (dB)", "HV (dB)"],
            "method": "Diferencia de retrodispersión por par, suavizado 5 × 5, umbral por par y desplazamiento de escena restado (processor); estado por fracción mínima (verdicts)"
            + ("; además, anomalía robusta en la serie" if stat else ""),
            "detection": ["verdict_change_probable"] * (v["state"] == "change_probable") + ["series_robust_anomaly"] * stat,
            "magnitude": {"changed_fraction": ev["changed_fraction"], "mean_change_hh_db": ev.get("mean_change_hh_db"), "mean_change_hv_db": ev.get("mean_change_hv_db")},
            "confidence": conf,
            "confidence_reasons": reasons,
            "confidence_calibrated": False,
            "verdict_state": v["state"],
            "hypotheses": v.get("hypotheses", []),
            "limitations": [x for x in (v["summary"]["does_not_prove"], v["summary"]["missing"]) if x],
            "granules": v["receipt"].get("granules", []),
            "verdict_path": f"/api/verdicts/aois/{aoi}/series/{s['id']}/verdicts/{v['id']}",
        })
    return out
