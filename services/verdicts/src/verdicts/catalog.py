"""Cliente HTTP de catalog (Antena): línea de tiempo y escenas ópticas. Nunca importa código de catalog."""
from __future__ import annotations

import datetime as dt
import math
import time
from dataclasses import dataclass
from typing import Callable, Protocol

import httpx

# Tiempos cortos: si catalog tarda, el veredicto sale igual y dice que falta la latencia.
TIMEOUT_SECONDS = 3.0
CACHE_SECONDS = 600
FAILURE_CACHE_SECONDS = 60


class CatalogUnavailable(RuntimeError):
    """catalog no respondió o devolvió algo que no se puede leer."""


@dataclass(frozen=True)
class PassTime:
    acquired_at: dt.datetime
    published_at: dt.datetime | None
    latency_hours: float | None


@dataclass(frozen=True)
class ExcludedPass:
    """Pasada que existe en CMR pero Antena declaró inservible (excluded[] de la línea de tiempo)."""

    id: str
    series: str
    date: dt.date
    reason: str
    evidence: str


class TimelineSource(Protocol):
    def passes(self, aoi: str) -> dict[str, PassTime]:
        """Pasadas de la zona por id de gránulo. Lanza CatalogUnavailable si no hay respuesta."""

    def excluded(self, aoi: str) -> list[ExcludedPass]:
        """Pasadas excluidas por catalog. Lanza CatalogUnavailable si no hay respuesta."""


def granule_key(granule_id: str) -> str:
    """El id de CMR y el de identification/granuleId pueden diferir solo en la extensión."""
    return granule_id.removesuffix(".h5")


def utc_time(value: str) -> dt.datetime:
    """Lee una hora ISO 8601 de catalog. fromisoformat solo acepta la "Z" desde Python 3.11."""
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))


def _parse(body: dict) -> tuple[dict[str, PassTime], list[ExcludedPass]]:
    result = {}
    for item in body["passes"]:
        published = item.get("published_at")
        result[granule_key(item["granule_id"])] = PassTime(
            acquired_at=utc_time(item["acquired_at"]),
            published_at=utc_time(published) if published else None,
            latency_hours=item.get("latency_hours"),
        )
    # excluded[] llegó con T-ANT (PR 22); un catalog anterior no lo trae y cuenta como lista vacía.
    excluded = [
        ExcludedPass(
            id=granule_key(item["id"]),
            series=item["series"],
            date=dt.date.fromisoformat(item["date"]),
            reason=item["reason"],
            evidence=item.get("evidence", ""),
        )
        for item in body.get("excluded", [])
    ]
    return result, excluded


class HttpTimeline:
    """Lee GET {base}/aois/{aoi}/timeline y guarda el resultado unos minutos."""

    def __init__(self, base_url: str, client: httpx.Client | None = None, monotonic: Callable[[], float] = time.monotonic):
        self.base_url = base_url.rstrip("/")
        self.client = client or httpx.Client(timeout=TIMEOUT_SECONDS)
        self.monotonic = monotonic
        self._cache: dict[str, tuple[float, tuple[dict[str, PassTime], list[ExcludedPass]] | None]] = {}

    def _timeline(self, aoi: str) -> tuple[dict[str, PassTime], list[ExcludedPass]]:
        now = self.monotonic()
        cached = self._cache.get(aoi)
        if cached and cached[0] > now:
            if cached[1] is None:
                raise CatalogUnavailable(aoi)
            return cached[1]
        try:
            response = self.client.get(f"{self.base_url}/aois/{aoi}/timeline")
            response.raise_for_status()
            result = _parse(response.json())
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            self._cache[aoi] = (now + FAILURE_CACHE_SECONDS, None)
            raise CatalogUnavailable(aoi) from exc
        self._cache[aoi] = (now + CACHE_SECONDS, result)
        return result

    def passes(self, aoi: str) -> dict[str, PassTime]:
        return self._timeline(aoi)[0]

    def excluded(self, aoi: str) -> list[ExcludedPass]:
        return self._timeline(aoi)[1]


# --- T-BAL-04: escenas Sentinel-2 de catalog ---------------------------------------------

# Earth Search puede tardar varios segundos en la primera consulta; catalog la guarda una hora.
OPTICAL_TIMEOUT_SECONDS = 15.0


@dataclass(frozen=True)
class OpticalTile:
    tile: str
    cloud_cover: float
    visual_url: str
    # Caja de los datos de la escena (no del cuadrado MGRS), [oeste, sur, este, norte]; None si catalog no la da.
    bbox: tuple[float, float, float, float] | None = None


@dataclass(frozen=True)
class OpticalAcquisition:
    platform: str
    acquired_at: dt.datetime
    covers_aoi: bool
    max_cloud_cover: float
    tiles: tuple[OpticalTile, ...]


@dataclass(frozen=True)
class OpticalReference:
    source: str
    collection: str
    license: str
    license_url: str
    attribution: str
    acquisitions: tuple[OpticalAcquisition, ...]


