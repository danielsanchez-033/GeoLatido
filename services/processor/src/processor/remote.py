"""Procesado en línea sin recortes en disco (2026-11-15).

`run-remote` abre cada gránulo GCOV en NASA por HTTPS, lee en memoria solo la ventana de la zona (las mismas lecturas
que `read_scene` hace sobre un recorte) y escribe únicamente los artefactos del veredicto. Nada de `data/raw`.

Medido el 2026-11-15 con Delicias (T048A-F016, ventana de 1112 × 986 px): las cuatro capas necesarias suman 17,8 MB de
trozos comprimidos, y leerlas con bloques de 1 MB tardó unos 34 s por fecha. La copia de ingest, que además trae los
cubos de `radarGrid` con bloques de 16 MB, había recibido 8,7 GB sin terminar dos fechas. Sin `radarGrid` no se marcan
layover ni sombra: el manifiesto lo avisa, como con cualquier serie sin DEM.
"""
from __future__ import annotations

import io
import json
import os
import re
import threading
import time
import urllib.request
import zlib
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from urllib.parse import quote, urlsplit

import numpy as np

NASA_HOST_SUFFIX = ".earthdatacloud.nasa.gov"
BLOCK_SIZE = 1024 * 1024


class RemoteGranule:
    """Archivo remoto con el aspecto de una ruta para `process_series` (`.stem`, `.name`) y de archivo para h5py."""

    def __init__(self, granule_id: str, handle):
        self.stem = granule_id
        self.name = f"{granule_id}.h5"
        self._h = handle

    def __getattr__(self, attr):
        return getattr(self._h, attr)

    def close(self):
        self._h.close()


class LazyGranule(RemoteGranule):
    """Fecha cuyos metadatos ya se leyeron (`meta`, que `process_series` usa sin abrir el archivo) y cuyo contenido
    sigue llegando de NASA en segundo plano: el primer acceso espera a que termine de bajar."""

    def __init__(self, granule_id: str, meta, future: Future):
        self.stem = granule_id
        self.name = f"{granule_id}.h5"
        self.meta = meta
        self._future = future

    @property
    def _h(self):
        return self._future.result()

    def close(self):
        if self._future.done() and self._future.exception() is None:
            self._future.result().close()


def is_nasa_url(url: str) -> bool:
    parts = urlsplit(url)
    return parts.scheme == "https" and (parts.hostname or "").endswith(NASA_HOST_SUFFIX)


def open_remote(url: str, token: str):
    import fsspec  # solo para el modo en línea

    if not is_nasa_url(url):
        raise ValueError(f"Enlace rechazado: no se envía el token a {urlsplit(url).hostname}")
    fs = fsspec.filesystem(
        "https",
        client_kwargs={"headers": {"Authorization": f"Bearer {token}"}, "trust_env": False},
        skip_instance_cache=True,
    )
    return fs.open(url, mode="rb", cache_type="blockcache", block_size=BLOCK_SIZE)


GRID = "/science/LSAR/GCOV/grids/frequencyA"
IDENTIFICATION = "/science/LSAR/identification"
LAYERS = ("HHHH", "HVHV", "mask", "numberOfLooks", "inputDataExceptionMask")
# Peticiones HTTP a la vez por fecha (fsspec las lanza en paralelo con asyncio).
PARALLEL_REQUESTS = 48


def _window(x: np.ndarray, y: np.ndarray, bbox: list[float], epsg: int) -> tuple[slice, slice]:
    """La misma ventana que `read_scene` (gcov.py): filas y columnas de la malla que cubren la caja."""
    from rasterio.warp import transform_bounds

    left, bottom, right, top = transform_bounds("EPSG:4326", f"EPSG:{epsg}", *bbox)
    descending = y[0] > y[-1]
    keys = -y if descending else y
    low, high = (-top, -bottom) if descending else (bottom, top)
    row0, row1 = np.searchsorted(keys, [low, high])
    col0, col1 = np.searchsorted(x, [left, right])
    return slice(int(row0), int(row1)), slice(int(col0), int(col1))


