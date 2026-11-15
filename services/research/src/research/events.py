"""Acontecimientos y su correlación con los hallazgos.

Fuentes: el registro verificado de `config/events/*.yaml` y NASA EONET v3 (público, sin cuenta). Otras fuentes
oficiales (CONAGUA, CENAPRED, EM-DAT, NOAA) no tienen aquí un conector: se documentan como pendientes.

La correlación nunca afirma causa. Cuatro niveles, de menos a más:
1. temporal: el acontecimiento cae dentro del intervalo del par (o a ±N días de su fin).
2. spatial: además, su geometría toca la del hallazgo.
3. statistical: no se calcula (haría falta una serie de eventos y de cambios mucho más larga).
4. causal: solo si una fuente lo demuestra; ninguna lo hace aquí.
"""
from __future__ import annotations

import datetime as dt
import os
from pathlib import Path
from typing import Protocol

import httpx
import yaml

from .analysis import intersects

EONET = "https://eonet.gsfc.nasa.gov/api/v3/events"
EONET_PHENOMENA = {
    "floods": ["flood"], "severeStorms": ["flood"], "landslides": ["landslide"], "wildfires": ["surface_change"],
    "earthquakes": ["deformation"], "volcanoes": ["deformation"], "seaLakeIce": ["glacier"], "snow": ["glacier"],
    "drought": ["flood"], "tempExtremes": [],
}
NEAR_DAYS = 12


class EonetSource(Protocol):
    def events(self, bbox: list[float], start: str, end: str) -> list[dict]: ...


class HttpEonet:
    def __init__(self, client: httpx.Client | None = None):
        self.client = client or httpx.Client(timeout=20)

    def events(self, bbox, start, end):
        w, s, e, n = bbox
        r = self.client.get(EONET, params={"bbox": f"{w},{n},{e},{s}", "start": start, "end": end, "status": "all", "limit": 50})
        r.raise_for_status()
        return r.json().get("events", [])


def load_registry(directory: Path | None = None) -> list[dict]:
    d = directory or Path(os.environ.get("EVENTS_DIR", "/config/events"))
    out: list[dict] = []
    if not d.exists():
        return out
    for f in sorted(d.glob("*.yaml")):
        data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        for e in data.get("events", []):
            e = dict(e)
            e["origin"] = "registry"
            e["registry_file"] = f"config/events/{f.name}"
            out.append(e)
    return out


def _eonet_norm(e: dict) -> dict | None:
    geoms = e.get("geometry") or []
    if not geoms:
        return None
    lons, lats, dates = [], [], []
    for g in geoms:
        c = g.get("coordinates")
        if g.get("type") == "Point" and c:
            lons.append(c[0])
            lats.append(c[1])
        elif g.get("type") == "Polygon" and c:
            for lon, lat in c[0]:
                lons.append(lon)
                lats.append(lat)
        if g.get("date"):
            dates.append(g["date"][:10])
    if not lons or not dates:
        return None
    cats = [c["id"] for c in e.get("categories", [])]
    return {
        "id": e["id"],
        "title": e.get("title"),
        "type": cats[0] if cats else "unknown",
        "phenomena": sorted({p for c in cats for p in EONET_PHENOMENA.get(c, [])}),
        "date": min(dates),
        "end_date": max(dates),
        "location": None,
        "bbox": [min(lons), min(lats), max(lons), max(lats)],
        "geometry_precision": "eonet_track",
        "description": e.get("description"),
        "confidence": "curated_index",
        "sources": [{"name": s.get("id"), "url": s.get("url")} for s in e.get("sources", [])] + [{"name": "NASA EONET", "url": e.get("link")}],
        "origin": "eonet",
    }


def gather(area: dict, start: str, end: str, registry: list[dict], eonet: EonetSource | None, providers: list | tuple = ()) -> dict:
    s0, e0 = dt.date.fromisoformat(start), dt.date.fromisoformat(end)
    found: list[dict] = []
    for e in registry:
        d0 = dt.date.fromisoformat(e["date"])
        d1 = dt.date.fromisoformat(e.get("end_date", e["date"]))
        if d1 >= s0 and d0 <= e0 and intersects(area["bbox"], e["bbox"]):
            found.append(e)
    errors = []
    status = [{"id": "registry", "name": "Registro verificado (config/events)", "status": "ok", "count": len(found)}]
    if eonet is not None:
        try:
            n0 = len(found)
            for raw in eonet.events(area["bbox"], start, end):
                n = _eonet_norm(raw)
                if n and intersects(area["bbox"], n["bbox"]):
                    found.append(n)
            status.append({"id": "eonet", "name": "NASA EONET", "status": "ok", "count": len(found) - n0})
        except Exception as ex:  # noqa: BLE001
            errors.append({"source": "eonet", "error": type(ex).__name__, "detail": str(ex)[:200]})
            status.append({"id": "eonet", "name": "NASA EONET", "status": "error", "count": 0})
    # Proveedores abiertos (sources.py): cada uno por separado; uno caído o sin credencial no para a los demás.
    for p in providers:
        if not p.enabled:
            status.append({"id": p.id, "name": p.name, "status": "needs_credentials", "credential_env": p.credential_env, "count": 0})
            continue
        try:
            got = [e for e in p.events(area["bbox"], start, end) if e.get("date")]
            found += got
            status.append({"id": p.id, "name": p.name, "status": "ok", "count": len(got)})
        except Exception as ex:  # noqa: BLE001
            errors.append({"source": p.id, "error": type(ex).__name__, "detail": str(ex)[:200]})
            status.append({"id": p.id, "name": p.name, "status": "error", "count": 0})
    found.sort(key=lambda e: e["date"])
    return {"area": area["id"], "events": found, "errors": errors, "sources": status}


def correlate(events: list[dict], findings: list[dict], series_blocks: list[dict]) -> list[dict]:
    """Relación de cada acontecimiento con los pares observados: dentro de qué par cae y si toca un hallazgo."""
    out = []
    for e in events:
        if e.get("type") == "data_gap":
            continue
        d0 = dt.date.fromisoformat(e["date"])
        links = []
        for block in series_blocks:
            for p in block["points"]:
                a, b = dt.date.fromisoformat(p["from"]), dt.date.fromisoformat(p["to"])
                inside = a <= d0 <= b
                if not inside and not (0 <= (d0 - b).days <= NEAR_DAYS or 0 <= (a - d0).days <= NEAR_DAYS):
                    continue
                finding = next((f for f in findings if f["series"] == block["series"] and f["pair_id"] == p["pair_id"]), None)
                level = "temporal" if inside else "temporal_near"
                if finding and inside and intersects(e["bbox"], _fbbox(finding)):
                    level = "spatial"
                links.append({
                    "series": block["series"],
                    "pair_id": p["pair_id"],
                    "pair_state": p["state"],
                    "event_inside_interval": inside,
                    "finding_id": finding["id"] if finding else None,
                    "level": level,
                })
        out.append({
            "event_id": e["id"],
            "links": links,
            "statistical_association": "not_computed",
            "causal_relation": "not_demonstrated",
            "note": "Coincidir en fechas o en lugar no prueba que el acontecimiento causara el cambio.",
        })
    return out


def _fbbox(f: dict) -> list[float]:
    g = f["geometry"]
    coords = []
    if g.get("type") == "FeatureCollection":
        for feat in g["features"]:
            for ring in feat["geometry"]["coordinates"]:
                coords += ring
    else:
        coords = g["coordinates"][0]
    xs, ys = [c[0] for c in coords], [c[1] for c in coords]
    return [min(xs), min(ys), max(xs), max(ys)]
