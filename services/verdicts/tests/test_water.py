"""Contraste con OPERA DSWx-S1 (T-BAL-08, RF-BAL-07): acuerdo o desacuerdo sobre agua, nunca un error."""
import json
import threading
from datetime import date, datetime, timezone

import httpx
import numpy as np
import pytest
import rasterio
from fastapi.testclient import TestClient
from rasterio.io import MemoryFile
from rasterio.transform import from_origin

from test_verdicts import LAT, LON, VERDICT, _as_real, _clock, manifest_root  # noqa: F401  (fixture)
from verdicts import water
from verdicts.catalog import CatalogUnavailable, HttpOpera, OperaAcquisition, OperaReference, OperaTile
from verdicts.main import create_app

ARCHIVE = "https://archive.podaac.earthdata.nasa.gov/podaac-ops-cumulus-protected/OPERA_L3_DSWX-S1_V1"
PUBLIC = "https://archive.podaac.earthdata.nasa.gov/podaac-ops-cumulus-public/OPERA_L3_DSWX-S1_V1"
JUNE_29, JULY_11 = date(2026, 6, 29), date(2026, 7, 11)


def _tile(name, day, hour=0, minute=58):
    stamp = f"{day:%Y%m%d}T{hour:02d}{minute:02d}00Z"
    product = f"OPERA_L3_DSWx-S1_T{name}_{stamp}_20260828T070924Z_S1A_30_v1.0"
    return OperaTile(
        id=product, tile=name, wtr_url=f"{ARCHIVE}/{product}/{product}_B01_WTR.tif",
        browse_url=f"{PUBLIC}/{product}/{product}_BROWSE.png",
        bbox=(-106.0, 26.0, -105.0, 27.0),
    )


def _pass(day, covers=True, hour=0, tiles=("13RDK",)):
    when = datetime(day.year, day.month, day.day, hour, 58, tzinfo=timezone.utc)
    return OperaAcquisition(
        platform="sentinel-1a", acquired_at=when, covers_aoi=covers,
        tiles=tuple(_tile(name, day, hour) for name in tiles),
    )


def _reference(*acquisitions):
    return OperaReference(
        source="NASA CMR", collection="OPERA_L3_DSWX-S1_V1", doi="10.5067/OPDSWS1-L3V1",
        attribution="OPERA Dynamic Surface Water Extent from Sentinel-1 (v1), NASA JPL OPERA, distribuido por PO.DAAC. "
        "Contiene datos modificados de Copernicus Sentinel 2026",
        product_spec_url="https://archive.podaac.earthdata.nasa.gov/podaac-ops-cumulus-docs/web-misc/opera/spec.pdf",
        min_water_body_ha=3, min_water_body_width_m=200, acquisitions=tuple(acquisitions),
    )


class FakeOpera:
    def __init__(self, acquisitions=(), fail=False):
        self.acquisitions = acquisitions
        self.fail = fail
        self.calls = []

    def products(self, aoi, day, days):
        self.calls.append((aoi, day, days))
        if self.fail:
            raise CatalogUnavailable(aoi)
        return _reference(*(a for a in self.acquisitions if abs((a.acquired_at.date() - day).days) <= days))


# Como en Parral (MEMORY.md): pasadas el 06-22 y el 06-27 antes de la tormenta, y nada del 06-28 al 09-13.
PARRAL_PASSES = (_pass(date(2026, 6, 22), hour=12), _pass(date(2026, 6, 27)), _pass(date(2026, 6, 27), hour=13))


def _wtr_bytes(values: np.ndarray, origin=(LON - 0.02, LAT + 0.02), nodata=255) -> bytes:
    height, width = values.shape
    with MemoryFile() as memory:
        with memory.open(driver="GTiff", height=height, width=width, count=1, dtype="uint8", crs="EPSG:4326",
                         transform=from_origin(*origin, 0.001, 0.001), nodata=nodata) as dataset:
            dataset.write(values.astype("uint8"), 1)
        return memory.read()


