"""Búsqueda de veredictos (T-BAL-11, RF-BUS-01 y 03 a 05)."""
import json

import pytest
from fastapi.testclient import TestClient

from test_verdicts import _clock, counts, manifest_root  # noqa: F401  (fixture)
from test_water import FakeFetcher
from verdicts import water
from verdicts.main import app as public_app
from verdicts.main import create_app

SEARCH = "/search/verdicts"
EXPORT = "/search/verdicts/export"
STUDENT = {"X-Auth-Role": "student"}
RESEARCHER = {"X-Auth-Role": "researcher"}
SERIES = "parral/T048A-F015"


def _pair(base, pair_id, start, end, kind="consecutive", **values):
    return {**base, "id": pair_id, "from": start, "to": end, "kind": kind,
            "stats": {**base["stats"], "counts": counts(**values)}}


@pytest.fixture()
def root(manifest_root):  # noqa: F811
    """Cuatro pares: dos change_probable (10 % y 6 %), uno sin cambio y uno not_observable."""
    path = manifest_root / SERIES / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    base = manifest["pairs"][0]
    manifest["dates"].append({**manifest["dates"][1], "date": "2026-07-23", "granule": "G20260723"})
    manifest["pairs"] = [
        base,
        _pair(base, "20260711_20260723", "2026-07-11", "2026-07-23", no_change=940, change_probable=60),
        _pair(base, "20260629_20260723", "2026-06-29", "2026-07-23", "full_window", no_change=1000),
        _pair(base, "20260723_20260816", "2026-07-23", "2026-08-16", no_change=100, low_looks=900),
    ]
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return manifest_root


@pytest.fixture()
def client(root):
    return TestClient(create_app(root, clock=_clock, build_index=False))


def _ids(body):
    return [row["pair_id"] for row in body["results"]]


@pytest.mark.parametrize("headers", [{}, {"X-Auth-Role": "admin"}, {"X-Auth-Role": "public"}])
def test_public_gets_403_with_required_role(client, headers):
    response = client.get(SEARCH, headers=headers)
    assert response.status_code == 403
    assert response.json()["required_role"] == "student"


def test_student_lists_every_verdict_with_data_kind_and_link(client):
    body = client.get(SEARCH, headers=STUDENT).json()
    assert body["total"] == 4 and body["next_cursor"] is None
    assert all(row["data_kind"] == "synthetic" for row in body["results"])
    row = next(row for row in body["results"] if row["pair_id"] == "20260629_20260711")
    assert row["verdict_path"] == "/aois/parral/series/T048A-F015/verdicts/20260629_20260711"
    assert row["granules"] == ["G20260629", "G20260711"] and row["direction"] == "A"
    assert body["query"]["role"] == "student" and body["query"]["sort"] == "date"


def test_rows_copy_the_full_verdict(client):
    """Ningún resultado afirma más que el veredicto completo: mismos valores, sin texto propio."""
    full = {v["id"]: v for v in client.get("/aois/parral/series/T048A-F015/verdicts").json()}
    for row in client.get(SEARCH, headers=STUDENT).json()["results"]:
        verdict = full[row["pair_id"]]
        assert row["state"] == verdict["state"] and row["cause"] == verdict["cause"]
        assert row["changed_fraction"] == verdict["evidence"]["changed_fraction"]
        assert row["observed_fraction"] == verdict["evidence"]["observed_fraction"]
        assert row["interval_days"] == verdict["interval_days"]
        assert row["data_kind"] == verdict["receipt"]["data_kind"]
        assert not {"summary", "hypotheses", "cause_label"} & set(row)


@pytest.mark.parametrize("state", ["change_probable", "no_detectable_change", "not_observable"])
def test_state_filter_matches_the_verdicts_route(client, state):
    expected = {v["id"] for v in client.get("/aois/parral/series/T048A-F015/verdicts").json() if v["state"] == state}
    body = client.get(SEARCH, params={"state": state}, headers=STUDENT).json()
    assert set(_ids(body)) == expected and body["total"] == len(expected) and expected


