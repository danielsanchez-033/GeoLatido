"""Control de calidad de Eco en el veredicto (T-BAL-07, RF-BAL-09) y desplazamiento de la escena.

El manifiesto trae `dates[].qa` con la mediana de HH y HV de cada fecha. Con las dos fechas del par
se mide cuánto cambió el nivel de toda la escena: con la serie real, el porcentaje de cambio sigue a ese
desplazamiento (correlación 0,9, MEMORY.md), así que el veredicto lo avisa en vez de callarlo.
Es un aviso: no cambia el estado.
"""
from __future__ import annotations

from dataclasses import dataclass

# Mismo valor que qa_outlier_db de processor (Eco). Inicial y sin calibrar.
SCENE_SHIFT_DB = 1.5
RADIOMETRIC_OUTLIER = "radiometric_outlier"


@dataclass(frozen=True)
class SceneShift:
    hh_db: float | None
    hv_db: float | None
    same_direction: bool | None  # None si falta alguna polarización o alguna no se movió
    exceeds_threshold: bool
    # pair_stats: stats.scene_shift_* de processor (T-ECO-07), ya restado del cambio y de los umbrales.
    # qa_median_difference: diferencia de medianas del QA, sin restar de nada.
    basis: str = "qa_median_difference"
    corrected: bool = False


def qa_by_date(manifest: dict) -> dict[str, dict]:
    """Bloque qa de cada fecha. Las fechas sin qa (manifiestos anteriores a T-ECO-03) no aparecen."""
    return {item["date"]: item["qa"] for item in manifest["dates"] if item.get("qa")}


def _difference(before: dict, after: dict, name: str) -> float | None:
    first, second = before.get(f"median_{name}_db"), after.get(f"median_{name}_db")
    return None if first is None or second is None else second - first


def _shift(hh: float | None, hv: float | None, basis: str, corrected: bool) -> SceneShift:
    same = None
    if hh is not None and hv is not None and hh != 0 and hv != 0:
        same = (hh > 0) == (hv > 0)
    exceeds = any(value is not None and abs(value) > SCENE_SHIFT_DB for value in (hh, hv))
    return SceneShift(hh, hv, same, exceeds, basis, corrected)


def scene_shift(before: dict | None, after: dict | None, stats: dict | None = None) -> SceneShift | None:
    """Desplazamiento de toda la escena entre las dos fechas del par, por polarización.

    Si el par trae stats.scene_shift_* (processor desde T-ECO-07), se usa ese valor exacto, que processor
    ya restó del cambio: según el esquema del manifiesto, su presencia significa que se descontó. Si no,
    se aproxima con la diferencia de medianas del QA de cada fecha, sin restar de nada. None sin ninguno.
    """
    stats = stats or {}
    if "scene_shift_hh_db" in stats or "scene_shift_hv_db" in stats:
        return _shift(stats.get("scene_shift_hh_db"), stats.get("scene_shift_hv_db"), "pair_stats", True)
    if not before or not after:
        return None
    return _shift(_difference(before, after, "hh"), _difference(before, after, "hv"), "qa_median_difference", False)


def flagged(qa: dict | None) -> bool:
    return bool(qa) and RADIOMETRIC_OUTLIER in qa.get("flags", [])
