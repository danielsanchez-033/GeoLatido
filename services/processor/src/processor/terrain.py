"""Layover y sombra con el DEM Copernicus GLO-30 y la geometría `radarGrid` del gránulo (T-ECO-05).

GCOV no marca layover ni sombra. Se calculan con un criterio local por pendiente:

- layover: la ladera sube, alejándose del sensor, con más pendiente que el ángulo de incidencia;
- sombra: la ladera baja, alejándose del sensor, con más pendiente que 90° menos la incidencia.

No se calculan las sombras proyectadas por una cresta sobre el terreno de detrás ni la zona que
recibe el layover de otra ladera: el criterio local subestima ambas.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import h5py
import numpy as np
import rasterio
from rasterio.errors import RasterioIOError
from rasterio.merge import merge
from rasterio.transform import Affine
from rasterio.warp import Resampling, reproject, transform_bounds
from scipy import ndimage
from scipy.interpolate import RegularGridInterpolator

RADAR_GRID = "/science/LSAR/GCOV/metadata/radarGrid"
# Paso de la malla gruesa donde se evalúa la geometría: varía despacio y así no cuesta RAM.
GEOMETRY_STEP = 32
GLO30_URL = (
    "https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_{lat}_00_{lon}_00_DEM/"
    "Copernicus_DSM_COG_10_{lat}_00_{lon}_00_DEM.tif"
)

# Margen alrededor de la zona al publicar el DEM: unos 1,1 km, para que el relieve no se corte en el borde.
DEM_MARGIN_DEG = 0.01
DEM_SOURCE = "Copernicus DEM GLO-30"
# GLO-30 da alturas ortométricas sobre el geoide EGM2008, no sobre el elipsoide.
DEM_VERTICAL_DATUM = "EGM2008"
# Texto que pide la licencia de Copernicus DEM para redistribuirlo.
# Etiqueta del GeoTIFF que marca un DEM sintético (T-ECO-13); sin ella, el DEM se toma por real.
DEM_KIND_TAG = "DATA_KIND"
SYNTHETIC_DEM_SOURCE = "DEM sintético de processor (no es Copernicus GLO-30)"
SYNTHETIC_DEM_ATTRIBUTION = "DEM sintético: no describe ningún relieve real."
DEM_ATTRIBUTION = (
    "Produced using Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 "
    "provided under COPERNICUS by the European Union and ESA; all rights reserved."
)


@dataclass
class RadarGrid:
    heights: np.ndarray  # (H,) metros sobre el elipsoide
    y: np.ndarray  # (Ny,) coordenada proyectada
    x: np.ndarray  # (Nx,)
    incidence: np.ndarray  # (H, Ny, Nx) grados
    los_x: np.ndarray  # (H, Ny, Nx) componente x del vector de visión
    los_y: np.ndarray  # (H, Ny, Nx)
    crs: str | None = None  # del `projection` propio del grupo, si lo trae


def read_radar_grid(handle: h5py.File) -> RadarGrid | None:
    """Lee `radarGrid` si el recorte lo trae; si falta algo imprescindible, devuelve None."""
    if RADAR_GRID not in handle:
        return None
    group = handle[RADAR_GRID]
    needed = ("heightAboveEllipsoid", "xCoordinates", "yCoordinates", "incidenceAngle", "losUnitVectorX", "losUnitVectorY")
    if not all(name in group for name in needed):
        return None
    return RadarGrid(
        heights=group["heightAboveEllipsoid"][()].astype(np.float64),
        y=group["yCoordinates"][()].astype(np.float64),
        x=group["xCoordinates"][()].astype(np.float64),
        incidence=group["incidenceAngle"][()].astype(np.float64),
        los_x=group["losUnitVectorX"][()].astype(np.float64),
        los_y=group["losUnitVectorY"][()].astype(np.float64),
        crs=f"EPSG:{int(group['projection'].attrs['epsg_code'])}"
        if "projection" in group and "epsg_code" in group["projection"].attrs
        else None,
    )


def glo30_tiles(bbox: list[float]) -> list[str]:
    """URLs públicas de las teselas GLO-30 de 1° que cubren el bbox (oeste, sur, este, norte)."""
    west, south, east, north = bbox
    urls = []
    for lat in range(int(np.floor(south)), int(np.floor(north - 1e-9)) + 1):
        for lon in range(int(np.floor(west)), int(np.floor(east - 1e-9)) + 1):
            lat_tag = f"{'N' if lat >= 0 else 'S'}{abs(lat):02d}"
            lon_tag = f"{'E' if lon >= 0 else 'W'}{abs(lon):03d}"
            urls.append(GLO30_URL.format(lat=lat_tag, lon=lon_tag))
    return urls


def dem_on_grid(sources: list[Path | str], crs: str, transform: Affine, shape: tuple[int, int]) -> np.ndarray:
    """Remuestrea el DEM (una o varias teselas) a la malla de la escena, con interpolación bilineal."""
    out = np.full(shape, np.nan, np.float32)
    for source in sources:
        with rasterio.open(source) as dataset:
            band = np.full(shape, np.nan, np.float32)
            reproject(
                rasterio.band(dataset, 1),
                band,
                dst_transform=transform,
                dst_crs=crs,
                dst_nodata=np.nan,
                resampling=Resampling.bilinear,
            )
        out = np.where(np.isnan(out), band, out)
    return out


def dem_kind(source: Path | str) -> str | None:
    """"synthetic" o "real" según la etiqueta del GeoTIFF; None si no se puede abrir."""
    try:
        with rasterio.open(source) as dataset:
            return "synthetic" if dataset.tags().get(DEM_KIND_TAG) == "synthetic" else "real"
    except RasterioIOError:
        return None


def dem_for_aoi(
    sources: list[Path | str], bbox: list[float], margin: float = DEM_MARGIN_DEG
) -> tuple[np.ndarray, Affine, str] | None:
    """El DEM recortado a la zona con margen, en su malla y su CRS nativos (1″ en EPSG:4326 para GLO-30).

    No se remuestrea a la malla de 10 m del radar: tendría unas tres veces más píxeles sin más información.
    Devuelve None si no hay teselas legibles o si no cubren la zona.
    """
    west, south, east, north = bbox
    datasets = []
    try:
        for source in sources:
            try:
                datasets.append(rasterio.open(source))
            except RasterioIOError:
                continue
        if not datasets or len({dataset.crs for dataset in datasets}) != 1:
            return None
        crs = datasets[0].crs
        bounds = (west - margin, south - margin, east + margin, north + margin)
        if not crs.is_geographic:
            bounds = transform_bounds("EPSG:4326", crs, *bounds)
        mosaic, transform = merge(datasets, bounds=bounds, nodata=np.nan, dtype="float32")
    finally:
        for dataset in datasets:
            dataset.close()
    data = mosaic[0].astype(np.float32)
    if not np.isfinite(data).any():
        return None
    return data, transform, crs.to_string()


def _toward_sensor_sign(los_x: np.ndarray, direction: str) -> float:
    """Orienta el vector de visión para que apunte del suelo al sensor.

    NISAR mira a la izquierda: en órbita ascendente (hacia el norte) mira al oeste, así que el sensor
    queda al este del terreno; en descendente, al oeste. Así no depende del convenio de signo del producto.
    """
    expected_east = 1.0 if direction == "A" else -1.0
    return expected_east * np.sign(np.nanmedian(los_x)) if np.nanmedian(los_x) != 0 else expected_east


def geometry_on_grid(
    radar: RadarGrid, dem: np.ndarray, transform: Affine, direction: str, step: int = GEOMETRY_STEP
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Incidencia (grados) y dirección horizontal hacia el sensor (este, norte) en la malla de la escena.

    Se evalúa en una malla gruesa a la altura media del DEM en cada celda y se interpola al detalle.
    """
    rows, cols = dem.shape
    coarse_r = np.arange(0, rows, step) + step / 2
    coarse_c = np.arange(0, cols, step) + step / 2
    cx = transform.c + (coarse_c + 0.5) * transform.a
    cy = transform.f + (coarse_r + 0.5) * transform.e
    height = ndimage.zoom(
        np.nan_to_num(dem, nan=float(np.nanmedian(dem))), (len(coarse_r) / rows, len(coarse_c) / cols), order=1
    )[: len(coarse_r), : len(coarse_c)]
    gy, gx = np.meshgrid(cy, cx, indexing="ij")
    height = np.clip(height, radar.heights.min(), radar.heights.max())
    points = np.stack([height.ravel(), gy.ravel(), gx.ravel()], axis=1)

    def sample(cube: np.ndarray) -> np.ndarray:
        y_axis, values = radar.y, cube
        if y_axis[0] > y_axis[-1]:  # RegularGridInterpolator pide ejes crecientes
            y_axis, values = y_axis[::-1], cube[:, ::-1, :]
        interp = RegularGridInterpolator((radar.heights, y_axis, radar.x), values, bounds_error=False, fill_value=None)
        return interp(points).reshape(height.shape)

    incidence = sample(radar.incidence)
    east, north = sample(radar.los_x), sample(radar.los_y)
    sign = _toward_sensor_sign(east, direction)
    norm = np.hypot(east, north)
    east, north = sign * east / norm, sign * north / norm

    def upsample(field: np.ndarray) -> np.ndarray:
        full = ndimage.zoom(field, (rows / field.shape[0], cols / field.shape[1]), order=1)
        return np.pad(full, ((0, max(0, rows - full.shape[0])), (0, max(0, cols - full.shape[1]))), mode="edge")[:rows, :cols]

    return upsample(incidence).astype(np.float32), upsample(east).astype(np.float32), upsample(north).astype(np.float32)


