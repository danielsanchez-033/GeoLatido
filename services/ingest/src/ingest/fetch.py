"""Trae por HTTPS solo el recorte de una zona, sin descargar gránulos completos."""
from __future__ import annotations

import asyncio
import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable
from urllib.parse import quote, urlsplit

import aiohttp
import fsspec

from . import log
from .subset import subset

# Valores que documenta ASF para leer NISAR por HTTPS.
CACHE_TYPE = "background"
BLOCK_SIZE = 16 * 1024 * 1024
NASA_HOST_SUFFIX = ".earthdatacloud.nasa.gov"


class FetchError(RuntimeError):
    """No se pudo obtener un gránulo; el mensaje nunca incluye el token."""


@dataclass(frozen=True)
class FetchResult:
    target: Path
    written: list[str]
    skipped: list[str]
    excluded: list[str] = field(default_factory=list)  # Declarados inservibles en la zona; no se traen.
    stale: list[str] = field(default_factory=list)  # Excluidos que siguen en disco; processor los leería.
    log: Path | None = None  # ingest.json de la serie; None si no se escribió.
    bytes_requested: int = 0  # Pedidos a NASA en esta ejecución.
    warnings: list[str] = field(default_factory=list)


def is_nasa_url(url: str) -> bool:
    parts = urlsplit(url)
    return parts.scheme == "https" and (parts.hostname or "").endswith(NASA_HOST_SUFFIX)


def get_json(url: str) -> Any:
    request = urllib.request.Request(url, headers={"User-Agent": "nisar-veredictos"})
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.load(response)
    except (urllib.error.URLError, TimeoutError) as exc:
        raise FetchError(f"El servicio catalog no respondió en {url}") from exc


def open_remote(url: str, token: str, block_size: int):
    filesystem = fsspec.filesystem(
        "https",
        client_kwargs={"headers": {"Authorization": f"Bearer {token}"}, "trust_env": False},
        skip_instance_cache=True,
    )
    return filesystem.open(url, mode="rb", cache_type=CACHE_TYPE, block_size=block_size)


def select_series(available: list[dict], wanted: dict) -> dict:
    """Localiza la serie configurada; si hay varias versiones no elige por su cuenta."""
    matches = [
        item
        for item in available
        if (item["track"], item["direction"], item["frame"]) == (wanted["track"], wanted["direction"], wanted["frame"])
    ]
    if len(matches) != 1:
        found = ", ".join(item["id"] for item in matches) or "ninguna"
        raise FetchError(f"Se esperaba una serie para {wanted['id']} y se encontró: {found}")
    return matches[0]


def _subset_one(
    granule: dict, bbox: list[float], wanted: dict, destination: Path, token: str, block_size: int
) -> tuple[int | None, float]:
    """Escribe el recorte; devuelve los bytes pedidos al servidor (None si fsspec no los cuenta) y los segundos."""
    partial = destination.with_suffix(".part")
    started = time.monotonic()
    try:
        with open_remote(granule["download_url"], token, block_size) as remote:
            subset(remote, bbox, wanted, partial)
            requested = getattr(getattr(remote, "cache", None), "total_requested_bytes", None)
        partial.replace(destination)
        return requested, time.monotonic() - started
    except (OSError, aiohttp.ClientError, asyncio.TimeoutError) as exc:
        raise FetchError(
            f"No se pudo leer {granule['id']} ({type(exc).__name__}). Revisa el token de Earthdata y la conexión."
        ) from exc
    finally:
        partial.unlink(missing_ok=True)


def _passes_by_granule(json_getter: Callable[[str], Any], catalog_url: str, aoi_id: str) -> tuple[dict[str, dict], str | None]:
    """Pasadas de la línea de tiempo por granule_id. Si catalog falla, vacío y un aviso: la ingesta sigue."""
    url = f"{catalog_url.rstrip('/')}/aois/{quote(aoi_id, safe='')}/timeline"
    try:
        return {item["granule_id"]: item for item in json_getter(url)["passes"]}, None
    except (FetchError, KeyError, TypeError) as exc:
        return {}, f"Sin línea de tiempo de catalog ({type(exc).__name__}); acquired_at y published_at quedan en null"


