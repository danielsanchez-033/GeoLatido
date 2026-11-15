"""Exportación de la búsqueda de veredictos (T-BAL-13, RF-BUS-06).

Cada fila sale del veredicto completo ya calculado, como en la búsqueda: copia sus campos y no redacta texto propio.
Lleva lo necesario para citarlo: `data_kind`, los dos `granule_id`, `interval_days`, la regla de decisión con sus
umbrales y `calibrated`, y los supuestos declarados. La consulta, el perfil y la hora van en `metadata` (JSON y
GeoJSON) y en cabeceras HTTP (los tres formatos). Se emite en streaming, fila a fila.
"""
from __future__ import annotations

import csv
import datetime as dt
import io
import json
from collections.abc import Iterable, Iterator
from typing import Literal

Format = Literal["csv", "geojson", "json"]
MEDIA_TYPES: dict[str, str] = {
    "csv": "text/csv; charset=utf-8",
    "geojson": "application/geo+json",
    "json": "application/json",
}
EXTENSIONS = {"csv": "csv", "geojson": "geojson", "json": "json"}
EXPORT_VERSION = 1

# Orden de las columnas del CSV. Las listas van unidas con " | ".
COLUMNS = (
    "aoi", "series_id", "pair_id", "kind", "direction", "data_kind", "maturity", "state", "cause",
    "from_date", "to_date", "interval_days", "granule_from", "granule_to",
    "observed_fraction", "changed_fraction", "min_observed_fraction", "min_changed_fraction", "decision_calibrated",
    "threshold_hh_db", "threshold_hv_db", "mean_change_hh_db", "mean_change_hv_db",
    "scene_shift_hh_db", "scene_shift_hv_db", "scene_shift_corrected", "scene_shift_exceeds_threshold",
    "noise_hh_db", "noise_hv_db", "flagged_dates", "excluded_passes", "optical_max_cloud_cover",
    "water_summary", "water_reasons", "assumptions", "verdict_path",
)
LIST_SEPARATOR = " | "


def assumptions(verdict) -> list[dict]:
    """Supuestos declarados del veredicto: los umbrales y reglas que usa y que no se han contrastado con verdad de
    campo. Todos los valores salen del propio veredicto."""
    evidence = verdict.evidence
    rule = evidence.decision_rule
    items = [
        {"name": "min_observed_fraction", "value": rule.min_observed_fraction, "unit": "fraction",
         "calibrated": rule.calibrated, "source": "evidence.decision_rule"},
        {"name": "min_changed_fraction", "value": rule.min_changed_fraction, "unit": "fraction",
         "calibrated": rule.calibrated, "source": "evidence.decision_rule"},
    ]
    if evidence.scene_shift is not None:
        items.append({"name": "scene_shift_threshold_db", "value": evidence.scene_shift.threshold_db, "unit": "dB",
                      "calibrated": evidence.scene_shift.calibrated, "source": "evidence.scene_shift"})
    optical = evidence.optical
    items.append({"name": "optical_max_cloud_cover", "value": optical.max_cloud_cover, "unit": "%",
                  "calibrated": False, "source": "evidence.optical"})
    items.append({"name": "optical_search_days", "value": optical.search_days, "unit": "days",
                  "calibrated": False, "source": "evidence.optical"})
    radar = evidence.water.radar_rule
    items.append({"name": "radar_water_hh_db_below", "value": radar.hh_db_below, "unit": "dB",
                  "calibrated": radar.calibrated, "source": "evidence.water.radar_rule"})
    items.append({"name": "radar_water_hv_db_below", "value": radar.hv_db_below, "unit": "dB",
                  "calibrated": radar.calibrated, "source": "evidence.water.radar_rule"})
    if evidence.noise is not None:
        items.append({"name": "noise_is_not_instrument_noise", "value": evidence.noise.caveat, "unit": None,
                      "calibrated": evidence.noise.calibrated, "source": "evidence.noise"})
    return items


def _assumption_text(item: dict) -> str:
    unit = f" {item['unit']}" if item["unit"] and item["unit"] != "fraction" else ""
    state = "calibrado" if item["calibrated"] else "sin calibrar"
    return f"{item['name']}={item['value']}{unit} ({state})"


