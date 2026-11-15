import json
from datetime import date, datetime, timezone
from pathlib import Path

import httpx
import jsonschema
import numpy as np
import pytest
import rasterio
from fastapi.testclient import TestClient
from rasterio.transform import from_origin

from verdicts import narrative, rules
from verdicts.catalog import CatalogUnavailable, HttpTimeline, PassTime
from verdicts.main import app as public_app
from verdicts.main import create_app

ROOT = Path(__file__).resolve().parents[3]
CODES = {"no_change": 0, "change_probable": 1, "outside_scene": 10, "invalid_or_partial": 11,
         "input_exception": 12, "low_looks": 13, "no_data": 14, "terrain": 15}
LON, LAT = -105.67, 26.93


def counts(**values):
    return {name: values.get(name, 0) for name in CODES}


def test_change_probable():
    decision = rules.decide(counts(no_change=900, change_probable=100))
    assert decision.state == rules.CHANGE_PROBABLE and decision.cause is None


def test_small_change_is_not_reported():
    assert rules.decide(counts(no_change=999, change_probable=1)).state == rules.NO_DETECTABLE_CHANGE


def test_mostly_masked_scene_is_not_observable_with_dominant_cause():
    decision = rules.decide(counts(no_change=100, change_probable=100, invalid_or_partial=600, outside_scene=200))
    assert decision.state == rules.NOT_OBSERVABLE and decision.cause == "invalid_or_partial"


def test_empty_counts_are_not_observable():
    assert rules.decide(counts()).state == rules.NOT_OBSERVABLE


def test_hypotheses_are_ordered_by_area_and_ignore_minor_signatures():
    result = rules.hypotheses({"hh_up_hv_up": 30, "hh_up_hv_stable": 60, "hh_down_hv_down": 5, "other": 5})
    assert result == ["surface_moisture_or_flooded_vegetation", "more_vegetation_wetting_or_water_retreat"]


def test_no_signatures_give_no_hypotheses():
    assert rules.hypotheses({"hh_up_hv_up": 0}) == []


def test_parral_storm_falls_between_passes():
    passes = [date(2026, 6, 26), date(2026, 6, 29), date(2026, 7, 8), date(2026, 7, 11)]
    status = rules.event_status(passes, date(2026, 7, 1), 24)
    assert status.state == rules.NOT_OBSERVABLE and status.cause == "no_acquisition_during_event"
    assert (status.previous_pass, status.next_pass) == (date(2026, 6, 29), date(2026, 7, 8))


def test_event_with_pass_on_time_is_observable():
    passes = [date(2026, 6, 29), date(2026, 7, 2)]
    assert rules.event_status(passes, date(2026, 7, 1), 48).state == rules.OBSERVABLE


def test_event_outside_series():
    assert rules.event_status([date(2026, 6, 29)], date(2027, 1, 1), 24).cause == "outside_series_window"


def _cog(path: Path, value: float, dtype: str, nodata) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = np.full((40, 40), value, dtype)
    transform = from_origin(LON - 0.02, LAT + 0.02, 0.001, 0.001)
    with rasterio.open(path, "w", driver="GTiff", height=40, width=40, count=1, dtype=dtype,
                       crs="EPSG:4326", transform=transform, nodata=nodata) as dataset:
        dataset.write(data, 1)


