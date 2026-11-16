"""CLI del procesador: datos sintéticos para desarrollo y gránulos reales locales."""
from __future__ import annotations

import argparse
import os
import shutil
import urllib.request
import sys
from pathlib import Path

import yaml

from .change import Params
from .gcov import GranuleError
from .pipeline import excluded_granules, process_series
from .synthetic import PARRAL_SERIES, generate_series, write_synthetic_dem
from .terrain import glo30_tiles


def load_aoi(aoi_dir: Path, aoi_id: str) -> dict:
    path = aoi_dir / f"{aoi_id}.yaml"
    if not path.is_file():
        raise SystemExit(f"Zona desconocida: {aoi_id}")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def series_id_for(spec) -> str:
    return f"T{spec.track:03d}{spec.direction}-F{spec.frame:03d}"


def seed_synthetic(args: argparse.Namespace) -> int:
    # Con EARTHDATA_TOKEN la app procesa datos reales en línea: los sintéticos sobran (compose pone SEED_SKIP=1).
    if os.environ.get("SEED_SKIP", "") == "1" and not args.force:
        print("Hay datos reales disponibles (EARTHDATA_TOKEN): no se generan datos sintéticos")
        return 0
    aoi = load_aoi(args.aoi_dir, "parral")
    artifacts = args.data_dir / "artifacts"
    # DEM sintético (T-ECO-13): da relieve a la pila sintética sin bajar GLO-30. Va marcado como sintético.
    dem = write_synthetic_dem(aoi["bbox"], args.data_dir / "raw" / "synthetic" / "dem" / "parral" / "synthetic_dem.tif")
    for spec in PARRAL_SERIES:
        series_id = series_id_for(spec)
        if (artifacts / "parral" / series_id / "manifest.json").exists() and not args.force:
            print(f"{series_id}: ya existe, se conserva")
            continue
        raw = args.data_dir / "raw" / "synthetic" / series_id
        shutil.rmtree(raw, ignore_errors=True)
        paths = generate_series(spec, aoi["bbox"], raw)
        manifest = process_series(paths, aoi, series_id, artifacts, aoi["maturity"], dem_sources=[dem])
        print(f"{series_id}: {len(manifest['pairs'])} pares sintéticos")
    return 0


def fetch_dem(args: argparse.Namespace) -> int:
    """Baja las teselas públicas GLO-30 que cubren la zona (no necesita cuenta)."""
    aoi = load_aoi(args.aoi_dir, args.aoi)
    target = args.data_dir / "dem" / aoi["id"]
    target.mkdir(parents=True, exist_ok=True)
    for url in glo30_tiles(aoi["bbox"]):
        path = target / url.rsplit("/", 1)[1]
        if path.exists():
            print(f"{path.name}: ya existe")
            continue
        partial = path.with_suffix(".part")
        urllib.request.urlretrieve(url, partial)
        partial.replace(path)
        print(f"{path.name}: {path.stat().st_size / 1e6:.1f} MB")
    return 0


def run(args: argparse.Namespace) -> int:
    aoi = load_aoi(args.aoi_dir, args.aoi)
    paths = sorted(args.input.glob("*.h5"))
    dem_dir = args.dem_dir or args.data_dir / "dem" / aoi["id"]
    dem = sorted(dem_dir.glob("*.tif")) if dem_dir.is_dir() else []
    exclude = excluded_granules(aoi)
    try:
        manifest = process_series(
            paths,
            aoi,
            args.series,
            args.data_dir / "artifacts",
            aoi["maturity"],
            Params(multitemporal=args.multitemporal),
            dem_sources=dem,
            exclude=exclude,
        )
    except GranuleError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    skipped = [notice for notice in manifest["notices"] if notice.startswith("Fechas excluidas")]
    print(f"{args.series}: {len(manifest['pairs'])} pares ({manifest['data_kind']})")
    for notice in skipped:
        print(notice)
    return 0


