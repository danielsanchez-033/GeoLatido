"""Buscador mundial (GET /search/world): CMR y vistas previas de ASF, sin cuenta."""
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from catalog.main import create_app
from catalog.world import WorldPage, parse_entry

TITLE_A = "NISAR_L2_PR_GCOV_023_048_A_015_4005_DHDH_A_20260617T122434_20260617T122509_P05023_N_F_J_001"
TITLE_D = "NISAR_L2_PR_GCOV_024_171_D_075_4005_DHDH_A_20260626T014432_20260626T014507_P05023_N_F_J_001"
BROWSE = "https://nisar.asf.earthdatacloud.nasa.gov/BROWSE/X/" + TITLE_A + "/" + TITLE_A


def entry(title: str) -> dict:
    return {
        "title": title,
        "granule_size": "7147.1",
        "polygons": [["26.0 -106.0 26.0 -105.0 27.5 -105.0 27.5 -106.0 26.0 -106.0"]],
        "collection_concept_id": "C123-ASF",
        "links": [
            {"rel": "http://esipfed.org/ns/fedsearch/1.1/data#", "href": f"https://nisar.asf.earthdatacloud.nasa.gov/NISAR/{title}.h5"},
            {"rel": "http://esipfed.org/ns/fedsearch/1.1/browse#", "href": BROWSE + "_LATLON.png"},
            {"rel": "http://esipfed.org/ns/fedsearch/1.1/browse#", "href": "s3://bucket/" + title + "_LATLON.png"},
            {"rel": "http://esipfed.org/ns/fedsearch/1.1/browse#", "href": BROWSE + "_LATLON_thumbnail.png"},
            {"rel": "http://esipfed.org/ns/fedsearch/1.1/browse#", "href": BROWSE + "_NATIVE.png"},
        ],
    }


class FakeWorld:
    def __init__(self):
        self.calls = []

    def search(self, bbox, start, end, direction, limit):
        self.calls.append((bbox, start, end, direction, limit))
        granules = [g for g in (parse_entry(entry(TITLE_A)), parse_entry(entry(TITLE_D))) if not direction or g.direction == direction]
        return WorldPage(total=2, granules=granules)


def client(fake):
    return TestClient(create_app(world_source=fake, clock=lambda: datetime(2026, 11, 14, tzinfo=timezone.utc)))


def test_parse_entry_takes_https_browse_and_thumbnail():
    g = parse_entry(entry(TITLE_A))
    assert g.direction == "A" and g.track == 48 and g.frame == 15
    assert g.browse_url == BROWSE + "_LATLON.png" and g.thumbnail_url == BROWSE + "_LATLON_thumbnail.png"
    assert g.footprint[0] == (-106.0, 26.0)


def test_world_search_is_open_and_returns_links_without_account():
    fake = FakeWorld()
    body = client(fake).get("/search/world", params={"bbox": "-106,26,-105,27.5"}).json()
    assert fake.calls[0][1:] == ("2026-08-16", "2026-11-14", None, 60)
    assert body["total"] == 2 and [g["direction"] for g in body["granules"]] == ["A", "D"]
    g = body["granules"][0]
    assert g["bbox"] == [-106.0, 26.0, -105.0, 27.5] and g["footprint"][0] == g["footprint"][-1]
    assert g["vertex_url"].startswith("https://search.asf.alaska.edu/") and TITLE_A in g["vertex_url"]
    assert g["earthdata_search_url"].startswith("https://search.earthdata.nasa.gov/")
    assert body["from"] == "2026-08-16" and body["data_kind"] == "real"


def test_world_search_filters_direction_and_rejects_bad_boxes():
    c = client(FakeWorld())
    assert [g["direction"] for g in c.get("/search/world", params={"bbox": "-106,26,-105,27.5", "direction": "D"}).json()["granules"]] == ["D"]
    for bad in ("1,2,3", "5,1,4,2", "-200,0,10,10", "a,b,c,d"):
        assert c.get("/search/world", params={"bbox": bad}).status_code == 422
    assert c.get("/search/world", params={"bbox": "1,1,2,2", "from": "2026-10-01", "to": "2026-09-01"}).status_code == 422