@pytest.fixture()
def manifest_root(tmp_path):
    prefix = "parral/T048A-F015"
    dates = []
    for day, stamp in (("2026-06-29", "20260629"), ("2026-07-11", "20260711")):
        hh, hv = f"{prefix}/dates/{stamp}/hh_db.tif", f"{prefix}/dates/{stamp}/hv_db.tif"
        _cog(tmp_path / hh, -12.5, "float32", float("nan"))
        _cog(tmp_path / hv, -19.5, "float32", float("nan"))
        dates.append({"date": day, "granule": f"G{stamp}", "hh_db": hh, "hv_db": hv})
    pair_id = "20260629_20260711"
    layers = {
        "state": f"{prefix}/pairs/{pair_id}/state.tif",
        "change_hh": f"{prefix}/pairs/{pair_id}/change_hh.tif",
        "change_hv": f"{prefix}/pairs/{pair_id}/change_hv.tif",
    }
    _cog(tmp_path / layers["state"], 1, "uint8", 255)
    manifest = {
        "schema_version": 1, "aoi": "parral",
        "series": {"id": "T048A-F015", "track": 48, "direction": "A", "frame": 15,
                   "mode": "4005", "polarization": "DHDH", "crid": "P05023"},
        "data_kind": "synthetic", "maturity": "PROVISIONAL", "crs": "EPSG:32613",
        "bbox": [-105.95, 26.7, -105.4, 27.15], "state_codes": CODES,
        "notices": ["DATOS SINTÉTICOS"], "dates": dates,
        "pairs": [{
            "id": pair_id, "from": "2026-06-29", "to": "2026-07-11", "kind": "consecutive", "spans_data_gap": False,
            "granules": ["G20260629", "G20260711"], "layers": layers,
            "stats": {"counts": counts(no_change=900, change_probable=100),
                      "signature_counts": {"hh_up_hv_stable": 100}, "threshold_hh_db": 3.0,
                      "threshold_hv_db": 3.0, "mean_change_hh_db": 5.0, "mean_change_hv_db": 0.4},
        }],
    }
    schema = json.loads((ROOT / "contracts" / "artifact-manifest.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(manifest, schema)
    (tmp_path / prefix / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return tmp_path


@pytest.fixture()
def client(manifest_root):
    return TestClient(create_app(manifest_root))


def test_verdict_has_receipt_and_marks_synthetic(client):
    body = client.get("/aois/parral/series/T048A-F015/verdicts/20260629_20260711").json()
    assert body["state"] == "change_probable"
    assert body["receipt"]["data_kind"] == "synthetic" and body["receipt"]["crid"] == "P05023"
    assert body["summary"]["detected"].startswith("[DATOS SINTÉTICOS]")
    assert body["hypotheses"] and "file%3A%2F%2F%2Fdata%2Fartifacts" in body["layers"]["state"]


def test_verdict_in_english(client):
    body = client.get("/aois/parral/series/T048A-F015/verdicts/20260629_20260711", params={"lang": "en"}).json()
    assert body["summary"]["detected"].startswith("[SYNTHETIC DATA]")


def test_event_endpoint(client):
    body = client.get("/aois/parral/events", params={"date": "2026-07-01"}).json()
    assert body["state"] == "not_observable" and body["cause"] == "no_acquisition_during_event"


def test_pixel_series(client):
    body = client.get("/aois/parral/series/T048A-F015/pixel", params={"lon": LON, "lat": LAT}).json()
    assert body["values"][0]["hh_db"] == pytest.approx(-12.5)
    assert body["changes"][0]["state"] == "change_probable"


def test_pixel_with_no_change_keeps_its_state(manifest_root):
    _cog(manifest_root / "parral/T048A-F015/pairs/20260629_20260711/state.tif", 0, "uint8", 255)
    body = TestClient(create_app(manifest_root)).get(
        "/aois/parral/series/T048A-F015/pixel", params={"lon": LON, "lat": LAT}
    ).json()
    assert body["changes"][0]["state"] == "no_change"


def test_pixel_at_zero_db_is_not_null(manifest_root):
    _cog(manifest_root / "parral/T048A-F015/dates/20260629/hv_db.tif", 0.0, "float32", float("nan"))
    body = TestClient(create_app(manifest_root)).get(
        "/aois/parral/series/T048A-F015/pixel", params={"lon": LON, "lat": LAT}
    ).json()
    assert body["values"][0]["hv_db"] == 0.0


def test_pixel_outside_series(client):
    assert client.get("/aois/parral/series/T048A-F015/pixel", params={"lon": 10, "lat": 40}).status_code == 404


@pytest.mark.parametrize("path", ["/aois/../series", "/aois/nope/series", "/aois/parral/series/bad/verdicts"])
def test_unknown_resources_are_404(client, path):
    assert client.get(path).status_code == 404


def test_contract_is_current():
    committed = json.loads((ROOT / "contracts" / "verdicts.openapi.json").read_text(encoding="utf-8"))
    assert committed == json.loads(json.dumps(public_app.openapi())), "Regenera el contrato con export_openapi"


# --- T-BAL-02: interval_days y frescura -------------------------------------------------

TODAY = datetime(2026, 11, 11, 18, 0, tzinfo=timezone.utc)
VERDICT = "/aois/parral/series/T048A-F015/verdicts/20260629_20260711"


def _clock():
    return TODAY


class FakeTimeline:
    def __init__(self, passes=None, fail=False, excluded=()):
        self.calls = 0
        self.fail = fail
        self.result = passes or {}
        self.dropped = list(excluded)

    def passes(self, aoi):
        self.calls += 1
        if self.fail:
            raise CatalogUnavailable(aoi)
        return self.result

    def excluded(self, aoi):
        if self.fail:
            raise CatalogUnavailable(aoi)
        return self.dropped


def _as_real(manifest_root, **pair_changes):
    path = manifest_root / "parral/T048A-F015/manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["data_kind"], manifest["notices"] = "real", []
    manifest["pairs"][0].update(pair_changes)
    path.write_text(json.dumps(manifest), encoding="utf-8")


REAL_PASSES = {
    "G20260629": PassTime(datetime(2026, 6, 29, 0, 41, 12, tzinfo=timezone.utc),
                          datetime(2026, 7, 1, 8, 11, tzinfo=timezone.utc), 55.5),
    "G20260711": PassTime(datetime(2026, 7, 11, 0, 41, 30, tzinfo=timezone.utc),
                          datetime(2026, 7, 12, 14, 0, tzinfo=timezone.utc), 37.3),
}


def test_verdict_reports_interval_and_age(manifest_root):
    body = TestClient(create_app(manifest_root, clock=_clock)).get(VERDICT).json()
    assert body["interval_days"] == 12
    freshness = body["receipt"]["freshness"]
    assert freshness["reference_date"] == "2026-11-11"
    assert freshness["before"]["age_days"] == 135 and freshness["after"]["age_days"] == 123
    assert "(12 días)" in body["summary"]["detected"]
    assert "123 días" in body["summary"]["missing"]


def test_synthetic_verdict_never_asks_catalog(manifest_root):
    timeline = FakeTimeline(REAL_PASSES)
    body = TestClient(create_app(manifest_root, timeline=timeline, clock=_clock)).get(VERDICT).json()
    assert timeline.calls == 0
    assert body["receipt"]["freshness"]["after"]["latency_status"] == "synthetic"
    assert body["receipt"]["freshness"]["after"]["publication_latency_hours"] is None
    assert "no aplica a datos sintéticos" in body["summary"]["missing"]


def test_real_verdict_takes_latency_from_catalog(manifest_root):
    _as_real(manifest_root)
    client = TestClient(create_app(manifest_root, timeline=FakeTimeline(REAL_PASSES), clock=_clock))
    body = client.get(VERDICT).json()
    after = body["receipt"]["freshness"]["after"]
    assert after["latency_status"] == "available" and after["publication_latency_hours"] == 37.3
    assert after["acquired_at"].startswith("2026-07-11T00:41:30")
    assert "37,3 horas" in body["summary"]["missing"]
    english = client.get(VERDICT, params={"lang": "en"}).json()["summary"]["missing"]
    assert "123 days old" in english and "37.3 hours" in english


def test_catalog_down_does_not_break_the_verdict(manifest_root):
    _as_real(manifest_root)
    response = TestClient(create_app(manifest_root, timeline=FakeTimeline(fail=True), clock=_clock)).get(VERDICT)
    assert response.status_code == 200
    after = response.json()["receipt"]["freshness"]["after"]
    assert after["latency_status"] == "catalog_unavailable" and after["acquired_at"] is None
    assert "el catálogo no respondió" in response.json()["summary"]["missing"]


def test_granule_missing_from_catalog_is_declared(manifest_root):
    _as_real(manifest_root)
    body = TestClient(create_app(manifest_root, timeline=FakeTimeline({}), clock=_clock)).get(VERDICT).json()
    assert body["receipt"]["freshness"]["after"]["latency_status"] == "granule_not_in_catalog"


def test_pair_across_august_gap_says_24_days_and_why(manifest_root):
    _as_real(manifest_root, **{"from": "2026-07-23", "to": "2026-08-16", "spans_data_gap": True})
    body = TestClient(create_app(manifest_root, clock=_clock)).get(VERDICT).json()
    assert body["interval_days"] == 24
    assert "(24 días)" in body["summary"]["detected"]
    assert "separadas 24 días" in body["summary"]["missing"] and "hueco" in body["summary"]["missing"]


def test_full_window_does_not_blame_the_gap_for_its_length(manifest_root):
    _as_real(manifest_root, **{"from": "2026-06-17", "to": "2026-10-15", "kind": "full_window", "spans_data_gap": True})
    client = TestClient(create_app(manifest_root, clock=_clock))
    body = client.get(VERDICT).json()
    assert body["interval_days"] == 120
    assert "porque el par cruza el hueco" not in body["summary"]["missing"]
    assert "primera y la última fecha" in body["summary"]["missing"] and "incluye el hueco" in body["summary"]["missing"]
    english = client.get(VERDICT, params={"lang": "en"}).json()["summary"]["missing"]
    assert "because the pair crosses" not in english and "first and last dates" in english


def test_singular_day_in_both_languages():
    assert narrative.freshness_text(1, None, "synthetic", "es").startswith("La imagen más reciente tiene 1 día.")
    assert narrative.freshness_text(1, None, "synthetic", "en").startswith("The most recent image is 1 day old.")


def _timeline_body():
    return {"passes": [
        {"granule_id": "G20260711.h5", "acquired_at": "2026-07-11T00:41:30Z",
         "published_at": "2026-07-12T14:00:00Z", "latency_hours": 37.3},
        {"granule_id": "G20260723", "acquired_at": "2026-07-23T00:41:30Z",
         "published_at": None, "latency_hours": None},
    ]}


def test_http_timeline_parses_and_caches():
    calls = []

    def handler(request):
        calls.append(request.url.path)
        return httpx.Response(200, json=_timeline_body())

    clock = [0.0]
    source = HttpTimeline("http://catalog:8000/", httpx.Client(transport=httpx.MockTransport(handler)), lambda: clock[0])
    passes = source.passes("parral")
    assert calls == ["/aois/parral/timeline"]
    assert passes["G20260711"].latency_hours == 37.3 and passes["G20260723"].published_at is None
    source.passes("parral")
    assert len(calls) == 1
    clock[0] = 10_000
    source.passes("parral")
    assert len(calls) == 2


def test_http_timeline_failure_is_cached_briefly():
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(404)

    clock = [0.0]
    source = HttpTimeline("http://catalog:8000", httpx.Client(transport=httpx.MockTransport(handler)), lambda: clock[0])
    for _ in range(2):
        with pytest.raises(CatalogUnavailable):
            source.passes("parral")
    assert len(calls) == 1
    clock[0] = 120
    with pytest.raises(CatalogUnavailable):
        source.passes("parral")
    assert len(calls) == 2


# --- T-BAL-04: contraste óptico Sentinel-2 ----------------------------------------------

from verdicts import optical  # noqa: E402
from verdicts.catalog import HttpOptical, OpticalAcquisition, OpticalReference, OpticalTile  # noqa: E402

S2 = "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/13/R/CK"


def _acq(day, cloud, covers=True, hour=17, minute=46):
    when = datetime(day.year, day.month, day.day, hour, minute, tzinfo=timezone.utc)
    stamp = f"{day:%Y%m%d}"
    return OpticalAcquisition(
        platform="sentinel-2c", acquired_at=when, covers_aoi=covers, max_cloud_cover=cloud,
        tiles=(OpticalTile("13RCK", cloud, f"{S2}/{day.year}/{day.month}/S2C_13RCK_{stamp}_0_L2A/TCI.tif"),),
    )


def _reference(*acquisitions):
    return OpticalReference(
        source="Earth Search v1 (Element 84)", collection="sentinel-2-l2a",
        license="Datos Copernicus Sentinel: acceso libre con atribución",
        license_url="https://sentinel.esa.int/documents/247904/690755/Sentinel_Data_Legal_Notice",
        attribution="Contiene datos modificados de Copernicus Sentinel 2026", acquisitions=tuple(acquisitions),
    )


class FakeOptical:
    def __init__(self, acquisitions=(), fail=False):
        self.acquisitions = acquisitions
        self.fail = fail
        self.calls = []

    def scenes(self, aoi, day, days):
        self.calls.append((aoi, day, days))
        if self.fail:
            raise CatalogUnavailable(aoi)
        # Como catalog: solo lo que cae a ±days de la fecha pedida.
        return _reference(*(a for a in self.acquisitions if abs((a.acquired_at.date() - day).days) <= days))


JUNE_29 = date(2026, 6, 29)


def test_before_is_closest_scene_not_after_the_radar_date():
    scenes = [_acq(date(2026, 6, 24), 5), _acq(date(2026, 6, 28), 10), _acq(date(2026, 7, 1), 0)]
    chosen = optical.pick(scenes, "before", JUNE_29)
    assert chosen.status == "clear" and chosen.days_from_radar == -1


def test_after_is_closest_scene_not_before_the_radar_date():
    scenes = [_acq(date(2026, 7, 10), 0), _acq(date(2026, 7, 13), 10), _acq(date(2026, 7, 20), 0)]
    chosen = optical.pick(scenes, "after", date(2026, 7, 11))
    assert chosen.status == "clear" and chosen.days_from_radar == 2


def test_a_clear_scene_wins_over_a_closer_cloudy_one():
    scenes = [_acq(date(2026, 6, 28), 80), _acq(date(2026, 6, 23), 12)]
    chosen = optical.pick(scenes, "before", JUNE_29)
    assert chosen.status == "clear" and chosen.days_from_radar == -6


def test_cloudy_window_shows_the_least_cloudy_scene_instead_of_hiding_it():
    scenes = [_acq(date(2026, 7, 3), 39), _acq(date(2026, 7, 8), 65), _acq(date(2026, 7, 2), 20, covers=False)]
    chosen = optical.pick(scenes, "after", date(2026, 7, 1))
    assert chosen.status == "cloudy" and chosen.acquisition.max_cloud_cover == 39


def test_only_partial_scenes_are_declared_as_partial():
    chosen = optical.pick([_acq(date(2026, 6, 28), 5, covers=False)], "before", JUNE_29)
    assert chosen.status == "partial_coverage" and chosen.acquisition is not None


def test_scenes_beyond_the_search_window_do_not_count():
    assert optical.pick([_acq(date(2026, 6, 18), 0)], "before", JUNE_29).status == "none_in_window"
    assert optical.pick([], "after", JUNE_29).status == "none_in_window"


def test_same_day_scene_is_placed_by_hour_when_the_pass_time_is_known():
    scene = [_acq(JUNE_29, 0)]  # 17:46 UTC
    radar = datetime(2026, 6, 29, 0, 41, tzinfo=timezone.utc)
    assert optical.pick(scene, "before", JUNE_29, radar).status == "none_in_window"
    assert optical.pick(scene, "after", JUNE_29, radar).days_from_radar == 0
    # Sin hora conocida se compara por día y cuenta en los dos lados.
    assert optical.pick(scene, "before", JUNE_29).status == "clear"


PARRAL_SCENES = (
    _acq(date(2026, 6, 28), 26.6),
    _acq(date(2026, 7, 3), 39),
    _acq(date(2026, 7, 13), 18.2),
)


def test_verdict_carries_optical_before_and_after_with_tile_and_license(manifest_root):
    source = FakeOptical(PARRAL_SCENES)
    body = TestClient(create_app(manifest_root, clock=_clock, optical_source=source)).get(VERDICT).json()
    evidence = body["evidence"]["optical"]
    assert evidence["data_kind"] == "real" and evidence["cloud_cover_basis"] == "tile"
    assert evidence["license_url"].startswith("https://sentinel.esa.int/")
    assert evidence["max_cloud_cover"] == 30 and evidence["search_days"] == 10
    before, after = evidence["before"], evidence["after"]
    assert before["status"] == "clear" and before["scene"]["days_from_radar"] == -1
    assert before["scene"]["acquired_at"].startswith("2026-06-28")
    assert after["status"] == "clear" and after["scene"]["days_from_radar"] == 2
    assert after["scene"]["attribution"].startswith("Contiene datos modificados de Copernicus Sentinel")
    tile = after["scene"]["tiles"][0]
    assert tile["tile_url"].startswith("/tiles/cog/tiles/WebMercatorQuad/{z}/{x}/{y}.png?url=")
    assert "url=https%3A%2F%2Fsentinel-cogs.s3.us-west-2.amazonaws.com%2F" in tile["tile_url"]
    assert "2026-06-28, 1 día antes de la primera fecha de radar" in evidence["text"]
    assert "26,6 %" in evidence["text"] and "no la de la zona" in evidence["text"]
    assert sorted(day for _, day, _ in source.calls) == [JUNE_29, date(2026, 7, 11)]


def test_optical_text_in_english(manifest_root):
    client = TestClient(create_app(manifest_root, clock=_clock, optical_source=FakeOptical(PARRAL_SCENES)))
    text = client.get(VERDICT, params={"lang": "en"}).json()["evidence"]["optical"]["text"]
    assert "2026-07-13, 2 days after the second radar date" in text and "18.2 %" in text


def test_real_pass_time_moves_same_day_scene_to_after(manifest_root):
    _as_real(manifest_root)
    scenes = (_acq(JUNE_29, 3), _acq(date(2026, 7, 11), 4))
    client = TestClient(create_app(manifest_root, timeline=FakeTimeline(REAL_PASSES), clock=_clock,
                                   optical_source=FakeOptical(scenes)))
    evidence = client.get(VERDICT).json()["evidence"]["optical"]
    # La pasada de radar es a las 00:41 UTC y la óptica a las 17:46: la del 06-29 ya no es "de antes".
    assert evidence["before"]["radar_acquired_at"].startswith("2026-06-29T00:41:12")
    assert evidence["before"]["status"] == "none_in_window"
    assert evidence["after"]["scene"]["days_from_radar"] == 0
    assert "el mismo día que la segunda fecha de radar" in evidence["text"]


def test_storm_pair_without_clear_after_scene_says_so(manifest_root):
    _as_real(manifest_root, **{"from": "2026-06-29", "to": "2026-07-01"})
    scenes = (_acq(date(2026, 6, 28), 26.6), _acq(date(2026, 7, 3), 39), _acq(date(2026, 7, 8), 70))
    body = TestClient(create_app(manifest_root, clock=_clock, optical_source=FakeOptical(scenes))).get(VERDICT).json()
    after = body["evidence"]["optical"]["after"]
    assert after["status"] == "cloudy" and after["scene"]["max_cloud_cover"] == 39
    assert "Es la menos nublada" in body["evidence"]["optical"]["text"]


def test_no_scene_in_window_is_declared(manifest_root):
    body = TestClient(create_app(manifest_root, clock=_clock, optical_source=FakeOptical())).get(VERDICT).json()
    evidence = body["evidence"]["optical"]
    assert evidence["before"]["status"] == evidence["after"]["status"] == "none_in_window"
    assert evidence["before"]["scene"] is None
    assert "No hay imagen óptica Sentinel-2 de antes a 10 días o menos" in evidence["text"]
    assert "nubosidad es la de cada tesela" not in evidence["text"]


@pytest.mark.parametrize("source", [None, FakeOptical(fail=True)])
def test_catalog_down_keeps_the_verdict_and_declares_it(manifest_root, source):
    response = TestClient(create_app(manifest_root, clock=_clock, optical_source=source)).get(VERDICT)
    assert response.status_code == 200
    evidence = response.json()["evidence"]["optical"]
    assert evidence["before"]["status"] == evidence["after"]["status"] == "catalog_unavailable"
    assert evidence["license"] is None
    assert evidence["text"] == "No se sabe si hay imágenes ópticas Sentinel-2: el catálogo no respondió."


def test_verdict_list_asks_each_date_once(manifest_root):
    source = FakeOptical(PARRAL_SCENES)
    client = TestClient(create_app(manifest_root, clock=_clock, optical_source=source))
    assert client.get("/aois/parral/series/T048A-F015/verdicts").status_code == 200
    assert sorted(day for _, day, _ in source.calls) == [JUNE_29, date(2026, 7, 11)]
    assert all(days == optical.SEARCH_DAYS for _, _, days in source.calls)


def _optical_body():
    return {
        "source": "Earth Search v1 (Element 84)", "collection": "sentinel-2-l2a",
        "license": "Datos Copernicus Sentinel: acceso libre con atribución",
        "license_url": "https://sentinel.esa.int/documents/247904/690755/Sentinel_Data_Legal_Notice",
        "attribution": "Contiene datos modificados de Copernicus Sentinel 2026",
        "acquisitions": [
            {"platform": "sentinel-2c", "acquired_at": "2026-06-28T17:46:31Z", "days_from_date": -1,
             "covers_aoi": True, "max_cloud_cover": 26.6,
             "tiles": [{"id": "S2C_13RCK_20260628_0_L2A", "tile": "13RCK", "acquired_at": "2026-06-28T17:46:31Z",
                        "cloud_cover": 26.6, "visual_url": f"{S2}/2026/6/S2C_13RCK_20260628_0_L2A/TCI.tif"}]},
            {"platform": "sentinel-2a", "acquired_at": "2026-06-30T17:46:31Z", "days_from_date": 1,
             "covers_aoi": True, "max_cloud_cover": 1.0,
             "tiles": [{"id": "x", "tile": "13RCK", "acquired_at": "2026-06-30T17:46:31Z",
                        "cloud_cover": 1.0, "visual_url": "file:///etc/passwd"}]},
        ],
    }


def test_http_optical_asks_without_cloud_limit_parses_and_caches():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json=_optical_body())

    clock = [0.0]
    source = HttpOptical("http://catalog:8000/", httpx.Client(transport=httpx.MockTransport(handler)), lambda: clock[0])
    result = source.scenes("parral", JUNE_29, 10)
    assert requests[0].url.path == "/aois/parral/references/optical"
    assert dict(requests[0].url.params) == {"date": "2026-06-29", "days": "10", "max_cloud": "100"}
    # Una URL que no es HTTPS nunca llega al veredicto ni a TiTiler.
    assert len(result.acquisitions) == 1 and result.acquisitions[0].max_cloud_cover == 26.6
    assert result.acquisitions[0].acquired_at.tzinfo is not None
    source.scenes("parral", JUNE_29, 10)
    assert len(requests) == 1
    clock[0] = 10_000
    source.scenes("parral", JUNE_29, 10)
    assert len(requests) == 2


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        # S2A_13RDK_20260812_1_L2A, escena de borde de franja: caja de los datos, no del cuadrado MGRS (T-ANT-19).
        ([-106.00934, 26.12852, -105.70229, 27.12071], (-106.00934, 26.12852, -105.70229, 27.12071)),
        ([179.5, -17.0, -179.5, -16.0], (179.5, -17.0, -179.5, -16.0)),  # cruza el antimeridiano: no se reordena
        (None, None),  # catalog anterior a T-ANT-19, sin el campo
        ([1, 2, 3], None),
        (["a", 0, 1, 2], None),
        ([0, 10, 1, 5], None),  # sur > norte
        ([0, 5, 1, 5], None),  # caja plana
        ([0, 0, 200, 1], None),
        ([float("-inf"), 26.0, -105.0, 27.0], None),
    ],
)
def test_http_optical_passes_tile_bbox_through_or_drops_it(value, expected):
    body = _optical_body()
    tile = body["acquisitions"][0]["tiles"][0]
    if value is None:
        tile.pop("bbox", None)
    else:
        tile["bbox"] = value
    content = json.dumps(body, allow_nan=True).encode()  # -inf no es JSON estricto, pero así se prueba el filtro
    source = HttpOptical(
        "http://catalog:8000/",
        httpx.Client(transport=httpx.MockTransport(
            lambda request: httpx.Response(200, content=content, headers={"content-type": "application/json"})
        )),
        lambda: 0.0,
    )
    assert source.scenes("parral", JUNE_29, 10).acquisitions[0].tiles[0].bbox == expected


