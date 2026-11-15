"""Variantes de escritura COG para una capa de ≈ 3400 × 3100 px (2026-11-15)."""
import tempfile
import time
from pathlib import Path

import numpy as np
import rasterio
import rasterio.shutil
from rasterio.io import MemoryFile
from rasterio.transform import Affine

rng = np.random.default_rng(1)
data = rng.normal(0, 1, (3437, 3135)).astype(np.float32)
profile = {"driver": "GTiff", "height": data.shape[0], "width": data.shape[1], "count": 1, "dtype": "float32",
           "crs": "EPSG:32614", "transform": Affine(10, 0, 0, 0, -10, 0), "nodata": float("nan")}


def disco(path, **opts):
    with tempfile.TemporaryDirectory() as t, rasterio.Env(GDAL_CACHEMAX=64):
        src = Path(t) / "raw.tif"
        with rasterio.open(src, "w", **profile) as d:
            d.write(data, 1)
        rasterio.shutil.copy(src, path, driver="COG", compress="DEFLATE", overview_resampling="average", **opts)


def memoria(path, **opts):
    with rasterio.Env(GDAL_CACHEMAX=64), MemoryFile() as mem:
        with mem.open(**profile) as d:
            d.write(data, 1)
        with mem.open() as d:
            rasterio.shutil.copy(d, path, driver="COG", compress="DEFLATE", overview_resampling="average", **opts)


with tempfile.TemporaryDirectory() as d:
    for nombre, fn, opts in (("actual (disco)", disco, {}), ("memoria", memoria, {}),
                             ("memoria + hilos", memoria, {"num_threads": "ALL_CPUS"}),
                             ("memoria + hilos + nivel 1", memoria, {"num_threads": "ALL_CPUS", "level": 1}),
                             ("memoria + hilos + predictor 3", memoria, {"num_threads": "ALL_CPUS", "predictor": 3})):
        t = time.monotonic()
        p = Path(d) / f"{len(nombre)}.tif"
        fn(p, **opts)
        print(f"{nombre:32} {time.monotonic() - t:5.1f} s  {p.stat().st_size / 1e6:6.1f} MB")