def test_several_states_and_structured_filters(client):
    body = client.get(SEARCH, params=[("state", "change_probable"), ("state", "not_observable")], headers=STUDENT).json()
    assert body["total"] == 3
    assert _ids(client.get(SEARCH, params={"kind": "full_window"}, headers=STUDENT).json()) == ["20260629_20260723"]
    assert client.get(SEARCH, params={"interval_min": 13}, headers=STUDENT).json()["total"] == 2
    assert client.get(SEARCH, params={"cause": "low_looks"}, headers=STUDENT).json()["total"] == 1
    body = client.get(SEARCH, params={"changed_min": 0.07}, headers=STUDENT).json()
    assert _ids(body) == ["20260629_20260711"]
    body = client.get(SEARCH, params={"date_from": "2026-07-11", "date_to": "2026-07-23"}, headers=STUDENT).json()
    assert _ids(body) == ["20260711_20260723"]
    assert client.get(SEARCH, params={"data_kind": "synthetic", "aoi": "parral"}, headers=STUDENT).json()["total"] == 4


def test_no_match_is_an_empty_list_not_a_404(client):
    response = client.get(SEARCH, params={"direction": "D", "series_id": "T048A-F015"}, headers=STUDENT)
    body = response.json()
    assert response.status_code == 200 and body["total"] == 0 and body["results"] == []
    assert body["query"]["filters"] == {"direction": "D", "series_id": "T048A-F015"}


def test_sort_by_changed_fraction_and_interval(client):
    body = client.get(SEARCH, params={"sort": "changed_fraction"}, headers=STUDENT).json()
    values = [row["changed_fraction"] for row in body["results"]]
    assert values == sorted(values, reverse=True)
    body = client.get(SEARCH, params={"sort": "interval", "order": "asc"}, headers=STUDENT).json()
    values = [row["interval_days"] for row in body["results"]]
    assert values == sorted(values)


def test_cursor_walks_every_row_once(client):
    seen, cursor = [], None
    while True:
        params = {"limit": 1, "sort": "date", **({"cursor": cursor} if cursor else {})}
        body = client.get(SEARCH, params=params, headers=STUDENT).json()
        assert body["total"] == 4
        seen += _ids(body)
        cursor = body["next_cursor"]
        if cursor is None:
            break
    assert len(seen) == 4 and len(set(seen)) == 4


def test_cursor_of_another_query_or_garbage_is_400(client):
    cursor = client.get(SEARCH, params={"limit": 1}, headers=STUDENT).json()["next_cursor"]
    assert client.get(SEARCH, params={"limit": 1, "state": "not_observable", "cursor": cursor},
                      headers=STUDENT).status_code == 400
    assert client.get(SEARCH, params={"cursor": "%%%"}, headers=STUDENT).status_code == 400


def test_quality_filter_is_for_researchers(client):
    response = client.get(SEARCH, params={"quality_flag": "true"}, headers=STUDENT)
    assert response.status_code == 403 and response.json()["required_role"] == "researcher"
    body = client.get(SEARCH, params={"quality_flag": "false"}, headers=RESEARCHER).json()
    assert body["total"] == 4 and body["query"]["role"] == "researcher"


def test_page_size_by_role(client):
    response = client.get(SEARCH, params={"limit": 51}, headers=STUDENT)
    assert response.status_code == 403 and response.json()["required_role"] == "researcher"
    assert client.get(SEARCH, params={"limit": 50}, headers=STUDENT).status_code == 200
    assert client.get(SEARCH, params={"limit": 500}, headers=RESEARCHER).status_code == 200
    assert client.get(SEARCH, params={"limit": 501}, headers=RESEARCHER).status_code == 422


def test_water_without_contrast_is_not_available_and_counted(client):
    body = client.get(SEARCH, headers=STUDENT).json()
    assert all(row["water"]["summary"] == "not_available" for row in body["results"])
    assert body["results"][0]["water"]["reasons"] == ["catalog_unavailable"]
    body = client.get(SEARCH, params={"water": "disagree"}, headers=STUDENT).json()
    assert body["total"] == 0
    assert body["query"]["not_evaluated"]["water"] == {"count": 4, "reasons": {"catalog_unavailable": 4}}


