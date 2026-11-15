"""Buscador mundial de pasadas NISAR (2026-11-14).

Busca gránulos GCOV en cualquier rectángulo y rango de fechas sin descargar nada y sin cuenta, con dos recursos
oficiales del reto (Space Apps 2026, "Dancing with the SARs"):

- el catálogo CMR de NASA, el mismo que hay detrás de NASA Earthdata Search: huella, hora, tamaño y enlaces;
- las vistas previas de ASF (el archivo de Vertex): PNG públicas, sin cuenta y con CORS abierto (comprobado el
  2026-11-14 con `_LATLON.png`, 4,5 MB, redirección 303 a CloudFront y `Access-Control-Allow-Origin: *`).

El HDF5 de cada gránulo sigue pidiendo una cuenta de Earthdata: aquí solo se da su enlace.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol
from urllib.parse import quote

import httpx

from .cmr import BASE_URL, _footprint, data_url
from .pairing import Point, parse_title

COLLECTION = "NISAR_L2_GCOV_PROVISIONAL_V1"
CACHE_SECONDS = 600
MAX_RESULTS = 200


@dataclass(frozen=True)
class WorldGranule:
    id: str
    acquired_at: datetime
    track: int
    direction: str
    frame: int
    mode: str
    polarization: str
    size_mb: float
    footprint: tuple[Point, ...]
    data_url: str
    browse_url: str | None
    thumbnail_url: str | None
    collection_concept_id: str | None


@dataclass(frozen=True)
class WorldPage:
    total: int
    granules: list[WorldGranule] = field(default_factory=list)


class WorldSource(Protocol):
    def search(self, bbox: list[float], start: str, end: str, direction: str | None, limit: int) -> WorldPage: ...


def _browse(entry: dict) -> tuple[str | None, str | None]:
    """Vista previa en latitud/longitud y su miniatura, por HTTPS (no s3://)."""
    full = thumb = None
    for link in entry.get("links", []):
        href = link.get("href", "")
        if not link.get("rel", "").endswith("/browse#") or not href.startswith("https://"):
            continue
        if href.endswith("_LATLON_thumbnail.png"):
            thumb = href
        elif href.endswith("_LATLON.png"):
            full = href
    return full, thumb


def parse_entry(entry: dict) -> WorldGranule | None:
    granule = parse_title(entry["title"], float(entry.get("granule_size") or 0), _footprint(entry), data_url(entry))
    if granule is None:
        return None
    full, thumb = _browse(entry)
    return WorldGranule(
        id=granule.id,
        acquired_at=granule.acquired_at,
        track=granule.track,
        direction=granule.direction,
        frame=granule.frame,
        mode=granule.mode,
        polarization=granule.polarization,
        size_mb=granule.size_mb,
        footprint=granule.footprint,
        data_url=granule.download_url,
        browse_url=full,
        thumbnail_url=thumb,
        collection_concept_id=entry.get("collection_concept_id"),
    )


class CmrWorldSource:
    def __init__(self, client: httpx.Client | None = None):
        self._client = client or httpx.Client(timeout=60, headers={"User-Agent": "nisar-veredictos"})
        self._cache: dict[tuple, tuple[float, WorldPage]] = {}

    def search(self, bbox: list[float], start: str, end: str, direction: str | None, limit: int) -> WorldPage:
        key = (tuple(bbox), start, end, direction, limit)
        cached = self._cache.get(key)
        if cached and time.monotonic() - cached[0] < CACHE_SECONDS:
            return cached[1]
        params: dict[str, str | int] = {
            "short_name": COLLECTION,
            "bounding_box": ",".join(f"{v:.5f}" for v in bbox),
            "temporal": f"{start}T00:00:00Z,{end}T23:59:59Z",
            "page_size": limit,
            "sort_key": "-start_date",
        }
        response = self._client.get(BASE_URL, params=params)
        response.raise_for_status()
        entries = response.json()["feed"]["entry"]
        # La dirección se filtra aquí: en el título, "_A_" aparece también tras la polarización (DHDH_A_...),
        # así que un patrón de CMR no la distingue. `total` es el de CMR, sin ese filtro.
        granules = [g for g in (parse_entry(e) for e in entries) if g is not None and (not direction or g.direction == direction)]
        total = int(response.headers.get("CMR-Hits", len(granules)))
        page = WorldPage(total=total, granules=granules)
        self._cache[key] = (time.monotonic(), page)
        return page


def vertex_url(granule_id: str) -> str:
    """El gránulo en ASF Data Search Vertex, con búsqueda por lista."""
    return f"https://search.asf.alaska.edu/#/?searchType=List%20Search&searchList={quote(granule_id)}&resultsLoaded=true"


def earthdata_search_url(granule_id: str) -> str:
    """El gránulo en NASA Earthdata Search."""
    return f"https://search.earthdata.nasa.gov/search?q={quote(granule_id)}"


__all__ = ["CmrWorldSource", "WorldGranule", "WorldPage", "WorldSource", "earthdata_search_url", "vertex_url"]