def layover_shadow(
    dem: np.ndarray, transform: Affine, incidence_deg: np.ndarray, toward_east: np.ndarray, toward_north: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Máscaras de layover y de sombra por el criterio local de pendiente en la dirección de alcance."""
    dx = abs(transform.a)
    dy = abs(transform.e)
    d_row, d_col = np.gradient(dem.astype(np.float32), dy, dx)
    north_up = transform.e < 0
    dz_north = -d_row if north_up else d_row
    dz_east = d_col
    # Subida al alejarse del sensor (dirección opuesta a `toward`).
    rise = -(dz_east * toward_east + dz_north * toward_north)
    slope = np.degrees(np.arctan(rise))
    valid = np.isfinite(slope) & np.isfinite(incidence_deg)
    layover = valid & (slope > incidence_deg)
    shadow = valid & (-slope > 90 - incidence_deg)
    return layover, shadow


def terrain_mask(
    handle_path: Path, dem_sources: list[Path | str], crs: str, transform: Affine, shape: tuple[int, int], direction: str
) -> tuple[np.ndarray | None, str]:
    """Máscara de relieve para la malla de la escena, o None con el motivo si no se puede calcular."""
    with h5py.File(handle_path, "r") as handle:
        radar = read_radar_grid(handle)
    if radar is None:
        return None, "el recorte no trae radarGrid"
    if radar.crs is not None and radar.crs != crs:
        return None, f"radarGrid está en {radar.crs} y la malla en {crs}"
    if not dem_sources:
        return None, "no hay DEM"
    dem = dem_on_grid(dem_sources, crs, transform, shape)
    if np.isnan(dem).all():
        return None, "el DEM no cubre la zona"
    incidence, east, north = geometry_on_grid(radar, dem, transform, direction)
    layover, shadow = layover_shadow(dem, transform, incidence, east, north)
    return layover | shadow, f"layover {layover.mean():.2%}, sombra {shadow.mean():.2%}"