def record(row, verdict) -> dict:
    """Una fila exportada: la fila de búsqueda más lo del veredicto completo que hace falta para citarlo."""
    evidence, receipt = verdict.evidence, verdict.receipt
    shift = evidence.scene_shift
    granules = list(receipt.granules)
    return {
        "aoi": row.aoi,
        "series_id": row.series_id,
        "pair_id": row.pair_id,
        "kind": row.kind,
        "direction": row.direction,
        "data_kind": row.data_kind,
        "maturity": receipt.maturity,
        "state": row.state,
        "cause": row.cause,
        "from_date": row.from_date.isoformat(),
        "to_date": row.to_date.isoformat(),
        "interval_days": row.interval_days,
        "granule_from": granules[0] if granules else None,
        "granule_to": granules[-1] if granules else None,
        "observed_fraction": row.observed_fraction,
        "changed_fraction": row.changed_fraction,
        "min_observed_fraction": evidence.decision_rule.min_observed_fraction,
        "min_changed_fraction": evidence.decision_rule.min_changed_fraction,
        "decision_calibrated": evidence.decision_rule.calibrated,
        "threshold_hh_db": evidence.threshold_hh_db,
        "threshold_hv_db": evidence.threshold_hv_db,
        "mean_change_hh_db": evidence.mean_change_hh_db,
        "mean_change_hv_db": evidence.mean_change_hv_db,
        "scene_shift_hh_db": row.scene_shift_hh_db,
        "scene_shift_hv_db": row.scene_shift_hv_db,
        "scene_shift_corrected": shift.corrected if shift else None,
        "scene_shift_exceeds_threshold": row.scene_shift_exceeds_threshold,
        "noise_hh_db": row.noise_hh_db,
        "noise_hv_db": row.noise_hv_db,
        "flagged_dates": [day.isoformat() for day in row.flagged_dates],
        "excluded_passes": [item.id for item in receipt.excluded_passes],
        "optical_max_cloud_cover": row.optical_max_cloud_cover,
        "water_summary": row.water.summary,
        "water_reasons": list(row.water.reasons),
        "assumptions": assumptions(verdict),
        "verdict_path": row.verdict_path,
    }


def _csv_value(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return LIST_SEPARATOR.join(_assumption_text(item) if isinstance(item, dict) else str(item) for item in value)
    return str(value)


def _csv_line(values: Iterable) -> str:
    buffer = io.StringIO()
    csv.writer(buffer, lineterminator="\r\n").writerow([_csv_value(value) for value in values])
    return buffer.getvalue()


def stream_csv(records: Iterable[dict]) -> Iterator[str]:
    """CSV con BOM para que las hojas de cálculo lean bien los acentos. La consulta va en las cabeceras HTTP."""
    yield "﻿" + _csv_line(COLUMNS)
    for item in records:
        yield _csv_line(item[column] for column in COLUMNS)


def _dumps(value) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def stream_json(metadata: dict, records: Iterable[dict]) -> Iterator[str]:
    yield '{"metadata":' + _dumps(metadata) + ',"results":['
    for i, item in enumerate(records):
        yield ("," if i else "") + _dumps(item)
    yield "]}"


def bbox_polygon(bbox) -> dict | None:
    """Polígono de la caja de la zona [oeste, sur, este, norte]. El veredicto es de toda la zona, no de un punto."""
    if not bbox or len(bbox) != 4:
        return None
    west, south, east, north = bbox
    return {"type": "Polygon", "coordinates": [[[west, south], [east, south], [east, north], [west, north],
                                                [west, south]]]}


def stream_geojson(metadata: dict, records: Iterable[tuple[dict, dict | None]]) -> Iterator[str]:
    """FeatureCollection; cada Feature lleva la caja de la zona del veredicto como geometría. metadata va como
    miembro propio de la colección (RFC 7946, 6.1)."""
    yield '{"type":"FeatureCollection","metadata":' + _dumps(metadata) + ',"features":['
    for i, (item, geometry) in enumerate(records):
        feature = {"type": "Feature", "id": f"{item['aoi']}/{item['series_id']}/{item['pair_id']}",
                   "geometry": geometry, "properties": item}
        yield ("," if i else "") + _dumps(feature)
    yield "]}"


def headers(fmt: str, metadata: dict, now: dt.datetime) -> dict[str, str]:
    """Cabeceras con la consulta y el recibo resumido; en ASCII, como exige HTTP."""
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    return {
        "Content-Disposition": f'attachment; filename="veredictos-{stamp}.{EXTENSIONS[fmt]}"',
        "X-Export-Total": str(metadata["total"]),
        "X-Export-Query": json.dumps(metadata["query"], ensure_ascii=True, separators=(",", ":"), default=str),
        "X-Export-Data-Kinds": ",".join(metadata["data_kinds"]) or "none",
        "X-Export-Generated-At": metadata["generated_at"],
    }
