"""Pasadas excluidas por catalog (excluded[] de la línea de tiempo, PR 22 de Antena).

En Parral, catalog excluye T171 del 2026-08-13 por defecto del producto: ya no está en passes ni en
intervals, y el par consecutivo pasa a ser 07-20 → 08-25. verdicts lo dice en vez de ocultarlo.
"""
import json
from datetime import date

import httpx
from fastapi.testclient import TestClient

from test_verdicts import REAL_PASSES, VERDICT, FakeTimeline, _as_real, _clock, manifest_root  # noqa: F401
from verdicts.catalog import ExcludedPass, HttpTimeline
from verdicts.main import create_app

EVIDENCE = "La vista previa LATLON de ASF ya muestra la anomalía."


def _excluded(granule="G20260705", day=date(2026, 7, 5), series="T048A-F015"):
    return ExcludedPass(id=granule, series=series, date=day, reason="product_defect", evidence=EVIDENCE)


def _client(manifest_root, *excluded, fail=False):
    timeline = FakeTimeline(REAL_PASSES, fail=fail, excluded=excluded)
    return TestClient(create_app(manifest_root, timeline=timeline, clock=_clock))


def test_excluded_pass_between_the_dates_is_explained(manifest_root):
    _as_real(manifest_root)
    body = _client(manifest_root, _excluded()).get(VERDICT).json()
    assert body["receipt"]["excluded_passes"] == [{
        "granule": "G20260705", "series": "T048A-F015", "date": "2026-07-05",
        "reason": "product_defect", "evidence": EVIDENCE,
    }]
    assert ("Además falta la pasada del 2026-07-05 de esta serie: el catálogo la excluye "
            "(defecto del producto publicado).") in body["summary"]["missing"]
    english = _client(manifest_root, _excluded()).get(VERDICT, params={"lang": "en"}).json()
    assert "the catalog excludes it (defect in the published product)" in english["summary"]["missing"]


def test_catalog_series_name_with_mode_polarization_and_crid_matches(manifest_root):
    # Así la nombra catalog de verdad (comprobado con la pila el 2026-11-12); el manifiesto dice T048A-F015.
    _as_real(manifest_root)
    full = _excluded(series="T048A-F015-4005-DHDH-P05023")
    body = _client(manifest_root, full).get(VERDICT).json()
    assert [item["series"] for item in body["receipt"]["excluded_passes"]] == ["T048A-F015-4005-DHDH-P05023"]
    other_crid = _excluded(series="T048A-F015-4005-DHDH-P05099")
    assert _client(manifest_root, other_crid).get(VERDICT).json()["receipt"]["excluded_passes"] == []


def test_pair_that_uses_an_excluded_pass_says_not_to_interpret_it(manifest_root):
    _as_real(manifest_root)
    body = _client(manifest_root, _excluded("G20260711", date(2026, 7, 11))).get(VERDICT).json()
    assert "este par la usa: su resultado no debe interpretarse" in body["summary"]["missing"]


def test_excluded_pass_on_a_pair_date_is_recognised_by_date_too(manifest_root):
    # El gránulo del manifiesto puede no llamarse igual que en CMR; la fecha de la serie basta.
    _as_real(manifest_root)
    body = _client(manifest_root, _excluded("OTRO_ID", date(2026, 7, 11))).get(VERDICT).json()
    assert "este par la usa" in body["summary"]["missing"]
    query = {"date": "2026-07-01", "persistence_hours": 264}
    event = _client(manifest_root, _excluded("OTRO_ID", date(2026, 7, 11))).get("/aois/parral/events", params=query).json()
    assert event["state"] == "not_observable" and [e["date"] for e in event["excluded_passes"]] == ["2026-07-11"]


def test_other_series_and_dates_outside_the_pair_are_ignored(manifest_root):
    _as_real(manifest_root)
    others = (_excluded(series="T171D-F075"), _excluded("G20260813", date(2026, 8, 13)))
    body = _client(manifest_root, *others).get(VERDICT).json()
    assert body["receipt"]["excluded_passes"] == []
    assert "excluye" not in body["summary"]["missing"]


