"""Descubrimiento de adquisiciones en CMR (NASA), sin cuenta y sin descargar datos.

CMR da metadatos públicos de todas las colecciones de `products.py`; los archivos de casi todas piden una cuenta de
Earthdata. Aquí solo se leen metadatos: fecha, huella, nombre, enlaces. Lo que el nombre no dice (órbita,
polarización) queda en null o como lo declara el producto, nunca inventado.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

import httpx

from .products import Product

CMR = "https://cmr.earthdata.nasa.gov/search/granules.json"
PAGE = 100


@dataclass
class DiscoveryPage:
    hits: int
    entries: list[dict]


class CmrSource(Protocol):
    def granules(self, short_name: str, bbox: list[float], start: str | None, end: str | None, limit: int) -> DiscoveryPage: ...


class HttpCmr:
    def __init__(self, client: httpx.Client | None = None):
        self.client = client or httpx.Client(timeout=30)

    def granules(self, short_name, bbox, start, end, limit) -> DiscoveryPage:
        params: dict = {
            "short_name": short_name,
            "bounding_box": ",".join(f"{v:.5f}" for v in bbox),
            "page_size": min(limit, 2000),
            "sort_key": "-start_date",
        }
        if start and end:
            params["temporal"] = f"{start}T00:00:00Z,{end}T23:59:59Z"
        r = self.client.get(CMR, params=params)
        r.raise_for_status()
        return DiscoveryPage(int(r.headers.get("CMR-Hits", "0")), r.json()["feed"]["entry"])


EODMS_STAC = "https://eodms-sgdot.nrcan-rncan.gc.ca/search/search"


class StacSource(Protocol):
    def search(self, collection: str, bbox: list[float], start: str | None, end: str | None, limit: int) -> tuple[list[dict], bool]: ...


class HttpEodms:
    """STAC público de EODMS (Recursos Naturales de Canadá): buscar no pide cuenta (comprobado el 2026-11-15).
    Devuelve las features y si hay más páginas (`next`), porque no da el total."""

    def __init__(self, client: httpx.Client | None = None):
        self.client = client or httpx.Client(timeout=60)

    def search(self, collection, bbox, start, end, limit):
        params: dict = {"collections": collection, "bbox": ",".join(f"{v:.5f}" for v in bbox), "limit": min(limit, 100)}
        if start and end:
            params["datetime"] = f"{start}T00:00:00Z/{end}T23:59:59Z"
        r = self.client.get(EODMS_STAC, params=params)
        r.raise_for_status()
        d = r.json()
        feats = d.get("features", [])
        # EODMS da un enlace `next` aunque no queden más páginas: solo cuenta si la página vino llena.
        return feats, len(feats) >= params["limit"] and any(link.get("rel") == "next" for link in d.get("links", []))


def normalize_stac(product: Product, f: dict) -> dict:
    p = f.get("properties", {})
    assets = f.get("assets", {})
    data = (assets.get("cog") or assets.get("product") or {}).get("href")
    return {
        "id": p.get("order_key") or f.get("id"),
        "concept_id": f.get("id"),
        "product": product.id,
        "short_name": product.short_name,
        "sensor": product.sensor,
        "band": p.get("sar:frequency_band") or product.band,
        "level": product.level + (f" — {p.get('product_type') or p.get('metadata.product_type')}" if (p.get("product_type") or p.get("metadata.product_type")) else ""),
        "kind": product.kind,
        "start": p.get("datetime") or p.get("start_datetime"),
        "end": p.get("end_datetime"),
        "bbox": [round(v, 5) for v in f["bbox"]] if f.get("bbox") else None,
        "polarizations": p.get("sar:polarizations") or list(product.polarizations),
        "polarization_source": "stac_metadata" if p.get("sar:polarizations") else "declared_by_product",
        "orbit_direction": p.get("sat:orbit_state"),
        "track": p.get("sat:relative_orbit"),
        "frame": None,
        "resolution_m": p.get("resolution") or p.get("spatial_resolution") or product.resolution_m,
        "size_mb": p.get("megabytes"),
        "data_url": data,
        "browse_url": (assets.get("thumbnail") or {}).get("href"),
        "access": product.access,
        "beam_mode": p.get("beam_mode") or p.get("sar:instrument_mode"),
        "provenance": f"{EODMS_STAC}?collections={product.short_name}",
    }


NISAR_RE = re.compile(r"NISAR_L2_\w+?_(?P<track>\d{3})_(?P<dir>[AD])_(?P<frame>\d{3})_(?P<mode>\d{4})_(?P<pol>[A-Z]{4})_")
S1_RE = re.compile(r"^S1[A-D]_\w{2}_\w{4}_1S(?P<pol>[SD][VH])_")
OPERA_POL_RE = re.compile(r"_(VV|VH|HH|HV)(?:\+(VV|VH|HH|HV))?_")

POL_PAIRS = {"DH": ["HH", "HV"], "DV": ["VV", "VH"], "SH": ["HH"], "SV": ["VV"]}
NISAR_POL = {"DHDH": ["HH", "HV"], "DVDV": ["VV", "VH"], "QPQP": ["HH", "HV", "VH", "VV"], "SHNA": ["HH"], "SVNA": ["VV"]}


def _bbox_of(entry: dict) -> list[float] | None:
    lats: list[float] = []
    lons: list[float] = []
    for poly in entry.get("polygons") or []:
        nums = [float(v) for v in poly[0].split()]
        lats += nums[0::2]
        lons += nums[1::2]
    for box in entry.get("boxes") or []:
        s, w, n, e = (float(v) for v in box.split())
        lats += [s, n]
        lons += [w, e]
    if not lats:
        return None
    return [round(min(lons), 5), round(min(lats), 5), round(max(lons), 5), round(max(lats), 5)]


def _links(entry: dict) -> tuple[str | None, str | None]:
    data = browse = None
    for link in entry.get("links", []):
        rel, href = link.get("rel", ""), link.get("href", "")
        if not href.startswith("https://"):
            continue
        if rel.endswith("/data#") and data is None:
            data = href
        elif rel.endswith("/browse#") and browse is None:
            browse = href
    return data, browse


def normalize(product: Product, entry: dict) -> dict:
    title = entry.get("title") or entry.get("producer_granule_id") or entry.get("id", "")
    pols: list[str] | None = None
    pol_source = "declared_by_product"
    direction = None
    track = frame = None
    if m := NISAR_RE.search(title):
        pols = NISAR_POL.get(m.group("pol"))
        direction = "ascending" if m.group("dir") == "A" else "descending"
        track, frame = int(m.group("track")), int(m.group("frame"))
        pol_source = "granule_name" if pols else pol_source
    elif m := S1_RE.search(title):
        pols = POL_PAIRS.get(m.group("pol"))
        pol_source = "granule_name"
    elif m := OPERA_POL_RE.search(title):
        pols = [p for p in m.groups() if p]
        pol_source = "granule_name"
    if pols is None:
        pols = list(product.polarizations)
    data_url, browse_url = _links(entry)
    return {
        "id": title,
        "concept_id": entry.get("id"),
        "product": product.id,
        "short_name": product.short_name,
        "sensor": product.sensor,
        "band": product.band,
        "level": product.level,
        "kind": product.kind,
        "start": entry.get("time_start"),
        "end": entry.get("time_end"),
        "bbox": _bbox_of(entry),
        "polarizations": pols,
        "polarization_source": pol_source,
        "orbit_direction": direction,
        "track": track,
        "frame": frame,
        "resolution_m": product.resolution_m,
        "size_mb": float(entry["granule_size"]) if entry.get("granule_size") else None,
        "data_url": data_url,
        "browse_url": browse_url,
        "access": product.access,
        "provenance": f"{CMR}?short_name={product.short_name}",
    }


def discover(source: CmrSource, products: list[Product], area: dict, start: str, end: str, limit: int = PAGE, stac: StacSource | None = None) -> dict:
    """Una consulta por producto. Un proveedor que falla no tumba los demás: queda en `errors`."""
    out: dict = {"area": area["id"], "products": [], "acquisitions": [], "errors": []}
    for p in products:
        if p.catalog == "eodms":
            if stac is None:
                out["products"].append(_summary(p, None, []))
                continue
            try:
                feats, more = stac.search(p.short_name, area["bbox"], start, end, limit)
            except Exception as e:  # noqa: BLE001
                out["errors"].append({"product": p.id, "error": type(e).__name__, "detail": str(e)[:200]})
                out["products"].append(_summary(p, None, []))
                continue
            acqs = [normalize_stac(p, f) for f in feats]
            out["acquisitions"] += acqs
            out["products"].append(_summary(p, len(acqs), acqs) | {"hits_is_lower_bound": more})
            continue
        try:
            page = source.granules(p.short_name, area["bbox"], None if p.static else start, None if p.static else end, limit)
        except Exception as e:  # noqa: BLE001 - cada proveedor falla por separado
            out["errors"].append({"product": p.id, "error": type(e).__name__, "detail": str(e)[:200]})
            out["products"].append(_summary(p, None, []))
            continue
        acqs = [normalize(p, e) for e in page.entries]
        out["acquisitions"] += acqs
        out["products"].append(_summary(p, page.hits, acqs))
    return out


def _summary(p: Product, hits: int | None, acqs: list[dict]) -> dict:
    dates = sorted({a["start"][:10] for a in acqs if a.get("start")})
    gaps = _gaps(dates)
    pols = sorted({x for a in acqs for x in (a["polarizations"] or [])})
    dirs = sorted({a["orbit_direction"] for a in acqs if a["orbit_direction"]})
    return {
        "product": p.id,
        "short_name": p.short_name,
        "sensor": p.sensor,
        "band": p.band,
        "level": p.level,
        "kind": p.kind,
        "phase": p.phase,
        "static": p.static,
        "access": p.access,
        "analyzed_here": p.analyzed_here,
        "notes": p.notes,
        "status": "unavailable" if hits is None else ("found" if hits else "none_found"),
        "hits": hits,
        "listed": len(acqs),
        "first_date": dates[0] if dates else None,
        "last_date": dates[-1] if dates else None,
        "distinct_dates": len(dates),
        "median_revisit_days": _median_revisit(dates),
        "largest_gaps": gaps[:3],
        "polarizations_seen": pols,
        "orbit_directions_seen": dirs,
    }


def _days(dates: list[str]) -> list[int]:
    import datetime as dt

    ds = [dt.date.fromisoformat(d) for d in dates]
    return [(b - a).days for a, b in zip(ds, ds[1:])]


def _median_revisit(dates: list[str]) -> float | None:
    d = sorted(_days(dates))
    if not d:
        return None
    n = len(d)
    return float(d[n // 2]) if n % 2 else (d[n // 2 - 1] + d[n // 2]) / 2


def _gaps(dates: list[str]) -> list[dict]:
    d = _days(dates)
    med = _median_revisit(dates)
    if not med:
        return []
    gaps = [
        {"from": a, "to": b, "days": n}
        for a, b, n in zip(dates, dates[1:], d)
        if n > max(1.5 * med, med + 6)
    ]
    return sorted(gaps, key=lambda g: -g["days"])


def compatibility(acquisitions: list[dict]) -> list[dict]:
    """Avisos de compatibilidad entre adquisiciones que alguien podría querer comparar directamente."""
    notes: list[dict] = []
    sar = [a for a in acquisitions if a["kind"] in ("sar", "insar")]
    bands = sorted({a["band"] for a in sar if a["band"]})
    if len(bands) > 1:
        notes.append({
            "code": "mixed_bands",
            "detail": f"Hay radar en bandas {', '.join(bands)}: la retrodispersión de bandas distintas no se compara en valor, "
            "solo en tendencia o en clases (agua/no agua).",
        })
    nisar = [a for a in sar if a["product"] == "nisar_gcov"]
    dirs = {a["orbit_direction"] for a in nisar if a["orbit_direction"]}
    if len(dirs) > 1:
        notes.append({
            "code": "mixed_orbit_directions",
            "detail": "NISAR ascendente y descendente miran la ladera desde lados opuestos: los pares se forman dentro de "
            "una misma pista y marco.",
        })
    tracks = {(a["track"], a["frame"]) for a in nisar if a["track"] is not None}
    if len(tracks) > 1:
        notes.append({"code": "multiple_tracks", "detail": f"{len(tracks)} pistas/marcos NISAR distintos; cada uno es una serie aparte."})
    levels = sorted({a["level"] for a in sar})
    if any("GRD" in lv for lv in levels) and any("RTC" in lv for lv in levels):
        notes.append({
            "code": "grd_vs_rtc",
            "detail": "GRD no tiene corrección radiométrica de relieve y RTC sí: no se mezclan sin procesar el GRD.",
        })
    return notes
