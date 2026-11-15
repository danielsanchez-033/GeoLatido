"""Dobles de prueba. Todo lo que generan es sintético y lo dice (`data_kind: synthetic`, ids SYNTH-...)."""
from __future__ import annotations

import datetime as dt

import pytest

from research.discovery import DiscoveryPage

PARRAL_BBOX = [-105.95, 26.70, -105.40, 27.15]


def verdict(i: int, frm: str, to: str, frac: float, state: str, kind: str = "consecutive", data_kind: str = "synthetic") -> dict:
    return {
        "id": f"{frm.replace('-', '')}_{to.replace('-', '')}",
        "aoi": "parral",
        "series": "SYNTH-T048",
        "kind": kind,
        "from_date": frm,
        "to_date": to,
        "interval_days": (dt.date.fromisoformat(to) - dt.date.fromisoformat(frm)).days,
        "state": state,
        "cause": None,
        "cause_label": None,
        "summary": {"detected": "x", "does_not_prove": "No prueba la causa.", "missing": ""},
        "hypotheses": ["Humedad del suelo (sintético)"],
        "evidence": {
            "observed_fraction": 0.98,
            "changed_fraction": frac,
            "decision_rule": {"min_observed_fraction": 0.5, "min_changed_fraction": 0.05, "calibrated": False},
            "mean_change_hh_db": 1.2,
            "mean_change_hv_db": 0.8,
            "scene_shift": {"hh_db": 0.3, "exceeds_threshold": False},
            "noise": None,
        },
        "receipt": {"data_kind": data_kind, "granules": [f"SYNTH-G-{frm}", f"SYNTH-G-{to}"], "spans_data_gap": False, "quality": {"before": None, "after": None}},
    }


SERIES_DATES = ["2026-06-17", "2026-06-29", "2026-07-11", "2026-07-23", "2026-08-16", "2026-08-28", "2026-09-09", "2026-09-21", "2026-10-03", "2026-10-15"]
FRACS = [0.02, 0.025, 0.021, 0.018, 0.0518, 0.0956, 0.03, 0.02, 0.015]


class FakeVerdicts:
    def __init__(self, fail: bool = False):
        self.fail = fail
        self.event_calls: list = []

    def aois(self):
        if self.fail:
            raise ConnectionError("verdicts caído (prueba)")
        return ["parral"]

    def series(self, aoi):
        return [{"id": "SYNTH-T048", "data_kind": "synthetic", "bbox": PARRAL_BBOX, "dates": SERIES_DATES, "relief": None}]

    def verdicts(self, aoi, series, lang):
        out = []
        for i, (a, b) in enumerate(zip(SERIES_DATES, SERIES_DATES[1:])):
            f = FRACS[i]
            out.append(verdict(i, a, b, f, "change_probable" if f >= 0.05 else "no_detectable_change"))
        out.append(verdict(99, SERIES_DATES[0], SERIES_DATES[-1], 0.03, "no_detectable_change", "full_window"))
        return out

    def event(self, aoi, date, params):
        self.event_calls.append((aoi, date, params))
        return {"state": "not_observable", "cause": "no_acquisition_during_event", "cause_label": "Ninguna pasada durante el evento",
                "previous_pass": "2026-06-29", "next_pass": "2026-07-08", "persistence_hours": 6}


class FakeCmr:
    def __init__(self, fail_for: set[str] = frozenset()):
        self.fail_for = fail_for
        self.calls: list = []

    def granules(self, short_name, bbox, start, end, limit):
        self.calls.append((short_name, start, end))
        if short_name in self.fail_for:
            raise TimeoutError("CMR sin respuesta (prueba)")
        if short_name == "NISAR_L2_GCOV_PROVISIONAL_V1":
            titles = [
                "NISAR_L2_PR_GCOV_023_048_A_015_4005_DHDH_A_20260617T122434_20260617T122509_P05023_N_F_J_001",
                "NISAR_L2_PR_GCOV_024_048_A_015_4005_DHDH_A_20260629T122434_20260629T122508_P05023_N_F_J_001",
                "NISAR_L2_PR_GCOV_024_171_D_075_4005_DHDH_A_20260626T014432_20260626T014507_P05023_N_F_J_001",
            ]
            entries = [
                {"title": t, "id": f"G-SYNTH-{i}", "time_start": f"2026-06-{17 + i * 6:02d}T12:24:34Z", "time_end": None,
                 "polygons": [["26.0 -106.0 26.0 -105.0 27.5 -105.0 27.5 -106.0 26.0 -106.0"]], "granule_size": "7000",
                 "links": [{"rel": "http://esipfed.org/ns/fedsearch/1.1/data#", "href": f"https://example.invalid/{t}.h5"}]}
                for i, t in enumerate(titles)
            ]
            return DiscoveryPage(3, entries)
        if short_name == "SENTINEL-1A_DP_GRD_HIGH":
            return DiscoveryPage(1, [{"title": "S1A_IW_GRDH_1SDV_20260701T005900_20260701T005925_000000_000000_0000", "time_start": "2026-07-01T00:59:00Z", "boxes": ["26 -106 27.5 -105"]}])
        return DiscoveryPage(0, [])


class FakeEonet:
    def events(self, bbox, start, end):
        return [{"id": "EONET_SYNTH_1", "title": "Tormenta sintética", "categories": [{"id": "severeStorms"}],
                 "sources": [{"id": "TEST", "url": "https://example.invalid/synth"}], "link": "https://example.invalid/eonet",
                 "geometry": [{"type": "Point", "date": "2026-08-20T00:00:00Z", "coordinates": [-105.66, 26.93]}]}]


REGISTRY = [{
    "id": "synth-storm", "title": "Tormenta (registro de prueba)", "type": "heavy_rain", "phenomena": ["flood"], "date": "2026-07-01",
    "time_utc": "21:37", "verdicts_event_type": "urban_storm", "bbox": [-105.75, 26.87, -105.60, 26.98], "confidence": "official",
    "sources": [{"name": "prueba", "url": "https://example.invalid/boletin"}], "unknown": ["Duración del agua en la calle."], "origin": "registry",
}]


@pytest.fixture
def deps():
    from research.pipeline import Deps

    return Deps(cmr=FakeCmr(), verdicts=FakeVerdicts(), eonet=FakeEonet(), registry=REGISTRY)
