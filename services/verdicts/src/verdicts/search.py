"""Búsqueda de veredictos (T-BAL-11, RF-BUS-01 y 03 a 05).

Cada fila sale de un veredicto completo ya calculado: copia sus campos y no redacta texto propio, así que nunca
afirma más que el veredicto. El índice se construye al arrancar y la consulta solo filtra, ordena y pagina en
memoria: con decenas o cientos de pares no hace falta una base de datos.
"""
from __future__ import annotations

import base64
import binascii
import datetime as dt
import hashlib
import json
import math
import re
import sqlite3
import threading
from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field

Role = Literal["public", "student", "researcher"]
ROLES: tuple[Role, ...] = ("public", "student", "researcher")
PAGE_LIMIT: dict[str, int] = {"student": 50, "researcher": 500}
DEFAULT_LIMIT = 50

# Filtros que solo puede usar researcher (RF-BUS-05: el estudiante no tiene los de calidad ni de ruido).
RESEARCHER_FILTERS = ("quality_flag", "noise_hh_min", "noise_hh_max", "noise_hv_min", "noise_hv_max")
# Ordenar por ruido es filtrar por ruido con otra forma: también solo researcher (T-BAL-14).
RESEARCHER_SORTS = ("noise_hh", "noise_hv")
NO_NOISE = "no_noise_stats"

SortKey = Literal["date", "interval", "changed_fraction", "noise_hh", "noise_hv"]
WaterFilter = Literal["agree", "disagree"]
WaterSummary = Literal["agree", "disagree", "not_available"]
CONTRAST_NOT_COMPUTED = "contrast_not_computed"


def role_from_header(value: str | None) -> Role:
    """X-Auth-Role lo pone el gateway y borra el del cliente. Cualquier otro valor cuenta como public."""
    return value if value in ROLES else "public"  # type: ignore[return-value]


class WaterSideRow(BaseModel):
    status: str = Field(description="evidence.water.<lado>.status del veredicto.")
    assessment: Literal["agree", "disagree"] | None
    compared_fraction: float | None = Field(description="Fracción de la zona comparada. null si no se comparó.")


class WaterRow(BaseModel):
    summary: WaterSummary = Field(
        description="disagree si alguna de las dos fechas del par sale disagree; agree si las dos salen agree; "
        "not_available en cualquier otro caso, también mientras el contraste con OPERA no está calculado o si "
        "verdicts no tiene token. disagree es un desacuerdo entre dos métodos, no dice cuál acierta."
    )
    reasons: list[str] = Field(
        description="Por qué no hay contraste en alguna fecha: los status distintos de compared, o "
        "contrast_not_computed si el índice aún no tiene el contraste. Vacía si las dos fechas se compararon."
    )
    before: WaterSideRow | None = Field(description="null mientras el contraste no está calculado.")
    after: WaterSideRow | None


class AreaRule(BaseModel):
    min_observed_fraction: float
    min_changed_fraction: float
    calibrated: bool = Field(False, description="Siempre false, como en evidence.decision_rule.")


class AreaResult(BaseModel):
    """Estado del par dentro del rectángulo con las celdas de 1 km de Eco (RF-BUS-10, P2; T-BAL-18)."""

    status: Literal["computed", "no_cells", "no_cells_in_bbox"] = Field(
        description="computed: hay celdas que tocan el rectángulo. no_cells: el manifiesto del par no trae celdas "
        "(artefactos anteriores a T-ECO-12 o malla no métrica). no_cells_in_bbox: ninguna celda del par toca el "
        "rectángulo."
    )
    basis: Literal["cells_touching_bbox"] = Field(
        "cells_touching_bbox", description="Se cuentan enteras las celdas de 1 km que tocan el rectángulo: el área "
        "evaluada es cells_bbox, que puede ser mayor que el rectángulo pedido."
    )
    state: Literal["change_probable", "no_detectable_change", "not_observable"] | None = Field(
        description="Misma regla que el veredicto, sobre las celdas. null si no hay celdas."
    )
    cause: str | None = Field(
        description="Con not_observable, la causa con más píxeles no observados entre las celdas que la declaran; "
        "null si ninguna la declara."
    )
    observed_fraction: float | None = Field(description="Píxeles observados entre píxeles de las celdas.")
    changed_fraction: float | None = Field(
        description="Píxeles con cambio entre píxeles observados: la fracción de cada celda ponderada por sus "
        "píxeles observados (pixels · observed_fraction)."
    )
    cells: int = Field(description="Celdas que tocan el rectángulo.")
    pixels: int = Field(description="Píxeles de esas celdas.")
    cells_bbox: list[float] | None = Field(description="Caja [oeste, sur, este, norte] de las celdas usadas.")
    decision_rule: AreaRule


