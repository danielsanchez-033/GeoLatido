"""Filtro multitemporal de speckle (Quegan y Yu, 2001), opcional (T-ECO-08).

Para cada fecha k:  J_k = <I_k> · (1/N) · Σ_i I_i / <I_i>

donde <·> es la media local en una ventana. Cada fecha conserva su media local, pero la textura
fina sale del promedio de todas las fechas, así que el speckle baja con el número de fechas.

Precio: mezcla información entre fechas. Un cambio fuerte en una fecha aparece atenuado (1/N) en la
textura de las demás. Por eso es opcional y el manifiesto lo declara cuando se usa.

Se hace en dos pasadas para no tener más de una escena en memoria: `add` acumula Σ I_i / <I_i> fecha
a fecha y `apply` filtra cada escena cuando el pipeline la vuelve a leer.
"""
from __future__ import annotations

import numpy as np

from .change import smooth
from .gcov import Scene


class MultitemporalFilter:
    def __init__(self, shape: tuple[int, int], window: int = 7):
        self.window = window
        self.ratio = {"hh": np.zeros(shape, np.float32), "hv": np.zeros(shape, np.float32)}
        self.count = np.zeros(shape, np.uint16)

    def add(self, scene: Scene, valid: np.ndarray) -> None:
        """Suma I / <I> de una fecha en los píxeles válidos."""
        for name, total in self.ratio.items():
            power = getattr(scene, name)
            mean = smooth(power, valid, self.window)
            with np.errstate(divide="ignore", invalid="ignore"):
                ratio = np.where(valid & (mean > 0), power / mean, 0).astype(np.float32)
            total += ratio
        self.count += valid.astype(np.uint16)

    def apply(self, scene: Scene, valid: np.ndarray) -> Scene:
        """Sustituye HH y HV de la escena por su versión filtrada; fuera de `valid` no toca nada."""
        usable = valid & (self.count > 0)
        for name, total in self.ratio.items():
            power = getattr(scene, name)
            mean = smooth(power, valid, self.window)
            with np.errstate(divide="ignore", invalid="ignore"):
                filtered = mean * total / np.maximum(self.count, 1)
            setattr(scene, name, np.where(usable & np.isfinite(filtered), filtered, power).astype(np.float32))
        return scene


def equivalent_looks(power: np.ndarray, valid: np.ndarray, block: int = 15) -> float:
    """Mediana del número equivalente de looks (media² / varianza) en bloques de `block` × `block`.

    En zonas homogéneas mide cuánto speckle queda: más alto es menos ruido. La mediana de todos los
    bloques es una medida tosca, porque la textura real también cuenta como varianza.
    """
    rows = power.shape[0] // block * block
    cols = power.shape[1] // block * block
    tiles = power[:rows, :cols].reshape(rows // block, block, cols // block, block).swapaxes(1, 2)
    ok = valid[:rows, :cols].reshape(rows // block, block, cols // block, block).swapaxes(1, 2).all(axis=(2, 3))
    tiles = tiles[ok].reshape(-1, block * block).astype(np.float64)
    if not len(tiles):
        return float("nan")
    mean = tiles.mean(axis=1)
    var = tiles.var(axis=1)
    enl = np.where(var > 0, mean**2 / var, np.nan)
    return float(np.nanmedian(enl))
