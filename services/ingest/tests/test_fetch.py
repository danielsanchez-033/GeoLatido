"""Prueba la ingesta con un servidor HTTP local que se comporta como NASA."""
import json
import shutil
import threading
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import h5py
import numpy as np
import pytest

from ingest.fetch import FetchError, fetch_series, is_nasa_url, select_series
from ingest.subset import GRID, IDENTIFICATION, RADAR_GRID, SubsetError

TOKEN = "token-de-prueba"
SIZE = 1500
POSTING = 200.0
# Malla en UTM 13N alrededor de Parral, con la y descendente como en los productos reales.
LEFT, TOP = 400000.0, 3100000.0
AOI_SMALL = [-105.95, 26.70, -105.90, 26.75]
SERIES = {"id": "T048A-F015", "track": 48, "direction": "A", "frame": 15}
AOI = {"id": "parral", "bbox": AOI_SMALL, "series": [SERIES]}
ALLOW_LOCAL = lambda url: url.startswith("http://127.0.0.1")  # noqa: E731


# radarGrid como en los gránulos reales: nodos cada 500 m, y descendente y cubos (altura, y, x).
NODE = 2500.0
HEIGHTS = np.arange(-1000.0, 1500.0, 500.0)


def write_radar_grid(handle):
    nodes_x = LEFT - NODE + NODE * np.arange(SIZE * POSTING / NODE + 3)
    nodes_y = TOP + NODE - NODE * np.arange(SIZE * POSTING / NODE + 3)
    group = handle.create_group(RADAR_GRID)
    group["xCoordinates"] = nodes_x
    group["yCoordinates"] = nodes_y
    group["heightAboveEllipsoid"] = HEIGHTS
    shape = (HEIGHTS.size, nodes_y.size, nodes_x.size)
    incidence = 30.0 + np.broadcast_to(np.arange(nodes_x.size, dtype=np.float32), shape)
    group.create_dataset("incidenceAngle", data=incidence, chunks=(1, 16, 16), compression="gzip")
    group["incidenceAngle"].attrs["units"] = "degrees"
    group.create_dataset("slantRange", data=np.ones(shape, np.float64), chunks=(1, 16, 16))
    group["projection"] = np.uint32(32613)
    group["projection"].attrs["epsg_code"] = 32613


def write_granule(path, radar_grid=True):
    rng = np.random.default_rng(3)
    with h5py.File(path, "w") as handle:
        identification = handle.create_group(IDENTIFICATION)
        identification["granuleId"] = "NISAR_GRANULE"
        identification["trackNumber"] = np.uint32(48)
        identification["frameNumber"] = np.uint16(15)
        identification["orbitPassDirection"] = "Ascending"
        identification["zeroDopplerStartTime"] = "2026-06-17T12:24:34.000000"
        identification["compositeReleaseId"] = "P05023"
        grid = handle.create_group(GRID)
        grid["xCoordinates"] = LEFT + POSTING * (np.arange(SIZE) + 0.5)
        grid["yCoordinates"] = TOP - POSTING * (np.arange(SIZE) + 0.5)
        shape = (SIZE, SIZE)
        for name, data in (
            ("HHHH", rng.random(shape, np.float32)),
            ("HVHV", rng.random(shape, np.float32)),
            ("mask", np.ones(shape, np.uint8)),
            ("numberOfLooks", np.full(shape, 20.0, np.float32)),
            ("inputDataExceptionMask", np.zeros(shape, np.uint8)),
        ):
            grid.create_dataset(name, data=data, chunks=(250, 250))
        grid["projection"] = np.uint32(32613)
        grid["projection"].attrs["epsg_code"] = 32613
        if radar_grid:
            write_radar_grid(handle)


class State:
    def __init__(self, file_bytes):
        self.file_bytes = file_bytes
        self.served = 0
        self.auth_seen = []
        self.redirect_to = None