class SearchResult(BaseModel):
    aoi: str
    series_id: str
    pair_id: str
    kind: Literal["consecutive", "full_window"]
    direction: str = Field(description="Dirección de la órbita de la serie: A ascendente, D descendente.")
    data_kind: Literal["real", "synthetic"] = Field(description="Nunca falta: los datos sintéticos lo dicen en cada fila.")
    state: Literal["change_probable", "no_detectable_change", "not_observable"]
    cause: str | None
    from_date: dt.date
    to_date: dt.date
    interval_days: int
    observed_fraction: float
    changed_fraction: float
    scene_shift_hh_db: float | None = Field(description="evidence.scene_shift.hh_db. null si el veredicto no lo trae.")
    scene_shift_hv_db: float | None
    scene_shift_exceeds_threshold: bool | None = Field(
        description="evidence.scene_shift.exceeds_threshold. null si el veredicto no trae desplazamiento."
    )
    flagged_dates: list[dt.date] = Field(
        description="Fechas del par con la bandera radiometric_outlier del QA de Eco (receipt.quality)."
    )
    optical_max_cloud_cover: float | None = Field(
        description="Mayor max_cloud_cover de las escenas ópticas de antes y después, por tesela. null si falta "
        "alguna de las dos escenas."
    )
    noise_hh_db: float | None = Field(
        description="evidence.noise.hh_db. null si el veredicto no trae ruido (manifiesto anterior a T-ECO-09)."
    )
    noise_hv_db: float | None = Field(description="evidence.noise.hv_db.")
    water: WaterRow
    granules: list[str] = Field(description="granule_id de las dos fechas, como en receipt.granules.")
    verdict_path: str = Field(
        description="Ruta del veredicto completo en esta API. Por el gateway lleva delante /api/verdicts."
    )
    area: AreaResult | None = Field(
        None,
        description="Solo con bbox: el par dentro del rectángulo con las celdas de 1 km de Eco (T-BAL-18). Es un "
        "cálculo aparte del veredicto, que sigue siendo de toda la zona; state y los filtros de la búsqueda miran "
        "el veredicto, no area.",
    )


class NotEvaluated(BaseModel):
    count: int = Field(description="Filas que el filtro dejó fuera porque no se podía evaluar en ellas.")
    reasons: dict[str, int] = Field(description="Cuántas filas por cada motivo.")


class SearchQuery(BaseModel):
    filters: dict[str, object] = Field(description="Filtros aplicados, tal como se interpretaron.")
    sort: SortKey
    order: Literal["asc", "desc"]
    limit: int
    role: Role
    not_evaluated: dict[str, NotEvaluated] = Field(
        description="Por filtro: filas que quedaron fuera porque el dato no existe (p. ej. water sin contraste)."
    )
    water_contrast: Literal["included", "pending"] = Field(
        description="pending: el índice aún no tiene el contraste con OPERA y todas las filas dicen not_available."
    )
    indexed_at: dt.datetime = Field(description="Cuándo se calcularon los veredictos del índice, en UTC.")


class SearchPage(BaseModel):
    total: int = Field(description="Resultados que cumplen la consulta, sumando todas las páginas.")
    results: list[SearchResult]
    next_cursor: str | None = Field(description="Cursor de la página siguiente. null en la última.")
    query: SearchQuery


class AccessDenied(BaseModel):
    detail: str
    required_role: Role


class InvalidCursor(ValueError):
    pass


@dataclass(frozen=True)
class Filters:
    aoi: str | None = None
    series_id: str | None = None
    direction: str | None = None
    kind: str | None = None
    date_from: dt.date | None = None
    date_to: dt.date | None = None
    interval_min: int | None = None
    interval_max: int | None = None
    state: tuple[str, ...] = ()
    cause: tuple[str, ...] = ()
    changed_min: float | None = None
    changed_max: float | None = None
    scene_shift_exceeds: bool | None = None
    quality_flag: bool | None = None
    water: str | None = None
    max_cloud_cover: float | None = None
    data_kind: str | None = None
    q: str | None = None
    lang: str | None = None
    bbox: tuple[float, float, float, float] | None = None
    noise_hh_min: float | None = None
    noise_hh_max: float | None = None
    noise_hv_min: float | None = None
    noise_hv_max: float | None = None

    def applied(self) -> dict[str, object]:
        result: dict[str, object] = {}
        for name, value in self.__dict__.items():
            if value is None or value == ():
                continue
            if isinstance(value, dt.date):
                value = value.isoformat()
            elif isinstance(value, tuple):
                value = list(value)
            result[name] = value
        return result


