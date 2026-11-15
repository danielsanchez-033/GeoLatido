"""Agrupa gránulos GCOV en series que se pueden comparar entre sí."""
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timezone

_FRACTION = re.compile(r"\.(\d+)")


def parse_utc(raw: str) -> datetime:
    """Lee una hora ISO 8601 de CMR o de STAC y la devuelve en UTC.

    Sin zona se toma como UTC, que es la referencia que publican CMR y Earth Search. Con otra
    zona se convierte. Python 3.10 solo acepta fracciones de 3 o 6 cifras, así que se ajustan a 6.
    """
    text = _FRACTION.sub(lambda m: "." + (m[1] + "000000")[:6], raw.strip().replace("Z", "+00:00"), count=1)
    value = datetime.fromisoformat(text)
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


# Hueco permanente de adquisición publicado por ASF.
DATA_GAP = (date(2026, 7, 27), date(2026, 8, 10))

_TITLE = re.compile(
    r"GCOV_(?P<cycle>\d+)_(?P<track>\d+)_(?P<direction>[AD])_(?P<frame>\d+)_(?P<mode>\w{4})_(?P<polarization>\w{4})_"
    r"\w_(?P<start>\d{8}T\d{6})_\d{8}T\d{6}_(?P<crid>[A-Z]\d+)_"
)

Point = tuple[float, float]


@dataclass(frozen=True)
class Granule:
    id: str
    track: int
    direction: str
    frame: int
    mode: str
    polarization: str
    crid: str
    start: date
    acquired_at: datetime  # Inicio de la adquisición en UTC, tomado del nombre del gránulo.
    size_mb: float
    footprint: tuple[Point, ...] = ()
    download_url: str = ""
    published_at: datetime | None = None  # Última actualización en CMR; aproxima la publicación.

    @property
    def group_key(self) -> tuple:
        # Todo lo que debe coincidir para que una diferencia no sea un artefacto de procesado.
        return (self.track, self.direction, self.frame, self.mode, self.polarization, self.crid)


@dataclass(frozen=True)
class Series:
    id: str
    track: int
    direction: str
    frame: int
    mode: str
    polarization: str
    crid: str
    granules: tuple[Granule, ...]
    contains_aoi: bool
    max_gap_days: int
    spans_data_gap: bool

    @property
    def dates(self) -> list[date]:
        return [granule.start for granule in self.granules]

    @property
    def footprint_granule(self) -> Granule | None:
        """El gránulo más reciente con huella. Todos los de una serie son del mismo marco y casi iguales."""
        return next((granule for granule in reversed(self.granules) if len(granule.footprint) >= 3), None)


def closed_ring(points: tuple[Point, ...], decimals: int = 5) -> list[list[float]]:
    """Anillo GeoJSON [lon, lat] cerrado y con 5 decimales (constitución V.3)."""
    ring = [[round(lon, decimals), round(lat, decimals)] for lon, lat in points]
    if ring and ring[0] != ring[-1]:
        ring.append(list(ring[0]))
    return ring


def parse_title(
    title: str,
    size_mb: float = 0.0,
    footprint: tuple[Point, ...] = (),
    download_url: str = "",
    published_at: datetime | None = None,
) -> Granule | None:
    match = _TITLE.search(title)
    if not match:
        return None
    acquired_at = datetime.strptime(match["start"], "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)
    return Granule(
        id=title,
        track=int(match["track"]),
        direction=match["direction"],
        frame=int(match["frame"]),
        mode=match["mode"],
        polarization=match["polarization"],
        crid=match["crid"],
        start=acquired_at.date(),
        acquired_at=acquired_at,
        size_mb=size_mb,
        footprint=footprint,
        download_url=download_url,
        published_at=published_at,
    )


def point_in_polygon(lon: float, lat: float, polygon: tuple[Point, ...]) -> bool:
    inside = False
    for (x1, y1), (x2, y2) in zip(polygon, polygon[1:] + polygon[:1]):
        if (y1 > lat) != (y2 > lat) and lon < (x2 - x1) * (lat - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def _contains(polygon: tuple[Point, ...], bbox: list[float]) -> bool:
    west, south, east, north = bbox
    corners = [(west, south), (west, north), (east, south), (east, north)]
    return bool(polygon) and all(point_in_polygon(x, y, polygon) for x, y in corners)


def crosses_gap(first: date, second: date) -> bool:
    return first < DATA_GAP[1] and second > DATA_GAP[0]


def series_id(track: int, direction: str, frame: int, mode: str, polarization: str, crid: str) -> str:
    return f"T{track:03d}{direction}-F{frame:03d}-{mode}-{polarization}-{crid}"


def build_series(granules: list[Granule], bbox: list[float], min_dates: int = 2) -> list[Series]:
    groups: dict[tuple, dict[date, Granule]] = defaultdict(dict)
    for granule in granules:
        groups[granule.group_key].setdefault(granule.start, granule)

    result = []
    for (track, direction, frame, mode, polarization, crid), by_date in groups.items():
        if len(by_date) < min_dates:
            continue
        ordered = tuple(by_date[day] for day in sorted(by_date))
        pairs = list(zip(ordered, ordered[1:]))
        result.append(
            Series(
                id=series_id(track, direction, frame, mode, polarization, crid),
                track=track,
                direction=direction,
                frame=frame,
                mode=mode,
                polarization=polarization,
                crid=crid,
                granules=ordered,
                contains_aoi=all(_contains(granule.footprint, bbox) for granule in ordered),
                max_gap_days=max(((b.start - a.start).days for a, b in pairs), default=0),
                spans_data_gap=any(crosses_gap(a.start, b.start) for a, b in pairs),
            )
        )
    return sorted(result, key=lambda series: (-series.contains_aoi, -len(series.granules), series.id))
