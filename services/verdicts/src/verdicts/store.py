"""Acceso de solo lectura a los manifiestos y COGs que escribe processor."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import transform
from rasterio.windows import Window


class OutsideLayer(ValueError):
    """El punto pedido queda fuera de la capa."""


class Store:
    def __init__(self, root: Path):
        self.root = root

    def aois(self) -> list[str]:
        if not self.root.is_dir():
            return []
        # Solo zonas con al menos una serie terminada: un procesado en línea cancelado deja la carpeta sin manifiesto,
        # y listarla hacía que /aois/{id}/series diera 404.
        return sorted(
            path.name for path in self.root.iterdir() if path.is_dir() and any(path.glob("*/manifest.json"))
        )

    def manifests(self, aoi: str) -> list[dict]:
        # El id se compara con lo que existe, así nunca se usa la entrada del usuario como ruta.
        if aoi not in self.aois():
            return []
        result = []
        for path in sorted((self.root / aoi).glob("*/manifest.json")):
            result.append(json.loads(path.read_text(encoding="utf-8")))
        return result

    def sample(self, relative: str, lon: float, lat: float) -> float | None:
        """Devuelve el valor del píxel o None si es nulo; falla si el punto cae fuera de la capa."""
        with rasterio.open(self.root / relative) as dataset:
            xs, ys = transform("EPSG:4326", dataset.crs, [lon], [lat])
            row, col = dataset.index(xs[0], ys[0])
            if not (0 <= row < dataset.height and 0 <= col < dataset.width):
                raise OutsideLayer(relative)
            value = float(dataset.read(1, window=Window(col, row, 1, 1))[0, 0])
            if np.isnan(value) or (dataset.nodata is not None and value == dataset.nodata):
                return None
            return value
