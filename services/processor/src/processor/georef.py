"""Comprobación de la georreferencia con un rasgo conocido: el agua de un embalse (T-ECO-06).

El radar ve el agua tranquila muy oscura en HH y en HV; el óptico la ve con NDWI positivo. Con las
dos máscaras en la misma malla, se busca el desplazamiento entero que mejor las superpone (IoU).

Las máscaras no coinciden solo por geometría: orillas expuestas o suelo liso también salen oscuros
en radar, y el viento o la vegetación cambian lo que cada sensor llama agua. Por eso se comparan
solo los cuerpos de agua que aparecen en las dos, y el resultado tiene una resolución de un píxel.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

from .change import smooth, to_db

# Umbrales elegidos el 2026-11-12 mirando La Boquilla: el agua óptica tiene HV p95 = −22,5 dB y HH
# p95 = −14,0 dB; la tierra, HV p25 = −22,1 dB y HH p25 = −14,0 dB. No están calibrados en otra zona.
WATER_HV_MAX_DB = -23.0
WATER_HH_MAX_DB = -15.0
MIN_WATER_PIXELS = 5000


def large_components(mask: np.ndarray, min_pixels: int = MIN_WATER_PIXELS) -> np.ndarray:
    """Quita el ruido con una apertura y deja solo las manchas grandes."""
    opened = ndimage.binary_opening(mask, iterations=2)
    labels, _ = ndimage.label(opened)
    sizes = np.bincount(labels.ravel())
    keep = sizes >= min_pixels
    keep[0] = False
    return keep[labels]


def water_from_sar(
    hh: np.ndarray,
    hv: np.ndarray,
    valid: np.ndarray,
    window: int = 5,
    hh_max_db: float = WATER_HH_MAX_DB,
    hv_max_db: float = WATER_HV_MAX_DB,
    min_pixels: int = MIN_WATER_PIXELS,
) -> np.ndarray:
    """Agua donde HH y HV suavizados están por debajo de sus umbrales, en manchas grandes."""
    hh_db = to_db(smooth(hh.astype(np.float32), valid, window))
    hv_db = to_db(smooth(hv.astype(np.float32), valid, window))
    with np.errstate(invalid="ignore"):
        dark = valid & (hh_db < hh_max_db) & (hv_db < hv_max_db)
    return large_components(dark, min_pixels)


def water_from_ndwi(green: np.ndarray, nir: np.ndarray, threshold: float = 0.0) -> np.ndarray:
    """Agua por NDWI de McFeeters: (verde − NIR) / (verde + NIR) > umbral."""
    green = green.astype(np.float64)
    nir = nir.astype(np.float64)
    total = green + nir
    with np.errstate(divide="ignore", invalid="ignore"):
        ndwi = np.where(total > 0, (green - nir) / total, np.nan)
    return np.isfinite(ndwi) & (ndwi > threshold)


def shared_components(mask: np.ndarray, other: np.ndarray, min_overlap: float = 0.5) -> np.ndarray:
    """Deja las manchas de `mask` que tienen al menos `min_overlap` de su área dentro de `other`."""
    labels, _ = ndimage.label(mask)
    total = np.bincount(labels.ravel())
    inside = np.bincount(labels.ravel(), weights=other.ravel().astype(np.float64))
    keep = inside >= min_overlap * total
    keep[0] = False
    return keep[labels]


def shift_mask(mask: np.ndarray, rows: int, cols: int) -> np.ndarray:
    """Mueve una máscara un número entero de píxeles (positivo: abajo y a la derecha), rellenando con False."""
    out = np.zeros_like(mask)
    src_r = slice(max(0, -rows), mask.shape[0] - max(0, rows))
    dst_r = slice(max(0, rows), mask.shape[0] - max(0, -rows))
    src_c = slice(max(0, -cols), mask.shape[1] - max(0, cols))
    dst_c = slice(max(0, cols), mask.shape[1] - max(0, -cols))
    out[dst_r, dst_c] = mask[src_r, src_c]
    return out


def agreement(a: np.ndarray, b: np.ndarray) -> float:
    """Intersección sobre unión de dos máscaras booleanas."""
    union = np.count_nonzero(a | b)
    return np.count_nonzero(a & b) / union if union else 1.0


def best_shift(moving: np.ndarray, reference: np.ndarray, radius: int = 5) -> tuple[int, int, dict]:
    """Desplazamiento entero (filas, columnas) de `moving` que maximiza su IoU con `reference`.

    Devuelve también la tabla completa {(filas, columnas): IoU}, para ver si el máximo es nítido.
    """
    if moving.shape != reference.shape:
        raise ValueError("Las dos máscaras deben tener la misma malla")
    table = {
        (rows, cols): agreement(shift_mask(moving, rows, cols), reference)
        for rows in range(-radius, radius + 1)
        for cols in range(-radius, radius + 1)
    }
    rows, cols = max(table, key=lambda key: (table[key], -abs(key[0]) - abs(key[1])))
    return rows, cols, table