class OpticalSource(Protocol):
    def scenes(self, aoi: str, day: dt.date, days: int) -> OpticalReference:
        """Todas las adquisiciones a ±days de day, sin filtrar nubes. Lanza CatalogUnavailable si no hay respuesta."""


def _parse_optical(body: dict) -> OpticalReference:
    acquisitions = []
    for item in body["acquisitions"]:
        tiles = tuple(
            OpticalTile(
                tile=str(tile["tile"]),
                cloud_cover=float(tile["cloud_cover"]),
                visual_url=tile["visual_url"],
                bbox=_tile_bbox(tile.get("bbox")),
            )
            for tile in item["tiles"]
            if str(tile["visual_url"]).startswith("https://")
        )
        if not tiles:
            continue
        acquisitions.append(
            OpticalAcquisition(
                platform=item["platform"],
                acquired_at=utc_time(item["acquired_at"]),
                covers_aoi=bool(item["covers_aoi"]),
                max_cloud_cover=float(item["max_cloud_cover"]),
                tiles=tiles,
            )
        )
    return OpticalReference(
        source=body["source"],
        collection=body["collection"],
        license=body["license"],
        license_url=body["license_url"],
        attribution=body["attribution"],
        acquisitions=tuple(acquisitions),
    )


class HttpOptical:
    """Lee GET {base}/aois/{aoi}/references/optical sin límite de nubes; la selección la hace verdicts."""

    def __init__(
        self, base_url: str, client: httpx.Client | None = None, monotonic: Callable[[], float] = time.monotonic
    ):
        self.base_url = base_url.rstrip("/")
        self.client = client or httpx.Client(timeout=OPTICAL_TIMEOUT_SECONDS)
        self.monotonic = monotonic
        self._cache: dict[tuple[str, dt.date, int], tuple[float, OpticalReference | None]] = {}

    def scenes(self, aoi: str, day: dt.date, days: int) -> OpticalReference:
        key = (aoi, day, days)
        now = self.monotonic()
        cached = self._cache.get(key)
        if cached and cached[0] > now:
            if cached[1] is None:
                raise CatalogUnavailable(aoi)
            return cached[1]
        try:
            response = self.client.get(
                f"{self.base_url}/aois/{aoi}/references/optical",
                params={"date": day.isoformat(), "days": days, "max_cloud": 100},
            )
            response.raise_for_status()
            result = _parse_optical(response.json())
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            self._cache[key] = (now + FAILURE_CACHE_SECONDS, None)
            raise CatalogUnavailable(aoi) from exc
        self._cache[key] = (now + CACHE_SECONDS, result)
        return result


# --- T-BAL-08: productos OPERA DSWx-S1 de catalog -----------------------------------------

# CMR puede tardar en la primera consulta; catalog la guarda una hora.
OPERA_TIMEOUT_SECONDS = 15.0


@dataclass(frozen=True)
class OperaTile:
    id: str
    tile: str
    wtr_url: str
    browse_url: str | None
    bbox: tuple[float, float, float, float] | None = None


def _tile_bbox(value) -> tuple[float, float, float, float] | None:
    """[oeste, sur, este, norte] en WGS84, tal como llega de catalog, o None si falta o no es válida.

    No se reordena: si oeste > este, la tesela cruza el antimeridiano y quien dibuja debe partirla.
    """
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        return None
    try:
        west, south, east, north = (float(item) for item in value)
    except (TypeError, ValueError):
        return None
    if not all(math.isfinite(item) for item in (west, south, east, north)):
        return None
    if not (-180 <= west <= 180 and -180 <= east <= 180 and -90 <= south < north <= 90):
        return None
    return (west, south, east, north)


@dataclass(frozen=True)
class OperaAcquisition:
    platform: str
    acquired_at: dt.datetime
    covers_aoi: bool
    tiles: tuple[OperaTile, ...]


@dataclass(frozen=True)
class OperaReference:
    source: str
    collection: str
    doi: str
    attribution: str
    product_spec_url: str
    min_water_body_ha: float
    min_water_body_width_m: float
    acquisitions: tuple[OperaAcquisition, ...]


class OperaSource(Protocol):
    def products(self, aoi: str, day: dt.date, days: int) -> OperaReference:
        """Pasadas DSWx-S1 a ±days de day. Lanza CatalogUnavailable si no hay respuesta."""