class Handler(BaseHTTPRequestHandler):
    def __init__(self, state, *args, **kwargs):
        self.state = state
        super().__init__(*args, **kwargs)

    def log_message(self, *args):
        pass

    def _respond(self, send_body):
        auth = self.headers.get("Authorization")
        self.state.auth_seen.append(auth)
        # El destino firmado imita a CloudFront: no pide token.
        if not self.path.startswith("/signed") and auth != f"Bearer {TOKEN}":
            self.send_response(401)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if self.path.startswith("/redirect"):
            self.send_response(303)
            self.send_header("Location", self.state.redirect_to)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        data = self.state.file_bytes
        header = self.headers.get("Range")
        if header:
            start, end = header.split("=")[1].split("-")
            start, end = int(start), min(int(end or len(data) - 1), len(data) - 1)
            body = data[start : end + 1]
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{end}/{len(data)}")
        else:
            body = data
            self.send_response(200)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if send_body:
            self.state.served += len(body)
            self.wfile.write(body)

    def do_HEAD(self):
        self._respond(False)

    def do_GET(self):
        self._respond(True)


def serve(state):
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, state))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


@pytest.fixture(scope="module")
def granule_bytes(tmp_path_factory):
    path = tmp_path_factory.mktemp("remote") / "granule.h5"
    write_granule(path)
    return path.read_bytes()


@pytest.fixture()
def nasa(granule_bytes):
    state = State(granule_bytes)
    server = serve(state)
    yield state, f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


def catalog_with(*urls, frame=15, timeline=None):
    series = [{
        "id": "T048A-F015-4005-DHDH-P05023", "track": 48, "direction": "A", "frame": frame,
        "granules": [
            {"id": f"GRANULE_{index}", "date": f"2026-06-{17 + 12 * index}", "size_mb": 6900.0, "download_url": url}
            for index, url in enumerate(urls)
        ],
    }]
    passes = timeline if timeline is not None else {
        "passes": [
            {
                "granule_id": f"GRANULE_{index}",
                "acquired_at": f"2026-06-{17 + 12 * index}T12:24:34Z",
                "published_at": f"2026-06-{19 + 12 * index}T03:00:00Z",
            }
            for index in range(len(urls))
        ]
    }

    def getter(url):
        if url.endswith("/timeline"):
            if isinstance(passes, Exception):
                raise passes
            return passes
        return series

    return getter


def run(tmp_path, json_getter, token=TOKEN, is_allowed=ALLOW_LOCAL, limit=None, aoi=AOI):
    return fetch_series(aoi, "T048A-F015", tmp_path, token, "http://catalog", limit, json_getter, is_allowed, 64 * 1024)


def test_subset_follows_contract_and_reads_a_fraction(tmp_path, nasa):
    state, base = nasa
    result = run(tmp_path, catalog_with(f"{base}/g0.h5"))
    assert result.written == ["GRANULE_0"]
    with h5py.File(result.target / "GRANULE_0.h5", "r") as handle:
        grid = handle[GRID]
        assert 0 < grid["HHHH"].shape[0] < SIZE and grid["HHHH"].dtype == np.float32
        assert grid["HHHH"].shape == (grid["yCoordinates"].size, grid["xCoordinates"].size)
        assert grid["yCoordinates"][0] > grid["yCoordinates"][-1]
        assert grid["projection"].attrs["epsg_code"] == 32613
        assert handle[IDENTIFICATION]["trackNumber"].dtype == np.uint32
        assert handle.attrs["subset_of"] == "NISAR_GRANULE" and "data_kind" not in handle.attrs
    assert state.served < len(state.file_bytes) * 0.5


def test_second_run_skips_existing_subset(tmp_path, nasa):
    state, base = nasa
    getter = catalog_with(f"{base}/g0.h5")
    run(tmp_path, getter)
    served = state.served
    result = run(tmp_path, getter)
    assert result.skipped == ["GRANULE_0"] and result.written == [] and state.served == served


def test_limit_restricts_dates(tmp_path, nasa):
    _, base = nasa
    result = run(tmp_path, catalog_with(f"{base}/g0.h5", f"{base}/g1.h5"), limit=1)
    assert result.written == ["GRANULE_0"]


