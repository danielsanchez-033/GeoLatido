"""Lectura de gránulos GCOV según la especificación JPL D-102274 Rev F."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import h5py
import numpy as np
from rasterio.transform import Affine
from rasterio.warp import transform_bounds

GRID = "/science/LSAR/GCOV/grids/frequencyA"
IDENTIFICATION = "/science/LSAR/identification"
_MODE = re.compile(r"_(\d{4})_([A-Z]{4})_")


class GranuleError(ValueError):
    """El gránulo no se puede usar para esta zona o esta serie."""


@dataclass(frozen=True)
class GranuleMeta:
    granule_id: str
    date: str  # YYYY-MM-DD
    track: int
    direction: str
    frame: int
    mode: str
    polarization: str
    crid: str
    data_kind: str


@dataclass
class Scene:
    hh: np.ndarray
    hv: np.ndarray
    mask: np.ndarray
    looks: np.ndarray
    exception: np.ndarray
    transform: Affine
    crs: str
    meta: GranuleMeta


def _text(value) -> str:
    if isinstance(value, np.ndarray):
        value = value.item()
    return value.decode() if isinstance(value, bytes) else str(value)


# Capas de covarianza de la diagonal -> código de polarización de la frecuencia A.
_POLARIZATIONS = {
    frozenset({"HHHH"}): "SH",
    frozenset({"VVVV"}): "SV",
    frozenset({"HHHH", "HVHV"}): "DH",
    frozenset({"VVVV", "VHVH"}): "DV",
    frozenset({"HHHH", "HVHV", "VHVH", "VVVV"}): "QP",
}
_NEEDED = {"HHHH", "HVHV"}


def _flag(identification: h5py.Group, name: str) -> bool | None:
    if name not in identification:
        return None
    return _text(identification[name][()]).strip().lower() == "true"


def _texts(identification: h5py.Group, name: str) -> list[str]:
    if name not in identification:
        return []
    return [_text(value).strip() for value in np.atleast_1d(identification[name][()])]


def _frequency_a_polarization(handle: h5py.File) -> str:
    """Código de polarización según las capas presentes, no según el nombre."""
    grid = handle[GRID]
    if "listOfPolarizations" in grid:
        pols = {_text(value).strip().upper() for value in np.atleast_1d(grid["listOfPolarizations"][()])}
        terms = {pol + pol for pol in pols}
    else:
        terms = {name for name in ("HHHH", "HVHV", "VHVH", "VVVV") if name in grid}
    if not _NEEDED <= terms:
        raise GranuleError(f"La frecuencia A no trae HH y HV (tiene {sorted(terms) or 'ninguna'})")
    return _POLARIZATIONS.get(frozenset(terms), "+".join(sorted(terms)))


def read_meta(handle: h5py.File) -> GranuleMeta:
    """Lee la identificación y comprueba el modo con los metadatos del producto.

    El recorte no trae el ancho de banda y en los gránulos reales `listOfObservationModes`
    vale "(NOT SPECIFIED)", así que el código de ancho de banda (p. ej. 4005) sale del nombre,
    pero solo después de comprobar con los metadatos que el nombre no contradice al producto.
    """
    identification = handle[IDENTIFICATION]
    granule_id = _text(identification["granuleId"][()])

    if _flag(identification, "isMixedMode"):
        raise GranuleError(f"{granule_id}: modo mixto, el ancho de banda cambia dentro del marco")
    if _flag(identification, "isGeocoded") is False:
        raise GranuleError(f"{granule_id}: el producto no está geocodificado")
    if "productType" in identification and _text(identification["productType"][()]).strip() != "GCOV":
        raise GranuleError(f"{granule_id}: no es un producto GCOV")
    frequencies = [value.upper() for value in _texts(identification, "listOfFrequencies")]
    if frequencies and "A" not in frequencies:
        raise GranuleError(f"{granule_id}: no trae la frecuencia A")

    polarization = _frequency_a_polarization(handle)
    named = _MODE.search(granule_id)
    if named:
        mode, named_polarization = named.groups()
        if named_polarization[:2] != polarization:
            raise GranuleError(
                f"{granule_id}: el nombre dice {named_polarization[:2]} pero las capas son {polarization}"
            )
        has_b = mode[2:] != "00"
        if frequencies and has_b != ("B" in frequencies):
            raise GranuleError(f"{granule_id}: el nombre ({mode}) no coincide con las frecuencias {frequencies}")
        # El código del nombre también describe la frecuencia B; la A ya quedó comprobada.
        polarization = named_polarization
    else:
        mode = "unknown"

    direction = _text(identification["orbitPassDirection"][()]).strip().upper()[0]
    return GranuleMeta(
        granule_id=granule_id,
        date=_text(identification["zeroDopplerStartTime"][()])[:10],
        track=int(identification["trackNumber"][()]),
        direction=direction,
        frame=int(identification["frameNumber"][()]),
        mode=mode,
        polarization=polarization,
        crid=_text(identification["compositeReleaseId"][()]),
        data_kind=_text(handle.attrs.get("data_kind", "real")),
    )


def read_meta_path(path: Path) -> GranuleMeta:
    """Lee solo la identificación, sin tocar las capas."""
    with h5py.File(path, "r") as handle:
        return read_meta(handle)


def read_scene(path: Path, bbox: list[float]) -> Scene:
    """Lee solo la ventana de la zona, sin cargar el gránulo completo."""
    with h5py.File(path, "r") as handle:
        grid = handle[GRID]
        x = grid["xCoordinates"][()]
        y = grid["yCoordinates"][()]
        crs = f"EPSG:{int(grid['projection'].attrs['epsg_code'])}"
        left, bottom, right, top = transform_bounds("EPSG:4326", crs, *bbox)

        descending = y[0] > y[-1]
        keys = -y if descending else y
        low, high = (-top, -bottom) if descending else (bottom, top)
        row0, row1 = np.searchsorted(keys, [low, high])
        col0, col1 = np.searchsorted(x, [left, right])
        if row1 <= row0 or col1 <= col0:
            raise GranuleError(f"La zona queda fuera de {path.name}")

        def window(name: str) -> np.ndarray:
            data = grid[name][row0:row1, col0:col1]
            return data if descending else data[::-1]

        hh = window("HHHH")
        exception = (
            window("inputDataExceptionMask") if "inputDataExceptionMask" in grid else np.zeros(hh.shape, np.uint8)
        )
        dx = float(x[1] - x[0])
        dy = abs(float(y[1] - y[0]))
        top_center = float(y[row0:row1].max())
        return Scene(
            hh=hh,
            hv=window("HVHV"),
            mask=window("mask"),
            looks=window("numberOfLooks"),
            exception=exception,
            transform=Affine(dx, 0, float(x[col0]) - dx / 2, 0, -dy, top_center + dy / 2),
            crs=crs,
            meta=read_meta(handle),
        )
