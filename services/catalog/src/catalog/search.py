"""Búsqueda de pasadas (T-ANT-16, RF-BUS-07): filtra la línea de tiempo de cada zona.

Es un índice derivado: cada fila sale de lo mismo que `/aois/{id}/timeline`, así que no puede contradecirla.
"""
from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime

# Letra que sigue al CRID en el nombre del gránulo: precisión de la órbita y del apuntamiento según la guía
# de ASF (P precisa, M media, N casi en tiempo real, F pronóstico). ORBIT_TYPE de CMR no coincide con ella.
_ORBIT = re.compile(r"_[A-Z]\d+_([PMNF])_")
ORBIT_PRECISIONS = ("P", "M", "N", "F")
KINDS = ("acquired", "excluded", "estimated")
SORTS = ("date", "-date", "latency", "-latency")


def orbit_precision(granule_id: str | None) -> str | None:
    match = _ORBIT.search(granule_id or "")
    return match[1] if match else None


@dataclass(frozen=True)
class PassRow:
    aoi: str
    series: str
    kind: str
    at: datetime
    track: int
    direction: str
    frame: int
    granule_id: str | None = None
    published_at: datetime | None = None
    latency_hours: float | None = None
    contains_aoi: bool | None = None
    excluded_reason: str | None = None
    plan_status: str = "unknown"

    @property
    def orbit_precision(self) -> str | None:
        return orbit_precision(self.granule_id)


@dataclass(frozen=True)
class PassQuery:
    series: tuple[str, ...] = ()
    start: date | None = None
    end: date | None = None
    direction: str | None = None
    min_latency_hours: float | None = None
    max_latency_hours: float | None = None
    orbit_precision: tuple[str, ...] = ()
    kind: tuple[str, ...] = ()
    plan: tuple[str, ...] = ()
    sort: str = "date"
    offset: int = 0
    limit: int = 50
    aoi: tuple[str, ...] = field(default=())

    def interpreted(self) -> dict:
        """La consulta tal como se aplicó, sin los valores por omisión vacíos."""
        out = {
            "aoi": list(self.aoi),
            "series": list(self.series),
            "from": self.start.isoformat() if self.start else None,
            "to": self.end.isoformat() if self.end else None,
            "direction": self.direction,
            "min_latency_hours": self.min_latency_hours,
            "max_latency_hours": self.max_latency_hours,
            "orbit_precision": list(self.orbit_precision),
            "kind": list(self.kind),
            "plan": list(self.plan),
            "sort": self.sort,
            "limit": self.limit,
        }
        return {key: value for key, value in out.items() if value not in (None, [])}


def _series_matches(series: str, wanted: tuple[str, ...]) -> bool:
    # Acepta el id completo (T048A-F015-4005-DHDH-P05023) o el corto de verdicts (T048A-F015).
    return not wanted or any(series == item or series.startswith(item + "-") for item in wanted)


def matches(row: PassRow, q: PassQuery) -> bool:
    day = row.at.date()
    if not _series_matches(row.series, q.series):
        return False
    if (q.start and day < q.start) or (q.end and day > q.end):
        return False
    if q.direction and row.direction != q.direction:
        return False
    if q.min_latency_hours is not None or q.max_latency_hours is not None:
        # Sin latencia (estimadas, o sin fecha de publicación) no se puede evaluar: no pasa el filtro.
        if row.latency_hours is None:
            return False
        if q.min_latency_hours is not None and row.latency_hours < q.min_latency_hours:
            return False
        if q.max_latency_hours is not None and row.latency_hours > q.max_latency_hours:
            return False
    if q.orbit_precision and row.orbit_precision not in q.orbit_precision:
        return False
    if q.kind and row.kind not in q.kind:
        return False
    if q.plan and row.plan_status not in q.plan:
        return False
    return True


def ordered(rows: list[PassRow], sort: str) -> list[PassRow]:
    by_date = sorted(rows, key=lambda row: (row.at, row.series, row.kind))
    if sort == "date":
        return by_date
    if sort == "-date":
        return list(reversed(by_date))
    known = [row for row in by_date if row.latency_hours is not None]
    unknown = [row for row in by_date if row.latency_hours is None]
    # Las filas sin latencia van siempre al final, en los dos sentidos.
    return sorted(known, key=lambda row: row.latency_hours, reverse=sort == "-latency") + unknown


def encode_cursor(offset: int) -> str:
    return base64.urlsafe_b64encode(json.dumps({"o": offset}).encode()).decode().rstrip("=")


def decode_cursor(cursor: str) -> int:
    """Desplazamiento del cursor opaco; ValueError si no es uno de los que da esta ruta."""
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        offset = json.loads(base64.urlsafe_b64decode(padded.encode()))["o"]
    except (ValueError, KeyError, TypeError) as error:
        raise ValueError("Cursor no válido") from error
    if not isinstance(offset, int) or offset < 0:
        raise ValueError("Cursor no válido")
    return offset


def search(rows: list[PassRow], q: PassQuery) -> tuple[list[PassRow], int, int | None]:
    """(página, total, desplazamiento siguiente o None)."""
    found = ordered([row for row in rows if matches(row, q)], q.sort)
    page = found[q.offset : q.offset + q.limit]
    following = q.offset + q.limit if q.offset + q.limit < len(found) else None
    return page, len(found), following
