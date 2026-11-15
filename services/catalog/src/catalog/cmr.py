"""Cliente mínimo del catálogo CMR de NASA, que es público y no requiere cuenta."""
from __future__ import annotations

import time
from datetime import datetime
from typing import Protocol

import httpx

from .pairing import Granule, Point, parse_title, parse_utc

BASE_URL = "https://cmr.earthdata.nasa.gov/search/granules.json"
PAGE_SIZE = 500
CACHE_SECONDS = 3600


class GranuleSource(Protocol):
    def granules(self, collection: str, bbox: list[float], start: str, end: str) -> list[Granule]: ...


def _footprint(entry: dict) -> tuple[Point, ...]:
    polygons = entry.get("polygons")
    if not polygons:
        return ()
    raw = polygons[0][0].split()  # CMR entrega "lat lon lat lon ..."
    return tuple((float(raw[i + 1]), float(raw[i])) for i in range(0, len(raw) - 1, 2))


def updated_at(entry: dict) -> datetime | None:
    """Fecha de última actualización del gránulo en CMR, en UTC.

    Comprobado el 2026-11-10: en la revisión 1 coincide con la fecha `Insert` de UMM-G,
    unos minutos después de la producción. Si ASF reprocesa el gránulo, se desplaza.
    """
    raw = entry.get("updated")
    if not raw:
        return None
    return parse_utc(raw)


def data_url(entry: dict) -> str:
    """Devuelve el enlace HTTPS del HDF5 principal, sin productos de calidad ni S3."""
    for link in entry.get("links", []):
        href = link.get("href", "")
        if link.get("rel", "").endswith("/data#") and href.startswith("https://") and href.endswith(".h5"):
            return href
    return ""


class CmrSource:
    def __init__(self, client: httpx.Client | None = None):
        self._client = client or httpx.Client(timeout=90, headers={"User-Agent": "nisar-veredictos"})
        self._cache: dict[tuple, tuple[float, list[Granule]]] = {}

    def granules(self, collection: str, bbox: list[float], start: str, end: str) -> list[Granule]:
        key = (collection, tuple(bbox), start, end)
        cached = self._cache.get(key)
        if cached and time.monotonic() - cached[0] < CACHE_SECONDS:
            return cached[1]
        result = self._fetch(collection, bbox, start, end)
        self._cache[key] = (time.monotonic(), result)
        return result

    def _fetch(self, collection: str, bbox: list[float], start: str, end: str) -> list[Granule]:
        result: list[Granule] = []
        page = 1
        while True:
            response = self._client.get(
                BASE_URL,
                params={
                    "short_name": collection,
                    "bounding_box": ",".join(str(value) for value in bbox),
                    "temporal": f"{start}T00:00:00Z,{end}T00:00:00Z",
                    "page_size": PAGE_SIZE,
                    "page_num": page,
                },
            )
            response.raise_for_status()
            entries = response.json()["feed"]["entry"]
            for entry in entries:
                granule = parse_title(
                    entry["title"],
                    float(entry.get("granule_size") or 0),
                    _footprint(entry),
                    data_url(entry),
                    updated_at(entry),
                )
                if granule:
                    result.append(granule)
            if len(entries) < PAGE_SIZE:
                return result
            page += 1
