"""Productos OPERA DSWx-S1 (agua superficial desde Sentinel-1) cercanos a una fecha.

Se buscan en CMR, que es público. Los archivos los distribuye PO.DAAC: los GeoTIFF piden
cuenta de Earthdata y la vista previa PNG no. `catalog` solo los lista, nunca lee sus píxeles.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Protocol

import httpx

from .optical import COVERAGE_GRID
from .pairing import parse_utc

BASE_URL = "https://cmr.earthdata.nasa.gov/search/granules.json"
COLLECTION = "OPERA_L3_DSWX-S1_V1"
DOI = "10.5067/OPDSWS1-L3V1"
PRODUCT_SPEC_URL = (
    "https://archive.podaac.earthdata.nasa.gov/podaac-ops-cumulus-docs/web-misc/opera/"
    "D-108761_OPERA_DSWx_S1AB_ProductSpec_Rev_A.pdf"
)
PUBLIC_BUCKET = "podaac-ops-cumulus-public"
# Límite de detección que declara el resumen de la colección en CMR (consultado el 2026-11-11).
MIN_WATER_BODY_HA = 3
MIN_WATER_BODY_WIDTH_M = 200
# Las teselas de una misma pasada distan segundos; dos pasadas del mismo día, horas.
PASS_TOLERANCE = timedelta(minutes=10)
PAGE_SIZE = 500
CACHE_SECONDS = 3600

TITLE = re.compile(
    r"^OPERA_L3_DSWx-S1_T(?P<tile>\d{2}[A-Z]{3})_(?P<acq>\d{8}T\d{6})Z_(?P<prod>\d{8}T\d{6})Z_"
    r"(?P<sensor>S1[A-Z])_30_v(?P<version>[\d.]+)$"
)

Box = tuple[float, float, float, float]  # oeste, sur, este, norte


@dataclass(frozen=True)
class OperaTile:
    id: str
    tile: str
    platform: str
    title_acquired_at: datetime
    acquired_at: datetime
    produced_at: datetime
    wtr_url: str
    conf_url: str
    browse_url: str | None
    box: Box | None = None


@dataclass(frozen=True)
class OperaPass:
    platform: str
    acquired_at: datetime
    days_from_date: int
    covers_aoi: bool
    tiles: tuple[OperaTile, ...]


class OperaSource(Protocol):
    def tiles(self, bbox: list[float], start: datetime, end: datetime) -> list[OperaTile]: ...


def _stamp(raw: str) -> datetime:
    return datetime.strptime(raw, "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)


def _box(entry: dict) -> Box | None:
    boxes = entry.get("boxes")
    if not boxes:
        return None
    south, west, north, east = (float(value) for value in boxes[0].split())  # CMR: "sur oeste norte este"
    return west, south, east, north


def _link(entry: dict, suffix: str, rel: str | None = None, bucket: str | None = None) -> str | None:
    for link in entry.get("links", []):
        href = link.get("href", "")
        if not href.startswith("https://") or not href.endswith(suffix):
            continue
        if rel and not link.get("rel", "").endswith(rel):
            continue
        if bucket and f"/{bucket}/" not in href:
            continue
        return href
    return None


def parse_entry(entry: dict) -> OperaTile | None:
    """Convierte una entrada de CMR en tesela. Devuelve None si no es DSWx-S1 o no trae la capa de agua."""
    title = entry.get("title", "")
    match = TITLE.match(title)
    if not match:
        return None
    wtr = _link(entry, "_B01_WTR.tif", rel="/data#")
    if not wtr:
        return None
    title_acquired = _stamp(match["acq"])
    raw_start = entry.get("time_start")
    return OperaTile(
        id=title,
        tile=match["tile"],
        platform=f"sentinel-{match['sensor'][1:].lower()}",
        title_acquired_at=title_acquired,
        acquired_at=parse_utc(raw_start) if raw_start else title_acquired,
        produced_at=_stamp(match["prod"]),
        wtr_url=wtr,
        conf_url=_link(entry, "_B03_CONF.tif", rel="/data#") or "",
        browse_url=_link(entry, "_BROWSE.png", bucket=PUBLIC_BUCKET),
        box=_box(entry),
    )


class CmrOperaSource:
    def __init__(self, client: httpx.Client | None = None):
        self._client = client or httpx.Client(timeout=90, headers={"User-Agent": "nisar-veredictos"})
        self._cache: dict[tuple, tuple[float, list[OperaTile]]] = {}

    def tiles(self, bbox: list[float], start: datetime, end: datetime) -> list[OperaTile]:
        key = (tuple(bbox), start, end)
        cached = self._cache.get(key)
        if cached and time.monotonic() - cached[0] < CACHE_SECONDS:
            return cached[1]
        result = self._fetch(bbox, start, end)
        self._cache[key] = (time.monotonic(), result)
        return result

    def _fetch(self, bbox: list[float], start: datetime, end: datetime) -> list[OperaTile]:
        result: list[OperaTile] = []
        page = 1
        while True:
            response = self._client.get(
                BASE_URL,
                params={
                    "short_name": COLLECTION,
                    "bounding_box": ",".join(str(value) for value in bbox),
                    "temporal": f"{start:%Y-%m-%dT%H:%M:%SZ},{end:%Y-%m-%dT%H:%M:%SZ}",
                    "page_size": PAGE_SIZE,
                    "page_num": page,
                },
            )
            response.raise_for_status()
            entries = response.json()["feed"]["entry"]
            result.extend(tile for tile in map(parse_entry, entries) if tile)
            if len(entries) < PAGE_SIZE:
                return result
            page += 1


def latest_versions(tiles: list[OperaTile]) -> list[OperaTile]:
    """Deja una tesela por (tesela, adquisición del título): la de producción más reciente."""
    latest: dict[tuple[str, datetime], OperaTile] = {}
    for tile in tiles:
        key = (tile.tile, tile.title_acquired_at)
        kept = latest.get(key)
        if kept is None or tile.produced_at > kept.produced_at:
            latest[key] = tile
    return list(latest.values())


def _covers(bbox: list[float], boxes: list[Box]) -> bool:
    west, south, east, north = bbox
    steps = COVERAGE_GRID - 1
    for i in range(COVERAGE_GRID):
        for j in range(COVERAGE_GRID):
            lon = west + (east - west) * i / steps
            lat = south + (north - south) * j / steps
            if not any(b[0] <= lon <= b[2] and b[1] <= lat <= b[3] for b in boxes):
                return False
    return True


def group_passes(tiles: list[OperaTile], bbox: list[float], day: date) -> list[OperaPass]:
    """Quita versiones repetidas y junta las teselas de una misma pasada de Sentinel-1."""
    ordered = sorted(latest_versions(tiles), key=lambda t: (t.platform, t.title_acquired_at))
    groups: list[list[OperaTile]] = []
    for tile in ordered:
        last = groups[-1][-1] if groups else None
        if last and last.platform == tile.platform and tile.title_acquired_at - last.title_acquired_at <= PASS_TOLERANCE:
            groups[-1].append(tile)
        else:
            groups.append([tile])

    result = []
    for group in groups:
        acquired_at = min(tile.acquired_at for tile in group)
        result.append(
            OperaPass(
                platform=group[0].platform,
                acquired_at=acquired_at,
                days_from_date=(acquired_at.date() - day).days,
                covers_aoi=_covers(bbox, [tile.box for tile in group if tile.box]),
                tiles=tuple(sorted(group, key=lambda t: t.tile)),
            )
        )
    return sorted(result, key=lambda p: (abs(p.days_from_date), p.acquired_at))