def test_water_is_pending_until_the_contrast_is_warmed(root):
    contrast = water.WaterContrast(root, FakeFetcher())
    client = TestClient(create_app(root, clock=_clock, water_contrast=contrast, build_index=False))
    body = client.get(SEARCH, headers=STUDENT).json()
    assert body["query"]["water_contrast"] == "pending"
    assert {tuple(row["water"]["reasons"]) for row in body["results"]} == {("contrast_not_computed",)}


def test_cloud_filter_skips_rows_without_scene(client):
    body = client.get(SEARCH, params={"max_cloud_cover": 30}, headers=STUDENT).json()
    assert body["total"] == 0 and body["query"]["not_evaluated"]["max_cloud_cover"]["count"] == 4


def test_index_is_built_at_startup(root):
    with TestClient(create_app(root, clock=_clock, build_index=True)) as client:
        assert client.get(SEARCH, headers=STUDENT).json()["total"] == 4


def test_contract_declares_profile_and_security():
    spec = public_app.openapi()
    operation = spec["paths"][SEARCH]["get"]
    assert operation["x-required-role"] == "student" and operation["security"] == [{"bearerAuth": []}]
    assert "403" in operation["responses"]
    assert spec["components"]["securitySchemes"]["bearerAuth"]["scheme"] == "bearer"
    export = spec["paths"][EXPORT]["get"]
    assert export["x-required-role"] == "researcher" and export["security"] == [{"bearerAuth": []}]
    assert all("security" not in ops["get"] for path, ops in spec["paths"].items() if path not in (SEARCH, EXPORT))


# --- Texto libre y área (T-BAL-17, RF-BUS-02 y 10) ----------------------------------------------------------------

from verdicts import search as search_module  # noqa: E402
from verdicts.catalog import CatalogUnavailable, Footprint  # noqa: E402

# Huella aproximada de T048 en CMR (5 puntos, anillo cerrado).
T048_RING = ((-104.24576, 25.97109), (-104.87266, 28.10246), (-107.50728, 27.44489), (-106.82264, 25.33107),
             (-104.24576, 25.97109))


class FakeFootprints:
    def __init__(self, items=None, fail=False):
        self.items = items if items is not None else [Footprint(48, "A", 15, (T048_RING,))]
        self.fail = fail
        self.calls = 0

    def footprints(self, aoi):
        self.calls += 1
        if self.fail:
            raise CatalogUnavailable(aoi)
        return self.items


def _area_client(root, source):
    return TestClient(create_app(root, clock=_clock, build_index=False, footprint_source=source))


def test_free_text_searches_the_verdict_texts_in_each_language(client):
    full = client.get("/aois/parral/series/T048A-F015/verdicts").json()
    body = client.get(SEARCH, headers=STUDENT, params={"q": "G20260629"}).json()
    expected = sorted(v["id"] for v in full if "G20260629" in v["receipt"]["granules"])
    assert expected and sorted(_ids(body)) == expected
    assert body["query"]["filters"]["q"] == "G20260629" and body["query"]["filters"]["lang"] == "es"
    # Causa de not_observable (low_looks), en mayúsculas y sin distinguir acentos.
    for text in ("MUESTRAS DE RADAR", "múestras"):
        assert _ids(client.get(SEARCH, headers=STUDENT, params={"q": text}).json()) == ["20260723_20260816"]
    # Mismo texto en inglés solo con lang=en.
    en = client.get(SEARCH, headers=STUDENT, params={"q": "radar samples", "lang": "en"}).json()
    assert _ids(en) == ["20260723_20260816"] and en["query"]["filters"]["lang"] == "en"
    assert client.get(SEARCH, headers=STUDENT, params={"q": "radar samples"}).json()["total"] == 0
    # Sin q, lang no cuenta como filtro.
    assert "lang" not in client.get(SEARCH, headers=STUDENT, params={"lang": "en"}).json()["query"]["filters"]


