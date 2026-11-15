"""Mide el desplazamiento de georreferencia entre un recorte GCOV y una escena Sentinel-2 L2A (T-ECO-06).

Uso (necesita red para leer Sentinel-2 desde Earth Search; no necesita token):

    python bench/georref.py --sar data/raw/real/boquilla/T048A-F015/<granulo>.h5 \\
        --stac https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a/items/S2C_13RDL_20260618_0_L2A

Compara la máscara de agua del radar (HV) con la del óptico (NDWI) en la malla del recorte.
"""
from __future__ import annotations

import argparse
import json
import urllib.request
from pathlib import Path

import h5py
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import transform_bounds
from rasterio.windows import from_bounds

from processor.change import Params, observable
from processor.gcov import read_scene
from processor.georef import agreement, best_shift, large_components, shared_components, water_from_ndwi, water_from_sar

# Clases SCL que no se usan: sin datos, saturado, sombra de nube, nubes y cirros.
SCL_EXCLUDED = (0, 1, 3, 8, 9, 10)


def _read_optical(href: str, scene, shape, resampling=Resampling.nearest) -> np.ndarray:
    bounds = rasterio.transform.array_bounds(*shape, scene.transform)
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR"), rasterio.open(href) as dataset:
        if dataset.crs.to_string() != scene.crs:
            raise SystemExit(f"CRS distinto: {dataset.crs} frente a {scene.crs}")
        window = from_bounds(*bounds, transform=dataset.transform)
        return dataset.read(1, window=window, out_shape=shape, resampling=resampling, boundless=True, fill_value=0)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sar", type=Path, required=True)
    parser.add_argument("--stac", required=True, help="URL del ítem STAC de Sentinel-2 L2A")
    parser.add_argument("--min-looks", type=float, default=4.0)
    args = parser.parse_args()

    with h5py.File(args.sar, "r") as handle:
        bbox = [float(v) for v in handle.attrs["subset_bbox"]]
    scene = read_scene(args.sar, bbox)
    shape = scene.hh.shape

    with urllib.request.urlopen(args.stac, timeout=60) as response:
        item = json.load(response)
    assets = item["assets"]
    green = _read_optical(assets["green"]["href"], scene, shape)
    nir = _read_optical(assets["nir"]["href"], scene, shape)
    scl = _read_optical(assets["scl"]["href"], scene, shape)

    radar_valid = observable(scene, Params(min_window_looks=args.min_looks * 25))
    optical_valid = (green > 0) & (nir > 0) & ~np.isin(scl, SCL_EXCLUDED)
    valid = radar_valid & optical_valid

    radar_water = water_from_sar(scene.hh, scene.hv, radar_valid) & valid
    optical_water = large_components(water_from_ndwi(green, nir) & valid)
    radar_shared = shared_components(radar_water, optical_water)
    optical_shared = shared_components(optical_water, radar_water)

    rows, cols, table = best_shift(radar_shared, optical_shared)
    pixel = abs(scene.transform.a)
    west, south, east, north = transform_bounds(scene.crs, "EPSG:4326", *rasterio.transform.array_bounds(*shape, scene.transform))
    half = shape[1] // 2
    halves = {}
    for name, columns in (("west", slice(0, half)), ("east", slice(half, None))):
        r, c, _ = best_shift(radar_shared[:, columns], optical_shared[:, columns], radius=3)
        halves[name] = {"rows": r, "cols": c}
    result = {
        "granule": scene.meta.granule_id,
        "optical": item["id"],
        "optical_datetime": item["properties"]["datetime"],
        "crs": scene.crs,
        "shape": list(shape),
        "bounds_wgs84": [round(v, 5) for v in (west, south, east, north)],
        "valid_fraction": round(float(valid.mean()), 4),
        "water_pixels": {
            "radar": int(radar_water.sum()),
            "optical": int(optical_water.sum()),
            "radar_shared": int(radar_shared.sum()),
            "optical_shared": int(optical_shared.sum()),
        },
        "iou_all_water": round(agreement(radar_water, optical_water), 4),
        "best_shift_px": {"rows": rows, "cols": cols},
        "best_shift_m": {"north": -rows * pixel, "east": cols * pixel},
        "iou_shared": {"no_shift": round(table[(0, 0)], 4), "best": round(table[(rows, cols)], 4)},
        "iou_shared_rows_-2..2_cols_-2..2": [[round(table[(r, c)], 4) for c in range(-2, 3)] for r in range(-2, 3)],
        "best_shift_by_half_px": halves,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