def test_last_takes_the_most_recent_dates(tmp_path, nasa):
    # Procesado en línea (2026-11-15): --last N trae las N fechas más recientes, no las primeras.
    _, base = nasa
    getter = catalog_with(f"{base}/g0.h5", f"{base}/g1.h5")
    result = fetch_series(AOI, "T048A-F015", tmp_path, TOKEN, "http://catalog", None, getter, ALLOW_LOCAL, 64 * 1024, last=1)
    assert result.written == ["GRANULE_1"]


def test_bad_token_gives_clear_error_without_leaving_files_or_token(tmp_path, nasa):
    _, base = nasa
    with pytest.raises(FetchError) as error:
        run(tmp_path, catalog_with(f"{base}/g0.h5"), token="malo")
    assert "malo" not in str(error.value) and "token" in str(error.value)
    assert not list((tmp_path / "raw" / "real" / "parral" / "T048A-F015").iterdir())


def test_redirect_to_other_origin_drops_token(tmp_path, nasa, granule_bytes):
    state, base = nasa
    signed_state = State(granule_bytes)
    signed = serve(signed_state)
    state.redirect_to = f"http://127.0.0.1:{signed.server_address[1]}/signed.h5"
    try:
        result = run(tmp_path, catalog_with(f"{base}/redirect.h5"))
    finally:
        signed.shutdown()
    assert result.written == ["GRANULE_0"]
    assert signed_state.auth_seen and all(value is None for value in signed_state.auth_seen)


def test_token_is_never_sent_to_a_foreign_host(tmp_path, nasa):
    state, _ = nasa
    with pytest.raises(FetchError):
        run(tmp_path, catalog_with("https://attacker.example/g.h5"), is_allowed=is_nasa_url)
    assert state.auth_seen == []


def test_granule_from_another_series_is_rejected(tmp_path, nasa):
    _, base = nasa
    aoi = {**AOI, "series": [{**SERIES, "frame": 99}]}
    with pytest.raises(SubsetError):
        run(tmp_path, catalog_with(f"{base}/g0.h5", frame=99), aoi=aoi)


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://nisar.asf.earthdatacloud.nasa.gov/NISAR/a.h5", True),
        ("http://nisar.asf.earthdatacloud.nasa.gov/NISAR/a.h5", False),
        ("https://earthdatacloud.nasa.gov.evil.example/a.h5", False),
    ],
)
def test_host_allow_list(url, expected):
    assert is_nasa_url(url) is expected


def test_multiple_versions_are_not_chosen_silently():
    candidates = [{"id": "a", "track": 48, "direction": "A", "frame": 15}, {"id": "b", "track": 48, "direction": "A", "frame": 15}]
    with pytest.raises(FetchError):
        select_series(candidates, SERIES)


def test_excluded_granule_is_never_fetched_and_limit_counts_usable_ones(tmp_path, nasa):
    state, base = nasa
    aoi = {**AOI, "series": [{**SERIES, "exclude": [{"granule": "GRANULE_0", "reason": "product_defect"}]}]}
    result = run(tmp_path, catalog_with(f"{base}/g0.h5", f"{base}/g1.h5"), limit=1, aoi=aoi)
    assert result.excluded == ["GRANULE_0"] and result.written == ["GRANULE_1"]
    assert not (result.target / "GRANULE_0.h5").exists() and result.stale == []


def test_excluded_file_already_on_disk_is_reported_not_deleted(tmp_path, nasa):
    _, base = nasa
    run(tmp_path, catalog_with(f"{base}/g0.h5"))
    aoi = {**AOI, "series": [{**SERIES, "exclude": [{"granule": "GRANULE_0", "reason": "product_defect"}]}]}
    result = run(tmp_path, catalog_with(f"{base}/g0.h5"), aoi=aoi)
    assert result.stale == ["GRANULE_0"] and (result.target / "GRANULE_0.h5").exists()