def test_free_text_is_a_prefix_and_of_every_word(client):
    all_ids = _ids(client.get(SEARCH, headers=STUDENT).json())
    body = client.get(SEARCH, headers=STUDENT, params={"q": "sintétic 20260711_2026"}).json()
    assert body["total"] >= 1 and set(_ids(body)) <= set(all_ids)
    assert all("20260711_2026" in pair for pair in _ids(body))
    assert client.get(SEARCH, headers=STUDENT, params={"q": "palabra-que-no-existe"}).json()["total"] == 0


@pytest.mark.parametrize("text", ['"', "NEAR(a b)", "*", "a OR", "body:x", "'; DROP TABLE docs; --", "   "])
def test_free_text_never_breaks_on_fts_syntax(client, text):
    response = client.get(SEARCH, headers=STUDENT, params={"q": text})
    assert response.status_code == 200
    assert isinstance(response.json()["total"], int)


def test_fts_query_quotes_every_term():
    assert search_module.fts_query('a "b" OR c*') == '"a"* AND "b"* AND "OR"* AND "c"*'
    assert search_module.fts_query(" ,;* ") is None


def test_bbox_keeps_series_whose_footprint_touches_it(root):
    source = FakeFootprints()
    client = _area_client(root, source)
    inside = client.get(SEARCH, headers=STUDENT, params={"bbox": "-105.8,26.85,-105.6,27.0"}).json()
    assert inside["total"] == 4 and inside["query"]["filters"]["bbox"] == [-105.8, 26.85, -105.6, 27.0]
    # Un rectángulo que contiene toda la huella también la toca.
    assert client.get(SEARCH, headers=STUDENT, params={"bbox": "-110,20,-100,30"}).json()["total"] == 4
    # Lejos de la huella (Ciudad de México), nada; dentro de la caja de la huella pero fuera del polígono, nada.
    assert client.get(SEARCH, headers=STUDENT, params={"bbox": "-99.3,19.2,-98.9,19.6"}).json()["total"] == 0
    assert client.get(SEARCH, headers=STUDENT, params={"bbox": "-107.5,25.35,-107.3,25.5"}).json()["total"] == 0


def test_bbox_without_footprint_is_counted_not_hidden(root):
    for source, reason in ((FakeFootprints(fail=True), "catalog_unavailable"),
                           (FakeFootprints([Footprint(48, "A", 15, None)]), "footprint_unavailable"),
                           (FakeFootprints([]), "footprint_unavailable"),
                           (None, "catalog_unavailable")):
        body = _area_client(root, source).get(SEARCH, headers=STUDENT, params={"bbox": "-106,26,-105,27"}).json()
        assert body["total"] == 0
        assert body["query"]["not_evaluated"]["bbox"] == {"count": 4, "reasons": {reason: 4}}


@pytest.mark.parametrize("value", ["1,2,3", "a,b,c,d", "-105,27,-106,28", "-105,27,-104,26", "-190,0,0,10",
                                   "0,-91,10,0", "nan,0,1,1"])
def test_bad_bbox_is_422(root, value):
    response = _area_client(root, FakeFootprints()).get(SEARCH, headers=STUDENT, params={"bbox": value})
    assert response.status_code == 422


def test_bbox_meets_ring_cases():
    square = ((0, 0), (10, 0), (10, 10), (0, 10), (0, 0))
    meets = search_module.bbox_meets_ring
    assert meets((2, 2, 3, 3), square)          # dentro
    assert meets((-5, -5, 20, 20), square)      # contiene al polígono
    assert meets((-5, 4, 20, 6), square)        # lo cruza sin vértices dentro de ninguno
    assert meets((10, 10, 12, 12), square)      # se tocan en una esquina
    assert not meets((11, 11, 12, 12), square)
    triangle = ((0, 0), (10, 0), (0, 10), (0, 0))
    assert not meets((8, 8, 9, 9), triangle)    # dentro de la caja del triángulo, fuera de él


# --- Exportación (T-BAL-13, RF-BUS-06) -----------------------------------------------------------------------------

import csv  # noqa: E402
import io  # noqa: E402


