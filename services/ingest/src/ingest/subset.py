"""Recorte de un gránulo GCOV según contracts/gcov-subset.md."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

import h5py
import numpy as np
from rasterio.warp import transform_bounds

LSAR = "/science/LSAR"
IDENTIFICATION = f"{LSAR}/identification"
GRID = f"{LSAR}/GCOV/grids/frequencyA"
RADAR_GRID = f"{LSAR}/GCOV/metadata/radarGrid"
# Nodos de radarGrid que se añaden a cada lado de la ventana, para poder interpolar en el borde.
RADAR_GRID_MARGIN = 2
REQUIRED_LAYERS = ("HHHH", "HVHV", "mask", "numberOfLooks")
OPTIONAL_LAYERS = ("inputDataExceptionMask",)


class SubsetError(ValueError):
    """El gránulo no sirve para esta zona o esta serie."""


@dataclass(frozen=True)
class Identity:
    granule_id: str
    track: int
    direction: str
    frame: int


def _text(value) -> str:
    if isinstance(value, np.ndarray):
        value = value.item()
    return value.decode() if isinstance(value, bytes) else str(value)


def read_identity(handle: h5py.File) -> Identity:
    identification = handle[IDENTIFICATION]
    return Identity(
        granule_id=_text(identification["granuleId"][()]),
        track=int(identification["trackNumber"][()]),
        direction=_text(identification["orbitPassDirection"][()]).strip().upper()[0],
        frame=int(identification["frameNumber"][()]),
    )


def _window(x: np.ndarray, y: np.ndarray, bounds: tuple[float, float, float, float]) -> tuple[slice, slice]:
    left, bottom, right, top = bounds
    descending = y[0] > y[-1]
    keys = -y if descending else y
    low, high = (-top, -bottom) if descending else (bottom, top)
    row0, row1 = np.searchsorted(keys, [low, high])
    col0, col1 = np.searchsorted(x, [left, right])
    return slice(int(row0), int(row1)), slice(int(col0), int(col1))


def _node_window(nodes: np.ndarray, low: float, high: float, margin: int) -> slice:
    """Índices de los nodos que rodean [low, high], más `margin` por lado; vale para ejes descendentes."""
    keys = -nodes if nodes[0] > nodes[-1] else nodes
    low, high = sorted((-low, -high) if nodes[0] > nodes[-1] else (low, high))
    first = int(np.searchsorted(keys, low, side="right")) - 1 - margin
    last = int(np.searchsorted(keys, high, side="left")) + 1 + margin
    return slice(max(first, 0), min(last, nodes.size))


def _copy_radar_grid(src: h5py.File, dst: h5py.File, x: np.ndarray, y: np.ndarray) -> None:
    """Copia radarGrid recortado a los nodos que cubren la ventana (x, y), con todas las alturas.

    Opcional según contracts/gcov-subset.md: si el gránulo no lo trae, no se copia nada.
    """
    if RADAR_GRID not in src:
        return
    grid = src[RADAR_GRID]
    nodes_x = grid["xCoordinates"][()]
    nodes_y = grid["yCoordinates"][()]
    cols = _node_window(nodes_x, float(x.min()), float(x.max()), RADAR_GRID_MARGIN)
    rows = _node_window(nodes_y, float(y.min()), float(y.max()), RADAR_GRID_MARGIN)
    out = dst.require_group(RADAR_GRID)
    for name, item in grid.items():
        if not isinstance(item, h5py.Dataset):
            src.copy(item, out, name=name)
        elif name == "xCoordinates":
            out.create_dataset(name, data=nodes_x[cols])
        elif name == "yCoordinates":
            out.create_dataset(name, data=nodes_y[rows])
        elif item.ndim >= 2 and item.shape[-2:] == (nodes_y.size, nodes_x.size):
            out.create_dataset(name, data=item[..., rows, cols], chunks=True, compression="lzf")
        else:
            # heightAboveEllipsoid, projection y cualquier otro valor que no dependa de x e y.
            src.copy(item, out, name=name)
            continue
        for key, value in item.attrs.items():
            out[name].attrs[key] = value


def subset(source: Path | BinaryIO, bbox: list[float], expected: dict, destination: Path) -> Identity:
    """Copia la identificación y solo la ventana de la zona; conserva tipos y orientación."""
    with h5py.File(source, "r") as src:
        identity = read_identity(src)
        if (identity.track, identity.direction, identity.frame) != (
            expected["track"],
            expected["direction"],
            expected["frame"],
        ):
            raise SubsetError(f"{identity.granule_id} no corresponde a la serie {expected['id']}")

        grid = src[GRID]
        x = grid["xCoordinates"][()]
        y = grid["yCoordinates"][()]
        crs = f"EPSG:{int(grid['projection'].attrs['epsg_code'])}"
        rows, cols = _window(x, y, transform_bounds("EPSG:4326", crs, *bbox))
        if rows.stop <= rows.start or cols.stop <= cols.start:
            raise SubsetError(f"La zona queda fuera de {identity.granule_id}")

        with h5py.File(destination, "w") as dst:
            dst.attrs["subset_of"] = identity.granule_id
            dst.attrs["subset_bbox"] = np.asarray(bbox, dtype=np.float64)
            src.copy(src[IDENTIFICATION], dst.require_group(LSAR), name="identification")
            out = dst.require_group(GRID)
            out["xCoordinates"] = x[cols]
            out["yCoordinates"] = y[rows]
            src.copy(grid["projection"], out, name="projection")
            for name in REQUIRED_LAYERS + OPTIONAL_LAYERS:
                if name in grid:
                    out.create_dataset(name, data=grid[name][rows, cols], chunks=True, compression="lzf")
                elif name in REQUIRED_LAYERS:
                    raise SubsetError(f"{identity.granule_id}: falta la capa {name}")
            _copy_radar_grid(src, dst, x[cols], y[rows])
    return identity