Key = tuple[str, str, str]  # zona, serie, par


def row_key(row: SearchResult) -> Key:
    return (row.aoi, row.series_id, row.pair_id)


# --- Texto libre (T-BAL-17, RF-BUS-02) ---------------------------------------------------------------------------

LANGS = ("es", "en")
MAX_TERMS = 12
_TERM = re.compile(r"[\w-]+", re.UNICODE)


def fts_query(text: str) -> str | None:
    """Consulta FTS5 segura: cada palabra entre comillas y con prefijo, unidas con AND. Ninguna sintaxis de FTS5
    del usuario llega a SQLite, así que no hay consultas que fallen ni operadores inesperados."""
    terms = [term.strip("-") for term in _TERM.findall(text)]
    terms = [term for term in terms if term][:MAX_TERMS]
    if not terms:
        return None
    return " AND ".join('"' + term.replace('"', "") + '"*' for term in terms)


def verdict_text(verdict) -> str:
    """Lo que se busca de un veredicto: sus textos, hipótesis, causa, gránulos y su identificador. Solo campos del
    propio veredicto, en el idioma en que se calculó."""
    summary = verdict.summary
    parts = [summary.detected, summary.does_not_prove, summary.missing, *verdict.hypotheses,
             verdict.cause or "", verdict.cause_label or "", verdict.id, verdict.series, *verdict.receipt.granules]
    return "\n".join(part for part in parts if part)


class TextIndex:
    """Índice FTS5 en memoria, uno por idioma. Sin acentos (remove_diacritics) y sin distinguir mayúsculas."""

    def __init__(self, docs: dict[str, dict[Key, str]]):
        self._lock = threading.Lock()
        self._db = sqlite3.connect(":memory:", check_same_thread=False)
        self._db.execute(
            "CREATE VIRTUAL TABLE docs USING fts5(aoi UNINDEXED, series UNINDEXED, pair UNINDEXED, lang UNINDEXED, "
            "body, tokenize = 'unicode61 remove_diacritics 2')"
        )
        self._db.executemany(
            "INSERT INTO docs VALUES (?, ?, ?, ?, ?)",
            [(*key, lang, body) for lang, items in docs.items() for key, body in items.items()],
        )

    def match(self, text: str, lang: str) -> set[Key]:
        query = fts_query(text)
        if query is None:
            return set()
        with self._lock:
            found = self._db.execute(
                "SELECT aoi, series, pair FROM docs WHERE docs MATCH ? AND lang = ?", (f"body : ({query})", lang)
            ).fetchall()
        return {tuple(row) for row in found}  # type: ignore[misc]


# --- Área (T-BAL-17, RF-BUS-10) ----------------------------------------------------------------------------------

BBox = tuple[float, float, float, float]
FOOTPRINT_UNAVAILABLE = "footprint_unavailable"
CATALOG_UNAVAILABLE = "catalog_unavailable"


def parse_bbox(text: str) -> BBox:
    """'oeste,sur,este,norte' en grados WGS84. ValueError con el motivo si no vale."""
    parts = text.split(",")
    if len(parts) != 4:
        raise ValueError("bbox lleva cuatro números: oeste,sur,este,norte")
    try:
        west, south, east, north = (float(part) for part in parts)
    except ValueError:
        raise ValueError("bbox lleva cuatro números: oeste,sur,este,norte") from None
    if not all(math.isfinite(v) for v in (west, south, east, north)):
        raise ValueError("bbox con valores no finitos")
    if not (-180 <= west <= 180 and -180 <= east <= 180 and -90 <= south <= 90 and -90 <= north <= 90):
        raise ValueError("bbox fuera de rango: longitud de -180 a 180 y latitud de -90 a 90")
    if west >= east or south >= north:
        raise ValueError("bbox con oeste >= este o sur >= norte (no se admite cruzar el antimeridiano)")
    return (west, south, east, north)


def _inside_ring(x: float, y: float, ring) -> bool:
    inside = False
    for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            inside = not inside
    return inside


def _cross(o, a, b) -> float:
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def _on_segment(p, a, b) -> bool:
    return min(a[0], b[0]) <= p[0] <= max(a[0], b[0]) and min(a[1], b[1]) <= p[1] <= max(a[1], b[1])