def run_remote_cmd(args: argparse.Namespace) -> int:
    """Procesado en línea: lee de NASA en memoria solo la ventana y escribe solo los artefactos (remote.py)."""
    from .remote import run_remote

    aoi = load_aoi(args.aoi_dir, args.aoi)

    def process(files):
        return process_series(files, aoi, args.series, args.data_dir / "artifacts", aoi["maturity"], Params(), dem_sources=None,
                              exclude=excluded_granules(aoi))

    try:
        manifest = run_remote(aoi, args.series, args.data_dir / "artifacts", args.catalog_url, args.last, process,
                              catalog_id=args.catalog_series)
    except (GranuleError, ValueError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(f"{args.series}: {len(manifest['pairs'])} pares ({manifest['data_kind']}), sin recortes en disco")
    return 0


def subsidence_cmd(args: argparse.Namespace) -> int:
    """Hundimiento con interferogramas NISAR GUNW leídos en memoria (subsidence.py)."""
    from .subsidence import run_subsidence

    aoi = load_aoi(args.aoi_dir, args.aoi)
    try:
        result = run_subsidence(aoi, args.data_dir / "artifacts", pairs=args.pairs)
    except (ValueError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    if result["status"] != "computed":
        print("Sin interferogramas NISAR GUNW suficientes sobre la zona")
        return 0
    print(f"{len(result['pairs'])} pares, {result['days']} días; se aleja ≥ {result['threshold_mm_yr']:.0f} mm/año "
          f"el {result['sinking_fraction']:.1%}; máximo {result['max_rate_mm_yr']:.0f} mm/año en {result['fastest_point']}")
    return 0


def resign_cmd(args: argparse.Namespace) -> int:
    """Recalcula las firmas por polarización de los manifiestos existentes con sus COG (resign.py)."""
    from .resign import resign_all

    for manifest, pairs in resign_all(args.data_dir / "artifacts", args.aoi).items():
        print(f"{manifest}: {pairs} pares actualizados")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="processor")
    parser.add_argument("--aoi-dir", type=Path, default=Path("/config/aois"))
    parser.add_argument("--data-dir", type=Path, default=Path("/data"))
    commands = parser.add_subparsers(dest="command", required=True)

    seed = commands.add_parser("seed-synthetic", help="Genera datos falsos de Parral y sus artefactos")
    seed.add_argument("--force", action="store_true")
    seed.set_defaults(handler=seed_synthetic)

    process = commands.add_parser("run", help="Procesa gránulos .h5 locales de una serie")
    process.add_argument("--aoi", required=True)
    process.add_argument("--series", required=True)
    process.add_argument("--input", type=Path, required=True)
    process.add_argument("--dem-dir", type=Path, help="Teselas GLO-30; por omisión <data-dir>/dem/<zona>")
    process.add_argument(
        "--multitemporal", action="store_true", help="Aplica el filtro multitemporal de speckle (T-ECO-08)"
    )
    process.set_defaults(handler=run)

    remote = commands.add_parser("run-remote", help="Procesa en línea: lee de NASA en memoria, sin recortes en disco")
    remote.add_argument("--aoi", required=True)
    remote.add_argument("--series", required=True)
    remote.add_argument("--last", type=int, default=4, help="Fechas más recientes que se procesan")
    remote.add_argument("--catalog-url", default=os.environ.get("CATALOG_URL", "http://localhost:8080/api/catalog"))
    remote.add_argument("--catalog-series", help="Id de la serie en catalog (p. ej. T043A-F024-4005-DHDH-P05023)")
    remote.set_defaults(handler=run_remote_cmd)

    subs = commands.add_parser("subsidence", help="Hundimiento con interferogramas NISAR GUNW, sin recortes en disco")
    subs.add_argument("--aoi", required=True)
    subs.add_argument("--pairs", type=int, default=8)
    subs.set_defaults(handler=subsidence_cmd)

    resign = commands.add_parser("resign", help="Recalcula las firmas por polarización de los artefactos ya escritos")
    resign.add_argument("--aoi", default=None, help="Solo esta zona; sin ella, todas")
    resign.set_defaults(handler=resign_cmd)

    dem = commands.add_parser("fetch-dem", help="Baja el DEM Copernicus GLO-30 de una zona")
    dem.add_argument("--aoi", required=True)
    dem.set_defaults(handler=fetch_dem)

    args = parser.parse_args()
    return args.handler(args)


if __name__ == "__main__":
    sys.exit(main())