def _radar(manifest_root, stamp, hh, hv):
    for name, values in (("hh_db", hh), ("hv_db", hv)):
        path = manifest_root / f"parral/T048A-F015/dates/{stamp}/{name}.tif"
        with rasterio.open(path, "r+") as dataset:
            dataset.write(values.astype("float32"), 1)


def _water_columns(first, last, wet, dry):
    values = np.full((40, 40), dry, "float32")
    values[:, first:last] = wet
    return values


class FakeFetcher:
    def __init__(self, tiles=None, fail=False):
        self.tiles = tiles or {}
        self.fail = fail
        self.urls = []

    def get(self, url):
        self.urls.append(url)
        if self.fail:
            raise httpx.ConnectError("sin red")
        return self.tiles[url]


# --- Reglas puras -------------------------------------------------------------------------

def test_pick_prefers_covering_then_closest_either_side():
    covering = _pass(date(2026, 6, 26))
    closer_partial = _pass(date(2026, 6, 29), covers=False)
    acq, days = water.pick([closer_partial, covering, _pass(date(2026, 7, 2))], JUNE_29)
    assert acq is covering and days == -3
    acq, days = water.pick([_pass(date(2026, 7, 1)), _pass(date(2026, 6, 26))], JUNE_29)
    assert days == 2  # después también vale: el agua es una foto, no un antes y un después


def test_pick_ignores_products_beyond_the_window():
    assert water.pick([_pass(date(2026, 6, 20))], JUNE_29) is None


def test_compare_counts_agreement_and_masks():
    hh = np.array([[-20, -20, -10, -10, -20, np.nan]], "float32")
    hv = np.array([[-26, -26, -18, -18, -26, -26]], "float32")
    wtr = np.array([[1, 0, 3, 0, 251, 1]], "uint8")
    result = water.compare(hh, hv, wtr)
    assert (result.both_water, result.radar_only_water, result.reference_only_water, result.both_not_water) == (1, 1, 1, 1)
    assert result.not_comparable == 2  # layover/sombra y radar sin dato
    assert result.agreement_fraction == 0.5 and result.water_iou == pytest.approx(1 / 3)
    assert result.assessment == "disagree" and result.basis == "water_overlap"


def test_hh_alone_is_not_water_for_the_radar():
    result = water.compare(np.array([[-20.0]]), np.array([[-18.0]]), np.array([[0]], "uint8"))
    assert result.both_not_water == 1


def test_no_water_in_either_source_counts_as_agreement():
    hh, hv = np.full((50, 50), -10.0), np.full((50, 50), -18.0)
    result = water.compare(hh, hv, np.zeros((50, 50), "uint8"))
    assert result.assessment == "agree" and result.basis == "little_water" and result.water_iou is None


def test_sample_grid_merges_overlapping_tiles_and_averages_radar(manifest_root):
    root = manifest_root / "parral/T048A-F015/dates/20260629"
    _radar(manifest_root, "20260629", _water_columns(0, 20, -20, -10), _water_columns(0, 20, -26, -18))
    left = np.full((40, 40), 255)
    left[:, :20] = 1
    right = np.zeros((40, 40))
    bbox = [LON - 0.02, LAT - 0.02, LON + 0.02, LAT + 0.02]
    hh, hv, wtr = water.sample_grid([_wtr_bytes(left), _wtr_bytes(right)], bbox, root / "hh_db.tif", root / "hv_db.tif")
    assert wtr.shape == (40, 40) and set(np.unique(wtr)) == {0, 1}
    result = water.compare(hh, hv, wtr)
    assert result.comparable == 1600 and result.water_iou > 0.9 and result.assessment == "agree"


# --- En el veredicto ----------------------------------------------------------------------

def _client(manifest_root, opera=None, fetcher=None):
    contrast = water.WaterContrast(manifest_root, fetcher)
    return TestClient(create_app(manifest_root, clock=_clock, opera_source=opera, water_contrast=contrast))