def test_radar_grid_is_cropped_to_the_window_with_margin_and_all_heights(tmp_path, nasa):
    _, base = nasa
    result = run(tmp_path, catalog_with(f"{base}/g0.h5"))
    with h5py.File(result.target / "GRANULE_0.h5", "r") as handle:
        grid, radar = handle[GRID], handle[RADAR_GRID]
        x, y = grid["xCoordinates"][()], grid["yCoordinates"][()]
        nodes_x, nodes_y = radar["xCoordinates"][()], radar["yCoordinates"][()]
        # Dos nodos de margen fuera de la ventana por cada lado, y la orientación original.
        assert (nodes_x < x.min()).sum() == 3 and (nodes_x > x.max()).sum() == 3
        assert (nodes_y > y.max()).sum() == 3 and (nodes_y < y.min()).sum() == 3
        assert nodes_y[0] > nodes_y[-1]
        cube = radar["incidenceAngle"]
        assert cube.shape == (HEIGHTS.size, nodes_y.size, nodes_x.size) and cube.dtype == np.float32
        assert cube.attrs["units"] == "degrees"
        assert radar["slantRange"].dtype == np.float64
        assert list(radar["heightAboveEllipsoid"][()]) == list(HEIGHTS)
        assert radar["projection"].attrs["epsg_code"] == 32613


def test_radar_grid_values_are_copied_unchanged(tmp_path, nasa, granule_bytes):
    _, base = nasa
    result = run(tmp_path, catalog_with(f"{base}/g0.h5"))
    (tmp_path / "original.h5").write_bytes(granule_bytes)
    with h5py.File(tmp_path / "original.h5", "r") as src, h5py.File(result.target / "GRANULE_0.h5", "r") as out:
        all_x = list(src[RADAR_GRID]["xCoordinates"][()])
        all_y = list(src[RADAR_GRID]["yCoordinates"][()])
        cut_x, cut_y = out[RADAR_GRID]["xCoordinates"][()], out[RADAR_GRID]["yCoordinates"][()]
        cols = slice(all_x.index(cut_x[0]), all_x.index(cut_x[-1]) + 1)
        rows = slice(all_y.index(cut_y[0]), all_y.index(cut_y[-1]) + 1)
        assert np.array_equal(src[RADAR_GRID]["incidenceAngle"][:, rows, cols], out[RADAR_GRID]["incidenceAngle"][()])


def test_granule_without_radar_grid_still_subsets(tmp_path):
    source = tmp_path / "plain.h5"
    write_granule(source, radar_grid=False)
    from ingest.subset import subset

    subset(source, AOI_SMALL, SERIES, tmp_path / "out.h5")
    with h5py.File(tmp_path / "out.h5", "r") as handle:
        assert GRID in handle and RADAR_GRID not in handle


# --- Registro de ingesta (T-ANT-07) ---


def read_log(result):
    return json.loads((result.target / "ingest.json").read_text(encoding="utf-8"))


def test_log_records_each_subset_with_measured_values(tmp_path, nasa):
    state, base = nasa
    result = run(tmp_path, catalog_with(f"{base}/g0.h5"))
    body = read_log(result)
    assert body["schema"] == "ingest-log/1" and body["data_kind"] == "real"
    assert body["published_at_basis"] == "cmr_updated" and body["catalog_series"] == "T048A-F015-4005-DHDH-P05023"
    assert body["aoi"] == "parral" and body["series"] == "T048A-F015" and body["bbox"] == AOI_SMALL
    assert body["read"] == {"cache_type": "background", "block_size_bytes": 64 * 1024}
    (entry,) = body["granules"]
    assert entry["id"] == "GRANULE_0" and entry["origin"] == "fetched"
    assert entry["subset_bytes"] == (result.target / "GRANULE_0.h5").stat().st_size
    # fsspec pide bloques completos; el servidor recorta el último al final del archivo.
    assert entry["bytes_requested"] >= state.served > 0 and result.bytes_requested == entry["bytes_requested"]
    assert entry["seconds"] > 0 and entry["fetched_at"].endswith("Z")
    assert entry["date"] == "2026-06-17" and entry["source_size_mb"] == 6900.0
    assert entry["acquired_at"] == "2026-06-17T12:24:34Z" and entry["published_at"] == "2026-06-19T03:00:00Z"
    assert body["excluded"] == [] and body["stale"] == [] and result.log == result.target / "ingest.json"