def _segments_meet(p1, p2, q1, q2) -> bool:
    d1, d2, d3, d4 = _cross(q1, q2, p1), _cross(q1, q2, p2), _cross(p1, p2, q1), _cross(p1, p2, q2)
    if ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0)) and 0 not in (d1, d2, d3, d4):
        return True
    return any(
        d == 0 and _on_segment(point, a, b)
        for d, point, a, b in ((d1, p1, q1, q2), (d2, p2, q1, q2), (d3, q1, p1, p2), (d4, q2, p1, p2))
    )


def bbox_meets_ring(bbox: BBox, ring) -> bool:
    """True si el rectángulo y el polígono se tocan o se cortan (también si uno contiene al otro)."""
    west, south, east, north = bbox
    if any(west <= x <= east and south <= y <= north for x, y in ring):
        return True
    corners = [(west, south), (east, south), (east, north), (west, north)]
    if any(_inside_ring(x, y, ring) for x, y in corners):
        return True
    edges = list(zip(corners, corners[1:] + corners[:1]))
    return any(_segments_meet(a, b, c, d) for a, b in zip(ring, ring[1:]) for c, d in edges)


def _cell_box(ring) -> BBox:
    xs = [x for x, _ in ring]
    ys = [y for _, y in ring]
    return (min(xs), min(ys), max(xs), max(ys))


def prepare_cells(collection: dict) -> list[tuple[BBox, tuple, dict]]:
    """Celdas de un GeoJSON de Eco con su caja precalculada, para descartar rápido las lejanas."""
    cells = []
    for feature in collection.get("features", []):
        ring = tuple(tuple(point[:2]) for point in feature["geometry"]["coordinates"][0])
        cells.append((_cell_box(ring), ring, feature["properties"]))
    return cells


def _boxes_meet(a: BBox, b: BBox) -> bool:
    return a[0] <= b[2] and b[0] <= a[2] and a[1] <= b[3] and b[1] <= a[3]


def area_result(bbox: BBox, cells: list[tuple[BBox, tuple, dict]] | None, min_observed: float, min_changed: float,
                causes: tuple[str, ...]) -> AreaResult:
    """Estado dentro del rectángulo con la regla del veredicto, sumando píxeles de las celdas que lo tocan."""
    rule = AreaRule(min_observed_fraction=min_observed, min_changed_fraction=min_changed)
    empty = dict(state=None, cause=None, observed_fraction=None, changed_fraction=None, cells=0, pixels=0,
                 cells_bbox=None, decision_rule=rule)
    if cells is None:
        return AreaResult(status="no_cells", **empty)
    used = [(box, props) for box, ring, props in cells if _boxes_meet(box, bbox) and bbox_meets_ring(bbox, ring)]
    if not used:
        return AreaResult(status="no_cells_in_bbox", **empty)
    pixels = sum(int(props["pixels"]) for _, props in used)
    observed = sum(int(props["pixels"]) * float(props["observed_fraction"]) for _, props in used)
    changed = sum(int(props["pixels"]) * float(props["observed_fraction"]) * float(props["changed_fraction"])
                  for _, props in used)
    observed_fraction = observed / pixels if pixels else 0.0
    changed_fraction = changed / observed if observed else 0.0
    cause = None
    if observed_fraction < min_observed:
        state = "not_observable"
        missing: dict[str, float] = {}
        for _, props in used:
            if props.get("cause"):
                missing[props["cause"]] = missing.get(props["cause"], 0.0) + int(props["pixels"]) * (
                    1 - float(props["observed_fraction"]))
        if missing:
            order_of = {name: i for i, name in enumerate(causes)}
            cause = max(missing, key=lambda name: (missing[name], -order_of.get(name, len(causes))))
    elif changed_fraction >= min_changed:
        state = "change_probable"
    else:
        state = "no_detectable_change"
    boxes = [box for box, _ in used]
    return AreaResult(
        status="computed", state=state, cause=cause, observed_fraction=round(observed_fraction, 6),
        changed_fraction=round(changed_fraction, 6), cells=len(used), pixels=pixels,
        cells_bbox=[min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes),
                    max(b[3] for b in boxes)],
        decision_rule=rule,
    )