def test_synthetic_radar_lists_the_product_but_never_compares(manifest_root):
    fetcher = FakeFetcher()
    body = _client(manifest_root, FakeOpera(PARRAL_PASSES), fetcher).get(VERDICT).json()
    evidence = body["evidence"]["water"]
    assert evidence["data_kind"] == "real" and evidence["doi"] == "10.5067/OPDSWS1-L3V1"
    assert evidence["radar_rule"] == {"hh_db_below": -15.0, "hv_db_below": -23.0, "resampling": "average",
                                      "calibrated": False}
    before = evidence["before"]
    assert before["status"] == "synthetic" and before["assessment"] is None and before["comparison"] is None
    assert before["reference"]["days_from_radar"] == -2 and before["reference"]["tiles"][0]["tile"] == "13RDK"
    assert "podaac-ops-cumulus-public" in before["reference"]["tiles"][0]["browse_url"]
    assert before["reference"]["tiles"][0]["bbox"] == [-106.0, 26.0, -105.0, 27.0]
    assert "no se compara con datos de radar sintéticos" in evidence["text"]
    assert "3 ha y 200 m" in evidence["text"]
    assert evidence["after"]["status"] == "none_in_window"
    assert fetcher.urls == []


def test_real_radar_without_token_says_it_was_not_compared(manifest_root):
    _as_real(manifest_root)
    body = _client(manifest_root, FakeOpera(PARRAL_PASSES)).get(VERDICT).json()
    assert body["evidence"]["water"]["before"]["status"] == "no_credentials"
    assert "cuenta de Earthdata" in body["evidence"]["water"]["text"]


def _tile_sized_aoi(manifest_root):
    """La zona del manifiesto pasa a ser la de las capas de prueba (0,04°), para que se compare entera."""
    path = manifest_root / "parral/T048A-F015/manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["bbox"] = [LON - 0.02, LAT - 0.02, LON + 0.02, LAT + 0.02]
    path.write_text(json.dumps(manifest), encoding="utf-8")


def _real_with_products(manifest_root, wtr_before, wtr_after, whole_aoi=True):
    _as_real(manifest_root)
    if whole_aoi:
        _tile_sized_aoi(manifest_root)
    wet = (_water_columns(0, 20, -20, -10), _water_columns(0, 20, -26, -18))
    _radar(manifest_root, "20260629", *wet)
    _radar(manifest_root, "20260711", *wet)
    passes = (_pass(date(2026, 6, 27)), _pass(date(2026, 7, 13)))
    tiles = {passes[0].tiles[0].wtr_url: _wtr_bytes(wtr_before), passes[1].tiles[0].wtr_url: _wtr_bytes(wtr_after)}
    return FakeOpera(passes), FakeFetcher(tiles)


def test_real_radar_compares_and_presents_disagreement_as_such(manifest_root):
    same = np.zeros((40, 40))
    same[:, :20] = 1
    elsewhere = np.zeros((40, 40))
    elsewhere[:, 25:] = 1
    opera, fetcher = _real_with_products(manifest_root, same, elsewhere)
    client = _client(manifest_root, opera, fetcher)
    evidence = client.get(VERDICT).json()["evidence"]["water"]
    before, after = evidence["before"], evidence["after"]
    assert before["status"] == after["status"] == "compared"
    assert before["assessment"] == "agree" and before["assessment_basis"] == "water_overlap"
    assert after["assessment"] == "disagree" and after["comparison"]["water_iou"] == 0
    assert after["comparison"]["radar_only_water"] > 0 and after["comparison"]["reference_only_water"] > 0
    assert "no coinciden en dónde hay agua" in evidence["text"]
    assert "desacuerdo entre dos métodos y no indica cuál de los dos acierta" in evidence["text"]
    assert "HH < -15,0 dB y HV < -23,0 dB" in evidence["text"]
    english = client.get(VERDICT, params={"lang": "en"}).json()["evidence"]["water"]["text"]
    assert "disagreement between two methods" in english
    assert len(fetcher.urls) == 2  # el segundo idioma usa la caché