def test_log_never_contains_the_token(tmp_path, nasa):
    _, base = nasa
    result = run(tmp_path, catalog_with(f"{base}/g0.h5"))
    assert TOKEN not in (result.target / "ingest.json").read_text(encoding="utf-8")


def test_timeline_failure_leaves_nulls_and_ingest_goes_on(tmp_path, nasa):
    _, base = nasa
    result = run(tmp_path, catalog_with(f"{base}/g0.h5", timeline=FetchError("catalog caído")))
    (entry,) = read_log(result)["granules"]
    assert result.written == ["GRANULE_0"] and result.warnings
    assert entry["published_at"] is None and entry["acquired_at"] is None and entry["bytes_requested"] > 0


def test_second_run_keeps_the_entry_unchanged(tmp_path, nasa):
    _, base = nasa
    getter = catalog_with(f"{base}/g0.h5")
    first = read_log(run(tmp_path, getter))["granules"]
    result = run(tmp_path, getter)
    assert result.skipped == ["GRANULE_0"] and read_log(result)["granules"] == first and result.bytes_requested == 0


def test_subset_already_on_disk_without_entry_is_not_estimated(tmp_path, nasa):
    _, base = nasa
    earlier = run(tmp_path / "antes", catalog_with(f"{base}/g0.h5"))
    target = tmp_path / "raw" / "real" / "parral" / "T048A-F015"
    target.mkdir(parents=True)
    shutil.copy(earlier.target / "GRANULE_0.h5", target / "GRANULE_0.h5")
    result = run(tmp_path, catalog_with(f"{base}/g0.h5"))
    (entry,) = read_log(result)["granules"]
    assert result.skipped == ["GRANULE_0"] and entry["origin"] == "found_on_disk"
    assert entry["subset_bytes"] == (target / "GRANULE_0.h5").stat().st_size and entry["date"] == "2026-06-17"
    assert entry["bytes_requested"] is None and entry["seconds"] is None and entry["fetched_at"] is None


def test_excluded_and_stale_are_listed_apart_from_granules(tmp_path, nasa):
    _, base = nasa
    run(tmp_path, catalog_with(f"{base}/g0.h5"))
    aoi = {**AOI, "series": [{**SERIES, "exclude": [{"granule": "GRANULE_0", "reason": "product_defect"}]}]}
    result = run(tmp_path, catalog_with(f"{base}/g0.h5", f"{base}/g1.h5"), aoi=aoi)
    body = read_log(result)
    assert [entry["id"] for entry in body["granules"]] == ["GRANULE_1"]
    assert body["excluded"] == [{"id": "GRANULE_0", "reason": "product_defect"}] and body["stale"] == ["GRANULE_0"]


def test_failure_midway_keeps_what_was_written(tmp_path, nasa):
    _, base = nasa
    with pytest.raises(FetchError):
        run(tmp_path, catalog_with(f"{base}/g0.h5", "https://attacker.example/g1.h5"))
    target = tmp_path / "raw" / "real" / "parral" / "T048A-F015"
    body = json.loads((target / "ingest.json").read_text(encoding="utf-8"))
    assert [entry["id"] for entry in body["granules"]] == ["GRANULE_0"]
    assert not list(target.glob("*.part"))


def test_unreadable_log_is_set_aside_not_deleted(tmp_path, nasa):
    _, base = nasa
    target = tmp_path / "raw" / "real" / "parral" / "T048A-F015"
    target.mkdir(parents=True)
    (target / "ingest.json").write_text("{roto", encoding="utf-8")
    result = run(tmp_path, catalog_with(f"{base}/g0.h5"))
    assert (target / "ingest.json.bad").read_text(encoding="utf-8") == "{roto"
    assert [entry["id"] for entry in read_log(result)["granules"]] == ["GRANULE_0"] and result.warnings