def test_verdict_gives_each_optical_tile_its_bbox_or_null(manifest_root):
    box = (-106.00934, 26.12852, -105.70229, 27.12071)
    day = date(2026, 7, 13)
    with_box = OpticalAcquisition(
        platform="sentinel-2a", acquired_at=datetime(2026, 7, 13, 17, 56, tzinfo=timezone.utc), covers_aoi=True,
        max_cloud_cover=4.0,
        tiles=(
            OpticalTile("13RCK", 4.0, f"{S2}/{day.year}/{day.month}/S2A_13RCK_20260713_0_L2A/TCI.tif"),
            OpticalTile("13RDK", 3.0, f"{S2}/{day.year}/{day.month}/S2A_13RDK_20260713_0_L2A/TCI.tif", box),
        ),
    )
    source = FakeOptical((_acq(date(2026, 6, 28), 5), with_box))
    body = TestClient(create_app(manifest_root, clock=_clock, optical_source=source)).get(VERDICT).json()
    tiles = {tile["tile"]: tile for tile in body["evidence"]["optical"]["after"]["scene"]["tiles"]}
    assert tiles["13RDK"]["bbox"] == list(box)
    assert tiles["13RCK"]["bbox"] is None


def test_http_optical_failure_is_cached_briefly():
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(502)

    clock = [0.0]
    source = HttpOptical("http://catalog:8000", httpx.Client(transport=httpx.MockTransport(handler)), lambda: clock[0])
    for _ in range(2):
        with pytest.raises(CatalogUnavailable):
            source.scenes("parral", JUNE_29, 10)
    assert len(calls) == 1


