"""Hundimiento del suelo con interferogramas NISAR GUNW, leídos en memoria solo en la ventana de la zona (2026-11-15).

GCOV (intensidad) no tiene fase y no puede medir hundimientos. GUNW sí: su fase desenrollada (`unwrappedPhase`)
entre dos pasadas de la misma órbita es el cambio de distancia al satélite. Aquí:

1. Se buscan en CMR los GUNW de la órbita con más pares que cubran la zona, y se toman los últimos `pairs` pares
   consecutivos (12 días cada uno).
2. De cada uno se lee la ventana de la zona: fase desenrollada menos la pantalla ionosférica que trae el propio
   producto, componentes conectadas, coherencia y máscara (agua y franjas inválidas fuera).
3. La fase de cada par solo es relativa dentro de una componente conectada: se usa la componente con más píxeles
   válidos y se resta su mediana. Así cada par mide cuánto se alejó o acercó cada punto **respecto al resto de la
   zona**, no un movimiento absoluto.
4. Los pares se suman (pila) y se pasa a milímetros por año en la línea de vista del satélite.

Signo, comprobado con datos reales el 2026-11-15 en la Ciudad de México (zona que se hunde unos 25-35 cm al año):
en 7 de 8 interferogramas de las pistas 019 A y 113 D, Nezahualcóyotl tuvo más fase que Ciudad Universitaria (roca
estable), +0,42 rad de media cada 12 días, unos 8 mm de alejamiento (≈ 24 cm/año en la línea de vista). Por tanto
**fase positiva = el suelo se aleja del satélite**, que en terreno llano es sobre todo hundimiento.

Límites declarados en el resultado: la atmósfera (vapor de agua) puede sumar centímetros por par; la medida es en la
línea de vista y no separa movimiento vertical de horizontal; los umbrales no están calibrados.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import os
import urllib.request
import warnings
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlencode

import numpy as np

from .remote import BLOCK_SIZE, _window, is_nasa_url

CMR = "https://cmr.earthdata.nasa.gov/search/granules.umm_json"
COLLECTION = "NISAR_L2_GUNW_PROVISIONAL_V1"
GRID = "/science/LSAR/GUNW/grids/frequencyA"
LIGHT_SPEED = 299_792_458.0
# Coherencia mínima de un píxel en un par: por debajo, la fase es casi ruido.
MIN_COHERENCE = 0.3
# Un píxel entra en la pila si es válido en al menos esta parte de los pares.
MIN_PAIR_SHARE = 0.7
# «Se hunde» si se aleja al menos este ritmo respecto a la zona y más de 2 veces su incertidumbre típica.
MIN_RATE_MM_YR = 20.0
# Incertidumbre de la velocidad: dispersión de los pares en cada píxel. No se usa la dispersión espacial de la
# zona: en la Ciudad de México gran parte de la zona se mueve de verdad y el umbral salía en 199 mm/año.
SIGN_CHECK = (
    "Signo comprobado el 2026-11-15 en la Ciudad de México: fase positiva = el suelo se aleja del satélite "
    "(7 de 8 interferogramas, Nezahualcóyotl frente a Ciudad Universitaria)."
)


def _parse(granule_id: str) -> dict | None:
    """NISAR_L2_PR_GUNW_032_048_A_015_033_4000_SH_<ref ini>_<ref fin>_<sec ini>_<sec fin>_..."""
    p = granule_id.split("_")
    try:
        return {"track": int(p[5]), "direction": p[6], "frame": int(p[7]), "pol": p[10],
                "reference": p[11][:8], "secondary": p[13][:8]}
    except (IndexError, ValueError):
        return None


def find_pairs(bbox: list[float], pairs: int = 8, getter=None) -> list[dict]:
    """Los últimos `pairs` interferogramas de la órbita (pista, sentido y marco) con más pares sobre la zona."""
    w, s, e, n = bbox
    params = {"short_name": COLLECTION, "bounding_box": f"{w},{s},{e},{n}", "page_size": 500, "sort_key": "-start_date"}
    url = f"{CMR}?{urlencode(params)}"
    if getter is None:
        with urllib.request.urlopen(url, timeout=60) as r:  # noqa: S310 (CMR fijo)
            items = json.load(r)["items"]
    else:
        items = getter(url)
    groups: dict[tuple, list[dict]] = {}
    for it in items:
        umm = it["umm"]
        meta = _parse(umm["GranuleUR"])
        link = next((u["URL"] for u in umm.get("RelatedUrls", []) if u["URL"].startswith("https") and u["URL"].endswith(".h5")), None)
        if not meta or not link or not is_nasa_url(link):
            continue
        groups.setdefault((meta["track"], meta["direction"], meta["frame"]), []).append({**meta, "id": umm["GranuleUR"], "url": link})
    if not groups:
        return []
    best = max(groups.values(), key=len)
    # Un par por fecha de referencia (la versión más reciente gana) y en orden de fecha.
    by_ref = {}
    for g in sorted(best, key=lambda g: g["id"]):
        by_ref[g["reference"]] = g
    return sorted(by_ref.values(), key=lambda g: g["reference"])[-pairs:]


def _valid(mask: np.ndarray) -> np.ndarray:
    """Máscara GUNW: bits 0-7 en dígitos decimales (agua, franja de referencia, franja secundaria); 255 es relleno."""
    sub = (mask & 0xFF).astype(np.int32)
    water = sub // 100 == 1
    return (sub != 255) & ~water & (sub % 10 != 0) & ((sub // 10) % 10 != 0)


def read_pair(url: str, token: str, bbox: list[float], fs=None) -> dict:
    """Ventana de la zona de un GUNW: desplazamiento relativo en mm (positivo = se aleja) y su malla."""
    import fsspec
    import h5py

    if not is_nasa_url(url):
        raise ValueError("Enlace rechazado: no se envía el token fuera de NASA")
    fs = fs or fsspec.filesystem("https", client_kwargs={"headers": {"Authorization": f"Bearer {token}"}, "trust_env": False},
                                 skip_instance_cache=True)
    with fs.open(url, mode="rb", cache_type="blockcache", block_size=BLOCK_SIZE) as remote, h5py.File(remote, "r") as h:
        grid = h[GRID]
        u = grid["unwrappedInterferogram"]
        x, y = u["xCoordinates"][()], u["yCoordinates"][()]
        epsg = int(u["projection"].attrs["epsg_code"])
        rows, cols = _window(x, y, bbox, epsg)
        if rows.stop <= rows.start or cols.stop <= cols.start:
            raise ValueError("La zona queda fuera del interferograma")
        wavelength = LIGHT_SPEED / float(grid["centerFrequency"][()])
        phase = u["HH/unwrappedPhase"][rows, cols].astype(np.float64)
        if "ionospherePhaseScreen" in u["HH"]:
            phase -= u["HH/ionospherePhaseScreen"][rows, cols]
        components = u["HH/connectedComponents"][rows, cols]
        coherence = u["HH/coherenceMagnitude"][rows, cols]
        valid = np.isfinite(phase) & (coherence >= MIN_COHERENCE) & (components != 0) & (components != 65535)
        valid &= _valid(u["mask"][rows, cols])
    if valid.any():
        # La fase solo es comparable dentro de una misma componente conectada: se usa la mayor.
        ids, counts = np.unique(components[valid], return_counts=True)
        valid &= components == ids[np.argmax(counts)]
    mm = phase * wavelength / (4 * math.pi) * 1000.0
    if valid.any():
        mm -= np.median(mm[valid])
    mm[~valid] = np.nan
    return {"mm": mm.astype(np.float32), "x": x[cols], "y": y[rows], "epsg": epsg, "wavelength_m": wavelength}


def _smooth(values: np.ndarray, size: int = 5) -> np.ndarray:
    from scipy import ndimage

    ok = np.isfinite(values)
    filled = np.where(ok, values, 0.0)
    num = ndimage.uniform_filter(filled, size)
    den = ndimage.uniform_filter(ok.astype(np.float64), size)
    out = np.where(den > 0.3, num / np.maximum(den, 1e-9), np.nan)
    out[~ok] = np.nan
    return out.astype(np.float32)


def stack(results: list[dict], granules: list[dict]) -> tuple[np.ndarray, dict]:
    """Suma los pares con la misma malla y devuelve la velocidad (mm/año, positiva = se aleja) y el resumen."""
    base = results[0]
    same = [(r, g) for r, g in zip(results, granules) if r["mm"].shape == base["mm"].shape
            and np.array_equal(r["x"], base["x"]) and np.array_equal(r["y"], base["y"])]
    cube = np.stack([r["mm"] for r, _ in same])
    count = np.isfinite(cube).sum(axis=0)
    total = np.nansum(cube, axis=0)
    days = sum((dt.date.fromisoformat(f"{g['secondary'][:4]}-{g['secondary'][4:6]}-{g['secondary'][6:]}")
                - dt.date.fromisoformat(f"{g['reference'][:4]}-{g['reference'][4:6]}-{g['reference'][6:]}")).days
               for _, g in same)
    # Cada píxel suma sus pares válidos; se escala al periodo completo para no castigar a los que faltan en uno.
    enough = count >= max(1, math.ceil(MIN_PAIR_SHARE * len(same)))
    cumulative = np.where(enough, total * len(same) / np.maximum(count, 1), np.nan)
    rate = _smooth(cumulative / days * 365.25) if days else np.full(cumulative.shape, np.nan, np.float32)
    rate -= np.float32(np.nanmedian(rate)) if np.isfinite(rate).any() else 0
    finite = rate[np.isfinite(rate)]
    spread = float(1.4826 * np.median(np.abs(finite - np.median(finite)))) if finite.size else None
    # Error de la suma de n pares independientes: desviación de los pares · √n, pasada a mm/año.
    with np.errstate(all="ignore"), warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        per_pair = np.nanstd(cube, axis=0)
    sigma = np.where(enough, per_pair * np.sqrt(np.maximum(count, 1)) / max(days, 1) * 365.25, np.nan)
    noise = float(np.nanmedian(sigma)) if np.isfinite(sigma).any() else None
    threshold = max(MIN_RATE_MM_YR, 2 * noise) if noise is not None else MIN_RATE_MM_YR
    sinking = np.isfinite(rate) & (rate >= threshold)
    summary = {
        "pairs": [{"id": g["id"], "reference": g["reference"], "secondary": g["secondary"]} for _, g in same],
        "track": same[0][1]["track"], "direction": same[0][1]["direction"], "frame": same[0][1]["frame"],
        "days": days,
        "wavelength_m": base["wavelength_m"],
        "valid_fraction": float(np.isfinite(rate).mean()),
        "spread_mm_yr": spread,
        "noise_mm_yr": noise,
        "threshold_mm_yr": threshold,
        "sinking_fraction": float(sinking.sum() / max(1, np.isfinite(rate).sum())),
        # Lo más rápido como percentil 99: el máximo de un solo píxel suele ser un valor aislado de la atmósfera.
        "max_rate_mm_yr": float(np.nanpercentile(rate, 99)) if finite.size else None,
    }
    return rate, summary


def run_subsidence(aoi: dict, artifact_root: Path, pairs: int = 8, token: str | None = None, reader=None, getter=None) -> dict:
    """Busca, lee y apila los GUNW de la zona; escribe `<zona>/subsidence/rate.tif` y `subsidence.json`."""
    import rasterio
    from rasterio.transform import from_origin
    from rasterio.warp import transform as warp

    token = token if token is not None else os.environ.get("EARTHDATA_TOKEN", "").strip()
    if not token and reader is None:
        raise ValueError("Falta EARTHDATA_TOKEN")
    granules = find_pairs(aoi["bbox"], pairs, getter)
    out_dir = artifact_root / aoi["id"] / "subsidence"
    if len(granules) < 2:
        result = {"status": "no_interferograms", "pairs": [], "generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "subsidence.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        return result
    read = reader or (lambda g: read_pair(g["url"], token, aoi["bbox"]))
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(read, granules))
    rate, summary = stack(results, granules)
    base = results[0]
    dx = float(base["x"][1] - base["x"][0])
    dy = float(abs(base["y"][1] - base["y"][0]))
    descending = base["y"][0] > base["y"][-1]
    grid = rate if descending else rate[::-1]
    top = float(base["y"].max())
    transform = from_origin(float(base["x"][0]) - dx / 2, top + dy / 2, dx, dy)
    out_dir.mkdir(parents=True, exist_ok=True)
    profile = dict(driver="GTiff", width=grid.shape[1], height=grid.shape[0], count=1, dtype="float32",
                   crs=f"EPSG:{base['epsg']}", transform=transform, nodata=float("nan"), compress="deflate")
    with rasterio.open(out_dir / "rate.tif", "w", **profile) as dst:
        dst.write(grid.astype(np.float32), 1)
    # Lugar del hundimiento más rápido (centro de su píxel), para llevar el mapa allí.
    where = None
    if summary["max_rate_mm_yr"] is not None and summary["sinking_fraction"] > 0:
        # El punto más rápido con un suavizado mayor (15 × 15 píxeles, ~1,2 km), para no caer en un píxel aislado.
        wide = _smooth(grid, 15)
        r, c = np.unravel_index(np.nanargmax(wide), wide.shape)
        px, py = transform * (c + 0.5, r + 0.5)
        (lon,), (lat,) = warp(f"EPSG:{base['epsg']}", "EPSG:4326", [px], [py])
        where = {"lon": round(lon, 5), "lat": round(lat, 5)}
    result = {
        "status": "computed",
        **summary,
        "fastest_point": where,
        "posting_m": dx,
        "rate_layer": f"{aoi['id']}/subsidence/rate.tif",
        "sign_check": SIGN_CHECK,
        "calibrated": False,
        "generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
    }
    (out_dir / "subsidence.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return result
