"""Proveedores de acontecimientos sin red: httpx.MockTransport con respuestas sintéticas con la forma de las reales
(comprobadas en vivo el 2026-11-15). Todo lo que devuelven es de prueba."""
import json

import httpx
import pytest

from research import events, sources

PARRAL = [-105.95, 26.70, -105.40, 27.15]


def client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_usgs_normalizes_epicenter():
    def h(req):
        assert req.url.params["minmagnitude"] == "2.5" and req.url.params["minlongitude"] == "-105.95"
        return httpx.Response(200, json={"features": [{"id": "us7000test", "properties": {"mag": 4.0, "magType": "mb", "place": "prueba", "time": 1681560000000, "url": "https://earthquake.usgs.gov/x", "title": "M 4.0 - prueba"}, "geometry": {"coordinates": [-105.6, 26.9, 10.0]}}]})

    ev = sources.Usgs(client(h)).events(PARRAL, "2023-01-01", "2023-12-31")
    assert ev[0]["id"] == "usgs-us7000test" and ev[0]["date"] == "2023-04-15" and ev[0]["bbox"] == [-105.6, 26.9, -105.6, 26.9]
    assert ev[0]["sources"][0]["url"].startswith("https://earthquake.usgs.gov")


def test_gdacs_filters_by_country_and_area_and_stops_on_204():
    pedidas = []

    def h(req):
        pedidas.append(dict(req.url.params))
        if req.url.params["pagenumber"] != "1":
            return httpx.Response(204)
        feats = [
            {"bbox": [-105.7, 26.9, -105.7, 26.9], "geometry": {"type": "Point", "coordinates": [-105.7, 26.9]},
             "properties": {"eventtype": "FL", "eventid": "1", "name": "Flood in Mexico", "fromdate": "2025-05-20T00:00:00", "todate": "2025-05-25T00:00:00",
                            "alertlevel": "Green", "country": "Mexico", "source": "GLOFAS", "Class": "Point_Centroid",
                            "url": {"report": "https://www.gdacs.org/report.aspx?eventid=1"}, "severitydata": {"severitytext": "Magnitude 0"}}},
            {"bbox": [-90, 15, -90, 15], "geometry": {"type": "Point", "coordinates": [-90, 15]},
             "properties": {"eventtype": "EQ", "eventid": "2", "name": "Lejos", "fromdate": "2025-01-01T00:00:00", "alertlevel": "Green", "url": {}}},
        ]
        return httpx.Response(200, json={"features": feats})

    g = sources.Gdacs(client(h), country_resolver=lambda b: "Mexico")
    ev = g.events(PARRAL, "2016-01-01", "2026-11-15")
    assert [e["id"] for e in ev] == ["gdacs-FL-1"] and ev[0]["type"] == "flood" and ev[0]["end_date"] == "2025-05-25"
    assert all(p["country"] == "Mexico" for p in pedidas) and not g.truncated


def test_gdacs_without_country_is_capped_and_says_so():
    def h(req):
        f = {"bbox": [0, 0, 0, 0], "geometry": {"type": "Point", "coordinates": [0, 0]},
             "properties": {"eventtype": "EQ", "eventid": req.url.params["pagenumber"], "fromdate": "2026-01-01T00:00:00", "url": {}}}
        return httpx.Response(200, json={"features": [f] * 100})

    g = sources.Gdacs(client(h), country_resolver=lambda b: None)
    g.events(PARRAL, "2016-01-01", "2026-11-15")
    assert g.truncated


def test_cems_uses_aoi_extent(tmp_path):
    def h(req):
        if "public-activations-info" in str(req.url):
            return httpx.Response(200, json={"next": None, "results": [
                {"code": "EMSRTEST", "name": "Flood test", "category": "Flood", "eventTime": "2026-07-01T10:00:00",
                 "centroid": "POINT (-105.7 26.9)", "closed": True, "lastUpdate": "2026-07-09T00:00:00", "n_products": 3},
                {"code": "EMSRFAR", "name": "Lejos", "category": "Wildfire", "eventTime": "2026-07-01T10:00:00", "centroid": "POINT (10 45)"}]})
        return httpx.Response(200, json={"results": [{"aois": [{"name": "Parral", "extent": "POLYGON ((-105.8 26.8, -105.6 26.8, -105.6 27.0, -105.8 26.8))"}]}]})

    ev = sources.CopernicusEms(client(h), sources.DiskCache(tmp_path)).events(PARRAL, "2026-01-01", "2026-11-15")
    assert len(ev) == 1 and ev[0]["bbox"] == [-105.8, 26.8, -105.6, 27.0] and ev[0]["geometry_precision"] == "cems_aoi_extent"
    assert ev[0]["sources"][0]["url"] == "https://rapidmapping.emergency.copernicus.eu/EMSRTEST/"