# --- Eventos en horas UTC (revisión de Antena: el corte llegaba 24 h antes) -----------------

from datetime import time as dtime  # noqa: E402

STORM_PASSES = [date(2026, 6, 26), date(2026, 6, 29), date(2026, 7, 8), date(2026, 7, 11)]
STORM = date(2026, 7, 1)


@pytest.mark.parametrize("hours, state, cause", [
    (144, "not_observable", "no_acquisition_during_event"),  # ni empezando a las 23:59 llega al 07-08
    (145, "not_observable", "timing_uncertain"),  # antes salía "observable"
    (168, "not_observable", "timing_uncertain"),
    (191, "not_observable", "timing_uncertain"),
    (192, "observable", None),  # cubre el 07-08 entero aunque empiece a las 00:00 del 07-01
])
def test_event_without_times_counts_hours_and_declares_doubt(hours, state, cause):
    status = rules.event_status(STORM_PASSES, STORM, hours)
    assert (status.state, status.cause, status.next_pass) == (state, cause, date(2026, 7, 8))


@pytest.mark.parametrize("hours, state", [(169, "not_observable"), (170, "observable")])
def test_event_with_known_times_cuts_at_the_pass(hours, state):
    times = {date(2026, 7, 8): datetime(2026, 7, 8, 13, 10, tzinfo=timezone.utc)}
    status = rules.event_status(STORM_PASSES, STORM, hours, dtime(12, 0), times)
    assert status.state == state  # 12:00 del 07-01 a 13:10 del 07-08 son 169 h 10 min
    assert status.cause in (None, "no_acquisition_during_event")