def fetch_series(
    aoi: dict,
    series_id: str,
    data_dir: Path,
    token: str,
    catalog_url: str,
    limit: int | None = None,
    json_getter: Callable[[str], Any] = get_json,
    is_allowed: Callable[[str], bool] = is_nasa_url,
    block_size: int = BLOCK_SIZE,
    *,
    last: int | None = None,
) -> FetchResult:
    wanted = next((item for item in aoi["series"] if item["id"] == series_id), None)
    if wanted is None:
        raise FetchError(f"La serie {series_id} no está configurada en la zona {aoi['id']}")

    available = json_getter(f"{catalog_url.rstrip('/')}/aois/{quote(aoi['id'], safe='')}/series")
    chosen = select_series(available, wanted)
    granules = chosen["granules"]
    # Se aplica aquí también, por si catalog todavía no conoce la exclusión.
    banned = {entry["granule"] for entry in wanted.get("exclude") or []}
    excluded = [granule["id"] for granule in granules if granule["id"] in banned]
    granules = [granule for granule in granules if granule["id"] not in banned]

    passes, warning = _passes_by_granule(json_getter, catalog_url, aoi["id"])
    warnings = [warning] if warning else []
    context = {
        granule["id"]: {
            "date": granule.get("date"),
            "source_size_mb": granule.get("size_mb"),
            "acquired_at": passes.get(granule["id"], {}).get("acquired_at"),
            "published_at": passes.get(granule["id"], {}).get("published_at"),
        }
        for granule in granules
    }

    if limit is not None:
        granules = granules[:limit]
    if last is not None:
        # Las N fechas más recientes (procesado en línea, 2026-11-15): las de catalog vienen en orden de fecha.
        granules = sorted(granules, key=lambda g: g.get("date") or "")[-last:]

    target = data_dir / "raw" / "real" / aoi["id"] / series_id
    target.mkdir(parents=True, exist_ok=True)
    stale = sorted(name for name in banned if (target / f"{name}.h5").exists())

    log_path = target / log.LOG_NAME
    previous, warning = log.load(log_path)
    warnings += [warning] if warning else []
    fresh: dict[str, log.GranuleRecord] = {}
    header = {
        "aoi": aoi["id"],
        "series": series_id,
        "catalog_series": chosen["id"],
        "bbox": aoi["bbox"],
        "read": {"cache_type": CACHE_TYPE, "block_size_bytes": block_size},
    }
    excluded_log = [{"id": entry["granule"], "reason": entry.get("reason")} for entry in wanted.get("exclude") or []]

    def save() -> None:
        on_disk = {path.stem: path.stat().st_size for path in target.glob("*.h5") if path.stem not in banned}
        log.write(log_path, header, log.merge(previous, fresh, on_disk, context), excluded_log, stale)

    written, skipped = [], []
    for granule in granules:
        url = granule["download_url"]
        if not is_allowed(url):
            raise FetchError(f"{granule['id']}: enlace rechazado, no se envía el token a {urlsplit(url).hostname}")
        destination = target / f"{granule['id']}.h5"
        if destination.exists():
            skipped.append(granule["id"])
            continue
        requested, seconds = _subset_one(granule, aoi["bbox"], wanted, destination, token, block_size)
        info = context[granule["id"]]
        fresh[granule["id"]] = log.GranuleRecord(
            id=granule["id"],
            date=info["date"],
            acquired_at=info["acquired_at"],
            published_at=info["published_at"],
            source_size_mb=info["source_size_mb"],
            subset_bytes=destination.stat().st_size,
            bytes_requested=requested,
            seconds=round(seconds, 3),
            fetched_at=log.utc_now(),
            origin="fetched",
        )
        written.append(granule["id"])
        save()  # Tras cada recorte: si el siguiente falla, este queda registrado.

    if any(target.glob("*.h5")) or log_path.exists():
        save()
    return FetchResult(
        target=target,
        written=written,
        skipped=skipped,
        excluded=excluded,
        stale=stale,
        log=log_path if log_path.exists() else None,
        bytes_requested=sum(record.bytes_requested or 0 for record in fresh.values()),
        warnings=warnings,
    )
