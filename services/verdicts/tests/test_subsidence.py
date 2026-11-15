"""Ruta de hundimiento (NISAR GUNW, processor subsidence): resumen en lenguaje llano, capa y 404 declarados."""
import json

import numpy as np
import rasterio
from fastapi.testclient import TestClient
from rasterio.transform import from_origin

from test_verdicts import _clock, manifest_root  # noqa: F401  (fixture)
from verdicts.main import create_app


def _write(root, **extra):
    d = root / "parral" / "subsidence"
    d.mkdir(parents=True, exist_ok=True)
    with rasterio.open(d / "rate.tif", "w", driver="GTiff", width=2, height=2, count=1, dtype="float32", crs="EPSG:32613",
                       transform=from_origin(0, 0, 80, 80), nodata=float("nan")) as dst:
        dst.write(np.array([[0, 30], [80, 150]], np.float32), 1)
    data = {"status": "computed", "days": 108, "pairs": [{"id": "g", "reference": "20260627", "secondary": "20260709"}],
            "track": 48, "direction": "A", "valid_fraction": 0.98, "noise_mm_yr": 36.6, "threshold_mm_yr": 73.3,
            "sinking_fraction": 0.25, "max_rate_mm_yr": 184.0, "fastest_point": {"lon": -105.6, "lat": 26.9},
            "rate_layer": "parral/subsidence/rate.tif", "calibrated": False, **extra}
    (d / "subsidence.json").write_text(json.dumps(data), encoding="utf-8")


def test_subsidence_is_explained_in_plain_words_with_its_layer(manifest_root):
    _write(manifest_root)
    c = TestClient(create_app(manifest_root, clock=_clock))
    body = c.get("/aois/parral/subsidence").json()
    assert body["status"] == "computed" and body["calibrated"] is False and "colormap=" in body["tiles"]
    assert "el 25 % de lo medido se hunde al menos 73 mm al año" in body["summary"]["detected"]
    assert "Hidalgo del Parral" in body["summary"]["detected"] and "relativo" in body["summary"]["does_not_prove"]
    en = c.get("/aois/parral/subsidence", params={"lang": "en"}).json()["summary"]["detected"]
    assert "25 % of what was measured is sinking at least 73 mm a year" in en


def test_no_sinking_says_so(manifest_root):
    _write(manifest_root, sinking_fraction=0.0003, threshold_mm_yr=109.0)
    detected = TestClient(create_app(manifest_root, clock=_clock)).get("/aois/parral/subsidence").json()["summary"]["detected"]
    assert "no se ve que el suelo en Hidalgo del Parral se hunda" in detected and "109 mm al año" in detected


def test_missing_subsidence_or_zone_is_404(manifest_root):
    c = TestClient(create_app(manifest_root, clock=_clock))
    assert c.get("/aois/parral/subsidence").status_code == 404
    assert c.get("/aois/no-existe/subsidence").status_code == 404