def test_same_day_pass_before_the_event_is_the_previous_one():
    times = {date(2026, 7, 1): datetime(2026, 7, 1, 0, 41, tzinfo=timezone.utc)}
    status = rules.event_status([date(2026, 7, 1), date(2026, 7, 8)], STORM, 24, dtime(18, 0), times)
    assert status.previous_pass == date(2026, 7, 1) and status.next_pass == date(2026, 7, 8)
    assert status.cause == "no_acquisition_during_event"


def test_event_endpoint_declares_doubt_and_takes_time(client):
    body = client.get("/aois/parral/events", params={"date": "2026-07-01", "persistence_hours": 230}).json()  # pasada: 07-11
    assert body["state"] == "not_observable" and body["cause"] == "timing_uncertain"
    assert body["event_time"] is None and body["next_pass_acquired_at"] is None
    assert "hora UTC de inicio" in body["summary"]["missing"]
    timed = client.get("/aois/parral/events", params={"date": "2026-07-01", "persistence_hours": 300, "time": "12:00"})
    assert timed.json()["event_time"] == "12:00:00" and timed.json()["state"] == "observable"


def test_real_event_uses_pass_times_from_catalog(manifest_root):
    _as_real(manifest_root)
    # Pasadas del fixture: 06-29 00:41:12 y 07-11 00:41:30 UTC.
    client = TestClient(create_app(manifest_root, timeline=FakeTimeline(REAL_PASSES), clock=_clock))
    params = {"date": "2026-07-01", "time": "00:00"}
    body = client.get("/aois/parral/events", params={**params, "persistence_hours": 240}).json()
    assert body["next_pass_acquired_at"].startswith("2026-07-11T00:41:30")
    assert body["state"] == "not_observable" and body["cause"] == "no_acquisition_during_event"
    body = client.get("/aois/parral/events", params={**params, "persistence_hours": 241}).json()
    assert body["state"] == "observable"