def test_partial_coverage_gives_counts_but_no_assessment(manifest_root):
    # Revisión de Antena (PR 34): una pasada con 13RDK y 13RDL dejó el 78,9 % de Parral en WTR 255 y salía disagree.
    elsewhere = np.zeros((40, 40))
    elsewhere[:, 25:] = 1
    opera, fetcher = _real_with_products(manifest_root, elsewhere, elsewhere, whole_aoi=False)
    evidence = _client(manifest_root, opera, fetcher).get(VERDICT).json()["evidence"]["water"]
    before = evidence["before"]
    assert before["status"] == "partial_overlap" and before["assessment"] is None
    assert 0 < before["comparison"]["compared_fraction"] < 0.5 and evidence["min_compared_fraction"] == 0.5
    assert "solo se pudo comparar el" in evidence["text"] and "menos del 50 %" in evidence["text"]
    assert "no coinciden" not in evidence["text"]


def test_half_of_the_area_with_data_is_enough(manifest_root):
    half = np.full((40, 40), 255)
    half[:, :20] = 1
    opera, fetcher = _real_with_products(manifest_root, half, half)
    before = _client(manifest_root, opera, fetcher).get(VERDICT).json()["evidence"]["water"]["before"]
    assert before["comparison"]["compared_fraction"] == pytest.approx(0.5, abs=0.03)
    assert before["status"] in ("compared", "partial_overlap")
    assert (before["status"] == "compared") == (before["comparison"]["compared_fraction"] >= 0.5)


def test_read_failure_is_declared_and_retried(manifest_root):
    _as_real(manifest_root)
    fetcher = FakeFetcher(fail=True)
    client = _client(manifest_root, FakeOpera(PARRAL_PASSES), fetcher)
    assert client.get(VERDICT).json()["evidence"]["water"]["before"]["status"] == "read_failed"
    client.get(VERDICT)
    assert len(fetcher.urls) == 2


@pytest.mark.parametrize("opera", [None, FakeOpera(fail=True)])
def test_catalog_down_keeps_the_verdict(manifest_root, opera):
    response = _client(manifest_root, opera).get(VERDICT)
    assert response.status_code == 200
    evidence = response.json()["evidence"]["water"]
    assert evidence["before"]["status"] == evidence["after"]["status"] == "catalog_unavailable"
    assert evidence["text"] == "No se sabe si hay productos de agua OPERA DSWx-S1: el catálogo no respondió."


def test_verdict_list_asks_each_date_once_with_seven_days(manifest_root):
    opera = FakeOpera(PARRAL_PASSES)
    assert _client(manifest_root, opera).get("/aois/parral/series/T048A-F015/verdicts").status_code == 200
    assert sorted(day for _, day, _ in opera.calls) == [JUNE_29, JULY_11]
    assert all(days == 7 for _, _, days in opera.calls)


# --- Token y cliente HTTP -----------------------------------------------------------------

def test_token_only_goes_to_podaac_and_is_dropped_on_redirect():
    seen = []

    def handler(request):
        seen.append((request.url.host, request.headers.get("authorization")))
        if request.url.host == "archive.podaac.earthdata.nasa.gov":
            return httpx.Response(303, headers={"location": "https://d1.cloudfront.net/x.tif?Signature=abc"})
        return httpx.Response(200, content=b"tif")

    fetcher = water.EarthdataFetcher("secreto", httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True))
    assert fetcher.get(f"{ARCHIVE}/a_B01_WTR.tif") == b"tif"
    assert seen == [("archive.podaac.earthdata.nasa.gov", "Bearer secreto"), ("d1.cloudfront.net", None)]
    with pytest.raises(ValueError):
        fetcher.get("https://example.com/a_B01_WTR.tif")
    assert len(seen) == 2