@pytest.mark.parametrize("headers", [{}, STUDENT])
def test_export_is_for_researchers(client, headers):
    response = client.get(EXPORT, headers=headers, params={"format": "csv"})
    assert response.status_code == 403 and response.json()["required_role"] == "researcher"


def test_export_csv_has_what_a_citation_needs(client):
    response = client.get(EXPORT, headers=RESEARCHER, params={"format": "csv", "state": "change_probable"})
    assert response.status_code == 200 and response.headers["content-type"].startswith("text/csv")
    assert "attachment" in response.headers["content-disposition"]
    rows = list(csv.DictReader(io.StringIO(response.content.decode("utf-8-sig"))))
    full = {v["id"]: v for v in client.get("/aois/parral/series/T048A-F015/verdicts").json()}
    assert sorted(row["pair_id"] for row in rows) == sorted(i for i, v in full.items() if v["state"] == "change_probable")
    for row in rows:
        verdict = full[row["pair_id"]]
        assert row["data_kind"] == "synthetic" and row["interval_days"] == str(verdict["interval_days"])
        assert [row["granule_from"], row["granule_to"]] == verdict["receipt"]["granules"]
        assert float(row["min_changed_fraction"]) == verdict["evidence"]["decision_rule"]["min_changed_fraction"]
        assert row["decision_calibrated"] == "false"
        assert "min_changed_fraction=" in row["assumptions"] and "sin calibrar" in row["assumptions"]
        assert row["verdict_path"].endswith(row["pair_id"])
    assert response.headers["x-export-total"] == str(len(rows))
    query = json.loads(response.headers["x-export-query"])
    assert query["filters"] == {"state": ["change_probable"]} and query["role"] == "researcher"
    assert response.headers["x-export-data-kinds"] == "synthetic"


def test_export_json_matches_the_search_and_carries_metadata(client):
    params = {"sort": "changed_fraction", "order": "asc"}
    search_ids = _ids(client.get(SEARCH, headers=RESEARCHER, params={**params, "limit": 500}).json())
    body = client.get(EXPORT, headers=RESEARCHER, params={**params, "format": "json"}).json()
    assert [item["pair_id"] for item in body["results"]] == search_ids
    meta = body["metadata"]
    assert meta["total"] == len(search_ids) and meta["data_kinds"] == ["synthetic"]
    assert meta["query"] == {"filters": {}, "sort": "changed_fraction", "order": "asc", "role": "researcher"}
    assert "sintéticos" in meta["notice"]
    first = body["results"][0]
    names = {item["name"] for item in first["assumptions"]}
    assert {"min_observed_fraction", "min_changed_fraction", "radar_water_hh_db_below"} <= names
    assert all(item["calibrated"] is False for item in first["assumptions"])


def test_export_geojson_uses_the_zone_box(client):
    response = client.get(EXPORT, headers=RESEARCHER, params={"format": "geojson"})
    assert response.headers["content-type"].startswith("application/geo+json")
    body = response.json()
    assert body["type"] == "FeatureCollection" and body["metadata"]["total"] == 4 == len(body["features"])
    feature = body["features"][0]
    assert feature["geometry"]["type"] == "Polygon"
    ring = feature["geometry"]["coordinates"][0]
    assert ring[0] == ring[-1] == [-105.95, 26.7]
    assert feature["properties"]["data_kind"] == "synthetic"


def test_export_empty_result_is_valid(client):
    body = client.get(EXPORT, headers=RESEARCHER, params={"format": "json", "interval_min": 999}).json()
    assert body["results"] == [] and body["metadata"]["total"] == 0
    response = client.get(EXPORT, headers=RESEARCHER, params={"format": "csv", "interval_min": 999})
    assert len(list(csv.reader(io.StringIO(response.content.decode("utf-8-sig"))))) == 1


def test_export_counts_rows_it_could_not_evaluate(client):
    meta = client.get(EXPORT, headers=RESEARCHER, params={"format": "json", "water": "agree"}).json()["metadata"]
    assert meta["total"] == 0 and meta["not_evaluated"]["water"]["count"] == 4


