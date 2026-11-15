"""Escenas ópticas Sentinel-2 L2A cercanas a una fecha, desde Earth Search, que es público y no requiere cuenta."""
from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time as dtime, timedelta, timezone
from typing import Protocol

import httpx

from .pairing import Point, parse_utc, point_in_polygon

SEARCH_URL = "https://earth-search.aws.element84.com/v1/search"
COLLECTION = "sentinel-2-l2a"
PAGE_SIZE = 100
CACHE_SECONDS = 3600
LICENSE_URL = "https://sentinel.esa.int/documents/247904/690755/Sentinel_Data_Legal_Notice"
# Puntos por lado de la rejilla con que se comprueba si las teselas cubren la zona.
COVERAGE_GRID = 5


@dataclass(frozen=True)
class Scene:
    id: str
    platform: str
    tile: str
    acquired_at: datetime
    cloud_cover: float
    visual_url: str
    footprint: tuple[Point, ...] = ()
    # Caja de los datos de la escena en WGS84, [oeste, sur, este, norte]; None si Earth Search no la da.
    bbox: tuple[float, float, float, float] | None = None

    @property
    def base_id(self) -> str:
        # S2C_13RCK_20260708_0_L2A -> S2C_13RCK_20260708: el número final es la versión de procesado.
        return self.id.rsplit("_", 2)[0]

    @property
    def sequence(self) -> int:
        try:
            return int(self.id.rsplit("_", 2)[1])
        except (IndexError, ValueError):
            return 0


@dataclass(frozen=True)
class Acquisition:
    platform: str
    acquired_at: datetime
    days_from_date: int
    covers_aoi: bool
    max_cloud_cover: float
    tiles: tuple[Scene, ...]


class SceneSource(Protocol):
    def scenes(self, bbox: list[float], start: datetime, end: datetime) -> list[Scene]: ...


def _parse_time(raw: str) -> datetime:
    return parse_utc(raw)


def _footprint(geometry: dict | None) -> tuple[Point, ...]:
    if not geometry or geometry.get("type") != "Polygon":
        return ()
    return tuple((float(lon), float(lat)) for lon, lat in geometry["coordinates"][0])


def _bbox(feature: dict, footprint: tuple[Point, ...]) -> tuple[float, float, float, float] | None:
    """La `bbox` del item STAC (la de su huella de datos); si falta, la de la huella. Nunca el cuadrado MGRS entero.

    Como en STAC, una caja con oeste > este cruza el antimeridiano y es válida; el mapa la desenrolla.
    """
    raw = feature.get("bbox")
    if isinstance(raw, list) and len(raw) == 4:
        try:
            west, south, east, north = (float(value) for value in raw)
        except (TypeError, ValueError):
            west = None
        if west is not None and south <= north and all(-180 <= lon <= 180 for lon in (west, east)):
            return (west, south, east, north)
    if footprint:
        lons = [lon for lon, _ in footprint]
        lats = [lat for _, lat in footprint]
        return (min(lons), min(lats), max(lons), max(lats))
    return None


def parse_feature(feature: dict) -> Scene | None:
    visual = feature.get("assets", {}).get("visual", {}).get("href", "")
    props = feature.get("properties", {})
    if not visual.startswith("https://") or "datetime" not in props:
        return None
    footprint = _footprint(feature.get("geometry"))
    return Scene(
        id=feature["id"],
        platform=props.get("platform", ""),
        tile=str(props.get("grid:code", "")).removeprefix("MGRS-"),
        acquired_at=_parse_time(props["datetime"]),
        cloud_cover=float(props.get("eo:cloud_cover", 100.0)),
        visual_url=visual,
        footprint=footprint,
        bbox=_bbox(feature, footprint),
    )


class EarthSearchSource:
    def __init__(self, client: httpx.Client | None = None):
        self._client = client or httpx.Client(timeout=60, headers={"User-Agent": "nisar-veredictos"})
        self._cache: dict[tuple, tuple[float, list[Scene]]] = {}

    def scenes(self, bbox: list[float], start: datetime, end: datetime) -> list[Scene]:
        key = (tuple(bbox), start, end)
        cached = self._cache.get(key)
        if cached and time.monotonic() - cached[0] < CACHE_SECONDS:
            return cached[1]
        result = self._fetch(bbox, start, end)
        self._cache[key] = (time.monotonic(), result)
        return result

    def _fetch(self, bbox: list[float], start: datetime, end: datetime) -> list[Scene]:
        body: dict | None = {
            "collections": [COLLECTION],
            "bbox": bbox,
            "datetime": f"{start:%Y-%m-%dT%H:%M:%SZ}/{end:%Y-%m-%dT%H:%M:%SZ}",
            "limit": PAGE_SIZE,
        }
        result: list[Scene] = []
        while body is not None:
            response = self._client.post(SEARCH_URL, json=body)
            response.raise_for_status()
            page = response.json()
            result.extend(scene for scene in map(parse_feature, page.get("features", [])) if scene)
            following = next((link for link in page.get("links", []) if link.get("rel") == "next"), None)
            body = following.get("body") if following else None
        return result


def window(day: date, days: int) -> tuple[datetime, datetime]:
    """Días completos en UTC, desde `day - days` hasta `day + days`, ambos incluidos."""
    start = datetime.combine(day - timedelta(days=days), dtime.min, tzinfo=timezone.utc)
    end = datetime.combine(day + timedelta(days=days), dtime.max.replace(microsecond=0), tzinfo=timezone.utc)
    return start, end


def _covers(bbox: list[float], footprints: list[tuple[Point, ...]]) -> bool:
    west, south, east, north = bbox
    steps = COVERAGE_GRID - 1
    for i in range(COVERAGE_GRID):
        for j in range(COVERAGE_GRID):
            lon = west + (east - west) * i / steps
            lat = south + (north - south) * j / steps
            if not any(fp and point_in_polygon(lon, lat, fp) for fp in footprints):
                return False
    return True


def group_acquisitions(scenes: list[Scene], bbox: list[float], day: date, max_cloud: float) -> list[Acquisition]:
    """Junta las teselas de un mismo satélite y día, y descarta las adquisiciones demasiado nubladas."""
    latest: dict[str, Scene] = {}
    for scene in scenes:
        kept = latest.get(scene.base_id)
        if kept is None or scene.sequence > kept.sequence:
            latest[scene.base_id] = scene

    groups: dict[tuple[str, date], list[Scene]] = defaultdict(list)
    for scene in latest.values():
        groups[(scene.platform, scene.acquired_at.date())].append(scene)

    result = []
    for (platform, acquired_day), tiles in groups.items():
        cloud = max(tile.cloud_cover for tile in tiles)
        if cloud > max_cloud:
            continue
        ordered = tuple(sorted(tiles, key=lambda tile: tile.tile))
        result.append(
            Acquisition(
                platform=platform,
                acquired_at=min(tile.acquired_at for tile in tiles),
                days_from_date=(acquired_day - day).days,
                covers_aoi=_covers(bbox, [tile.footprint for tile in tiles]),
                max_cloud_cover=cloud,
                tiles=ordered,
            )
        )
    return sorted(result, key=lambda acq: (abs(acq.days_from_date), acq.max_cloud_cover, acq.acquired_at))
