"""Plan de observación (T-ANT-09) con XML que copian la estructura real de NISAR_COP."""
import json
from datetime import datetime, timezone

import pytest

from ingest.fetch import FetchError, is_nasa_url
from ingest.plan import CmrPlanSource, PlanFile, build_plan, classify, latest_versions, parse_plan, write_plan

TOKEN = "token-de-prueba"
UTC = timezone.utc
CATALOG_T171 = "T171D-F075-4005-DHDH-P05023"
AOI = {"id": "parral", "series": [{"id": "T171D-F075", "track": 171, "direction": "D", "frame": 75}]}
NOW = datetime(2026, 11, 12, 20, 0, tzinfo=UTC)
LAST = "2026-10-12T01:44:32Z"


def obs(start: str, end: str, kind: str = "lsar", config: str = "156") -> str:
    return (
        f"<OBS><TYPE>{kind}</TYPE><REF_START_DATETIME>{start}</REF_START_DATETIME>"
        f"<REF_END_DATETIME>{end}</REF_END_DATETIME><LSAR_CONFIG_ID>{config}</LSAR_CONFIG_ID></OBS>"
    )


def xml(*items: str) -> bytes:
    return f"<OP><HEADER><FORMAT_VERSION>2.4</FORMAT_VERSION></HEADER><OBSERVATIONS>{''.join(items)}</OBSERVATIONS></OP>".encode()


# Observación real de T171 sobre Parral: de 01:39:20 a 01:46:00 UTC, configuración 156.
def t171_day(doy: int, config: str = "156") -> bytes:
    return xml(obs(f"2026-{doy}T01:39:20.000000", f"2026-{doy}T01:46:00.000000", config=config))


class FakeSource:
    def __init__(self, days: dict[str, bytes]):
        self.days = days  # "2026-11-05" -> XML del plan de ese día
        self.read = []

    def plans(self, start, end):
        key = start.strftime("%Y-%m-%d")
        if key not in self.days:
            return []
        return [PlanFile(f"dcop_{start:%Y%j}_v01", f"https://nisar.asf.earthdatacloud.nasa.gov/NISAR/DCOP/{key}.xml")]

    def observations(self, plan):
        self.read.append(plan.title)
        return parse_plan(self.days[plan.url.rsplit("/", 1)[1][:-4]])


def catalog(url):
    if url.endswith("/series"):
        return [{"id": CATALOG_T171, "track": 171, "direction": "D", "frame": 75, "granules": []}]
    if url.endswith("/timeline"):
        return {"passes": [
            {"series": CATALOG_T171, "acquired_at": "2026-09-30T01:44:32Z"},
            {"series": CATALOG_T171, "acquired_at": LAST},
        ]}
    raise AssertionError(url)


def plan_for(days, horizon=10):
    return build_plan(AOI, "http://catalog", catalog, FakeSource(days), NOW, horizon)


def at(text):
    return datetime.fromisoformat(text).replace(tzinfo=UTC)


def test_parse_plan_reads_type_times_and_config():
    (item,) = parse_plan(t171_day(326))
    assert item.kind == "lsar" and item.config_id == "156"
    assert item.start == datetime(2026, 11, 22, 1, 39, 20, tzinfo=UTC) and item.end == datetime(2026, 11, 22, 1, 46, tzinfo=UTC)


def test_classify_states():
    full = parse_plan(t171_day(309))
    expected = at("2026-11-05T01:44:32")
    assert classify(full, expected, True)[0] == "planned"
    short = parse_plan(xml(obs("2026-309T01:39:20.000000", "2026-309T01:44:50.000000")))
    assert classify(short, expected, True)[0] == "partial"
    sband = parse_plan(xml(obs("2026-309T01:39:20.000000", "2026-309T01:46:00.000000", kind="ssar")))
    assert classify(sband, expected, True) == ("not_planned", None)
    assert classify([], expected, False) == ("no_plan", None)


def test_joint_observation_counts_as_radar():
    joint = parse_plan(xml(obs("2026-309T01:39:20.000000", "2026-309T01:46:00.000000", kind="joint")))
    assert classify(joint, at("2026-11-05T01:44:32"), True)[0] == "planned"


