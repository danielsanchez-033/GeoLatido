"""Hundimiento con GUNW, sin red: nombres, máscara, búsqueda en CMR y pila con un desplazamiento conocido."""
import json

import numpy as np

from processor import subsidence as sb

NAME = "NISAR_L2_PR_GUNW_032_048_A_015_033_4000_SH_{a}T122431_{a}T122505_{b}T122431_{b}T122506_P05023_N_F_J_001"


def test_name_is_parsed():
    m = sb._parse(NAME.format(a="20261003", b="20261015"))
    assert m == {"track": 48, "direction": "A", "frame": 15, "pol": "SH", "reference": "20261003", "secondary": "20261015"}


def test_mask_drops_water_and_invalid_subswaths():
    mask = np.array([11, 111, 10, 1, 255, 22 | (1 << 8)], np.uint32)
    assert sb._valid(mask).tolist() == [True, False, False, False, False, True]


def test_find_pairs_keeps_the_orbit_with_most_pairs_in_date_order():
    def item(a, b, track="048"):
        gid = NAME.format(a=a, b=b).replace("_048_", f"_{track}_")
        return {"umm": {"GranuleUR": gid, "RelatedUrls": [{"URL": f"https://nisar.asf.earthdatacloud.nasa.gov/x/{gid}.h5"}]}}

    items = [item("20261003", "20261015"), item("20260921", "20261003"), item("20260909", "20260921"), item("20261001", "20261013", "171")]
    pairs = sb.find_pairs([0, 0, 1, 1], pairs=2, getter=lambda url: items)
    assert [p["reference"] for p in pairs] == ["20260921", "20261003"] and all(p["track"] == 48 for p in pairs)


def test_stack_turns_a_known_sinking_bowl_into_mm_per_year():
    rng = np.random.default_rng(0)
    x, y = np.arange(60) * 80.0, 1000 - np.arange(60) * 80.0
    bowl = np.zeros((60, 60), np.float32)
    bowl[20:40, 20:40] = 6.0  # 6 mm más lejos del satélite cada 12 días respecto al resto
    granules, results = [], []
    import datetime as dt

    start = dt.date(2026, 7, 1)
    for i in range(8):  # pares consecutivos de 12 días
        a, b = start + dt.timedelta(days=12 * i), start + dt.timedelta(days=12 * (i + 1))
        granules.append({"id": f"g{i}", "reference": a.strftime("%Y%m%d"), "secondary": b.strftime("%Y%m%d"), "track": 48, "direction": "A", "frame": 15})
        results.append({"mm": bowl + rng.normal(0, 1.0, bowl.shape).astype(np.float32), "x": x, "y": y, "epsg": 32613, "wavelength_m": 0.242})
    rate, summary = sb.stack(results, granules)
    assert summary["days"] == 96
    inside, outside = np.nanmedian(rate[25:35, 25:35]), np.nanmedian(rate[:10, :10])
    assert abs((inside - outside) - 6 * 8 / 96 * 365.25) < 15  # unos 183 mm/año
    assert summary["sinking_fraction"] > 0.05 and summary["threshold_mm_yr"] >= sb.MIN_RATE_MM_YR


def test_run_without_interferograms_says_so(tmp_path):
    out = sb.run_subsidence({"id": "z", "bbox": [0, 0, 1, 1]}, tmp_path, token="t", getter=lambda url: [])
    assert out["status"] == "no_interferograms"
    assert json.loads((tmp_path / "z" / "subsidence" / "subsidence.json").read_text(encoding="utf-8"))["status"] == "no_interferograms"