@dataclass
class Index:
    rows: list[SearchResult]
    water_included: bool
    built_at: dt.datetime
    generation: int = 0
    errors: list[str] = field(default_factory=list)
    text: TextIndex | None = None
    # Serie de cada fila en catalog: (track, dirección, marco), para buscar su huella.
    series_keys: dict[tuple[str, str], tuple[int, str, int]] = field(default_factory=dict)
    # Caja de la zona de cada serie (bbox del manifiesto) y veredicto completo de cada fila, para exportar.
    series_bbox: dict[tuple[str, str], list[float]] = field(default_factory=dict)
    verdicts: dict = field(default_factory=dict)
    # Ruta relativa del GeoJSON de celdas de cada par (T-ECO-12); falta si el manifiesto no lo trae.
    cells_paths: dict[Key, str] = field(default_factory=dict)


def water_row(evidence, included: bool) -> WaterRow:
    """Resumen del contraste con OPERA de un veredicto. evidence es su evidence.water."""
    if not included:
        return WaterRow(summary="not_available", reasons=[CONTRAST_NOT_COMPUTED], before=None, after=None)
    sides = (evidence.before, evidence.after)
    rows = [
        WaterSideRow(
            status=side.status,
            assessment=side.assessment,
            compared_fraction=side.comparison.compared_fraction if side.comparison else None,
        )
        for side in sides
    ]
    assessments = [side.assessment for side in sides]
    if "disagree" in assessments:
        summary = "disagree"
    elif all(item == "agree" for item in assessments):
        summary = "agree"
    else:
        summary = "not_available"
    reasons = sorted({side.status for side in sides if side.status != "compared"})
    return WaterRow(summary=summary, reasons=reasons, before=rows[0], after=rows[1])


def row_from_verdict(verdict, water_included: bool) -> SearchResult:
    """Fila de búsqueda con los mismos valores que el veredicto completo."""
    evidence, receipt = verdict.evidence, verdict.receipt
    shift = evidence.scene_shift
    noise = evidence.noise
    scenes = (evidence.optical.before.scene, evidence.optical.after.scene)
    clouds = None if any(scene is None for scene in scenes) else max(scene.max_cloud_cover for scene in scenes)
    flagged = [
        item.date for item in (receipt.quality.before, receipt.quality.after)
        if item is not None and "radiometric_outlier" in item.flags
    ]
    return SearchResult(
        aoi=verdict.aoi,
        series_id=verdict.series,
        pair_id=verdict.id,
        kind=verdict.kind,
        direction=receipt.direction,
        data_kind=receipt.data_kind,
        state=verdict.state,
        cause=verdict.cause,
        from_date=verdict.from_date,
        to_date=verdict.to_date,
        interval_days=verdict.interval_days,
        observed_fraction=evidence.observed_fraction,
        changed_fraction=evidence.changed_fraction,
        scene_shift_hh_db=shift.hh_db if shift else None,
        scene_shift_hv_db=shift.hv_db if shift else None,
        scene_shift_exceeds_threshold=shift.exceeds_threshold if shift else None,
        flagged_dates=flagged,
        optical_max_cloud_cover=clouds,
        noise_hh_db=noise.hh_db if noise else None,
        noise_hv_db=noise.hv_db if noise else None,
        water=water_row(evidence.water, water_included),
        granules=list(receipt.granules),
        verdict_path=f"/aois/{verdict.aoi}/series/{verdict.series}/verdicts/{verdict.id}",
    )


def _between(value, low, high) -> bool:
    return (low is None or value >= low) and (high is None or value <= high)


def _noise_ok(row: SearchResult, filters: Filters, skip) -> bool:
    """Filtros de ruido. Una fila sin el valor pedido no se evalúa: queda fuera y se cuenta."""
    for name, value, low, high in (
        ("noise_hh", row.noise_hh_db, filters.noise_hh_min, filters.noise_hh_max),
        ("noise_hv", row.noise_hv_db, filters.noise_hv_min, filters.noise_hv_max),
    ):
        if low is None and high is None:
            continue
        if value is None:
            skip(name, NO_NOISE)
            return False
        if not _between(value, low, high):
            return False
    return True