def test_build_plan_lists_passes_from_last_plus_cycle_to_horizon():
    body = plan_for({"2026-10-12": t171_day(285), "2026-10-24": t171_day(297), "2026-11-05": t171_day(309)}, horizon=10)
    assert body["schema"] == "observation-plan/1" and body["collection"] == "NISAR_COP"
    assert body["checked_at"] == "2026-11-12T20:00:00Z" and body["window_seconds"] == [-10, 40]
    (series,) = body["series"]
    assert series["catalog_series"] == CATALOG_T171 and series["last_acquired_at"] == LAST
    assert series["reference_config_id"] == "156" and series["reference_plan"] == "dcop_2026285_v01"
    assert [(p["expected_at"], p["status"]) for p in series["passes"]] == [
        ("2026-10-24T01:44:32Z", "planned"),
        ("2026-11-05T01:44:32Z", "planned"),
        ("2026-11-17T01:44:32Z", "no_plan"),
    ]
    first = series["passes"][0]
    assert first["plan"] == "dcop_2026297_v01" and first["config_id"] == "156" and first["same_config"] is True
    assert first["observation"] == {"start": "2026-10-24T01:39:20Z", "end": "2026-10-24T01:46:00Z"}
    assert series["passes"][2]["plan"] is None and series["passes"][2]["same_config"] is None


def test_config_change_is_flagged():
    body = plan_for({"2026-10-12": t171_day(285), "2026-10-24": t171_day(297, config="8")}, horizon=0)
    (item,) = [p for p in body["series"][0]["passes"] if p["status"] == "planned"]
    assert item["config_id"] == "8" and item["same_config"] is False


def test_each_plan_is_read_once():
    source = FakeSource({"2026-10-12": t171_day(285), "2026-10-24": t171_day(297)})
    build_plan(AOI, "http://catalog", catalog, source, NOW, 0)
    assert sorted(source.read) == ["dcop_2026285_v01", "dcop_2026297_v01"]


def test_series_without_passes_in_catalog_is_an_error():
    def empty(url):
        return catalog(url) if url.endswith("/series") else {"passes": []}

    with pytest.raises(FetchError):
        build_plan(AOI, "http://catalog", empty, FakeSource({}), NOW, 10)


def test_latest_version_of_each_day_wins_and_only_public_xml_is_used():
    base = "https://nisar.asf.earthdatacloud.nasa.gov"

    def entry(title):
        return {"title": title, "links": [
            {"href": f"{base}/NISAR/DCOP/{title}/{title}.xml"},
            {"href": f"{base}/NISAR-JPL-PRIVATE-DATA/DCOP/{title}/{title}.met.json"},
        ]}

    plans = latest_versions([
        entry("dcop_2026207_c027_d06_s1a_o7a_o2s1b_v01"),
        entry("dcop_2026207_c027_d06_s1a_o7a_o2s1b_v02"),
        entry("dcop_2026208_c027_d07_s1b_o7b_o2s1c_v01"),
        {"title": "otro_producto", "links": []},
    ])
    assert [p.title for p in plans] == ["dcop_2026207_c027_d06_s1a_o7a_o2s1b_v02", "dcop_2026208_c027_d07_s1b_o7b_o2s1c_v01"]
    assert all("/NISAR/DCOP/" in p.url and p.url.endswith(".xml") for p in plans)


class Remote:
    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.body


def test_cmr_source_sends_token_only_to_nasa_and_reads_xml():
    seen = []

    def opener(url, token, block):
        seen.append((url, token))
        return Remote(t171_day(309))

    cmr = {"feed": {"entry": [{"title": "dcop_2026309_v01", "links": [
        {"href": "https://nisar.asf.earthdatacloud.nasa.gov/NISAR/DCOP/x/dcop_2026309_v01.xml"}]}]}}
    queries = []
    source = CmrPlanSource(TOKEN, lambda url: queries.append(url) or cmr, opener, is_nasa_url)
    (plan,) = source.plans(at("2026-11-05T01:44:22"), at("2026-11-05T01:45:12"))
    assert "short_name=NISAR_COP" in queries[0] and "2026-11-05T01%3A44%3A22Z" in queries[0]
    assert source.observations(plan)[0].config_id == "156" and seen == [(plan.url, TOKEN)]
    with pytest.raises(FetchError) as error:
        source.observations(PlanFile("dcop_x_v01", "https://attacker.example/NISAR/DCOP/x.xml"))
    assert TOKEN not in str(error.value) and len(seen) == 1


def test_unreadable_xml_is_a_clear_error_without_token():
    source = CmrPlanSource(TOKEN, lambda url: {}, lambda *a: Remote(b"<OP><roto"), is_nasa_url)
    with pytest.raises(FetchError) as error:
        source.observations(PlanFile("dcop_x_v01", "https://nisar.asf.earthdatacloud.nasa.gov/NISAR/DCOP/x.xml"))
    assert "dcop_x_v01" in str(error.value) and TOKEN not in str(error.value)


def test_written_plan_has_no_token_and_is_atomic(tmp_path):
    body = plan_for({"2026-10-12": t171_day(285), "2026-10-24": t171_day(297)}, horizon=0)
    target = write_plan(tmp_path, body)
    assert target == tmp_path / "plan" / "parral.json"
    text = target.read_text(encoding="utf-8")
    assert TOKEN not in text and json.loads(text) == body and not list(target.parent.glob("*.part"))
