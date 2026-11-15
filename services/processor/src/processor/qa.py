"""Control de calidad por fecha: avisa de fechas sospechosas antes de interpretar un cambio."""
from __future__ import annotations

import numpy as np

from .change import Params, observable, to_db
from .gcov import Scene

RADIOMETRIC_OUTLIER = "radiometric_outlier"


def _median_db(power: np.ndarray, valid: np.ndarray) -> float | None:
    # La mediana conserva el orden, así que da lo mismo en lineal que en dB: no viola el promedio en lineal.
    values = power[valid]
    return float(to_db(np.median(values))) if values.size else None


def _deviation(value: float | None, reference: float | None) -> float | None:
    return None if value is None or reference is None else value - reference


def _series_median(values: list[float | None]) -> float | None:
    present = [value for value in values if value is not None]
    return float(np.median(present)) if present else None


def scene_stats(scene: Scene, params: Params = Params()) -> dict:
    """Cifras de una sola fecha. Son pequeñas: se guardan sin retener la escena."""
    valid = observable(scene, params)
    return {
        "valid_fraction": float(np.count_nonzero(valid) / valid.size) if valid.size else 0.0,
        "median_hh_db": _median_db(scene.hh, valid),
        "median_hv_db": _median_db(scene.hv, valid),
    }


def date_qa(scenes: list[Scene], params: Params = Params()) -> list[dict]:
    """Devuelve el bloque `qa` de cada escena, en el mismo orden."""
    return finalize_qa([scene_stats(scene, params) for scene in scenes], params)


def finalize_qa(per_date: list[dict], params: Params = Params()) -> list[dict]:
    """Añade desviaciones y banderas a las cifras de cada fecha.

    La desviación se mide contra la mediana de las medianas de la serie. Una fecha desviada es
    una bandera, no una exclusión: puede ser un cambio real de toda la escena, como una lluvia general.
    """
    references = {name: _series_median([item[f"median_{name}_db"] for item in per_date]) for name in ("hh", "hv")}
    result = []
    for item in per_date:
        deviations = {
            f"deviation_{name}_db": _deviation(item[f"median_{name}_db"], references[name]) for name in ("hh", "hv")
        }
        outlier = any(value is not None and abs(value) > params.qa_outlier_db for value in deviations.values())
        result.append({**item, **deviations, "flags": [RADIOMETRIC_OUTLIER] if outlier else []})
    return result