def test_contrast_reads_token_from_environment(tmp_path):
    assert water.contrast_from_env(tmp_path, {}.get).fetcher is None
    assert water.contrast_from_env(tmp_path, {"EARTHDATA_TOKEN": "  "}.get).fetcher is None
    assert isinstance(water.contrast_from_env(tmp_path, {"EARTHDATA_TOKEN": "t"}.get).fetcher, water.EarthdataFetcher)


def _opera_body():
    product = "OPERA_L3_DSWx-S1_T13RDK_20260627T005842Z_20260828T070924Z_S1A_30_v1.0"
    return {
        "aoi": "parral", "date": "2026-06-29", "days": 7, "source": "NASA CMR", "collection": "OPERA_L3_DSWX-S1_V1",
        "doi": "10.5067/OPDSWS1-L3V1", "attribution": "OPERA DSWx-S1", "product_spec_url": "https://x/spec.pdf",
        "min_water_body_ha": 3, "min_water_body_width_m": 200, "coverage_basis": "tile_bbox",
        "data_access": "earthdata_login",
        "acquisitions": [
            {"platform": "sentinel-1a", "acquired_at": "2026-06-27T00:58:42Z", "days_from_date": -2, "covers_aoi": True,
             "tiles": [{"id": product, "tile": "13RDK", "acquired_at": "2026-06-27T00:58:42Z",
                        "produced_at": "2026-08-28T07:09:24Z", "wtr_url": f"{ARCHIVE}/{product}_B01_WTR.tif",
                        "conf_url": "", "browse_url": None}]},
            {"platform": "sentinel-1a", "acquired_at": "2026-06-22T12:56:00Z", "days_from_date": -7, "covers_aoi": True,
             "tiles": [{"id": "x", "tile": "13RDK", "acquired_at": "2026-06-22T12:56:00Z",
                        "produced_at": "2026-08-28T07:09:24Z", "wtr_url": "file:///etc/passwd", "conf_url": "",
                        "browse_url": None}]},
        ],
    }


def test_http_opera_parses_drops_non_https_and_caches():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json=_opera_body())

    clock = [0.0]
    source = HttpOpera("http://catalog:8000/", httpx.Client(transport=httpx.MockTransport(handler)), lambda: clock[0])
    result = source.products("parral", JUNE_29, 7)
    assert requests[0].url.path == "/aois/parral/references/opera"
    assert dict(requests[0].url.params) == {"date": "2026-06-29", "days": "7"}
    assert len(result.acquisitions) == 1 and result.acquisitions[0].tiles[0].browse_url is None
    assert result.min_water_body_ha == 3.0
    source.products("parral", JUNE_29, 7)
    assert len(requests) == 1
    clock[0] = 10_000
    source.products("parral", JUNE_29, 7)
    assert len(requests) == 2


def test_http_opera_failure_is_cached_briefly():
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(502, json={"detail": "CMR no respondió; no hay referencias OPERA"})

    source = HttpOpera("http://catalog:8000", httpx.Client(transport=httpx.MockTransport(handler)), lambda: 0.0)
    for _ in range(2):
        with pytest.raises(CatalogUnavailable):
            source.products("parral", JUNE_29, 7)
    assert len(calls) == 1


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ([-106.1, 26.9, -105.0, 27.9], (-106.1, 26.9, -105.0, 27.9)),
        ([179.5, -17.0, -179.5, -16.0], (179.5, -17.0, -179.5, -16.0)),  # cruza el antimeridiano: no se reordena
        (None, None),  # catalog todavía sin el campo
        ([1, 2, 3], None),
        (["a", 0, 1, 2], None),
        ([0, 10, 1, 5], None),  # sur > norte
        ([0, 0, 200, 1], None),
    ],
)
def test_http_opera_passes_tile_bbox_through_or_drops_it(value, expected):
    body = _opera_body()
    tile = body["acquisitions"][0]["tiles"][0]
    if value is None:
        tile.pop("bbox", None)
    else:
        tile["bbox"] = value
    source = HttpOpera(
        "http://catalog:8000/",
        httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json=body))),
        lambda: 0.0,
    )
    assert source.products("parral", JUNE_29, 7).acquisitions[0].tiles[0].bbox == expected


