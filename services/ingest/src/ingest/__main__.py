"""CLI de ingesta: python -m ingest fetch --aoi parral --series T048A-F015, o plan --aoi parral."""
from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml

from .fetch import FetchError, fetch_series, get_json, is_nasa_url, open_remote
from .plan import CmrPlanSource, build_plan, write_plan
from .subset import SubsetError


def _token_and_aoi(args: argparse.Namespace) -> tuple[str, dict] | int:
    token = os.environ.get("EARTHDATA_TOKEN", "").strip()
    if not token:
        print("Error: falta EARTHDATA_TOKEN (cópialo a .env desde tu cuenta de Earthdata)", file=sys.stderr)
        return 2
    path = args.aoi_dir / f"{args.aoi}.yaml"
    if not path.is_file():
        print(f"Error: zona desconocida: {args.aoi}", file=sys.stderr)
        return 1
    return token, yaml.safe_load(path.read_text(encoding="utf-8"))


def plan(args: argparse.Namespace) -> int:
    loaded = _token_and_aoi(args)
    if isinstance(loaded, int):
        return loaded
    token, aoi = loaded
    source = CmrPlanSource(token, get_json, open_remote, is_nasa_url)
    try:
        body = build_plan(aoi, args.catalog_url, get_json, source, datetime.now(timezone.utc), args.days)
    except FetchError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    target = write_plan(args.data_dir, body)
    for series in body["series"]:
        print(f"{series['series']}: última pasada {series['last_acquired_at']}, configuración {series['reference_config_id']}")
        for item in series["passes"]:
            change = " (configuración distinta)" if item["same_config"] is False else ""
            print(f"  {item['expected_at']}  {item['status']:<11} {item['plan'] or '-'}{change}")
    print(f"Plan de observación: {target}. Un plan no garantiza la adquisición.")
    return 0


def fetch(args: argparse.Namespace) -> int:
    loaded = _token_and_aoi(args)
    if isinstance(loaded, int):
        return loaded
    token, aoi = loaded
    started = time.monotonic()
    try:
        result = fetch_series(aoi, args.series, args.data_dir, token, args.catalog_url, args.limit, last=args.last)
    except (FetchError, SubsetError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    megabytes = sum(item.stat().st_size for item in result.target.glob("*.h5")) / 1024**2
    print(
        f"{args.series}: {len(result.written)} recortes nuevos, {len(result.skipped)} ya existían, "
        f"{megabytes:.0f} MB en disco, {result.bytes_requested / 1024**2:.0f} MB pedidos a NASA, "
        f"{time.monotonic() - started:.0f} s"
    )
    for warning in result.warnings:
        print(f"Aviso: {warning}", file=sys.stderr)
    if result.log:
        print(f"Registro de ingesta: {result.log}")
    if result.excluded:
        print(f"Excluidos en config/aois/{args.aoi}.yaml, no se traen: {', '.join(result.excluded)}")
    for name in result.stale:
        print(f"Aviso: {name}.h5 está excluido pero sigue en {result.target}; apártalo antes de processor run", file=sys.stderr)
    print(f"Siguiente paso, en processor: run --aoi {args.aoi} --series {args.series} --input {result.target}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="ingest")
    parser.add_argument("--aoi-dir", type=Path, default=Path("/config/aois"))
    parser.add_argument("--data-dir", type=Path, default=Path("/data"))
    commands = parser.add_subparsers(dest="command", required=True)

    remote = commands.add_parser("fetch", help="Trae por HTTPS el recorte de la zona desde NASA")
    remote.add_argument("--aoi", required=True)
    remote.add_argument("--series", required=True)
    remote.add_argument("--limit", type=int, help="Solo las primeras N fechas; útil para una primera prueba")
    remote.add_argument("--last", type=int, help="Solo las N fechas más recientes (procesado en línea)")
    remote.add_argument("--catalog-url", default=os.environ.get("CATALOG_URL", "http://localhost:8080/api/catalog"))
    remote.set_defaults(handler=fetch)

    planned = commands.add_parser("plan", help="Consulta el plan de observación de NISAR para las próximas pasadas")
    planned.add_argument("--aoi", required=True)
    planned.add_argument("--days", type=int, default=30, help="Horizonte en días desde ahora")
    planned.add_argument("--catalog-url", default=os.environ.get("CATALOG_URL", "http://localhost:8080/api/catalog"))
    planned.set_defaults(handler=plan)

    args = parser.parse_args()
    return args.handler(args)


if __name__ == "__main__":
    sys.exit(main())
