"""Procesado en línea con catalog e ingest/processor de prueba (sin red ni NASA). Ids y datos sintéticos."""
import time

import httpx
import pytest
import yaml
from fastapi.testclient import TestClient

from online.main import Runner, choose_series, clamp_bbox, create_app, series_config_id


def serie(id_, pol, n, contains=True, track=48, direction="A", frame=15):
    return {"id": id_, "track": track, "direction": direction, "frame": frame, "polarization": pol, "contains_aoi": contains,
            "granules": [{"id": f"SYNTH-{id_}-{i}", "date": f"2026-0{6 + i}-01"} for i in range(n)]}


def test_clamp_centers_and_limits_the_box():
    assert clamp_bbox([-106.0, 26.0, -105.0, 27.0], 0.3) == [-105.65, 26.35, -105.35, 26.65]
    # Un punto se amplía a 0,1° para que haya algo que medir.
    assert clamp_bbox([-105.66, 26.93, -105.66, 26.93], 0.3) == [-105.71, 26.88, -105.61, 26.98]


def test_choose_series_needs_hh_and_hv():
    chosen, found = choose_series([serie("A", "SHNA", 9), serie("B", "DHDH", 3, contains=False), serie("C", "DHDH", 2)])
    assert chosen["id"] == "C"  # contiene la zona aunque tenga menos fechas
    assert {f["id"] for f in found} == {"A", "B", "C"}
    assert choose_series([serie("A", "SHNA", 9)])[0] is None
    assert series_config_id(serie("X", "DHDH", 2, track=7, direction="D", frame=5)) == "T007D-F005"


def _runner(tmp_path, series_json, rc=0):
    calls = []

    def handler(req):
        return httpx.Response(200, json=series_json)

    def run(args, job):
        calls.append(args)
        job["log"].append("SYNTH " + args[2])
        return rc

    r = Runner(tmp_path / "zones", tmp_path, "http://catalog.test", max_dates=3, window_days=150, run=run,
               client=httpx.Client(transport=httpx.MockTransport(handler)))
    return r, calls


def _wait(r, zid):
    for _ in range(200):
        job = r.get(zid)
        if job["state"] not in ("queued", "running"):
            return job
        time.sleep(0.02)
    raise AssertionError("no terminó")


def test_full_pipeline_writes_zone_and_calls_ingest_and_processor(tmp_path):
    r, calls = _runner(tmp_path, [serie("T048A-F015-4005-DHDH-P05023", "DHDH", 5)])
    job = r.submit("Hidalgo del Parral", [-105.75, 26.87, -105.60, 26.98], 0.3)
    job = _wait(r, job["id"])
    assert job["state"] == "done" and job["series"]["id"] == "T048A-F015"
    zone = yaml.safe_load((tmp_path / "zones" / f"{job['id']}.yaml").read_text(encoding="utf-8"))
    assert zone["series"] == [{"id": "T048A-F015", "track": 48, "direction": "A", "frame": 15}] and zone["maturity"] == "PROVISIONAL"
    (run,) = calls
    # Un solo paso, en memoria: processor run-remote, sin ingest ni recortes en disco.
    assert run[2:4] == ["processor", "--aoi-dir"] and "run-remote" in run and run[run.index("--last") + 1] == "3"
    assert not (tmp_path / "raw").exists()
    # Volver a pedirla no repite el trabajo.
    assert r.submit("Hidalgo del Parral", [-105.75, 26.87, -105.60, 26.98], 0.3)["state"] == "done"


def test_zone_without_hh_hv_says_so(tmp_path):
    r, calls = _runner(tmp_path, [serie("T126D-F055-7700-SHNA-P05023", "SHNA", 9)])
    job = _wait(r, r.submit("Helheim", [-38.6, 66.25, -38.0, 66.5], 0.3)["id"])
    assert job["state"] == "no_processable_series" and calls == []
    assert job["series_found"][0]["polarization"] == "SHNA" and "HH y HV" in job["error"]


def test_failed_fetch_is_reported(tmp_path):
    r, _ = _runner(tmp_path, [serie("S", "DHDH", 4)], rc=1)
    job = _wait(r, r.submit("X", [10, 10, 10.2, 10.2], 0.3)["id"])
    assert job["state"] == "failed" and "EARTHDATA_TOKEN" in job["error"] and job["steps"]["process"].startswith("failed")


def test_api_requires_token(tmp_path, monkeypatch):
    r, _ = _runner(tmp_path, [])
    monkeypatch.delenv("EARTHDATA_TOKEN", raising=False)
    c = TestClient(create_app(r))
    assert c.get("/health").json()["earthdata_token"] is False
    assert c.post("/zones", json={"name": "X", "bbox": [1, 1, 2, 2]}).status_code == 503
    monkeypatch.setenv("EARTHDATA_TOKEN", "token-de-prueba")
    c = TestClient(create_app(r))
    assert c.post("/zones", json={"name": "X", "bbox": [2, 1, 1, 2]}).status_code == 422