# --- Caché en disco y calentamiento (revisión de Antena: la primera carga real tardaba ~63 s) -----------------

def _disk_client(manifest_root, cache_dir, opera, fetcher, **kwargs):
    contrast = water.WaterContrast(manifest_root, fetcher, cache_dir)
    return TestClient(create_app(manifest_root, clock=_clock, opera_source=opera, water_contrast=contrast, **kwargs))


def _same_and_elsewhere():
    same = np.zeros((40, 40))
    same[:, :20] = 1
    elsewhere = np.zeros((40, 40))
    elsewhere[:, 25:] = 1
    return same, elsewhere


def test_disk_cache_survives_a_restart(manifest_root, tmp_path):
    opera, fetcher = _real_with_products(manifest_root, *_same_and_elsewhere())
    first = _disk_client(manifest_root, tmp_path, opera, fetcher).get(VERDICT).json()["evidence"]["water"]
    assert len(fetcher.urls) == 2 and len(list((tmp_path / "water").glob("*.json"))) == 2
    restarted = FakeFetcher(fail=True)
    again = _disk_client(manifest_root, tmp_path, opera, restarted).get(VERDICT).json()["evidence"]["water"]
    assert restarted.urls == []
    assert again["before"] == first["before"] and again["after"]["status"] == "compared"


def test_regenerated_radar_is_compared_again(manifest_root, tmp_path):
    opera, fetcher = _real_with_products(manifest_root, *_same_and_elsewhere())
    _disk_client(manifest_root, tmp_path, opera, fetcher).get(VERDICT)
    _radar(manifest_root, "20260629", _water_columns(0, 30, -20, -10), _water_columns(0, 30, -26, -18))
    later = FakeFetcher(fetcher.tiles)
    _disk_client(manifest_root, tmp_path, opera, later).get(VERDICT)
    assert len(later.urls) == 1  # solo la fecha que processor volvió a escribir


def test_unreadable_cache_file_is_ignored(manifest_root, tmp_path):
    opera, fetcher = _real_with_products(manifest_root, *_same_and_elsewhere())
    _disk_client(manifest_root, tmp_path, opera, fetcher).get(VERDICT)
    for path in (tmp_path / "water").glob("*.json"):
        path.write_text("{roto", encoding="utf-8")
    later = FakeFetcher(fetcher.tiles)
    before = _disk_client(manifest_root, tmp_path, opera, later).get(VERDICT).json()["evidence"]["water"]["before"]
    assert before["status"] == "compared" and len(later.urls) == 2


def test_failed_download_is_not_stored(manifest_root, tmp_path):
    _as_real(manifest_root)
    _disk_client(manifest_root, tmp_path, FakeOpera(PARRAL_PASSES), FakeFetcher(fail=True)).get(VERDICT)
    assert not list(tmp_path.glob("water/*.json"))


def test_warm_up_compares_real_series_in_the_background(manifest_root, tmp_path):
    opera, fetcher = _real_with_products(manifest_root, *_same_and_elsewhere())
    with _disk_client(manifest_root, tmp_path, opera, fetcher, warm_cache=True):
        for thread in [t for t in threading.enumerate() if t.name == "warm-up"]:
            thread.join(timeout=30)
    assert len(fetcher.urls) == 2 and len(list((tmp_path / "water").glob("*.json"))) == 2


def test_warm_up_does_nothing_without_token(manifest_root):
    _as_real(manifest_root)
    opera = FakeOpera(PARRAL_PASSES)
    with _disk_client(manifest_root, None, opera, None, warm_cache=True):
        pass
    assert opera.calls == []


def test_cache_dir_comes_from_environment(tmp_path):
    assert water.contrast_from_env(tmp_path, {}.get).cache_dir is None
    env = {"VERDICTS_CACHE_DIR": str(tmp_path / "c")}.get
    assert water.contrast_from_env(tmp_path, env).cache_dir == tmp_path / "c"
