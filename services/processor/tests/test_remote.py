"""Procesado en línea (run-remote) sin red: los «gránulos remotos» son GCOV sintéticos abiertos como objetos de
archivo, igual que llegarían de fsspec. Comprueba que no se escribe ningún recorte y que salen los artefactos."""
import io

import numpy as np
import pytest

from processor.change import Params
from processor.pipeline import process_series
from processor.remote import RemoteGranule, is_nasa_url, latest_granules, run_remote
from processor.synthetic import SeriesSpec, generate_series

BBOX = [-105.75, 26.87, -105.60, 26.98]


def test_only_nasa_hosts_get_the_token():
    assert is_nasa_url("https://nisar.asf.earthdatacloud.nasa.gov/NISAR/x.h5")
    assert not is_nasa_url("https://example.invalid/x.h5") and not is_nasa_url("http://nisar.asf.earthdatacloud.nasa.gov/x")


def test_latest_granules_takes_the_most_recent():
    serie = {"track": 48, "direction": "A", "frame": 15,
             "granules": [{"id": f"G{i}", "date": f"2026-0{6 + i}-01", "download_url": "u"} for i in range(4)]}
    got = latest_granules("http://catalog", {"id": "z"}, {"id": "T048A-F015", "track": 48, "direction": "A", "frame": 15}, 2,
                          getter=lambda url: [serie])
    assert [g["id"] for g in got] == ["G2", "G3"]


def test_run_remote_reads_in_memory_and_writes_only_artifacts(tmp_path):
    paths = generate_series(SeriesSpec(48, "A", 15, ("20260617", "20260629", "20260711")), BBOX, tmp_path / "fuente", posting_m=100.0)
    by_id = {p.stem: p for p in paths}
    serie = {"track": 48, "direction": "A", "frame": 15,
             "granules": [{"id": p.stem, "date": f"2026-0{6 + i}-01", "download_url": f"https://nisar.asf.earthdatacloud.nasa.gov/{p.stem}.h5"}
                          for i, p in enumerate(sorted(paths))]}
    abiertos = []

    def opener(url):
        stem = url.rsplit("/", 1)[1][:-3]
        f = io.BytesIO(by_id[stem].read_bytes())  # en memoria, como el archivo remoto
        abiertos.append(f)
        return f

    aoi = {"id": "z-prueba", "bbox": BBOX, "maturity": "PROVISIONAL", "series": [{"id": "T048A-F015", "track": 48, "direction": "A", "frame": 15}]}
    artifacts = tmp_path / "data" / "artifacts"

    def process(files):
        assert all(isinstance(f, RemoteGranule) for f in files)
        return process_series(files, aoi, "T048A-F015", artifacts, "PROVISIONAL", Params(), dem_sources=None)

    manifest = run_remote(aoi, "T048A-F015", artifacts, "http://catalog", 3, process, opener=opener, getter=lambda url: [serie])
    assert len(manifest["pairs"]) >= 2 and (artifacts / "z-prueba" / "T048A-F015" / "manifest.json").exists()
    assert not (tmp_path / "data" / "raw").exists()  # ningún recorte en disco
    assert all(f.closed for f in abiertos)


def test_run_remote_needs_token(monkeypatch):
    monkeypatch.delenv("EARTHDATA_TOKEN", raising=False)
    with pytest.raises(ValueError, match="EARTHDATA_TOKEN"):
        run_remote({"id": "z", "series": []}, "S", None, "http://c", 2, lambda f: None)


def _rechunk(src_path, dst_path):
    """Copia un gránulo sintético con los filtros de los reales de NASA: trozos, shuffle + gzip y máscaras gzip."""
    import h5py

    with h5py.File(src_path, "r") as src, h5py.File(dst_path, "w") as dst:
        src.copy(src["/science/LSAR/identification"], dst.require_group("/science/LSAR"), name="identification")
        g = dst.require_group("/science/LSAR/GCOV/grids/frequencyA")
        s = src["/science/LSAR/GCOV/grids/frequencyA"]
        for name in ("xCoordinates", "yCoordinates", "projection"):
            s.copy(s[name], g, name=name)
        for name in ("HHHH", "HVHV", "numberOfLooks"):
            g.create_dataset(name, data=s[name][()], chunks=(16, 16), compression="gzip", compression_opts=1, shuffle=True)
        for name in ("mask", "inputDataExceptionMask"):
            g.create_dataset(name, data=s[name][()], chunks=(16, 16), compression="gzip", compression_opts=9)


def test_parallel_reader_matches_h5py_window(tmp_path):
    import fsspec

    from processor.gcov import read_scene
    from processor.remote import read_window_parallel

    (path,) = generate_series(SeriesSpec(48, "A", 15, ("20260617",)), BBOX, tmp_path / "fuente", posting_m=100.0)
    rechunked = tmp_path / "troceado.h5"
    _rechunk(path, rechunked)
    fs = fsspec.filesystem("memory")
    url = "https://nisar.asf.earthdatacloud.nasa.gov/prueba/troceado.h5"
    with fs.open(url, "wb") as f:
        f.write(rechunked.read_bytes())
    zona = [-105.70, 26.90, -105.64, 26.95]  # dentro de la escena, sin alinear con los trozos
    rapido = read_scene(RemoteGranule("troceado", read_window_parallel(url, "x", zona, fs=fs)), zona)
    lento = read_scene(rechunked, zona)
    for capa in ("hh", "hv", "mask", "looks", "exception"):
        assert np.array_equal(getattr(rapido, capa), getattr(lento, capa)), capa
    assert rapido.transform == lento.transform and rapido.meta.granule_id == lento.meta.granule_id