def apply(
    rows: list[SearchResult],
    filters: Filters,
    text_hits: set[Key] | None = None,
    footprints: dict[tuple[str, str], tuple | str] | None = None,
) -> tuple[list[SearchResult], dict[str, NotEvaluated]]:
    """Filas que cumplen todos los filtros y, por filtro, las que no se pudieron evaluar.

    text_hits: claves que casan con el texto libre (None si no hay q). footprints: por (zona, serie), sus polígonos
    o el motivo por el que no hay huella; solo se mira con bbox."""
    kept: list[SearchResult] = []
    skipped: dict[str, NotEvaluated] = {}

    def skip(name: str, *reasons: str) -> None:
        """Una fila más sin evaluar; en water puede tener dos motivos, uno por fecha."""
        entry = skipped.setdefault(name, NotEvaluated(count=0, reasons={}))
        entry.count += 1
        for reason in reasons:
            entry.reasons[reason] = entry.reasons.get(reason, 0) + 1

    for row in rows:
        if filters.aoi is not None and row.aoi != filters.aoi:
            continue
        if filters.series_id is not None and row.series_id != filters.series_id:
            continue
        if filters.direction is not None and row.direction != filters.direction:
            continue
        if filters.kind is not None and row.kind != filters.kind:
            continue
        if filters.data_kind is not None and row.data_kind != filters.data_kind:
            continue
        if filters.date_from is not None and row.from_date < filters.date_from:
            continue
        if filters.date_to is not None and row.to_date > filters.date_to:
            continue
        if not _between(row.interval_days, filters.interval_min, filters.interval_max):
            continue
        if filters.state and row.state not in filters.state:
            continue
        if filters.cause and row.cause not in filters.cause:
            continue
        if not _between(row.changed_fraction, filters.changed_min, filters.changed_max):
            continue
        if filters.scene_shift_exceeds is not None:
            if row.scene_shift_exceeds_threshold is None:
                skip("scene_shift_exceeds", "no_scene_shift")
                continue
            if row.scene_shift_exceeds_threshold != filters.scene_shift_exceeds:
                continue
        if filters.quality_flag is not None and bool(row.flagged_dates) != filters.quality_flag:
            continue
        if filters.max_cloud_cover is not None:
            if row.optical_max_cloud_cover is None:
                skip("max_cloud_cover", "no_optical_scene")
                continue
            if row.optical_max_cloud_cover > filters.max_cloud_cover:
                continue
        if not _noise_ok(row, filters, skip):
            continue
        if text_hits is not None and row_key(row) not in text_hits:
            continue
        if filters.bbox is not None:
            found = (footprints or {}).get((row.aoi, row.series_id), FOOTPRINT_UNAVAILABLE)
            if isinstance(found, str):
                skip("bbox", found)
                continue
            if not any(bbox_meets_ring(filters.bbox, ring) for ring in found):
                continue
        if filters.water is not None:
            if row.water.summary == "not_available":
                skip("water", *(row.water.reasons or ["not_compared"]))
                continue
            if row.water.summary != filters.water:
                continue
        kept.append(row)
    return kept, skipped


def _sort_value(row: SearchResult, key: SortKey):
    if key == "noise_hh":
        return row.noise_hh_db
    if key == "noise_hv":
        return row.noise_hv_db
    if key == "interval":
        return row.interval_days
    if key == "changed_fraction":
        return row.changed_fraction
    return row.to_date


def order(rows: list[SearchResult], key: SortKey, direction: str) -> list[SearchResult]:
    """Orden estable: a igual valor, por zona, serie y par, siempre ascendente, para que el cursor no salte filas."""
    tie = sorted(rows, key=lambda row: (row.aoi, row.series_id, row.from_date, row.to_date, row.pair_id))
    known = [row for row in tie if _sort_value(row, key) is not None]
    unknown = [row for row in tie if _sort_value(row, key) is None]  # sin ruido: al final en los dos sentidos
    return sorted(known, key=lambda row: _sort_value(row, key), reverse=direction == "desc") + unknown


def fingerprint(filters: Filters, key: str, direction: str) -> str:
    text = json.dumps({"f": filters.applied(), "s": key, "o": direction}, sort_keys=True, default=str)
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def encode_cursor(offset: int, print_: str, generation: int) -> str:
    raw = json.dumps({"o": offset, "q": print_, "g": generation}, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_cursor(cursor: str, print_: str, generation: int) -> int:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        data = json.loads(base64.urlsafe_b64decode(padded.encode()))
        offset, query, gen = int(data["o"]), data["q"], int(data["g"])
    except (binascii.Error, ValueError, KeyError, TypeError) as exc:
        raise InvalidCursor("Cursor ilegible") from exc
    if query != print_:
        raise InvalidCursor("El cursor es de otra consulta: repite la consulta sin cursor")
    if gen != generation:
        raise InvalidCursor("El índice se recalculó desde esa página (p. ej. llegó el contraste con OPERA): "
                            "repite la consulta sin cursor")
    if offset < 0:
        raise InvalidCursor("Cursor ilegible")
    return offset