def test_export_needs_a_known_format(client):
    assert client.get(EXPORT, headers=RESEARCHER).status_code == 422
    assert client.get(EXPORT, headers=RESEARCHER, params={"format": "xlsx"}).status_code == 422


# --- Fracción de cambio dentro del rectángulo (T-BAL-18, RF-BUS-10 P2) ------------------------------------------------


def _cell(west, south, pixels, observed, changed, state="no_detectable_change", cause=None, size=0.01):
    ring = [[west, south], [west + size, south], [west + size, south + size], [west, south + size], [west, south]]
    return {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [ring]},
            "properties": {"id": f"{west}_{south}", "state": state, "cause": cause, "observed_fraction": observed,
                           "changed_fraction": changed, "pixels": pixels}}


@pytest.fixture()
def cells_root(root):
    """Celdas en el primer par: dos con cambio al oeste, una sin observar al este y otra sin cambio en medio."""
    cells = {"type": "FeatureCollection", "cell_size_m": 1000.0,
             "rules": {"min_observed_fraction": 0.5, "min_changed_fraction": 0.05},
             "features": [
                 _cell(-105.80, 26.90, 10000, 1.0, 0.20, "change_probable"),
                 _cell(-105.79, 26.90, 10000, 0.5, 0.10, "change_probable"),
                 _cell(-105.70, 26.90, 10000, 1.0, 0.0),
                 _cell(-105.60, 26.90, 10000, 0.1, 0.0, "not_observable", "terrain"),
             ]}
    path = root / SERIES / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    relative = f"{SERIES}/pairs/20260629_20260711/cells.geojson"
    (root / relative).parent.mkdir(parents=True, exist_ok=True)
    (root / relative).write_text(json.dumps(cells), encoding="utf-8")
    manifest["pairs"][0]["cells"] = relative
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return root


def _area(client, bbox, pair="20260629_20260711"):
    body = client.get(SEARCH, headers=STUDENT, params={"bbox": bbox, "limit": 50}).json()
    return next(row["area"] for row in body["results"] if row["pair_id"] == pair)


def test_area_weights_each_cell_by_its_observed_pixels(cells_root):
    client = _area_client(cells_root, FakeFootprints())
    area = _area(client, "-105.805,26.902,-105.775,26.905")
    # 10000 · 1 · 0,20 + 10000 · 0,5 · 0,10 = 2500 cambios sobre 15000 observados.
    assert area["status"] == "computed" and area["cells"] == 2 and area["pixels"] == 20000
    assert area["observed_fraction"] == 0.75 and area["changed_fraction"] == pytest.approx(2500 / 15000, abs=1e-6)
    assert area["state"] == "change_probable" and area["cause"] is None
    assert area["cells_bbox"] == [-105.80, 26.90, -105.78, 26.91]
    assert area["decision_rule"]["min_changed_fraction"] == 0.05 and area["decision_rule"]["calibrated"] is False


def test_area_without_enough_observed_is_not_observable_with_cause(cells_root):
    area = _area(_area_client(cells_root, FakeFootprints()), "-105.598,26.902,-105.595,26.905")
    assert area["state"] == "not_observable" and area["cause"] == "terrain" and area["changed_fraction"] == 0


def test_area_with_no_change_and_rows_without_cells(cells_root):
    client = _area_client(cells_root, FakeFootprints())
    assert _area(client, "-105.698,26.902,-105.695,26.905")["state"] == "no_detectable_change"
    assert _area(client, "-105.95,26.70,-105.90,26.75")["status"] == "no_cells_in_bbox"
    other = _area(client, "-105.698,26.902,-105.695,26.905", pair="20260711_20260723")
    assert other["status"] == "no_cells" and other["state"] is None


def test_area_does_not_change_the_verdict_or_the_filters(cells_root):
    client = _area_client(cells_root, FakeFootprints())
    body = client.get(SEARCH, headers=STUDENT, params={"bbox": "-105.598,26.902,-105.595,26.905",
                                                       "state": "change_probable"}).json()
    row = next(row for row in body["results"] if row["pair_id"] == "20260629_20260711")
    assert row["state"] == "change_probable" and row["area"]["state"] == "not_observable"
    assert all(row["area"] is None for row in client.get(SEARCH, headers=STUDENT).json()["results"])