def test_parallel_reader_refuses_foreign_hosts():
    from processor.remote import read_window_parallel

    with pytest.raises(ValueError, match="no se envía el token"):
        read_window_parallel("https://example.invalid/x.h5", "x", BBOX)


def test_same_track_and_frame_with_several_series_uses_the_chosen_one():
    # Venecia (2026-11-15): catalog dio 3 series con la misma pista, dirección y marco.
    def serie(id_, n):
        return {"id": id_, "track": 43, "direction": "A", "frame": 24,
                "granules": [{"id": f"{id_}-{i}", "date": f"2026-0{6 + i}-01", "download_url": "u"} for i in range(n)]}

    datos = [serie("T043A-F024-4005-DHDH-P05023", 6), serie("T043A-F024-2005-DHDH-P05023", 3), serie("T043A-F024-4005-DHDH-P05024", 2)]
    spec = {"id": "T043A-F024", "track": 43, "direction": "A", "frame": 24}
    elegida = latest_granules("http://c", {"id": "z"}, spec, 2, getter=lambda u: datos, catalog_id="T043A-F024-2005-DHDH-P05023")
    assert [g["id"] for g in elegida] == ["T043A-F024-2005-DHDH-P05023-1", "T043A-F024-2005-DHDH-P05023-2"]
    sin_id = latest_granules("http://c", {"id": "z"}, spec, 2, getter=lambda u: datos)
    assert sin_id[0]["id"].startswith("T043A-F024-4005-DHDH-P05023")


def test_failed_chunks_are_retried(monkeypatch):
    from processor import remote

    monkeypatch.setattr(remote.time, "sleep", lambda s: None)

    class Flaky:
        calls = 0

        def cat_ranges(self, urls, starts, ends, batch_size, on_error):
            Flaky.calls += 1
            out = [bytes(range(s % 256, s % 256 + 1)) * (e - s) for s, e in zip(starts, ends)]
            if Flaky.calls == 1:
                out[0] = ConnectionResetError("cortada")
            return out

    wanted = [("HHHH", (0, 0), 0, 3, 0), ("HHHH", (0, 512), 10, 2, 0)]
    raw = remote._fetch_chunks(Flaky(), "https://x.earthdatacloud.nasa.gov/a.h5", wanted)
    assert Flaky.calls == 2 and raw[("HHHH", (0, 0))] == b"\x00\x00\x00" and raw[("HHHH", (0, 512))] == b"\n\n"


def test_chunks_that_keep_failing_raise(monkeypatch):
    from processor import remote

    monkeypatch.setattr(remote.time, "sleep", lambda s: None)

    class Broken:
        def cat_ranges(self, urls, starts, ends, batch_size, on_error):
            return [ConnectionResetError("cortada")] * len(urls)

    with pytest.raises(IOError, match="1 trozos"):
        remote._fetch_chunks(Broken(), "u", [("HHHH", (0, 0), 0, 3, 0)])


def test_fast_path_starts_computing_before_every_date_arrives(tmp_path, monkeypatch):
    """Los metadatos llegan antes que los trozos y las fechas bajan en orden, de 2 en 2: process_series calcula la
    primera fecha mientras la última aún no ha empezado a bajar."""
    import threading

    import h5py

    from processor import remote
    from processor.gcov import read_meta

    paths = sorted(generate_series(SeriesSpec(48, "A", 15, ("20260617", "20260629", "20260711")), BBOX, tmp_path / "f", posting_m=100.0))
    by_url = {f"https://nisar.asf.earthdatacloud.nasa.gov/{p.stem}.h5": p for p in paths}
    serie = {"track": 48, "direction": "A", "frame": 15,
             "granules": [{"id": p.stem, "date": f"2026-0{6 + i}-01", "download_url": u} for i, (u, p) in enumerate(by_url.items())]}
    last_may_start = threading.Event()
    order = []

    def fake(url, token, bbox, fs=None, on_meta=None, gate=None):
        p = by_url[url]
        with h5py.File(p, "r") as h:
            on_meta(read_meta(h))
        if p == paths[-1]:
            assert last_may_start.wait(5)  # la tercera no baja hasta que la primera termina
        gate()
        order.append(p.stem)
        return io.BytesIO(p.read_bytes())

    monkeypatch.setattr(remote, "read_window_parallel", fake)
    monkeypatch.setenv("EARTHDATA_TOKEN", "token-de-prueba")
    aoi = {"id": "z-prueba", "bbox": BBOX, "maturity": "PROVISIONAL", "series": [{"id": "T048A-F015", "track": 48, "direction": "A", "frame": 15}]}
    artifacts = tmp_path / "artifacts"

    def process(files):
        assert all(isinstance(f, remote.LazyGranule) and f.meta for f in files)
        files[0]._future.result()
        last_may_start.set()
        return process_series(files, aoi, "T048A-F015", artifacts, "PROVISIONAL", Params(), dem_sources=None)

    manifest = remote.run_remote(aoi, "T048A-F015", artifacts, "http://catalog", 3, process, getter=lambda url: [serie])
    # La tercera fecha solo baja después de la primera; la segunda puede terminar antes o después que la tercera.
    assert len(manifest["pairs"]) == 3 and order.index(paths[-1].stem) > order.index(paths[0].stem)