# --- T-BAL-06: persistencias por tipo de evento, declaradas como supuestos ------------------

@pytest.mark.parametrize("event_type, hours", [(None, None), ("urban_storm", None), (None, 30), ("wildfire", 30)])
def test_persistence_says_where_the_hours_come_from(event_type, hours):
    assumed = rules.persistence(event_type, hours)
    expected = hours or rules.PERSISTENCE_BY_EVENT_TYPE.get(event_type) or rules.DEFAULT_PERSISTENCE_HOURS
    source = "user" if hours else ("event_type" if event_type else "default")
    assert (assumed.hours, assumed.source, assumed.event_type) == (expected, source, event_type)


def test_persistence_table_matches_the_plan():
    assert rules.PERSISTENCE_BY_EVENT_TYPE == {"urban_storm": 6, "river_flood": 72, "wildfire": 240}


@pytest.mark.parametrize("event_type, hours, cause", [
    ("urban_storm", 6, "no_acquisition_during_event"),
    ("river_flood", 72, "no_acquisition_during_event"),
    # 240 h desde el 07-01 llegan al 07-11, pero sin horas no se sabe si cubren la pasada.
    ("wildfire", 240, "timing_uncertain"),
])
def test_event_type_sets_the_assumed_persistence(client, event_type, hours, cause):
    body = client.get("/aois/parral/events", params={"date": "2026-07-01", "event_type": event_type}).json()
    assert body["event_type"] == event_type and body["persistence_hours"] == hours
    assert body["state"] == "not_observable" and body["cause"] == cause
    assumption = body["assumption"]
    assert assumption["source"] == "event_type" and assumption["persistence_hours"] == hours
    assert assumption["calibrated"] is False
    assert assumption["hours_by_event_type"] == rules.PERSISTENCE_BY_EVENT_TYPE
    assert assumption["text"].startswith("Supuesto:") and f"{hours} h" in assumption["text"]
    assert assumption["text"] in body["summary"]["does_not_prove"]