# --- Ruido de la diferencia (T-BAL-14, RF-BUS-09) ---------------------------------------------------------------


@pytest.fixture()
def noisy(root):
    """Ruido en tres de los cuatro pares; el cuarto, como un manifiesto anterior a T-ECO-09."""
    path = root / SERIES / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    values = {"20260629_20260711": (0.8, 0.6), "20260711_20260723": (1.3, 0.9), "20260629_20260723": (1.1, None)}
    for pair in manifest["pairs"]:
        if pair["id"] in values:
            hh, hv = values[pair["id"]]
            pair["stats"] = {**pair["stats"], "noise_hh_db": hh, "noise_hv_db": hv}
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return TestClient(create_app(root, clock=_clock, build_index=False))


def test_verdict_exposes_noise_with_its_caveat(noisy):
    verdict = noisy.get("/aois/parral/series/T048A-F015/verdicts/20260629_20260711").json()
    noise = verdict["evidence"]["noise"]
    assert noise["hh_db"] == 0.8 and noise["hv_db"] == 0.6 and noise["basis"] == "pair_stats"
    assert noise["calibrated"] is False and "instrumento" in noise["caveat"]


def test_manifest_without_noise_gives_null_noise(noisy):
    verdict = noisy.get("/aois/parral/series/T048A-F015/verdicts/20260723_20260816").json()
    assert verdict["evidence"]["noise"] is None


def test_rows_copy_the_noise_of_the_verdict(noisy):
    full = {v["id"]: v for v in noisy.get("/aois/parral/series/T048A-F015/verdicts").json()}
    for row in noisy.get(SEARCH, headers=RESEARCHER).json()["results"]:
        noise = full[row["pair_id"]]["evidence"]["noise"]
        assert row["noise_hh_db"] == (noise["hh_db"] if noise else None)
        assert row["noise_hv_db"] == (noise["hv_db"] if noise else None)


def test_noise_filter_keeps_the_range_and_counts_rows_without_noise(noisy):
    body = noisy.get(SEARCH, headers=RESEARCHER, params={"noise_hh_max": 1.2}).json()
    assert sorted(_ids(body)) == ["20260629_20260711", "20260629_20260723"]
    assert body["query"]["not_evaluated"]["noise_hh"] == {"count": 1, "reasons": {"no_noise_stats": 1}}
    assert body["query"]["filters"] == {"noise_hh_max": 1.2}
    body = noisy.get(SEARCH, headers=RESEARCHER, params={"noise_hv_min": 0.7}).json()
    assert _ids(body) == ["20260711_20260723"]
    assert body["query"]["not_evaluated"]["noise_hv"]["count"] == 2


def test_change_probable_with_low_noise(noisy):
    """Historia de usuario: pares change_probable con ruido en HH menor de 1 dB."""
    body = noisy.get(SEARCH, headers=RESEARCHER, params={"state": "change_probable", "noise_hh_max": 1.0}).json()
    assert _ids(body) == ["20260629_20260711"]


@pytest.mark.parametrize("direction", ["asc", "desc"])
def test_sort_by_noise_leaves_unknown_last(noisy, direction):
    body = noisy.get(SEARCH, headers=RESEARCHER, params={"sort": "noise_hh", "order": direction}).json()
    known = ["20260629_20260711", "20260629_20260723", "20260711_20260723"]
    assert _ids(body) == (known if direction == "asc" else known[::-1]) + ["20260723_20260816"]


@pytest.mark.parametrize("params", [{"noise_hh_max": 1}, {"noise_hv_min": 0.5}, {"sort": "noise_hv"}])
def test_noise_filters_and_sort_are_for_researchers(noisy, params):
    response = noisy.get(SEARCH, headers=STUDENT, params=params)
    assert response.status_code == 403 and response.json()["required_role"] == "researcher"
