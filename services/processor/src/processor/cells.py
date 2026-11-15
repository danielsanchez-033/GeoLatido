"""Celdas de 1 km por par, para buscar por rectángulo sin leer el COG en cada consulta (T-ECO-12, RF-BUS-10).

Cada celda da la fracción observable y la de cambio dentro de lo observado, y un estado con la misma regla que
el veredicto de Balanza: una celda con poco observable sale `not_observable` y no 0 % de cambio (constitución II).
Las celdas se alinean con múltiplos de 1 km de la proyección de la escena, así que dos series en la misma zona
UTM comparten celdas. El polígono se reproyecta a WGS84 desde sus esquinas: no es una caja en lon/lat.
"""
from __future__ import annotations

import math

import numpy as np
from rasterio.crs import CRS
from rasterio.transform import Affine
from rasterio.warp import transform as reproject_points

from .change import CHANGE_PROBABLE, NO_CHANGE, STATE_CODES, STATE_NODATA

CELL_SIZE_M = 1000.0
# Copia de services/verdicts/src/verdicts/rules.py (los servicios no importan código entre sí). Si Balanza los
# cambia, hay que cambiarlos aquí; el GeoJSON los publica para que se pueda comprobar con qué regla salió.
MIN_OBSERVED_FRACTION = 0.5
MIN_CHANGED_FRACTION = 0.05
# Mismo orden que UNOBSERVABLE_CAUSES de Balanza: en un empate gana la primera.
UNOBSERVABLE_CAUSES = ("outside_scene", "invalid_or_partial", "input_exception", "low_looks", "no_data", "terrain")
COORDINATE_DECIMALS = 6


def _groups(centres: np.ndarray, size: float) -> tuple[np.ndarray, np.ndarray]:
    """Índice de celda de cada fila o columna y dónde empieza cada grupo contiguo."""
    index = np.floor(centres / size).astype(np.int64)
    starts = np.flatnonzero(np.r_[True, index[1:] != index[:-1]])
    return index[starts], starts


def _decide(counts: dict[str, int]) -> tuple[str, str | None, float, float]:
    observed = counts["no_change"] + counts["change_probable"]
    total = sum(counts.values())
    observed_fraction = observed / total if total else 0.0
    changed_fraction = counts["change_probable"] / observed if observed else 0.0
    if observed_fraction < MIN_OBSERVED_FRACTION:
        cause = max(UNOBSERVABLE_CAUSES, key=lambda name: counts.get(name, 0))
        return "not_observable", cause, observed_fraction, changed_fraction
    state = "change_probable" if changed_fraction >= MIN_CHANGED_FRACTION else "no_detectable_change"
    return state, None, observed_fraction, changed_fraction


def cell_features(state: np.ndarray, transform: Affine, crs, size: float = CELL_SIZE_M) -> dict | None:
    """FeatureCollection de celdas con datos; None si la malla no está en metros (CRS geográfico)."""
    crs = CRS.from_user_input(crs)
    if crs.is_geographic or transform.b or transform.d:
        return None
    rows, cols = state.shape
    xs = transform.c + (np.arange(cols) + 0.5) * transform.a
    ys = transform.f + (np.arange(rows) + 0.5) * transform.e
    col_cells, col_starts = _groups(xs, size)
    row_cells, row_starts = _groups(ys, size)
    left, top = transform.c, transform.f
    right, bottom = left + cols * transform.a, top + rows * transform.e
    x_min, x_max = sorted((left, right))
    y_min, y_max = sorted((top, bottom))

    features, rings = [], []
    row_ends = np.r_[row_starts[1:], rows]
    for row_cell, start, end in zip(row_cells, row_starts, row_ends):
        band = state[start:end]
        # Píxeles de cada estado por columna de celda: una banda de ~100 filas cada vez, sin índices de toda la escena.
        per_code = {
            name: np.add.reduceat((band == code).sum(axis=0), col_starts) for name, code in STATE_CODES.items()
        }
        for position, col_cell in enumerate(col_cells):
            counts = {name: int(values[position]) for name, values in per_code.items()}
            if not sum(counts.values()):
                continue  # solo STATE_NODATA: la celda queda fuera de la escena recortada
            decision, cause, observed_fraction, changed_fraction = _decide(counts)
            # La celda recortada a la extensión de la escena, para no prometer área que no se procesó.
            west, east = max(col_cell * size, x_min), min((col_cell + 1) * size, x_max)
            south, north = max(row_cell * size, y_min), min((row_cell + 1) * size, y_max)
            rings.append(([west, east, east, west, west], [south, south, north, north, south]))
            features.append(
                {
                    "type": "Feature",
                    "properties": {
                        "id": f"{col_cell}_{row_cell}",
                        "state": decision,
                        "cause": cause,
                        "observed_fraction": round(observed_fraction, 4),
                        "changed_fraction": round(changed_fraction, 4),
                        "pixels": sum(counts.values()),
                    },
                }
            )
    if features:
        flat_x = [x for ring_x, _ in rings for x in ring_x]
        flat_y = [y for _, ring_y in rings for y in ring_y]
        lons, lats = reproject_points(crs, "EPSG:4326", flat_x, flat_y)
        for number, feature in enumerate(features):
            ring = [
                [round(lons[i], COORDINATE_DECIMALS), round(lats[i], COORDINATE_DECIMALS)]
                for i in range(number * 5, number * 5 + 5)
            ]
            feature["geometry"] = {"type": "Polygon", "coordinates": [ring]}
    return {
        "type": "FeatureCollection",
        "cell_size_m": size,
        "source_crs": crs.to_string(),
        "rules": {"min_observed_fraction": MIN_OBSERVED_FRACTION, "min_changed_fraction": MIN_CHANGED_FRACTION},
        "features": features,
    }
