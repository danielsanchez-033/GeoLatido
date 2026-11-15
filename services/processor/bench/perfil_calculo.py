"""Reparto del cálculo de `process_series` en una zona de 0,3° (≈ 3300 × 3300 px a 10 m), con datos sintéticos.

Uso: python bench/perfil_calculo.py
Mide por separado leer la escena, `compare` y escribir los COG de un par y de una fecha (2026-11-15).
"""
import tempfile
import time
from pathlib import Path

from processor import pipeline
from processor.change import Params, compare
from processor.gcov import read_scene
from processor.synthetic import SeriesSpec, generate_series

BBOX = [-100.45, 25.55, -100.15, 25.85]
with tempfile.TemporaryDirectory() as d:
    t = time.monotonic()
    paths = generate_series(SeriesSpec(91, "A", 15, ("20260901", "20260913")), BBOX, Path(d) / "raw", posting_m=10.0)
    print(f"generar: {time.monotonic() - t:.1f} s")
    t = time.monotonic()
    a, b = (read_scene(p, BBOX) for p in paths)
    print(f"leer 2 escenas: {time.monotonic() - t:.1f} s, {a.hh.shape}")
    params = Params()
    t = time.monotonic()
    r = compare(a, b, params)
    print(f"compare: {time.monotonic() - t:.1f} s")
    t = time.monotonic()
    pipeline._write_cog(Path(d) / "s.tif", r.state, a, pipeline.STATE_NODATA, "nearest")
    pipeline._write_cog(Path(d) / "h.tif", r.change_hh, a, float("nan"), "average")
    pipeline._write_cog(Path(d) / "v.tif", r.change_hv, a, float("nan"), "average")
    print(f"3 COG del par: {time.monotonic() - t:.1f} s")
    t = time.monotonic()
    pipeline._write_date(a, "z/s", Path(d), params)
    print(f"fecha (2 COG con suavizado): {time.monotonic() - t:.1f} s")
    t = time.monotonic()
    pipeline.cell_features(r.state, a.transform, a.crs)
    print(f"celdas: {time.monotonic() - t:.1f} s")
