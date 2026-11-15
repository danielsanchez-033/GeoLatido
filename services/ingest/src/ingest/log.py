"""Registro de ingesta por serie (ingest.json): qué se leyó, cuánto y cuándo.

Lo que no se midió queda en None; nunca se estima.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "ingest-log/1"
LOG_NAME = "ingest.json"


@dataclass(frozen=True)
class GranuleRecord:
    id: str
    date: str | None
    acquired_at: str | None
    published_at: str | None
    source_size_mb: float | None
    subset_bytes: int
    bytes_requested: int | None
    seconds: float | None
    fetched_at: str | None
    origin: str  # "fetched" o "found_on_disk"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load(path: Path) -> tuple[dict[str, dict], str | None]:
    """Entradas del registro anterior por id, y un aviso si estaba ilegible (se aparta, no se borra)."""
    if not path.exists():
        return {}, None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("schema") != SCHEMA:
            raise ValueError(f"esquema {data.get('schema')!r}")
        return {item["id"]: item for item in data["granules"]}, None
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        bad = path.with_name(path.name + ".bad")
        path.replace(bad)
        return {}, f"{path} no se pudo leer ({type(exc).__name__}); se apartó a {bad.name} y se empieza uno nuevo"


def merge(previous: dict[str, dict], fresh: dict[str, GranuleRecord], on_disk: dict[str, int], context: dict) -> list[dict]:
    """Una entrada por recorte presente: la nueva, la anterior o una de found_on_disk.

    `on_disk` va de granule_id a bytes del archivo; `context` de granule_id a lo que sabe catalog.
    """
    entries = []
    for name in sorted(on_disk):
        if name in fresh:
            entries.append(asdict(fresh[name]))
        elif name in previous:
            entries.append(previous[name])
        else:
            info = context.get(name, {})
            record = GranuleRecord(
                id=name,
                date=info.get("date"),
                acquired_at=info.get("acquired_at"),
                published_at=info.get("published_at"),
                source_size_mb=info.get("source_size_mb"),
                subset_bytes=on_disk[name],
                bytes_requested=None,
                seconds=None,
                fetched_at=None,
                origin="found_on_disk",
            )
            entries.append(asdict(record))
    return entries


def write(path: Path, header: dict, granules: list[dict], excluded: list[dict], stale: list[str]) -> None:
    """Escribe en un .part y lo renombra: nunca queda a medio escribir."""
    body = {
        "schema": SCHEMA,
        "data_kind": "real",
        **header,
        "published_at_basis": "cmr_updated",
        "updated_at": utc_now(),
        "granules": granules,
        "excluded": excluded,
        "stale": sorted(stale),
    }
    partial = path.with_name(path.name + ".part")
    partial.write_text(json.dumps(body, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    partial.replace(path)