def _parse_opera(body: dict) -> OperaReference:
    acquisitions = []
    for item in body["acquisitions"]:
        tiles = tuple(
            OperaTile(
                id=str(tile["id"]),
                tile=str(tile["tile"]),
                wtr_url=tile["wtr_url"],
                browse_url=tile.get("browse_url") if str(tile.get("browse_url") or "").startswith("https://") else None,
                bbox=_tile_bbox(tile.get("bbox")),
            )
            for tile in item["tiles"]
            if str(tile["wtr_url"]).startswith("https://")
        )
        if not tiles:
            continue
        acquisitions.append(
            OperaAcquisition(
                platform=item["platform"],
                acquired_at=utc_time(item["acquired_at"]),
                covers_aoi=bool(item["covers_aoi"]),
                tiles=tiles,
            )
        )
    return OperaReference(
        source=body["source"],
        collection=body["collection"],
        doi=body["doi"],
        attribution=body["attribution"],
        product_spec_url=body["product_spec_url"],
        min_water_body_ha=float(body["min_water_body_ha"]),
        min_water_body_width_m=float(body["min_water_body_width_m"]),
        acquisitions=tuple(acquisitions),
    )


class HttpOpera:
    """Lee GET {base}/aois/{aoi}/references/opera; la elección del producto la hace verdicts."""

    def __init__(
        self, base_url: str, client: httpx.Client | None = None, monotonic: Callable[[], float] = time.monotonic
    ):
        self.base_url = base_url.rstrip("/")
        self.client = client or httpx.Client(timeout=OPERA_TIMEOUT_SECONDS)
        self.monotonic = monotonic
        self._cache: dict[tuple[str, dt.date, int], tuple[float, OperaReference | None]] = {}

    def products(self, aoi: str, day: dt.date, days: int) -> OperaReference:
        key = (aoi, day, days)
        now = self.monotonic()
        cached = self._cache.get(key)
        if cached and cached[0] > now:
            if cached[1] is None:
                raise CatalogUnavailable(aoi)
            return cached[1]
        try:
            response = self.client.get(
                f"{self.base_url}/aois/{aoi}/references/opera", params={"date": day.isoformat(), "days": days}
            )
            response.raise_for_status()
            result = _parse_opera(response.json())
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            self._cache[key] = (now + FAILURE_CACHE_SECONDS, None)
            raise CatalogUnavailable(aoi) from exc
        self._cache[key] = (now + CACHE_SECONDS, result)
        return result


# --- T-BAL-17: huella de cada serie (T-ANT-17) -------------------------------------------

Ring = tuple[tuple[float, float], ...]


@dataclass(frozen=True)
class Footprint:
    """Huella de una serie de catalog: polígonos con su anillo exterior (lon, lat). None si CMR no da polígono."""

    track: int
    direction: str
    frame: int
    polygons: tuple[Ring, ...] | None


class FootprintSource(Protocol):
    def footprints(self, aoi: str) -> list[Footprint]:
        """Huellas de las series de la zona. Lanza CatalogUnavailable si no hay respuesta."""


def _ring(points) -> Ring:
    ring = tuple((float(lon), float(lat)) for lon, lat, *_ in points)
    if len(ring) < 4 or not all(math.isfinite(v) for point in ring for v in point):
        raise ValueError("anillo no válido")
    return ring


def _polygons(feature) -> tuple[Ring, ...] | None:
    """Anillos exteriores de un Polygon o MultiPolygon. Los huecos se ignoran: la huella queda por exceso."""
    if not feature:
        return None
    geometry = feature["geometry"]
    if geometry["type"] == "Polygon":
        return (_ring(geometry["coordinates"][0]),)
    if geometry["type"] == "MultiPolygon":
        return tuple(_ring(polygon[0]) for polygon in geometry["coordinates"])
    raise ValueError(f"geometría no admitida: {geometry['type']}")


def _parse_footprints(body) -> list[Footprint]:
    return [
        Footprint(
            track=int(item["track"]), direction=item["direction"], frame=int(item["frame"]),
            polygons=_polygons(item.get("footprint")),
        )
        for item in body
    ]


class HttpFootprints:
    """Lee GET {base}/aois/{aoi}/series y guarda las huellas unos minutos."""

    def __init__(self, base_url: str, client: httpx.Client | None = None, monotonic: Callable[[], float] = time.monotonic):
        self.base_url = base_url.rstrip("/")
        # /series consulta CMR en catalog: más margen que la línea de tiempo.
        self.client = client or httpx.Client(timeout=OPTICAL_TIMEOUT_SECONDS)
        self.monotonic = monotonic
        self._cache: dict[str, tuple[float, list[Footprint] | None]] = {}

    def footprints(self, aoi: str) -> list[Footprint]:
        now = self.monotonic()
        cached = self._cache.get(aoi)
        if cached and cached[0] > now:
            if cached[1] is None:
                raise CatalogUnavailable(aoi)
            return cached[1]
        try:
            response = self.client.get(f"{self.base_url}/aois/{aoi}/series")
            response.raise_for_status()
            result = _parse_footprints(response.json())
        except (httpx.HTTPError, ValueError, KeyError, TypeError, IndexError) as exc:
            self._cache[aoi] = (now + FAILURE_CACHE_SECONDS, None)
            raise CatalogUnavailable(aoi) from exc
        self._cache[aoi] = (now + CACHE_SECONDS, result)
        return result