def test_explicit_hours_win_over_event_type_and_default_is_declared(client):
    both = client.get("/aois/parral/events", params={"date": "2026-07-01", "event_type": "urban_storm",
                                                     "persistence_hours": 30, "lang": "en"}).json()
    assert both["persistence_hours"] == 30 and both["assumption"]["source"] == "user"
    assert both["assumption"]["text"].startswith("Assumption:")
    plain = client.get("/aois/parral/events", params={"date": "2026-07-01"}).json()
    assert plain["persistence_hours"] == 24 and plain["event_type"] is None
    assert plain["assumption"]["source"] == "default" and "tipo de evento" in plain["assumption"]["text"]


def test_unknown_event_type_is_rejected(client):
    assert client.get("/aois/parral/events", params={"date": "2026-07-01", "event_type": "tornado"}).status_code == 422


# Los textos de /events los lee alguien sin conocer la API: no nombran parámetros.
@pytest.mark.parametrize("lang", ["es", "en"])
@pytest.mark.parametrize("params", [
    {"date": "2026-07-01"},
    {"date": "2026-07-01", "persistence_hours": 230},
    {"date": "2026-07-01", "event_type": "wildfire"},
    {"date": "2026-07-01", "persistence_hours": 300, "time": "12:00"},
])
def test_event_texts_do_not_name_api_parameters(client, params, lang):
    body = client.get("/aois/parral/events", params={**params, "lang": lang}).json()
    texts = [*body["summary"].values(), body["assumption"]["text"], body["cause_label"] or ""]
    for jargon in ("event_type", "persistence_hours", "parámetro", "parameter", "time)"):
        assert not any(jargon in text for text in texts if text), (jargon, texts)


