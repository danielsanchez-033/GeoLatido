"""Genera archivos HDF5 falsos con la estructura GCOV. Nunca representan la realidad."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import h5py
import numpy as np
import rasterio
from rasterio.transform import from_origin
from rasterio.warp import transform_bounds
from scipy import ndimage

from .gcov import GRID, IDENTIFICATION
from .terrain import DEM_KIND_TAG

POSTING_M = 200.0
LOOKS = 20.0
EPSG = 32613


@dataclass(frozen=True)
class SeriesSpec:
    track: int
    direction: str
    frame: int
    dates: tuple[str, ...]


# Fechas reales de CMR para Parral: la cadencia es verdadera, los valores no. Sin el 2026-08-13 de T171,
# excluido en config/aois/parral.yaml por un defecto del producto: la demo muestra los mismos pares que los datos reales.
PARRAL_SERIES = (
    SeriesSpec(48, "A", 15, ("20260617", "20260629", "20260711", "20260723", "20260816",
                             "20260828", "20260909", "20260921", "20261003", "20261015")),
    SeriesSpec(171, "D", 75, ("20260626", "20260708", "20260720", "20260825",
                              "20260906", "20260918", "20260930", "20261012")),
)


def _background(rng: np.random.Generator, shape: tuple[int, int]) -> np.ndarray:
    field = ndimage.gaussian_filter(rng.normal(size=shape), 12)
    return -13 + 3 * field / field.std()


def _disk(shape: tuple[int, int], row: float, col: float, radius: float) -> np.ndarray:
    rows, cols = np.ogrid[: shape[0], : shape[1]]
    return (rows - row) ** 2 + (cols - col) ** 2 <= radius**2


def _write(path: Path, name: str, hh, hv, mask, looks, exception, x, y, day, spec: SeriesSpec) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(path, "w") as handle:
        handle.attrs["data_kind"] = "synthetic"
        identification = handle.create_group(IDENTIFICATION)
        identification["granuleId"] = name
        identification["trackNumber"] = spec.track
        identification["frameNumber"] = spec.frame
        identification["orbitPassDirection"] = "Ascending" if spec.direction == "A" else "Descending"
        identification["zeroDopplerStartTime"] = datetime.strptime(day, "%Y%m%d").strftime("%Y-%m-%dT09:42:25")
        identification["compositeReleaseId"] = "P05023"
        # Mismos campos y formato que los gránulos reales (texto en bytes, listas como arreglos).
        identification["productType"] = "GCOV"
        identification["isGeocoded"] = "True"
        identification["isMixedMode"] = "False"
        identification["listOfFrequencies"] = np.array([b"A", b"B"])
        identification["listOfObservationModes"] = np.array([b"(NOT SPECIFIED)"])
        grid = handle.create_group(GRID)
        grid["xCoordinates"] = x
        grid["yCoordinates"] = y
        grid["HHHH"] = hh.astype(np.float32)
        grid["HVHV"] = hv.astype(np.float32)
        grid["mask"] = mask.astype(np.uint8)
        grid["numberOfLooks"] = looks.astype(np.float32)
        grid["inputDataExceptionMask"] = exception.astype(np.uint8)
        grid["projection"] = EPSG
        grid["projection"].attrs["epsg_code"] = EPSG


def write_radar_grid(path: Path, x: np.ndarray, y: np.ndarray, direction: str, incidence=(33.0, 47.0)) -> None:
    """Añade un radarGrid falso: incidencia que crece hacia el alcance lejano y visión a la izquierda.

    El vector de visión va del suelo al sensor, como en los gránulos reales (comprobado el 2026-11-12:
    losUnitVectorX medio de +0,62 en T048 ascendente y de −0,63 en T171 descendente). processor no depende del signo.
    """
    xs = np.linspace(x.min() - 2000, x.max() + 2000, 12)
    ys = np.linspace(y.max() + 2000, y.min() - 2000, 10)
    heights = np.array([-500.0, 0.0, 1000.0, 2000.0, 3000.0, 4000.0])
    near_to_far = (xs.max() - xs) / np.ptp(xs) if direction == "A" else (xs - xs.min()) / np.ptp(xs)
    inc = incidence[0] + (incidence[1] - incidence[0]) * near_to_far
    cube = np.broadcast_to(inc[None, None, :], (heights.size, ys.size, xs.size)).astype(np.float32)
    look_east = 1.0 if direction == "A" else -1.0  # del suelo al sensor: el sensor queda al este en ascendente
    with h5py.File(path, "a") as handle:
        group = handle.require_group("/science/LSAR/GCOV/metadata/radarGrid")
        group["xCoordinates"] = xs
        group["yCoordinates"] = ys
        group["heightAboveEllipsoid"] = heights
        group["incidenceAngle"] = cube
        group["losUnitVectorX"] = np.full(cube.shape, look_east * 0.9, np.float32)
        group["losUnitVectorY"] = np.full(cube.shape, 0.15, np.float32)
        group["projection"] = np.uint32(EPSG)
        group["projection"].attrs["epsg_code"] = EPSG


# Malla y margen como una tesela GLO-30 (1″ en EPSG:4326), para que la pila sintética pruebe lo mismo que la real.
SYNTHETIC_DEM_STEP_DEG = 1 / 3600
SYNTHETIC_DEM_MARGIN_DEG = 0.05


def write_synthetic_dem(bbox: list[float], path: Path, seed: int = 11) -> Path:
    """DEM sintético de la zona (T-ECO-13): colinas suaves y una sierra, de 1500 a 3000 m.

    Lleva la etiqueta DATA_KIND=synthetic, que el pipeline lee para publicarlo como sintético y para no
    usarlo nunca con gránulos reales. No describe ningún relieve real.
    """
    west, south, east, north = bbox
    west, south = west - SYNTHETIC_DEM_MARGIN_DEG, south - SYNTHETIC_DEM_MARGIN_DEG
    east, north = east + SYNTHETIC_DEM_MARGIN_DEG, north + SYNTHETIC_DEM_MARGIN_DEG
    width = int(round((east - west) / SYNTHETIC_DEM_STEP_DEG))
    height = int(round((north - south) / SYNTHETIC_DEM_STEP_DEG))
    rng = np.random.default_rng(seed)
    # Se genera grueso y se interpola: el relieve fino no aporta a la prueba y así cuesta poco.
    coarse = ndimage.gaussian_filter(rng.normal(size=(height // 30 + 2, width // 30 + 2)), 3)
    hills = ndimage.zoom(coarse / coarse.std(), (height / coarse.shape[0], width / coarse.shape[1]), order=1)
    hills = np.pad(hills, ((0, max(0, height - hills.shape[0])), (0, max(0, width - hills.shape[1]))), mode="edge")
    cols = np.linspace(0, 1, width)[None, :]
    ridge = 900 * np.exp(-(((cols - 0.3) / 0.08) ** 2))  # sierra norte-sur al oeste de la zona
    relief = 250 * hills[:height, :width] + ridge
    # De 1500 a 3000 m, como el relieve de Parral (GLO-30 da de 1521 a 3041 m).
    dem = (1500 + 1500 * (relief - relief.min()) / (relief.max() - relief.min())).astype(np.float32)
    path.parent.mkdir(parents=True, exist_ok=True)
    profile = {
        "driver": "GTiff", "width": width, "height": height, "count": 1, "dtype": "float32",
        "crs": "EPSG:4326", "transform": from_origin(west, north, SYNTHETIC_DEM_STEP_DEG, SYNTHETIC_DEM_STEP_DEG),
        "compress": "deflate", "tiled": True,
    }
    with rasterio.open(path, "w", **profile) as dataset:
        dataset.write(dem, 1)
        dataset.update_tags(**{DEM_KIND_TAG: "synthetic"})
    return path


def _speckle(rng: np.random.Generator, db: np.ndarray) -> np.ndarray:
    return 10 ** (db / 10) * rng.gamma(LOOKS, 1 / LOOKS, db.shape)


def generate_series(
    spec: SeriesSpec,
    bbox: list[float],
    out_dir: Path,
    seed: int = 7,
    posting_m: float = POSTING_M,
    radar_grid: bool = False,
) -> list[Path]:
    left, bottom, right, top = transform_bounds("EPSG:4326", f"EPSG:{EPSG}", *bbox)
    margin = 4 * posting_m
    x = np.arange(left - margin, right + margin, posting_m)
    y = np.arange(top + margin, bottom - margin, -posting_m)
    shape = (y.size, x.size)
    rng = np.random.default_rng(seed + spec.track)

    base_hh = _background(rng, shape)
    base_hv = base_hh - 7
    city = _disk(shape, shape[0] * 0.55, shape[1] * 0.5, shape[0] * 0.09)
    base_hh[city] += 7
    base_hv[city] += 5
    wetting = _disk(shape, shape[0] * 0.28, shape[1] * 0.28, shape[0] * 0.14)
    water_center = (shape[0] * 0.75, shape[1] * 0.75)

    mask = np.ones(shape, np.uint8)
    mask[:, shape[1] // 2 :] = 2
    mask[: 3, :] = 255
    mask[:, : 3] = 255
    mask[:, shape[1] // 2 - 1 : shape[1] // 2 + 1] = 0
    looks = np.full(shape, LOOKS, np.float32)
    looks[_disk(shape, shape[0] * 0.2, shape[1] * 0.8, shape[0] * 0.06)] = 1.0

    paths = []
    for index, day in enumerate(spec.dates):
        progress = index / max(len(spec.dates) - 1, 1)
        hh, hv = base_hh.copy(), base_hv.copy()
        if progress >= 0.4:  # humedecimiento ficticio a mitad de la serie
            hh[wetting] += 5
            hv[wetting] += 1
        water = _disk(shape, *water_center, shape[0] * (0.16 - 0.08 * progress))
        hh[water] = -24
        hv[water] = -30

        exception = np.zeros(shape, np.uint8)
        if index == 2:
            exception[_disk(shape, shape[0] * 0.5, shape[1] * 0.15, shape[0] * 0.05)] = 2

        name = (
            f"SYNTHETIC_NISAR_L2_PR_GCOV_{index + 1:03d}_{spec.track:03d}_{spec.direction}_{spec.frame:03d}"
            f"_4005_DHDH_A_{day}T094225_{day}T094259_P05023_N_F_J_001"
        )
        hh_power = _speckle(rng, hh)
        hv_power = _speckle(rng, hv)
        hh_power[mask == 255] = np.nan
        hv_power[mask == 255] = np.nan
        path = out_dir / f"{name}.h5"
        _write(path, name, hh_power, hv_power, mask, looks, exception, x, y, day, spec)
        if radar_grid:
            write_radar_grid(path, x, y, spec.direction)
        paths.append(path)
    return paths