def test_synthetic_and_catalog_down_list_nothing(manifest_root):
    body = _client(manifest_root, _excluded()).get(VERDICT).json()
    assert body["receipt"]["data_kind"] == "synthetic" and body["receipt"]["excluded_passes"] == []
    _as_real(manifest_root)
    response = _client(manifest_root, _excluded(), fail=True).get(VERDICT)
    assert response.status_code == 200 and response.json()["receipt"]["excluded_passes"] == []


def test_excluded_pass_does_not_count_for_an_event(manifest_root):
    # Con un evento el 1 de julio y 264 h, la pasada del 07-11 a las 00:41 cae dentro seguro; si catalog la excluye, ya no.
    _as_real(manifest_root)
    query = {"date": "2026-07-01", "persistence_hours": 264}
    assert _client(manifest_root).get("/aois/parral/events", params=query).json()["state"] == "observable"
    body = _client(manifest_root, _excluded("G20260711", date(2026, 7, 11))).get(
        "/aois/parral/events", params=query).json()
    assert body["state"] == "not_observable" and body["next_pass"] is None
    assert [item["date"] for item in body["excluded_passes"]] == ["2026-07-11"]
    assert "el catálogo la excluye" in body["summary"]["missing"]


def test_event_cites_excluded_pass_missing_from_the_manifest(manifest_root):
    # Revisión de Antena (PR 40): el manifiesto real de Eco ya no trae el 08-13, pero el evento debe citarlo.
    _as_real(manifest_root)
    gap = _excluded("G20260705", date(2026, 7, 5))  # entre las pasadas del fixture (06-29 y 07-11), sin fecha propia
    body = _client(manifest_root, gap).get("/aois/parral/events", params={"date": "2026-07-04", "persistence_hours": 48}).json()
    assert body["state"] == "not_observable"
    assert body["previous_pass"] == "2026-06-29" and body["next_pass"] == "2026-07-11"
    assert [item["date"] for item in body["excluded_passes"]] == ["2026-07-05"]
    assert "Además falta la pasada del 2026-07-05 de esta serie" in body["summary"]["missing"]


def test_event_ignores_excluded_passes_outside_its_passes(manifest_root):
    _as_real(manifest_root)
    far = _excluded("G20260813", date(2026, 8, 13))
    body = _client(manifest_root, far).get("/aois/parral/events", params={"date": "2026-07-04", "persistence_hours": 48}).json()
    assert body["excluded_passes"] == [] and "excluye" not in body["summary"]["missing"]


def test_catalog_times_with_z_parse_on_python_3_10():
    from verdicts.catalog import utc_time

    assert utc_time("2026-08-13T01:44:33Z").isoformat() == "2026-08-13T01:44:33+00:00"


def test_http_timeline_parses_excluded_with_one_request():
    requests = []
    body = {
        "passes": [{"granule_id": "G20260825", "acquired_at": "2026-08-25T01:44:33Z",
                    "published_at": None, "latency_hours": None}],
        "excluded": [{"id": "NISAR_L2_PR_GCOV_027_171_D_075_4005_DHDH_A_20260813T014433_20260813T014508_P05023_N_F_J_001",
                      "series": "T171D-F075", "date": "2026-08-13", "acquired_at": "2026-08-13T01:44:33Z",
                      "reason": "product_defect", "evidence": EVIDENCE, "checked_on": "2026-11-12"}],
    }

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json=body)

    source = HttpTimeline("http://catalog:8000", httpx.Client(transport=httpx.MockTransport(handler)), lambda: 0.0)
    assert list(source.passes("parral")) == ["G20260825"]
    [item] = source.excluded("parral")
    assert item.series == "T171D-F075" and item.date == date(2026, 8, 13) and item.reason == "product_defect"
    assert len(requests) == 1


def test_http_timeline_without_excluded_field_still_works():
    # Un catalog anterior al PR 22 no trae excluded[].
    body = {"passes": []}
    source = HttpTimeline("http://c", httpx.Client(transport=httpx.MockTransport(
        lambda request: httpx.Response(200, content=json.dumps(body)))), lambda: 0.0)
    assert source.excluded("parral") == []