def test_restart_marks_interrupted_jobs(tmp_path):
    r, _ = _runner(tmp_path, [])
    job = {"id": "z-x", "state": "running", "created_at": "2026-11-15T00:00:00+00:00", "log": []}
    r._save(job)
    r2, _ = _runner(tmp_path, [])
    assert r2.get("z-x")["state"] == "failed" and "reinicio" in r2.get("z-x")["error"]


def test_done_job_carries_light_summary_from_manifest(tmp_path):
    """Al terminar, el trabajo trae el resumen por par sacado del manifiesto (conteos sintéticos)."""
    import json

    def handler(req):
        return httpx.Response(200, json=[serie("T048A-F015-4005-DHDH-P05023", "DHDH", 4)])

    def run(args, job):
        zid = args[args.index("--aoi") + 1]
        target = tmp_path / "artifacts" / zid / "T048A-F015"
        target.mkdir(parents=True)
        pair = lambda i, f, t, kind, counts: {"id": i, "from": f, "to": t, "kind": kind, "spans_data_gap": False,
                                             "granules": [], "layers": {}, "stats": {"counts": counts}}
        manifest = {"series": {"id": "T048A-F015"}, "data_kind": "synthetic",
                    "dates": [{"date": "2026-09-09"}, {"date": "2026-09-21"}, {"date": "2026-10-03"}],
                    "pairs": [pair("p1", "2026-09-09", "2026-09-21", "consecutive", {"no_change": 90, "change_probable": 10}),
                              pair("p2", "2026-09-21", "2026-10-03", "consecutive", {"no_change": 99, "change_probable": 1}),
                              pair("p3", "2026-09-09", "2026-10-03", "full_window", {"no_change": 10, "low_looks": 80, "terrain": 10})]}
        (target / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        return 0

    r = Runner(tmp_path / "zones", tmp_path, "http://catalog.test", max_dates=3, window_days=150, run=run,
               client=httpx.Client(transport=httpx.MockTransport(handler)))
    job = _wait(r, r.submit("Delicias", [-105.5, 28.1, -105.4, 28.2], 0.3)["id"])
    s = job["summary"]
    assert job["state"] == "done" and s["series"] == "T048A-F015" and s["data_kind"] == "synthetic"
    assert s["rules"]["calibrated"] is False
    p1, p2, p3 = s["pairs"]
    assert (p1["state"], p1["changed_fraction"], p1["interval_days"]) == ("change_probable", 0.1, 12)
    assert (p2["state"], p2["changed_fraction"]) == ("no_detectable_change", 0.01)
    assert (p3["state"], p3["cause"], p3["observed_fraction"]) == ("not_observable", "low_looks", 0.1)


def test_mixed_mode_granules_do_not_count():
    # Venecia (2026-11-15): una serie DHDH cuyos gránulos son de modo mixto (…_DHDH_M_…).
    mixta = serie("T043A-F024-2005-DHDH-P05023", "DHDH", 6)
    for g in mixta["granules"]:
        g["id"] = "NISAR_L2_PR_GCOV_028_043_A_024_2005_DHDH_M_20260816T041010_20260816T041045_P05023_N_F_J_001"
    assert choose_series([mixta])[0] is None
    buena = serie("T043A-F024-4005-DHDH-P05023", "DHDH", 3)
    for i, g in enumerate(buena["granules"]):
        g["id"] = f"NISAR_L2_PR_GCOV_02{i}_043_A_024_4005_DHDH_A_2026081{i}T041010_2026081{i}T041045_P05023_N_F_J_001"
    elegida, resumen = choose_series([mixta, buena])
    assert elegida["id"] == buena["id"] and {r["id"]: r["usable_dates"] for r in resumen}[mixta["id"]] == 0


def test_regenerate_reruns_a_finished_zone_and_drops_old_series(tmp_path):
    r, calls = _runner(tmp_path, [serie("T048A-F015-4005-DHDH-P05023", "DHDH", 5)])
    job = _wait(r, r.submit("Hidalgo del Parral", [-105.75, 26.87, -105.60, 26.98], 0.3)["id"])
    vieja = tmp_path / "artifacts" / job["id"] / "T999A-F001"
    vieja.mkdir(parents=True)
    assert r.regenerate("z-no-existe") is None
    again = r.regenerate(job["id"])
    assert again["state"] == "queued" and again["regenerated_at"]
    job = _wait(r, job["id"])
    assert job["state"] == "done" and len(calls) == 2 and not vieja.exists()
