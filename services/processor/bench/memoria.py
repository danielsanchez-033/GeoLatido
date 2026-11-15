"""Mide la RAM máxima de process_series con una serie sintética a resolución real.

Uso, desde services/processor:

    python bench/memoria.py generar --dir /tmp/bench --fechas 10
    python bench/memoria.py medir --dir /tmp/bench

`generar` escribe gránulos sintéticos a 10 m sobre la zona de Parral (unos 5500 x 5000 píxeles,
como los recortes reales de T048). `medir` los procesa en un proceso nuevo e imprime la memoria
máxima. Los datos son sintéticos: miden el consumo, no describen ningún lugar real.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

PARRAL_BBOX = [-105.95, 26.70, -105.40, 27.15]
T048_DATES = ("20260617", "20260629", "20260711", "20260723", "20260816",
              "20260828", "20260909", "20260921", "20261003", "20261015")


def peak_memory_mb() -> float:
    try:
        import resource

        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024  # Linux: KiB
    except ImportError:
        import psutil  # Windows: pip install psutil

        return psutil.Process().memory_info().peak_wset / 2**20


def generate(directory: Path, count: int) -> None:
    from processor.synthetic import SeriesSpec, generate_series

    spec = SeriesSpec(48, "A", 15, T048_DATES[:count])
    paths = generate_series(spec, PARRAL_BBOX, directory / "raw", posting_m=10.0)
    print(f"{len(paths)} gránulos en {directory / 'raw'}")


def measure(directory: Path) -> None:
    import h5py

    from processor.gcov import GRID
    from processor.pipeline import process_series

    paths = sorted((directory / "raw").glob("*.h5"))
    with h5py.File(paths[0], "r") as handle:
        shape = handle[GRID]["HHHH"].shape
    start = time.perf_counter()
    manifest = process_series(paths, {"id": "parral", "bbox": PARRAL_BBOX}, "T048A-F015",
                              directory / "artifacts", "PROVISIONAL")
    elapsed = time.perf_counter() - start
    print(f"fechas={len(manifest['dates'])} pares={len(manifest['pairs'])} malla={shape[0]}x{shape[1]} "
          f"tiempo={elapsed:.0f}s ram_max={peak_memory_mb():.0f}MB")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("accion", choices=["generar", "medir"])
    parser.add_argument("--dir", type=Path, required=True)
    parser.add_argument("--fechas", type=int, default=10)
    args = parser.parse_args()
    if args.accion == "generar":
        generate(args.dir, args.fechas)
    else:
        measure(args.dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