def test_landslide_catalog_parses_us_dates(tmp_path):
    csv_text = ("event_id,event_date,event_title,location_accuracy,landslide_category,landslide_trigger,landslide_size,fatality_count,"
                "location_description,source_name,source_link,longitude,latitude\n"
                "77,07/02/2014 12:00:00 AM,Prueba,5km,landslide,downpour,small,0,Parral,Prensa,https://example.invalid/n,-105.66,26.93\n"
                "78,07/02/2014 12:00:00 AM,Lejos,5km,landslide,rain,small,0,X,,,10,10\n")
    p = sources.NasaLandslides(client(lambda r: httpx.Response(200, text=csv_text)), sources.DiskCache(tmp_path))
    ev = p.events(PARRAL, "2014-01-01", "2014-12-31")
    assert [e["id"] for e in ev] == ["glc-77"] and ev[0]["date"] == "2014-07-02" and "downpour" in ev[0]["description"]
    assert (tmp_path / "nasa_glc.csv").exists()  # se guarda en disco para no volver a bajar 8 MB


def test_ibtracs_track_near_area(tmp_path):
    csv_text = ("SID,NAME,ISO_TIME,LAT,LON,WMO_WIND,USA_WIND\n ,, , , , ,kts\n"
                "2023X,NORMA,2023-10-22 00:00:00,24.0,-107.0, ,80\n"
                "2023X,NORMA,2023-10-23 00:00:00,25.5,-106.5, ,45\n"
                "2023Y,LEJOS,2023-10-23 00:00:00,10.0,120.0, ,30\n")
    ev = sources.Ibtracs(client(lambda r: httpx.Response(200, text=csv_text)), sources.DiskCache(tmp_path)).events(PARRAL, "2023-01-01", "2023-12-31")
    assert [e["id"] for e in ev] == ["ibtracs-2023X"] and ev[0]["date"] == "2023-10-23" and "80 kt" in ev[0]["description"]


def test_credentialed_providers_are_reported_not_called(monkeypatch):
    monkeypatch.delenv("RELIEFWEB_APPNAME", raising=False)
    monkeypatch.delenv("FIRMS_MAP_KEY", raising=False)

    def boom(req):
        raise AssertionError("no debe llamar sin credencial")

    out = events.gather({"id": "p", "bbox": PARRAL}, "2026-01-01", "2026-11-15", [], None,
                        [sources.ReliefWeb(client(boom)), sources.Firms(client(boom))])
    st = {s["id"]: s for s in out["sources"]}
    assert st["reliefweb"]["status"] == "needs_credentials" and st["reliefweb"]["credential_env"] == "RELIEFWEB_APPNAME"
    assert st["firms"]["status"] == "needs_credentials"


def test_firms_groups_by_day_when_key_present(monkeypatch):
    monkeypatch.setenv("FIRMS_MAP_KEY", "clave-de-prueba")

    def h(req):
        assert "/clave-de-prueba/" in str(req.url)
        return httpx.Response(200, text="latitude,longitude,acq_date\n26.9,-105.7,2026-11-01\n26.91,-105.71,2026-11-01\n")

    ev = sources.Firms(client(h)).events(PARRAL, "2026-11-01", "2026-11-05")
    assert len(ev) == 1 and ev[0]["title"].startswith("2 detecciones")


def test_failing_provider_is_isolated():
    class Roto(sources.Provider):
        id, name = "roto", "Roto"

        def events(self, *a):
            raise TimeoutError("sin respuesta")

    out = events.gather({"id": "p", "bbox": PARRAL}, "2026-01-01", "2026-11-15", [], None, [Roto(client(lambda r: None)), sources.Usgs(client(lambda r: httpx.Response(200, json={"features": []})))])
    assert {s["id"]: s["status"] for s in out["sources"]} == {"registry": "ok", "roto": "error", "usgs": "ok"}


def test_inegi_layers_only_in_mexico():
    assert {x["code"] for x in sources.inegi_layers(PARRAL)} >= {"c402", "c310", "c783", "c416", "c102"}
    assert sources.inegi_layers([-38.6, 66.25, -38.0, 66.5]) == []
    assert "BBOX=-105.95,26.7,-105.4,27.15" in sources.inegi_layers(PARRAL)[0]["getmap"]
