"""Convierte una serie de gránulos en COGs, estados y manifiesto."""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

import numpy as np
import rasterio
import rasterio.shutil
from rasterio.io import MemoryFile

from .cells import cell_features
from .change import STATE_CODES, STATE_NODATA, Params, compare, smooth, observable, to_db
from .gcov import GranuleError, GranuleMeta, Scene, read_meta_path, read_scene
from .qa import finalize_qa, scene_stats
from .multitemporal import MultitemporalFilter
from .terrain import (
    DEM_ATTRIBUTION,
    DEM_SOURCE,
    DEM_VERTICAL_DATUM,
    SYNTHETIC_DEM_ATTRIBUTION,
    SYNTHETIC_DEM_SOURCE,
    dem_for_aoi,
    dem_kind,
    terrain_mask,
)

DATA_GAP = (date(2026, 7, 27), date(2026, 8, 10))
BASE_NOTICES = [
    "Datos PROVISIONAL: se reprocesarán a VALIDATED en 2027 y no deben mezclarse con otra versión.",
    "Hueco permanente de adquisición del 2026-07-27 al 2026-08-10.",
    "Umbrales estimados sobre la propia escena: indicador del modelo, no error calibrado.",
]
SHIFT_NOTICE = (
    "El cambio de cada par se mide respecto al desplazamiento de toda la escena: se resta la mediana de la "
    "diferencia (scene_shift_hh_db y scene_shift_hv_db en stats) antes de aplicar el umbral. Un cambio que "
    "afecta a casi toda la zona, como una lluvia general, queda en ese desplazamiento y no como cambio local."
)
QA_NOTICE = (
    "El control de calidad marca una fecha si su mediana se aparta más de {:g} dB de la serie. "
    "Ese umbral no está calibrado y la marca es una advertencia, no una exclusión."
)
GDAL_CACHE_MB = 128
TERRAIN_NOTICE = (
    "Layover y sombra (estado terrain) calculados con el {dem} y la geometría radarGrid de la "
    "primera fecha ({detail}), con un criterio local por pendiente: no incluye sombras proyectadas por crestas."
)
NO_TERRAIN_NOTICE = "Layover y sombra no se marcaron: {reason}. Las laderas empinadas pueden aparecer como cambio o sin cambio."
MULTITEMPORAL_NOTICE = (
    "Filtro multitemporal de speckle (Quegan y Yu, ventana {window}×{window}, {dates} fechas) aplicado antes de "
    "calcular QA, capas y cambios: cada fecha conserva su media local, pero su textura fina sale del promedio de la "
    "serie, así que un cambio fuerte en una fecha se ve atenuado en las demás."
)
EXCLUDED_NOTICE = "Fechas excluidas de la serie por declararse inservibles en config/aois: {items}."
SYNTHETIC_NOTICE = "DATOS SINTÉTICOS: sirven para probar el sistema y no describen ningún lugar real."


def _write_cog(path: Path, data: np.ndarray, scene: Scene, nodata, resampling: str) -> None:
    _write_cog_grid(path, data, scene.crs, scene.transform, nodata, resampling)


