"""Recalcula `signature_counts` de los manifiestos ya escritos a partir de sus propios COG (2026-11-15).

Las firmas de vegetación (`hv_up_hh_stable` y `hv_down_hh_stable`) se añadieron después de procesar Parral y las
zonas en línea, y antes caían en `other`. Las firmas solo dependen de los píxeles con cambio probable (`state`) y del
cambio en dB ya corregido por el desplazamiento de escena (`change_hh` y `change_hv`), que están en los artefactos:
no hace falta volver a leer NASA ni los recortes.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import rasterio

from .change import CHANGE_PROBABLE, signature_counts


def _read(path: Path) -> np.ndarray:
    with rasterio.open(path) as src:
        return src.read(1)


def resign_manifest(manifest_path: Path, artifact_root: Path) -> int:
    """Actualiza las firmas de cada par del manifiesto y devuelve cuántos pares cambió."""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    changed_pairs = 0
    for pair in manifest.get("pairs", []):
        layers = pair.get("layers") or {}
        try:
            state = _read(artifact_root / layers["state"])
            hh = _read(artifact_root / layers["change_hh"])
            hv = _read(artifact_root / layers["change_hv"])
        except (KeyError, OSError, rasterio.errors.RasterioIOError):
            continue
        mask = state == CHANGE_PROBABLE
        counts = signature_counts(hh[mask], hv[mask])
        if pair["stats"].get("signature_counts") != counts:
            pair["stats"]["signature_counts"] = counts
            changed_pairs += 1
    if changed_pairs:
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return changed_pairs


def resign_all(artifact_root: Path, aoi: str | None = None) -> dict[str, int]:
    pattern = f"{aoi}/*/manifest.json" if aoi else "*/*/manifest.json"
    return {str(p.relative_to(artifact_root)): resign_manifest(p, artifact_root) for p in sorted(artifact_root.glob(pattern))}