# La duración del evento es un supuesto: los textos no la dan por hecha ("mientras duraba").
@pytest.mark.parametrize("lang, assumed, as_fact", [
    ("es", "duración supuesta", ("mientras duraba", "duración indicada")),
    ("en", "assumed duration", ("while the event lasted", "while it lasted", "stated duration")),
])
@pytest.mark.parametrize("params", [
    {"date": "2026-07-01"},                                              # no_acquisition_during_event
    {"date": "2026-07-01", "persistence_hours": 230},                    # timing_uncertain
    {"date": "2026-07-01", "persistence_hours": 300, "time": "12:00"},   # observable
])
def test_event_texts_call_the_duration_an_assumption(client, params, lang, assumed, as_fact):
    body = client.get("/aois/parral/events", params={**params, "lang": lang}).json()
    texts = [body["summary"]["detected"], body["summary"]["does_not_prove"], body["cause_label"] or ""]
    assert any(assumed in text for text in texts), texts
    for phrase in as_fact:
        assert not any(phrase in text for text in texts), (phrase, texts)


# --- Relieve (T-BAL-15, RF-INT-12) ---------------------------------------------------------------------------------

DEM = {
    "layer": "parral/dem.tif", "source": "Copernicus DEM GLO-30", "crs": "EPSG:4326",
    "vertical_datum": "EGM2008", "units": "m",
    "attribution": "produced using Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH "
                   "2014-2018 provided under COPERNICUS by the European Union and ESA; all rights reserved",
}


def test_series_without_dem_has_null_relief(client):
    series = client.get("/aois/parral/series").json()
    assert series and all(item["relief"] is None for item in series)


def test_series_with_dem_gives_a_terrainrgb_template(manifest_root):
    path = manifest_root / "parral/T048A-F015/manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["dem"] = DEM
    schema = json.loads((ROOT / "contracts" / "artifact-manifest.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(manifest, schema)
    path.write_text(json.dumps(manifest), encoding="utf-8")
    relief = TestClient(create_app(manifest_root)).get("/aois/parral/series").json()[0]["relief"]
    assert relief["tiles"].startswith("/tiles/cog/tiles/WebMercatorQuad/{z}/{x}/{y}.png?url=")
    assert "file%3A%2F%2F%2Fdata%2Fartifacts%2Fparral%2Fdem.tif" in relief["tiles"]
    assert "algorithm=terrainrgb" in relief["tiles"]
    assert relief["encoding"] == "mapbox" and relief["exaggeration"] == 1.0 and relief["tile_size"] == 256
    assert relief["attribution"] == DEM["attribution"] and relief["vertical_datum"] == "EGM2008"
    assert relief["data_kind"] == "real"


def test_synthetic_dem_is_declared_and_keeps_its_own_attribution(manifest_root):
    """T-ECO-13: el DEM de seed-synthetic dice synthetic y nunca hereda la atribución de Copernicus."""
    path = manifest_root / "parral/T048A-F015/manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["dem"] = {**DEM, "data_kind": "synthetic", "source": "DEM sintético de seed-synthetic",
                       "vertical_datum": "none", "attribution": "DEM sintético: no describe ningún relieve real."}
    schema = json.loads((ROOT / "contracts" / "artifact-manifest.schema.json").read_text(encoding="utf-8"))
    if "data_kind" in schema["properties"]["dem"]["properties"]:  # el esquema lo admite desde el PR 106
        jsonschema.validate(manifest, schema)
    path.write_text(json.dumps(manifest), encoding="utf-8")
    relief = TestClient(create_app(manifest_root)).get("/aois/parral/series").json()[0]["relief"]
    assert relief["data_kind"] == "synthetic" and relief["vertical_datum"] == "none"
    assert "Copernicus" not in relief["attribution"]
