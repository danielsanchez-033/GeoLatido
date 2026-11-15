"""Mide dónde se va el tiempo del procesado en línea (2026-11-15): lectura de la ventana desde NASA frente a cálculo.

Uso, dentro del contenedor `online` (que tiene el token):
    python bench/perfil_remoto.py <zona> <serie> [fechas]
Lee de catalog las fechas más recientes de la serie, abre una en NASA, mide `read_scene` (solo lectura) y después
`process_series` con dos fechas ya leídas en memoria (solo cálculo). No escribe nada fuera de un directorio temporal.
"""
import io
import os
import sys
import tempfile
import time
from pathlib import Path

import yaml

from processor.change import Params
from processor.gcov import read_scene
from processor.pipeline import process_series
from processor.remote import RemoteGranule, latest_granules, open_remote

zid, sid = sys.argv[1], sys.argv[2]
n = int(sys.argv[3]) if len(sys.argv) > 3 else 2
aoi = yaml.safe_load(Path(f"/data/aois-online/{zid}.yaml").read_text(encoding="utf-8"))
spec = next(s for s in aoi["series"] if s["id"] == sid)
token = os.environ["EARTHDATA_TOKEN"]
granules = latest_granules(os.environ.get("CATALOG_URL", "http://catalog:8000"), aoi, spec, n)
print("caja", aoi["bbox"])
t = time.monotonic()
scene = read_scene(RemoteGranule(granules[-1]["id"], open_remote(granules[-1]["download_url"], token)), aoi["bbox"])
print(f"lectura de 1 fecha: {time.monotonic() - t:.1f} s, ventana {scene.hh.shape}")
files = [RemoteGranule(g["id"], open_remote(g["download_url"], token)) for g in granules]
t = time.monotonic()
with tempfile.TemporaryDirectory() as d:
    process_series(files, aoi, sid, Path(d), "PROVISIONAL", Params(), dem_sources=None)
print(f"process_series con {n} fechas (lectura incluida): {time.monotonic() - t:.1f} s")