def _write_cog_grid(path: Path, data: np.ndarray, crs, transform, nodata, resampling: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    profile = {
        "driver": "GTiff",
        "height": data.shape[0],
        "width": data.shape[1],
        "count": 1,
        "dtype": data.dtype.name,
        "crs": crs,
        "transform": transform,
        "nodata": nodata,
    }
    # La caché de GDAL por omisión es el 5 % de la RAM; con una escena completa en memoria basta con poca.
    # Origen en memoria y compresión con todos los núcleos (2026-11-15): con una capa de 3437 × 3135 px, 3,9 s por COG
    # pasaba a 1,3 s con el mismo tamaño de archivo (bench/perfil_cog.py). Mismo COG: DEFLATE y las mismas vistas.
    with rasterio.Env(GDAL_CACHEMAX=GDAL_CACHE_MB), MemoryFile() as memory:
        with memory.open(**profile) as dataset:
            dataset.write(data, 1)
        with memory.open() as source:
            rasterio.shutil.copy(
                source, path, driver="COG", compress="DEFLATE", overview_resampling=resampling, num_threads="ALL_CPUS"
            )


def _check_comparable(reference: GranuleMeta, other: GranuleMeta) -> None:
    fields = ("track", "direction", "frame", "mode", "polarization", "crid", "data_kind")
    for field in fields:
        if getattr(reference, field) != getattr(other, field):
            raise GranuleError(f"{other.granule_id}: {field} no coincide con la serie")


def _db(scene: Scene, name: str, params: Params) -> np.ndarray:
    return to_db(smooth(getattr(scene, name), observable(scene, params), params.window))


def _crosses_gap(first: str, second: str) -> bool:
    return date.fromisoformat(first) < DATA_GAP[1] and date.fromisoformat(second) > DATA_GAP[0]


def _stamp(meta: GranuleMeta) -> str:
    return meta.date.replace("-", "")


def _write_date(scene: Scene, prefix: str, artifact_root: Path, params: Params) -> dict:
    layers = {}
    for name in ("hh", "hv"):
        relative = f"{prefix}/dates/{_stamp(scene.meta)}/{name}_db.tif"
        _write_cog(artifact_root / relative, _db(scene, name, params), scene, float("nan"), "average")
        layers[f"{name}_db"] = relative
    return {"date": scene.meta.date, "granule": scene.meta.granule_id, **layers}


def _write_pair(
    before: Scene, after: Scene, kind: str, prefix: str, artifact_root: Path, params: Params, terrain=None
) -> dict:
    pair_id = f"{_stamp(before.meta)}_{_stamp(after.meta)}"
    result = compare(before, after, params, terrain)
    layers = {
        "state": f"{prefix}/pairs/{pair_id}/state.tif",
        "change_hh": f"{prefix}/pairs/{pair_id}/change_hh.tif",
        "change_hv": f"{prefix}/pairs/{pair_id}/change_hv.tif",
    }
    _write_cog(artifact_root / layers["state"], result.state, before, STATE_NODATA, "nearest")
    _write_cog(artifact_root / layers["change_hh"], result.change_hh, before, float("nan"), "average")
    _write_cog(artifact_root / layers["change_hv"], result.change_hv, before, float("nan"), "average")
    # Fuera de `layers`, que son COGs: las celdas son un GeoJSON para buscar, no una capa del mapa.
    cells = cell_features(result.state, before.transform, before.crs)
    cells_path = None
    if cells is not None:
        cells_path = f"{prefix}/pairs/{pair_id}/cells.geojson"
        (artifact_root / cells_path).write_text(json.dumps(cells, ensure_ascii=False), encoding="utf-8")
    return {
        "id": pair_id,
        "from": before.meta.date,
        "to": after.meta.date,
        "kind": kind,
        "spans_data_gap": _crosses_gap(before.meta.date, after.meta.date),
        "granules": [before.meta.granule_id, after.meta.granule_id],
        "layers": layers,
        "stats": result.stats,
        **({"cells": cells_path} if cells_path else {}),
    }


def _multitemporal(ordered, bbox: list[float], params: Params) -> MultitemporalFilter:
    """Primera pasada: acumula la textura de todas las fechas, leyendo una escena cada vez."""
    speckle = None
    for _, path in ordered:
        scene = read_scene(path, bbox)
        speckle = speckle or MultitemporalFilter(scene.hh.shape, params.multitemporal_window)
        speckle.add(scene, observable(scene, params))
        del scene
    return speckle


def _read(path: Path, bbox: list[float], params: Params, speckle: MultitemporalFilter | None) -> Scene:
    scene = read_scene(path, bbox)
    return speckle.apply(scene, observable(scene, params)) if speckle else scene


def _date_in_name(name: str) -> str:
    """Fecha de inicio del nombre de un gránulo NISAR (…_20260813T014433_…); el nombre entero si no la trae."""
    found = re.search(r"_(\d{4})(\d{2})(\d{2})T\d{6}_", name)
    return "-".join(found.groups()) if found else name


def _usable_dem(dem_sources, data_kind: str) -> tuple[list, str]:
    """Las fuentes de DEM que se pueden usar con esta serie y si son sintéticas.

    Un DEM sintético (T-ECO-13) solo acompaña a gránulos sintéticos: con datos reales se descarta, para no
    marcar layover ni dibujar relieve inventado sobre una zona real.
    """
    kinds = {source: dem_kind(source) for source in dem_sources or []}
    if data_kind != "synthetic":
        return [source for source, kind in kinds.items() if kind != "synthetic"], "real"
    synthetic = [source for source, kind in kinds.items() if kind == "synthetic"]
    return (synthetic, "synthetic") if synthetic else (list(kinds), "real")


def _publish_dem(dem_sources, dem_kind_: str, aoi: dict, artifact_root: Path) -> dict | None:
    """Publica el DEM de la zona como COG para el relieve de la interfaz (T-ECO-10); None si no hay DEM útil."""
    found = dem_for_aoi(list(dem_sources), aoi["bbox"]) if dem_sources else None
    if found is None:
        return None
    data, transform, crs = found
    relative = f"{aoi['id']}/dem.tif"
    _write_cog_grid(artifact_root / relative, data, crs, transform, float("nan"), "average")
    synthetic = dem_kind_ == "synthetic"
    return {
        "layer": relative,
        "data_kind": dem_kind_,
        "source": SYNTHETIC_DEM_SOURCE if synthetic else DEM_SOURCE,
        "crs": crs,
        "vertical_datum": "none" if synthetic else DEM_VERTICAL_DATUM,
        "units": "m",
        "attribution": SYNTHETIC_DEM_ATTRIBUTION if synthetic else DEM_ATTRIBUTION,
    }


def excluded_granules(aoi: dict) -> dict[str, str]:
    """granule_id -> motivo, según `series[].exclude[]` de la zona (lo mantiene Antena, T-ANT-10)."""
    return {
        entry["granule"]: str(entry.get("reason", "sin motivo"))
        for item in aoi.get("series") or []
        for entry in item.get("exclude") or []
    }


def process_series(
    paths: list[Path],
    aoi: dict,
    series_id: str,
    artifact_root: Path,
    maturity: str,
    params: Params = Params(),
    dem_sources: list[Path | str] | None = None,
    exclude: dict[str, str] | None = None,
) -> dict:
    """Procesa la serie con como máximo dos escenas en memoria, sea cual sea el número de fechas."""
    exclude = exclude or {}
    # Primero por el nombre en disco, que ingest escribe igual que el granuleId: así un excluido que además
    # venga corrupto ni se abre. Los renombrados se reconocen después por el granuleId de dentro del archivo.
    skipped = [(_date_in_name(path.stem), exclude[path.stem]) for path in paths if path.stem in exclude]
    ordered = sorted(
        # Una fecha remota que aún está bajando trae sus metadatos ya leídos (`remote.LazyGranule`).
        ((getattr(path, "meta", None) or read_meta_path(path), path) for path in paths if path.stem not in exclude),
        key=lambda item: item[0].date,
    )
    skipped += [(meta.date, exclude[meta.granule_id]) for meta, _ in ordered if meta.granule_id in exclude]
    ordered = [(meta, path) for meta, path in ordered if meta.granule_id not in exclude]
    if len(ordered) < 2:
        raise GranuleError("Hacen falta al menos dos fechas")
    reference = ordered[0][0]
    for meta, _ in ordered[1:]:
        _check_comparable(reference, meta)
    dem_sources, dem_data_kind = _usable_dem(dem_sources, reference.data_kind)

    prefix = f"{aoi['id']}/{series_id}"
    target = artifact_root / aoi["id"] / series_id
    dates, stats, pairs = [], [], []
    crs = None
    previous: Scene | None = None
    terrain, terrain_detail = None, "no hay DEM"
    speckle = _multitemporal(ordered, aoi["bbox"], params) if params.multitemporal else None
    for index, (_, path) in enumerate(ordered):
        scene = _read(path, aoi["bbox"], params, speckle)
        crs = crs or scene.crs
        if index == 0 and dem_sources:
            # La geometría casi no cambia entre pasadas de la misma órbita: basta la primera fecha.
            terrain, terrain_detail = terrain_mask(
                path, list(dem_sources), scene.crs, scene.transform, scene.hh.shape, reference.direction
            )
        dates.append(_write_date(scene, prefix, artifact_root, params))
        stats.append(scene_stats(scene, params))
        if previous is not None:
            pairs.append(_write_pair(previous, scene, "consecutive", prefix, artifact_root, params, terrain))
        previous = scene
        del scene

    if len(ordered) > 2:
        # La primera fecha se vuelve a leer: guardarla toda la serie costaría una escena más de RAM.
        first = _read(ordered[0][1], aoi["bbox"], params, speckle)
        pairs.append(_write_pair(first, previous, "full_window", prefix, artifact_root, params, terrain))
        del first
    del previous

    for item, qa in zip(dates, finalize_qa(stats, params)):
        item["qa"] = qa

    notices = (
        ([SYNTHETIC_NOTICE] if reference.data_kind == "synthetic" else [])
        + BASE_NOTICES
        + ([SHIFT_NOTICE] if params.correct_scene_shift else [])
        + [
            TERRAIN_NOTICE.format(
                detail=terrain_detail,
                dem="DEM sintético" if dem_data_kind == "synthetic" else "DEM Copernicus GLO-30",
            )
            if terrain is not None
            else NO_TERRAIN_NOTICE.format(reason=terrain_detail)
        ]
        + [QA_NOTICE.format(params.qa_outlier_db)]
        + ([MULTITEMPORAL_NOTICE.format(window=params.multitemporal_window, dates=len(ordered))] if speckle else [])
        + (
            [EXCLUDED_NOTICE.format(items=", ".join(f"{day} ({reason})" for day, reason in sorted(skipped)))]
            if skipped
            else []
        )
    )
    dem = _publish_dem(dem_sources, dem_data_kind, aoi, artifact_root)
    manifest = {
        "schema_version": 1,
        "aoi": aoi["id"],
        "series": {
            "id": series_id,
            "track": reference.track,
            "direction": reference.direction,
            "frame": reference.frame,
            "mode": reference.mode,
            "polarization": reference.polarization,
            "crid": reference.crid,
        },
        "data_kind": reference.data_kind,
        "maturity": maturity,
        "crs": crs,
        "bbox": list(aoi["bbox"]),
        "state_codes": STATE_CODES,
        "notices": notices,
        "dates": dates,
        "pairs": pairs,
    }
    if dem is not None:
        manifest["dem"] = dem
    target.mkdir(parents=True, exist_ok=True)
    (target / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest
