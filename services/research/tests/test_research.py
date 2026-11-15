import datetime as dt
import json
import time
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from research import discovery, events, nlq, places, story, temporal
from research.main import create_app
from research.pipeline import Deps, Runner
from research.products import BY_ID, PRODUCTS
from research.store import Store

from conftest import REGISTRY, FakeCmr, FakeEonet, FakeVerdicts

TODAY = dt.date(2026, 11, 15)


# --- lenguaje natural ---------------------------------------------------------------------------------------------

def test_parse_mining_parral_decade():
    p = nlq.parse_question("Investiga cómo ha cambiado el terreno alrededor de las zonas mineras de Hidalgo del Parral entre 2016 y 2026.", TODAY)
    assert [a["id"] for a in p["areas"]] == ["la_prieta"]
    assert p["period"] == {"start": "2016-01-01", "end": "2026-11-15"}
    assert "mining" in p["phenomena"] and "mining_terrain" in p["profiles"]
    assert p["notes"], "debe avisar de que NISAR no cubre 2016"
    assert "nisar_gcov" in p["products"] and "opera_disp_s1" in p["products"]


def test_parse_greenland_comparison_relative_years():
    p = nlq.parse_question("Compara el retroceso y movimiento de Jakobshavn y Helheim durante los últimos cinco años.", TODAY)
    assert [a["id"] for a in p["areas"]] == ["sermeq_kujalleq", "helheim"]
    assert p["comparative"] is True
    assert p["phenomena"] == ["glacier"]
    assert p["period"]["start"] == (TODAY - dt.timedelta(days=5 * 365)).isoformat()


def test_parse_unknown_place_is_unresolved_not_guessed():
    p = nlq.parse_question("¿Qué pasó en un lugar inventado?", TODAY)
    assert p["areas"] == [] and "area" in p["unresolved"] and "period" in p["unresolved"]


def test_parse_english_flood():
    p = nlq.parse_question("How did flooded areas evolve in Parral in 2026?", TODAY)
    assert p["areas"][0]["id"] == "parral" and "flood" in p["phenomena"]
    assert p["period"] == {"start": "2026-01-01", "end": "2026-11-15"}


def test_gazetteer_boxes_valid():
    for pl in places.GAZETTEER:
        w, s, e, n = pl.bbox
        assert -180 <= w < e <= 180 and -90 <= s < n <= 90, pl.id
        assert pl.source


# --- descubrimiento -----------------------------------------------------------------------------------------------

def test_normalize_reads_orbit_and_pols_from_names():
    page = FakeCmr().granules("NISAR_L2_GCOV_PROVISIONAL_V1", [0, 0, 1, 1], "2026-01-01", "2026-12-31", 10)
    a = discovery.normalize(BY_ID["nisar_gcov"], page.entries[0])
    assert a["orbit_direction"] == "ascending" and a["track"] == 48 and a["frame"] == 15
    assert a["polarizations"] == ["HH", "HV"] and a["polarization_source"] == "granule_name"
    s1 = discovery.normalize(BY_ID["s1a_grd"], FakeCmr().granules("SENTINEL-1A_DP_GRD_HIGH", [], None, None, 1).entries[0])
    assert s1["polarizations"] == ["VV", "VH"] and s1["orbit_direction"] is None  # el nombre no la dice: no se inventa


def test_discover_isolates_provider_failure():
    cmr = FakeCmr(fail_for={"OPERA_L2_RTC-S1_V1"})
    area = {"id": "x", "bbox": [-106, 26, -105, 27]}
    d = discovery.discover(cmr, [BY_ID["nisar_gcov"], BY_ID["opera_rtc_s1"], BY_ID["nasadem"]], area, "2026-01-01", "2026-11-15")
    by = {p["product"]: p for p in d["products"]}
    assert by["nisar_gcov"]["status"] == "found" and by["nisar_gcov"]["hits"] == 3
    assert by["opera_rtc_s1"]["status"] == "unavailable" and d["errors"][0]["product"] == "opera_rtc_s1"
    assert by["nasadem"]["status"] == "none_found"
    assert ("NASADEM_HGT", None, None) in cmr.calls  # producto estático: sin filtro temporal


def test_compatibility_warns_on_mixed_orbits_and_bands():
    cmr = FakeCmr()
    area = {"id": "x", "bbox": [-106, 26, -105, 27]}
    d = discovery.discover(cmr, [BY_ID["nisar_gcov"], BY_ID["s1a_grd"]], area, "2026-01-01", "2026-11-15")
    codes = {c["code"] for c in discovery.compatibility(d["acquisitions"])}
    assert {"mixed_bands", "mixed_orbit_directions", "multiple_tracks"} <= codes


def test_every_product_short_name_unique():
    assert len({p.short_name for p in PRODUCTS}) == len(PRODUCTS)


# --- temporal ---------------------------------------------------------------------------------------------------

def _pts(vals, start=dt.date(2026, 1, 1), step=12):
    return [(start + dt.timedelta(days=i * step), v) for i, v in enumerate(vals)]


def test_theil_sen_linear():
    assert temporal.theil_sen(_pts([0, 1, 2, 3, 4], step=30)) == pytest.approx(1.0)


def test_anomaly_detected_only_for_outlier():
    a = temporal.robust_anomalies(_pts([0.02, 0.021, 0.019, 0.02, 0.2, 0.022, 0.018]))
    assert [x["value"] for x in a] == [0.2]


def test_change_point_found_and_not_on_flat():
    cp = temporal.change_point(_pts([0.01, 0.012, 0.011, 0.01, 0.05, 0.052, 0.049, 0.051]))
    assert cp and cp["date"] == (dt.date(2026, 1, 1) + dt.timedelta(days=48)).isoformat()
    assert temporal.change_point(_pts([0.01, 0.011, 0.01, 0.012, 0.01, 0.011])) is None


def test_gap_is_listed_not_stability():
    g = temporal.gaps([dt.date(2026, 7, 23), dt.date(2026, 8, 4), dt.date(2026, 8, 28), dt.date(2026, 9, 9)], [(dt.date(2026, 7, 27), dt.date(2026, 8, 10))])
    assert g[0]["declared_gap"] is True
    assert temporal.analyze_series(_pts([0.02, 0.03]))["label"] == "insufficient_points"


# --- acontecimientos ----------------------------------------------------------------------------------------------

def test_registry_file_is_valid():
    reg = events.load_registry(Path(__file__).resolve().parents[3] / "config" / "events")
    assert reg, "config/events debe tener acontecimientos"
    for e in reg:
        dt.date.fromisoformat(e["date"])
        assert e["sources"] and all(s["url"].startswith("https://") for s in e["sources"])


def test_correlation_never_claims_cause():
    area = {"id": "parral", "bbox": [-105.95, 26.70, -105.40, 27.15]}
    ev = events.gather(area, "2026-06-01", "2026-11-15", REGISTRY, FakeEonet())
    assert {e["id"] for e in ev["events"]} == {"synth-storm", "EONET_SYNTH_1"}
    from research.analysis import analyze_area

    an = analyze_area(FakeVerdicts(), area, "2026-06-01", "2026-11-15")
    corr = events.correlate(ev["events"], an["findings"], an["series"])
    assert all(c["causal_relation"] == "not_demonstrated" for c in corr)
    eonet = next(c for c in corr if c["event_id"] == "EONET_SYNTH_1")
    inside = [lk for lk in eonet["links"] if lk["event_inside_interval"]]
    assert inside[0]["pair_id"] == "20260816_20260828" and inside[0]["level"] == "spatial"


# --- análisis ---------------------------------------------------------------------------------------------------

def test_analysis_findings_and_no_high_confidence():
    from research.analysis import analyze_area

    an = analyze_area(FakeVerdicts(), {"id": "parral", "bbox": [-105.75, 26.87, -105.6, 26.98]}, "2026-06-01", "2026-11-15")
    assert [f["pair_id"] for f in an["findings"]] == ["20260816_20260828", "20260828_20260909"]
    assert all(f["confidence"] in ("low", "medium") and f["confidence_calibrated"] is False for f in an["findings"])
    assert an["findings"][0]["data_kind"] == "synthetic"


def test_analysis_outside_processed_area_says_so():
    from research.analysis import analyze_area

    an = analyze_area(FakeVerdicts(), {"id": "g", "bbox": [-50.2, 69.1, -49.6, 69.3]}, "2026-01-01", "2026-11-15")
    assert an["series"] == [] and "Ausencia de análisis no es ausencia de cambio" in an["limitations"][0]


def test_analysis_verdicts_down():
    from research.analysis import analyze_area

    an = analyze_area(FakeVerdicts(fail=True), {"id": "p", "bbox": [-105.9, 26.8, -105.5, 27]}, "2026-01-01", "2026-11-15")
    assert an["errors"] and an["findings"] == []


# --- API e historia -----------------------------------------------------------------------------------------------

@pytest.fixture
def client(deps):
    app = create_app(Store(":memory:"), deps, places.Geocoder(enabled=False))
    return TestClient(app)


def _wait(client, rid):
    for _ in range(200):
        s = client.get(f"/research/{rid}/status").json()
        if s["job"] and s["job"]["state"] in ("done", "failed", "cancelled"):
            return s
        time.sleep(0.02)
    raise AssertionError("el trabajo no terminó")


def test_end_to_end_story_traceable(client, deps):
    r = client.post("/research", json={"question": "Compara Parral y Jakobshavn durante 2026", "run": True})
    assert r.status_code == 201
    rid = r.json()["id"]
    s = _wait(client, rid)
    assert s["job"]["state"] == "done", s
    sid = s["story_ids"][0]
    st = client.get(f"/stories/{sid}").json()
    assert [c["key"] for c in st["chapters"]][:3] == ["title", "question", "geography"] and len(st["chapters"]) == 17
    assert st["traceability"]["ok"], st["traceability"]
    assert st["data_kind"] == "synthetic"
    md = client.get(f"/stories/{sid}/export?format=md").text
    assert "Datos sintéticos" in md and "Registro de evidencia" in md
    ex = client.get(f"/stories/{sid}/export?format=json").json()
    assert ex["research"]["id"] == rid
    # todo número en hallazgos sale de la evidencia del par
    ev = {e["id"]: e for e in st["evidence"]}
    finding_claims = next(c for c in st["chapters"] if c["key"] == "findings")["claims"]
    assert any("9,56 %" in c["text"] for c in finding_claims)
    assert ev["calc:parral:SYNTH-T048:20260828_20260909"]["changed_fraction"] == 0.0956
    # el evento verificado pidió la observabilidad a verdicts con su tipo y hora
    assert deps.verdicts.event_calls[0][2]["event_type"] == "urban_storm"
    comp = client.get(f"/research/{rid}/comparison").json()
    assert {row["area"] for row in comp["areas"]} == {"parral", "sermeq_kujalleq"}
    assert "no se comparan en magnitud" in comp["warning"]
    insar = client.get(f"/research/{rid}/insar").json()
    assert all(i["displacement_available"] is False for i in insar)


def test_traceability_detects_unsupported_numbers():
    s = {"chapters": [{"key": "findings", "claims": [{"text": "Cambió un 12 %", "evidence": []}, {"text": "ok", "evidence": ["nope"]}]}], "evidence": []}
    t = story.check_traceability(s)
    assert not t["ok"] and t["unsupported_numeric_claims"] and t["dangling_evidence"]


def test_validation_errors(client):
    assert client.post("/research", json={}).status_code == 422
    assert client.post("/research", json={"areas": [{"bbox": [10, 0, 5, 1]}]}).status_code == 422
    assert client.post("/research", json={"areas": [{"id": "parral"}], "period": {"start": "2026-10-01", "end": "2026-01-01"}}).status_code == 422
    assert client.post("/research", json={"areas": [{"id": "parral"}], "period": {"start": "2026-10-01", "end": "2099-01-01"}}).status_code == 422
    r = client.post("/research", json={"question": "algo sin lugar"})
    assert r.status_code == 422


def test_manual_selection_and_section_409(client):
    r = client.post("/research", json={"areas": [{"id": "la_boquilla"}, {"name": "Mía", "bbox": [-105, 26, -104, 27]}],
                                        "period": {"start": "2026-06-01", "end": "2026-10-31"}, "phenomena": ["flood"]})
    assert r.status_code == 201
    d = r.json()
    assert [a["id"] for a in d["plan"]["areas"]] == ["la_boquilla", "custom_2"] and d["plan"]["comparative"]
    assert "gpm_imerg_late" in d["plan"]["products"]
    assert client.get(f"/research/{d['id']}/anomalies").status_code == 409


def test_places_and_profiles(client):
    r = client.get("/places", params={"q": "parral"}).json()
    assert r["geocoder"] == "disabled" and any(p["id"] == "parral" for p in r["results"])
    assert len(client.get("/profiles").json()) == 4
    r = client.post("/research", json={"profile": "glacier_climate"}).json()
    assert r["plan"]["areas"][0]["id"] == "sermeq_kujalleq" and "icesat2_atl06" in r["plan"]["products"]


def test_cancel(deps):
    import threading

    gate = threading.Event()

    class SlowCmr(FakeCmr):
        def granules(self, *a, **k):
            gate.wait(2)
            return super().granules(*a, **k)

    store = Store(":memory:")
    runner = Runner(store, Deps(cmr=SlowCmr(), verdicts=FakeVerdicts(), eonet=None), workers=1)
    doc = store.create_research({"plan": nlq.parse_question("Parral y Helheim en 2026", TODAY) | {"lang": "es"}})
    runner.submit(doc["id"], ["discover", "analyze", "story"])
    time.sleep(0.05)
    assert runner.cancel(doc["id"])
    gate.set()
    for _ in range(200):
        if store.get_research(doc["id"])["job"]["state"] in ("cancelled", "done"):
            break
        time.sleep(0.02)
    assert store.get_research(doc["id"])["job"]["state"] == "cancelled"


def test_contract_matches(tmp_path):
    from research.export_openapi import main

    out = tmp_path / "o.json"
    main(str(out))
    published = Path(__file__).resolve().parents[3] / "contracts" / "research.openapi.json"
    assert json.loads(out.read_text(encoding="utf-8")) == json.loads(published.read_text(encoding="utf-8")), \
        "Regenera: python -m research.export_openapi contracts/research.openapi.json"


# --- EODMS (RADARSAT-1 y RCM, socios del reto) ------------------------------------------------------------------

class FakeEodms:
    """Features con la forma del STAC de EODMS (comprobada el 2026-11-15); valores de prueba."""

    def search(self, collection, bbox, start, end, limit):
        if collection == "RCMImageProducts":
            return [], False
        f = {"id": "SYNTH-r1", "bbox": [-107.16, 26.13, -105.52, 27.67],
             "properties": {"order_key": "X0597340", "datetime": "2002-01-05T13:02:58.868", "sar:polarizations": ["HH"],
                            "sat:orbit_state": "descending", "sar:frequency_band": "C", "product_type": "SGF", "resolution": 12.5, "megabytes": 249},
             "assets": {"cog": {"href": "https://radarsat-r1-l1-cog.s3.ca-central-1.amazonaws.com/2002/1/x.tif"}, "thumbnail": {"href": "https://example.invalid/t"}}}
        return [f], False


def test_eodms_products_are_discovered_and_normalized():
    d = discovery.discover(FakeCmr(), [BY_ID["radarsat1"], BY_ID["rcm"], BY_ID["nisar_gcov"]], {"id": "p", "bbox": [-106, 26, -105, 27]},
                           "1995-01-01", "2026-11-15", stac=FakeEodms())
    by = {p["product"]: p for p in d["products"]}
    assert by["radarsat1"]["status"] == "found" and by["radarsat1"]["first_date"] == "2002-01-05"
    assert by["radarsat1"]["access"] == "public" and by["rcm"]["status"] == "none_found" and by["rcm"]["access"] == "eodms_login"
    a = next(x for x in d["acquisitions"] if x["product"] == "radarsat1")
    assert a["polarizations"] == ["HH"] and a["polarization_source"] == "stac_metadata" and a["orbit_direction"] == "descending"
    assert a["data_url"].startswith("https://radarsat-r1-l1-cog.s3") and a["level"].endswith("SGF")


def test_eodms_without_source_is_unavailable_not_invented():
    d = discovery.discover(FakeCmr(), [BY_ID["radarsat1"]], {"id": "p", "bbox": [-106, 26, -105, 27]}, "1995-01-01", "2026-11-15")
    assert d["products"][0]["status"] == "unavailable" and d["acquisitions"] == []


def test_reverse_place_names_a_clicked_point(client):
    """Nombre del lugar de un punto: respuesta de Nominatim de prueba (sin red), caché y API sin geocodificador."""
    calls = []

    def handler(req):
        calls.append(dict(req.url.params))
        return httpx.Response(200, json={"display_name": "Tasiilaq, Sermersooq, Kalaallit Nunaat",
                                         "address": {"town": "Tasiilaq", "state": "Sermersooq", "country": "Kalaallit Nunaat"}})

    geo = places.Geocoder(enabled=True, client=httpx.Client(transport=httpx.MockTransport(handler)))
    p = geo.reverse(65.6145, -37.6368, "es")
    assert p["name"] == "Tasiilaq, Sermersooq, Kalaallit Nunaat" and p["source"].startswith("OpenStreetMap")
    assert calls[0]["accept-language"] == "es" and calls[0]["zoom"] == "12"
    # Un punto a menos de ~100 m sale de la caché, sin otra petición.
    assert geo.reverse(65.61451, -37.63681, "es") == p and len(calls) == 1
    # Sobre el mar Nominatim responde con error: no hay nombre.
    mar = places.Geocoder(enabled=True, client=httpx.Client(transport=httpx.MockTransport(
        lambda req: httpx.Response(200, json={"error": "Unable to geocode"}))))
    assert mar.reverse(0.0, -30.0) is None
    # La API sin geocodificador responde sin nombre, y valida el rango.
    r = client.get("/places/reverse", params={"lat": 66.35, "lon": -38.17}).json()
    assert r == {"lat": 66.35, "lon": -38.17, "place": None, "geocoder": "disabled"}
    assert client.get("/places/reverse", params={"lat": 95, "lon": 0}).status_code == 422