def _decode(raw: bytes, filter_mask: int, filters: list[str], dtype: np.dtype, chunk: tuple[int, int]) -> np.ndarray:
    """Deshace los filtros de un trozo HDF5 en orden inverso: gzip y después shuffle. El bit i de filter_mask marca
    un filtro que no se aplicó a ese trozo."""
    data = raw
    for i in reversed(range(len(filters))):
        if filter_mask & (1 << i):
            continue
        if filters[i] == "gzip":
            data = zlib.decompress(data)
        elif filters[i] == "shuffle":
            size = np.dtype(dtype).itemsize
            data = np.frombuffer(data, np.uint8).reshape(size, -1).T.tobytes()
        else:
            raise ValueError(f"Filtro HDF5 no soportado: {filters[i]}")
    return np.frombuffer(data, dtype=dtype).reshape(chunk)


def _fetch_chunks(fs, url: str, wanted: list, attempts: int = 4) -> dict:
    """Pide los trozos con `cat_ranges` y reintenta los que fallan. `cat_ranges` no lanza el error de una petición
    cortada (en Guadalajara, 2026-11-15, `ClientConnectionResetError` con 4 fechas a la vez): lo deja en la lista en
    lugar de los bytes. Cada reintento pide solo los que faltan, con la mitad de peticiones simultáneas."""
    raw: dict = {}
    pending = list(wanted)
    batch = PARALLEL_REQUESTS
    for attempt in range(attempts):
        failed, last_error = [], None
        for i in range(0, len(pending), batch * 4):
            part = pending[i : i + batch * 4]
            blobs = fs.cat_ranges([url] * len(part), [p[2] for p in part], [p[2] + p[3] for p in part],
                                  batch_size=batch, on_error="return")
            for p, b in zip(part, blobs):
                if isinstance(b, (bytes, bytearray)):
                    raw[(p[0], p[1])] = b
                else:
                    failed.append(p)
                    last_error = b
        if not failed:
            return raw
        print(f"{len(failed)} trozos fallaron ({type(last_error).__name__}); reintento {attempt + 1}", flush=True)
        pending, batch = failed, max(4, batch // 2)
        time.sleep(1 + attempt)
    raise IOError(f"{len(pending)} trozos no se pudieron leer de NASA: {last_error!r}")


def read_window_parallel(url: str, token: str, bbox: list[float], fs=None, on_meta=None, gate=None) -> io.BytesIO:
    """Lee de NASA solo los trozos HDF5 que cortan la zona, todos a la vez, y devuelve un HDF5 en memoria con la misma
    estructura que un recorte de ingest (identificación, malla recortada y capas), listo para `process_series`.

    h5py lee los trozos de uno en uno a través de Python: en Tlaxcala (ventana de 3335 × 3166 px) una fecha tardó
    205 s (medido el 2026-11-15), casi todo esperando peticiones seguidas. Aquí h5py solo lee el índice (qué trozos
    y en qué bytes) y los trozos se piden en paralelo con `cat_ranges`; se descomprimen con zlib y numpy.

    `on_meta` recibe los metadatos (`gcov.read_meta`, las mismas comprobaciones de modo y polarización) en cuanto se
    abre el índice, antes de bajar los trozos; `gate` se llama justo antes de bajarlos, para ordenar las descargas.
    """
    import fsspec
    import h5py

    if not is_nasa_url(url):
        raise ValueError(f"Enlace rechazado: no se envía el token a {urlsplit(url).hostname}")
    fs = fs or fsspec.filesystem(
        "https", client_kwargs={"headers": {"Authorization": f"Bearer {token}"}, "trust_env": False}, skip_instance_cache=True
    )
    out = io.BytesIO()
    with fs.open(url, mode="rb", cache_type="blockcache", block_size=BLOCK_SIZE) as remote, h5py.File(remote, "r") as src:
        # La URL de NASA redirige a una firmada de S3: se piden los trozos a la final para no repetir la redirección.
        final_url = getattr(remote, "url", url)
        if on_meta is not None:
            from .gcov import read_meta

            on_meta(read_meta(src))
        grid = src[GRID]
        x, y = grid["xCoordinates"][()], grid["yCoordinates"][()]
        epsg = int(grid["projection"].attrs["epsg_code"])
        rows, cols = _window(x, y, bbox, epsg)
        if rows.stop <= rows.start or cols.stop <= cols.start:
            raise ValueError("La zona queda fuera del gránulo")
        plan = []  # (capa, offset del trozo, byte inicial, tamaño, filter_mask)
        meta = {}
        for name in LAYERS:
            if name not in grid:
                continue
            ds = grid[name]
            if not ds.chunks:
                raise ValueError(f"{name} no está troceada: no se puede leer por trozos")
            filters = [f for f in ("shuffle", "gzip") if (f == "shuffle" and ds.shuffle) or (f == "gzip" and ds.compression == "gzip")]
            other = set(getattr(ds, "_filters", {}).keys()) - {"shuffle", "gzip"}
            if other or ds.fletcher32 or ds.scaleoffset is not None:
                raise ValueError(f"{name}: filtros no soportados {sorted(other)}")
            meta[name] = (ds.dtype, ds.chunks, filters, ds.fillvalue)
            cr, cc = ds.chunks
            for r0 in range(rows.start // cr * cr, rows.stop, cr):
                for c0 in range(cols.start // cc * cc, cols.stop, cc):
                    info = ds.id.get_chunk_info_by_coord((r0, c0))
                    if info.byte_offset is None:  # trozo sin escribir: vale el fillvalue
                        plan.append((name, (r0, c0), None, 0, 0))
                    else:
                        plan.append((name, (r0, c0), info.byte_offset, info.size, info.filter_mask))
        wanted = [p for p in plan if p[2] is not None]
        if gate is not None:
            gate()
        raw = _fetch_chunks(fs, final_url, wanted)
        shape = (rows.stop - rows.start, cols.stop - cols.start)
        arrays = {}
        for name, (dtype, chunk, filters, fill) in meta.items():
            arr = np.full(shape, fill if fill is not None else 0, dtype=dtype)
            for p in (q for q in plan if q[0] == name):
                r0, c0 = p[1]
                block = _decode(raw[(name, p[1])], p[4], filters, dtype, chunk) if p[2] is not None else np.full(chunk, fill, dtype)
                rs, re_ = max(r0, rows.start), min(r0 + chunk[0], rows.stop)
                cs, ce = max(c0, cols.start), min(c0 + chunk[1], cols.stop)
                arr[rs - rows.start : re_ - rows.start, cs - cols.start : ce - cols.start] = block[rs - r0 : re_ - r0, cs - c0 : ce - c0]
            arrays[name] = arr
        with h5py.File(out, "w") as dst:
            src.copy(src[IDENTIFICATION], dst.require_group("/science/LSAR"), name="identification")
            g = dst.require_group(GRID)
            g["xCoordinates"] = x[cols]
            g["yCoordinates"] = y[rows]
            src.copy(grid["projection"], g, name="projection")
            for name, arr in arrays.items():
                g.create_dataset(name, data=arr)
    out.seek(0)
    return out


def latest_granules(catalog_url: str, aoi: dict, series_spec: dict, last: int, getter=None, catalog_id: str | None = None) -> list[dict]:
    """Las `last` fechas más recientes de la serie configurada, según catalog (HTTP)."""
    def get(url):
        with urllib.request.urlopen(url, timeout=120) as r:  # noqa: S310 - URL de catalog de la propia pila
            return json.load(r)

    data = (getter or get)(f"{catalog_url.rstrip('/')}/aois/{quote(aoi['id'], safe='')}/series")
    key = (series_spec["track"], series_spec["direction"], series_spec["frame"])
    matches = [s for s in data if (s["track"], s["direction"], s["frame"]) == key]
    # Una misma pista y marco puede tener varias series (otro modo o versión; Venecia, 2026-11-15, tenía 3): manda
    # la que eligió online por su id de catalog; sin él, la de más fechas.
    exact = [s for s in matches if catalog_id and s["id"] == catalog_id]
    if exact:
        matches = exact
    if not matches:
        raise ValueError(f"No hay en catalog ninguna serie {series_spec['id']}")
    chosen = max(matches, key=lambda s: len(s["granules"]))
    # Sin los gránulos en modo mixto (…_DHDH_M_…), que read_meta rechaza: así no tumban la serie entera.
    granules = sorted((g for g in chosen["granules"] if not re.search(r"_[A-Z]{4}_M_\d{8}T", g["id"])), key=lambda g: g.get("date") or "")
    return granules[-last:]


# Fechas que bajan a la vez. Con la red de casa (unos 2,5 MB/s medidos en Guadalajara el 2026-11-15) bajar las 4 a
# la vez hace que todas terminen al final; de 2 en 2 y por fecha, la primera llega antes y el cálculo empieza ya.
DOWNLOADS_AT_ONCE = 2


def _start_downloads(granules: list[dict], token: str, bbox: list[float]):
    """Abre todas las fechas a la vez (solo el índice y los metadatos, unos segundos) y deja bajando sus trozos en
    orden de fecha, `DOWNLOADS_AT_ONCE` cada vez. Devuelve en cuanto están los metadatos: `process_series` calcula
    la fecha 1 y el par 1-2 mientras bajan las siguientes."""
    granules = sorted(granules, key=lambda g: g.get("date") or "")
    metas = [Future() for _ in granules]
    downloaded = [threading.Event() for _ in granules]
    inicio = time.monotonic()

    def leer(i: int, g: dict):
        def gate():
            if i >= DOWNLOADS_AT_ONCE:
                downloaded[i - DOWNLOADS_AT_ONCE].wait()

        try:
            print(f"Leyendo en NASA {g['id']} ({g.get('date')}), solo los trozos de la zona", flush=True)
            data = read_window_parallel(g["download_url"], token, bbox, on_meta=metas[i].set_result, gate=gate)
            print(f"Fecha {g.get('date')} leída a los {time.monotonic() - inicio:.0f} s", flush=True)
            return data
        except BaseException as exc:
            if not metas[i].done():
                metas[i].set_exception(exc)
            raise
        finally:
            downloaded[i].set()

    pool = ThreadPoolExecutor(max_workers=len(granules))
    futures = [pool.submit(leer, i, g) for i, g in enumerate(granules)]
    try:
        files = [LazyGranule(g["id"], m.result(), f) for g, m, f in zip(granules, metas, futures)]
    except BaseException:
        pool.shutdown(wait=False, cancel_futures=True)
        raise
    return pool, files


def run_remote(aoi: dict, series_id: str, artifact_root: Path, catalog_url: str, last: int, process, opener=None, getter=None,
               catalog_id: str | None = None) -> dict:
    """Abre las fechas en NASA y llama a `process(files)`; cierra todo al terminar. Devuelve el manifiesto."""
    token = os.environ.get("EARTHDATA_TOKEN", "").strip()
    if not token and opener is None:
        raise ValueError("Falta EARTHDATA_TOKEN: sin él NASA no deja leer los gránulos")
    spec = next((s for s in aoi.get("series", []) if s["id"] == series_id), None)
    if spec is None:
        raise ValueError(f"La serie {series_id} no está en la zona {aoi['id']}")
    granules = latest_granules(catalog_url, aoi, spec, last, getter, catalog_id)
    if len(granules) < 2:
        raise ValueError("Hacen falta al menos dos fechas")
    files = []
    pool = None
    try:
        if opener is None:
            pool, files = _start_downloads(granules, token, aoi["bbox"])
        else:
            for g in granules:
                print(f"Abriendo en NASA {g['id']} ({g.get('date')}), solo la ventana de la zona", flush=True)
                files.append(RemoteGranule(g["id"], opener(g["download_url"])))
        inicio = time.monotonic()
        manifest = process(files)
        print(f"Cálculo de los pares (solapado con la lectura): {time.monotonic() - inicio:.0f} s", flush=True)
        return manifest
    finally:
        if pool is not None:
            pool.shutdown(wait=False, cancel_futures=True)
        for f in files:
            try:
                f.close()
            except Exception:  # noqa: BLE001
                pass
