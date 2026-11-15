import json
import shutil
from pathlib import Path

import h5py
import jsonschema
import numpy as np
import pytest
import rasterio
from rasterio.transform import Affine
from rasterio.warp import transform_bounds

from processor.cells import cell_features
from processor.change import (
    CHANGE_PROBABLE,
    INPUT_EXCEPTION,
    INVALID_OR_PARTIAL,
    LOW_LOOKS,
    NO_CHANGE,
    OUTSIDE_SCENE,
    TERRAIN,
    STATE_NODATA,
    NO_DATA,
    Params,
    _state_for_unobservable,
    compare,
    observable,
    otsu,
)
from processor.georef import agreement, best_shift, shared_components, shift_mask, water_from_ndwi, water_from_sar
from processor.multitemporal import MultitemporalFilter, equivalent_looks
from processor.terrain import geometry_on_grid, glo30_tiles, layover_shadow, read_radar_grid
from processor.gcov import GRID, IDENTIFICATION, GranuleError, GranuleMeta, Scene, read_meta_path, read_scene
from processor.pipeline import excluded_granules, process_series
from processor.qa import RADIOMETRIC_OUTLIER, date_qa
from processor.synthetic import SeriesSpec, generate_series, write_synthetic_dem

ROOT = Path(__file__).resolve().parents[3]
BBOX = [-105.95, 26.70, -105.40, 27.15]
AOI = {"id": "parral", "bbox": BBOX}
SHAPE = (80, 80)


def scene(hh=None, hv=None, mask=None, looks=None, exception=None, granule="a", rng=None) -> Scene:
    rng = rng or np.random.default_rng(1)
    speckle = rng.gamma(20, 1 / 20, SHAPE).astype(np.float32)
    return Scene(
        hh=(0.05 * speckle if hh is None else hh * speckle).astype(np.float32),
        hv=(0.01 * speckle if hv is None else hv * speckle).astype(np.float32),
        mask=np.ones(SHAPE, np.uint8) if mask is None else mask,
        looks=np.full(SHAPE, 20.0, np.float32) if looks is None else looks,
        exception=np.zeros(SHAPE, np.uint8) if exception is None else exception,
        transform=Affine(200, 0, 0, 0, -200, 0),
        crs="EPSG:32613",
        meta=GranuleMeta(granule, "2026-06-17", 48, "A", 15, "4005", "DHDH", "P05023", "synthetic"),
    )


def test_stable_scene_reports_no_change():
    result = compare(scene(rng=np.random.default_rng(1)), scene(rng=np.random.default_rng(2)))
    assert result.stats["counts"]["change_probable"] == 0


def test_injected_change_is_detected_with_sign():
    after = np.full(SHAPE, 0.05, np.float32)
    after[20:40, 20:40] = 0.05 * 10 ** (6 / 10)
    result = compare(scene(rng=np.random.default_rng(1)), scene(hh=after, rng=np.random.default_rng(2)))
    assert result.state[30, 30] == CHANGE_PROBABLE
    assert result.state[70, 70] == NO_CHANGE
    assert result.stats["mean_change_hh_db"] == pytest.approx(6, abs=1.5)
    signatures = result.stats["signature_counts"]
    assert signatures["hh_up_hv_stable"] == max(signatures.values())
    assert sum(signatures.values()) == result.stats["counts"]["change_probable"]


def test_every_unobservable_cause_is_kept_and_never_called_change():
    mask = np.ones(SHAPE, np.uint8)
    mask[0:10, :] = 255
    mask[10:20, :] = 0
    exception = np.zeros(SHAPE, np.uint8)
    exception[20:30, :] = 2
    looks = np.full(SHAPE, 20.0, np.float32)
    looks[30:40, :] = 1
    before = scene(rng=np.random.default_rng(1))
    after = scene(hh=np.full(SHAPE, 1.0, np.float32), mask=mask, looks=looks, exception=exception, rng=np.random.default_rng(2))
    state = compare(before, after).state
    assert state[5, 5] == OUTSIDE_SCENE
    assert state[15, 5] == INVALID_OR_PARTIAL
    assert state[25, 5] == INPUT_EXCEPTION
    assert state[35, 5] == LOW_LOOKS


def test_small_clusters_are_removed():
    after = np.full(SHAPE, 0.05, np.float32)
    after[10:11, 10:11] = 5.0
    result = compare(scene(rng=np.random.default_rng(1)), scene(hh=after, rng=np.random.default_rng(2)), Params(window=1))
    assert result.state[10, 10] != CHANGE_PROBABLE


def test_mismatched_grids_are_rejected():
    other = scene()
    other.transform = Affine(100, 0, 0, 0, -100, 0)
    with pytest.raises(ValueError):
        compare(scene(), other)


def test_otsu_separates_two_groups():
    values = np.concatenate([np.full(100, 1.0), np.full(100, 9.0)])
    assert 1.0 <= otsu(values) < 9.0


SHIFT_3_DB = 10 ** (3 / 10)


def test_qa_flags_only_the_date_shifted_3_db():
    scenes = [scene(rng=np.random.default_rng(seed)) for seed in range(4)]
    scenes[2] = scene(hh=np.full(SHAPE, 0.05 * SHIFT_3_DB, np.float32), rng=np.random.default_rng(2))
    qa = date_qa(scenes)
    assert [item["flags"] for item in qa] == [[], [], [RADIOMETRIC_OUTLIER], []]
    assert qa[2]["deviation_hh_db"] == pytest.approx(3, abs=0.3)
    assert abs(qa[2]["deviation_hv_db"]) < 0.3
    assert qa[0]["median_hh_db"] == pytest.approx(10 * np.log10(0.05), abs=0.3)
    assert all(item["valid_fraction"] == 1.0 for item in qa)


def test_qa_flags_a_shift_in_hv_alone():
    scenes = [scene(rng=np.random.default_rng(seed)) for seed in range(3)]
    scenes[1] = scene(hv=np.full(SHAPE, 0.01 / SHIFT_3_DB, np.float32), rng=np.random.default_rng(1))
    assert date_qa(scenes)[1]["flags"] == [RADIOMETRIC_OUTLIER]


def test_qa_counts_only_observable_pixels_and_reports_null_without_any():
    half = np.ones(SHAPE, np.uint8)
    half[:, : SHAPE[1] // 2] = 255
    empty = np.zeros(SHAPE, np.uint8)
    qa = date_qa([scene(), scene(mask=half), scene(mask=empty)])
    assert qa[1]["valid_fraction"] == pytest.approx(0.5)
    assert qa[2]["valid_fraction"] == 0.0
    assert qa[2]["median_hh_db"] is None and qa[2]["deviation_hh_db"] is None
    assert qa[2]["flags"] == []


@pytest.fixture(scope="module")
def series(tmp_path_factory):
    root = tmp_path_factory.mktemp("synthetic")
    spec = SeriesSpec(48, "A", 15, ("20260617", "20260723", "20260816", "20261015"))
    return generate_series(spec, BBOX, root / "raw"), root


def test_synthetic_file_follows_specification_paths(series):
    paths, _ = series
    with h5py.File(paths[0], "r") as handle:
        for name in ("HHHH", "HVHV", "mask", "numberOfLooks", "inputDataExceptionMask", "xCoordinates", "yCoordinates"):
            assert name in handle[GRID]
        assert handle[GRID]["projection"].attrs["epsg_code"] == 32613
        assert handle.attrs["data_kind"] == "synthetic"


def test_read_scene_windows_to_aoi(series):
    paths, _ = series
    data = read_scene(paths[0], [-105.75, 26.87, -105.60, 26.98])
    assert 0 < data.hh.shape[0] < 150 and data.meta.track == 48 and data.meta.direction == "A"


def test_read_scene_outside_granule_fails(series):
    paths, _ = series
    with pytest.raises(GranuleError):
        read_scene(paths[0], [10.0, 40.0, 10.1, 40.1])


def test_pipeline_writes_valid_manifest_and_cogs(series):
    paths, root = series
    manifest = process_series(paths, AOI, "T048A-F015", root / "artifacts", "PROVISIONAL")
    schema = json.loads((ROOT / "contracts" / "artifact-manifest.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(manifest, schema)
    assert manifest["data_kind"] == "synthetic"
    assert any("SINTÉTICOS" in notice for notice in manifest["notices"])
    assert [pair["kind"] for pair in manifest["pairs"]].count("full_window") == 1
    gap = next(pair for pair in manifest["pairs"] if pair["id"] == "20260723_20260816")
    assert gap["spans_data_gap"]
    with rasterio.open(root / "artifacts" / gap["layers"]["state"]) as dataset:
        assert dataset.profile["dtype"] == "uint8" and dataset.nodata == 255
        assert dataset.tags(ns="IMAGE_STRUCTURE").get("LAYOUT") == "COG"



def _layers(manifest):
    for item in manifest["dates"]:
        yield item["hh_db"]
        yield item["hv_db"]
    for pair in manifest["pairs"]:
        yield from pair["layers"].values()


def test_every_cog_declares_the_crs_and_covers_the_manifest_bbox(series):
    paths, root = series
    manifest = process_series(paths, AOI, "T048A-F015", root / "artifacts", "PROVISIONAL")
    west, south, east, north = manifest["bbox"]
    layers = list(_layers(manifest))
    assert len(layers) == 2 * len(manifest["dates"]) + 3 * len(manifest["pairs"])
    for layer in layers:
        with rasterio.open(root / "artifacts" / layer) as dataset:
            assert dataset.crs is not None and dataset.crs.to_string() == manifest["crs"], layer
            left, bottom, right, top = transform_bounds(dataset.crs, "EPSG:4326", *dataset.bounds, densify_pts=21)
        # Cubre la zona entera y la excede como mucho por el recorte en UTM (en Parral real, 0,004°).
        margins = (west - left, south - bottom, right - east, top - north)
        assert all(-1e-6 <= margin < 0.01 for margin in margins), (layer, margins)


def test_unobservable_pixels_keep_their_cause_in_the_written_state(series):
    paths, root = series
    params = Params()
    manifest = process_series(paths, AOI, "T048A-F015", root / "artifacts", "PROVISIONAL", params)
    by_date = {path.name.split("_DHDH_A_")[1][:8]: path for path in paths}
    checked = 0
    for pair in manifest["pairs"]:
        a = read_scene(by_date[pair["from"].replace("-", "")], BBOX)
        b = read_scene(by_date[pair["to"].replace("-", "")], BBOX)
        hidden = ~(observable(a, params) & observable(b, params))
        expected = _state_for_unobservable(a, b, params)
        expected[hidden & (expected == NO_CHANGE)] = NO_DATA
        with rasterio.open(root / "artifacts" / pair["layers"]["state"]) as dataset:
            state = dataset.read(1)
        assert hidden.any()
        assert np.array_equal(state[hidden], expected[hidden]), pair["id"]
        assert not np.isin(state[hidden], [NO_CHANGE, CHANGE_PROBABLE]).any()
        checked += 1
    assert checked == len(manifest["pairs"])


def test_pipeline_writes_qa_and_flags_a_shifted_granule(series, tmp_path):
    paths, _ = series
    copies = []
    for path in paths:
        copy = tmp_path / "raw" / path.name
        copy.parent.mkdir(parents=True, exist_ok=True)
        copy.write_bytes(path.read_bytes())
        copies.append(copy)
    with h5py.File(copies[1], "r+") as handle:
        handle[GRID]["HHHH"][...] = handle[GRID]["HHHH"][()] * SHIFT_3_DB

    manifest = process_series(copies, AOI, "T048A-F015", tmp_path / "artifacts", "PROVISIONAL")
    schema = json.loads((ROOT / "contracts" / "artifact-manifest.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(manifest, schema)
    flags = [item["qa"]["flags"] for item in manifest["dates"]]
    assert flags == [[], [RADIOMETRIC_OUTLIER], [], []]
    assert all(0 < item["qa"]["valid_fraction"] < 1 for item in manifest["dates"])
    assert any("control de calidad" in notice and "no está calibrado" in notice for notice in manifest["notices"])


def test_pipeline_does_not_flag_the_unshifted_synthetic_series(series, tmp_path):
    paths, _ = series
    manifest = process_series(paths, AOI, "T048A-F015", tmp_path / "artifacts", "PROVISIONAL")
    assert all(item["qa"]["flags"] == [] for item in manifest["dates"])


def test_pipeline_never_holds_more_than_two_scenes(series, tmp_path, monkeypatch):
    import weakref

    from processor import pipeline

    paths, _ = series
    references, peak = [], []
    original = pipeline.read_scene

    def tracked(path, bbox):
        result = original(path, bbox)
        references.append(weakref.ref(result))
        peak.append(sum(reference() is not None for reference in references))
        return result

    monkeypatch.setattr(pipeline, "read_scene", tracked)
    manifest = process_series(paths, AOI, "T048A-F015", tmp_path / "artifacts", "PROVISIONAL")
    assert len(manifest["pairs"]) == len(paths)  # consecutivos más la ventana completa
    assert max(peak) <= 2


def test_pipeline_memory_does_not_grow_with_the_number_of_dates(tmp_path):
    import tracemalloc

    dates = ("20260617", "20260629", "20260711", "20260723", "20260816", "20260828", "20260909", "20260921")
    peaks = {}
    for count in (3, 8):
        paths = generate_series(SeriesSpec(48, "A", 15, dates[:count]), BBOX, tmp_path / f"raw{count}", posting_m=100.0)
        tracemalloc.start()
        process_series(paths, AOI, "T048A-F015", tmp_path / f"out{count}", "PROVISIONAL")
        peaks[count] = tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()
    assert peaks[8] < 1.25 * peaks[3]


def test_pipeline_finds_the_injected_wetting(series):
    paths, root = series
    manifest = process_series(paths, AOI, "T048A-F015", root / "artifacts", "PROVISIONAL")
    full = next(pair for pair in manifest["pairs"] if pair["kind"] == "full_window")
    assert full["stats"]["counts"]["change_probable"] > 0


def _cell(features, state):
    return [feature for feature in features if feature["properties"]["state"] == state]


def test_cells_follow_the_verdict_rule_and_never_give_zero_where_nothing_was_observed():
    # 10 m en UTM 13N, con el origen a 500 m de un múltiplo de 1 km: las celdas se alinean al km, no a la escena.
    transform = Affine(10, 0, 440_500, 0, -10, 2_980_300)
    state = np.full((230, 250), NO_CHANGE, np.uint8)  # 2,3 km × 2,5 km
    cell = (slice(30, 130), slice(50, 150))  # x 441-442 km, y 2979-2980 km: una celda entera
    block = state[cell]
    block[:10, :] = CHANGE_PROBABLE  # 10 % de cambio
    neighbour = (slice(30, 130), slice(150, 250))  # x 442-443 km: 60 % sin looks y 5 % de cambio en el resto
    state[neighbour][:60, :] = LOW_LOOKS
    state[neighbour][60:62, :] = CHANGE_PROBABLE
    state[130:, :] = STATE_NODATA  # fuera de la escena recortada: no debe salir ninguna celda ahí
    state[:30, :50] = TERRAIN

    collection = cell_features(state, transform, "EPSG:32613")
    features = {feature["properties"]["id"]: feature for feature in collection["features"]}
    changed = features["441_2979"]["properties"]
    assert changed["state"] == "change_probable" and changed["changed_fraction"] == pytest.approx(0.1)
    assert changed["observed_fraction"] == 1.0 and changed["pixels"] == 10_000
    blind = features["442_2979"]["properties"]
    assert blind["state"] == "not_observable" and blind["cause"] == "low_looks"
    assert blind["observed_fraction"] == pytest.approx(0.4)
    assert blind["changed_fraction"] == pytest.approx(0.05)  # se publica, pero no decide: la celda no se observó
    assert all(row >= 2979 for row in (int(key.split("_")[1]) for key in features))
    assert sum(feature["properties"]["pixels"] for feature in features.values()) == int((state != STATE_NODATA).sum())
    assert collection["rules"] == {"min_observed_fraction": 0.5, "min_changed_fraction": 0.05}
    jsonschema.validate(collection, {"type": "object", "required": ["type", "features"]})

    ring = features["441_2979"]["geometry"]["coordinates"][0]
    assert ring[0] == ring[-1] and len(ring) == 5
    assert all(-106.5 < lon < -105 and 26.5 < lat < 27.5 for lon, lat in ring)
    # Reproyectada, no una caja en lon/lat: el borde oeste no tiene la misma longitud abajo y arriba.
    assert ring[0][0] != ring[3][0]
    # La celda de la esquina se recorta a la escena (x desde 440,5 km), no se promete 1 km entero.
    corner = features["440_2980"]["geometry"]["coordinates"][0]
    assert abs(corner[1][0] - corner[0][0]) < 0.006  # unos 500 m de ancho, no 1 km


def test_cells_need_a_grid_in_metres():
    state = np.zeros((10, 10), np.uint8)
    assert cell_features(state, Affine(0.0001, 0, -105.9, 0, -0.0001, 27.1), "EPSG:4326") is None


def test_pipeline_writes_cells_for_every_pair_and_they_add_up_to_the_state(series, tmp_path):
    paths, _ = series
    manifest = process_series(paths, AOI, "T048A-F015", tmp_path, "PROVISIONAL")
    schema = json.loads((ROOT / "contracts" / "artifact-manifest.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(manifest, schema)
    for pair in manifest["pairs"]:
        cells = json.loads((tmp_path / pair["cells"]).read_text(encoding="utf-8"))
        with rasterio.open(tmp_path / pair["layers"]["state"]) as dataset:
            state = dataset.read(1)
        counts = pair["stats"]["counts"]
        assert sum(feature["properties"]["pixels"] for feature in cells["features"]) == int((state != STATE_NODATA).sum())
        changed = sum(
            feature["properties"]["changed_fraction"] * feature["properties"]["observed_fraction"] * feature["properties"]["pixels"]
            for feature in cells["features"]
        )
        assert changed == pytest.approx(counts["change_probable"], rel=0.01, abs=5)
    full = next(pair for pair in manifest["pairs"] if pair["kind"] == "full_window")
    cells = json.loads((tmp_path / full["cells"]).read_text(encoding="utf-8"))
    assert _cell(cells["features"], "change_probable")  # la humectación sintética cae en alguna celda


def test_pipeline_refuses_granules_from_another_series(series, tmp_path):
    paths, _ = series
    other = generate_series(SeriesSpec(171, "D", 75, ("20260626", "20260708")), BBOX, tmp_path)
    with pytest.raises(GranuleError):
        process_series([paths[0], other[0]], AOI, "mix", tmp_path / "out", "PROVISIONAL")


def _altered(series, tmp_path, identification=None, drop=()):
    """Copia el primer gránulo sintético cambiando campos de identificación o quitando capas."""
    paths, _ = series
    copy = tmp_path / paths[0].name
    shutil.copy(paths[0], copy)
    with h5py.File(copy, "r+") as handle:
        group = handle[IDENTIFICATION]
        for name, value in (identification or {}).items():
            del group[name]
            group[name] = value
        for name in drop:
            del handle[GRID][name]
    return copy


def test_mode_and_polarization_come_from_the_product(series):
    meta = read_meta_path(series[0][0])
    assert (meta.mode, meta.polarization) == ("4005", "DHDH")


def test_polarization_without_a_readable_name_comes_from_the_layers(series, tmp_path):
    meta = read_meta_path(_altered(series, tmp_path, {"granuleId": "recorte_renombrado"}))
    assert (meta.mode, meta.polarization) == ("unknown", "DH")


def test_a_name_that_contradicts_the_layers_is_rejected(series, tmp_path):
    name = read_meta_path(series[0][0]).granule_id.replace("_DHDH_", "_DVDV_")
    with pytest.raises(GranuleError, match="las capas son DH"):
        read_meta_path(_altered(series, tmp_path, {"granuleId": name}))


def test_a_name_that_contradicts_the_frequencies_is_rejected(series, tmp_path):
    name = read_meta_path(series[0][0]).granule_id.replace("_4005_", "_4000_")
    with pytest.raises(GranuleError, match="frecuencias"):
        read_meta_path(_altered(series, tmp_path, {"granuleId": name}))


def test_mixed_mode_granules_are_rejected(series, tmp_path):
    with pytest.raises(GranuleError, match="modo mixto"):
        read_meta_path(_altered(series, tmp_path, {"isMixedMode": "True"}))


def test_granules_without_hv_are_rejected_before_reading_layers(series, tmp_path):
    with pytest.raises(GranuleError, match="HH y HV"):
        read_meta_path(_altered(series, tmp_path, drop=("HVHV",)))


REAL = sorted((ROOT / "data" / "raw" / "real" / "parral" / "T048A-F015").glob("*.h5"))


@pytest.mark.skipif(not REAL, reason="sin recortes reales en data/raw/real")
def test_real_granules_agree_with_their_names():
    for path in REAL:
        meta = read_meta_path(path)
        assert (meta.mode, meta.polarization, meta.track, meta.frame) == ("4005", "DHDH", 48, 15)


def _lake(shape=(200, 260)):
    rows, cols = np.ogrid[: shape[0], : shape[1]]
    lake = ((rows - 90) / 45) ** 2 + ((cols - 120) / 80) ** 2 < 1
    arm = (np.abs(rows - 150) < 6) & (cols > 120) & (cols < 230)
    return lake | arm


def test_georef_best_shift_recovers_a_known_shift_with_its_sign():
    reference = _lake()
    moved = shift_mask(reference, 3, -2)  # 3 filas abajo, 2 columnas a la izquierda
    rows, cols, table = best_shift(moved, reference)
    assert (rows, cols) == (-3, 2)
    assert table[(rows, cols)] == 1.0 and table[(0, 0)] < 1.0


def test_georef_prefers_no_shift_when_masks_already_agree():
    rows, cols, _ = best_shift(_lake(), _lake())
    assert (rows, cols) == (0, 0)


def test_georef_finds_water_in_radar_and_optical_and_ignores_unshared_patches():
    rng = np.random.default_rng(3)
    lake = _lake()
    dry_flat = np.zeros(lake.shape, bool)
    dry_flat[10:60, 200:255] = True  # suelo liso: oscuro en radar, seco en el óptico
    dark = lake | dry_flat
    hh = np.where(dark, 10 ** (-19 / 10), 10 ** (-10 / 10)) * rng.gamma(4, 1 / 4, lake.shape)
    hv = np.where(dark, 10 ** (-26 / 10), 10 ** (-18 / 10)) * rng.gamma(4, 1 / 4, lake.shape)
    valid = np.ones(lake.shape, bool)
    radar = water_from_sar(hh.astype(np.float32), hv.astype(np.float32), valid, min_pixels=500)
    optical = water_from_ndwi(np.where(lake, 900, 700), np.where(lake, 300, 2500))
    assert agreement(optical, lake) == 1.0
    assert radar[30, 230]  # el radar ve el suelo liso como agua...
    shared = shared_components(radar, optical)
    assert not shared[30, 230]  # ...pero no se usa para medir el desplazamiento
    assert agreement(shared, lake) > 0.9


def _ramp(shape, pixel, degrees, rising_toward):
    """DEM con pendiente constante que sube hacia el este o el oeste."""
    cols = np.arange(shape[1]) * pixel * np.tan(np.radians(degrees))
    plane = cols if rising_toward == "east" else cols[::-1]
    return np.broadcast_to(plane, shape).astype(np.float32) + 1000


def test_layover_and_shadow_follow_the_slope_facing_the_sensor():
    shape, pixel = (20, 30), 10.0
    transform = Affine(pixel, 0, 0, 0, -pixel, 0)
    incidence = np.full(shape, 40.0, np.float32)
    east, north = np.ones(shape, np.float32), np.zeros(shape, np.float32)  # el sensor está al este
    # Sube hacia el oeste = sube alejándose del sensor: ladera de cara al radar.
    layover, shadow = layover_shadow(_ramp(shape, pixel, 50, "west"), transform, incidence, east, north)
    assert layover[5:15, 5:25].all() and not shadow.any()
    layover, shadow = layover_shadow(_ramp(shape, pixel, 30, "west"), transform, incidence, east, north)
    assert not layover.any() and not shadow.any()
    # Sube hacia el este = baja alejándose del sensor: ladera de espaldas.
    layover, shadow = layover_shadow(_ramp(shape, pixel, 60, "east"), transform, incidence, east, north)
    assert shadow[5:15, 5:25].all() and not layover.any()
    layover, shadow = layover_shadow(_ramp(shape, pixel, 45, "east"), transform, incidence, east, north)
    assert not shadow.any()


def test_glo30_tiles_cover_parral():
    names = [url.rsplit("/", 1)[1] for url in glo30_tiles(BBOX)]
    assert names == [
        "Copernicus_DSM_COG_10_N26_00_W106_00_DEM.tif",
        "Copernicus_DSM_COG_10_N27_00_W106_00_DEM.tif",
    ]


def test_geometry_points_to_the_sensor_whatever_the_sign_convention(tmp_path):
    for direction, sensor_side in (("A", 1), ("D", -1)):
        spec = SeriesSpec(48 if direction == "A" else 171, direction, 15, ("20260617", "20260629"))
        path = generate_series(spec, BBOX, tmp_path / direction, radar_grid=True)[0]
        scene = read_scene(path, BBOX)
        with h5py.File(path, "r") as handle:
            radar = read_radar_grid(handle)
        dem = np.full(scene.hh.shape, 1500, np.float32)
        incidence, east, north = geometry_on_grid(radar, dem, scene.transform, direction, step=8)
        assert 33 <= incidence.min() and incidence.max() <= 47
        assert np.all(np.sign(east) == sensor_side)
        assert np.allclose(np.hypot(east, north), 1, atol=1e-3)
        near = incidence[:, -1] if direction == "A" else incidence[:, 0]  # el sensor queda del lado cercano
        far = incidence[:, 0] if direction == "A" else incidence[:, -1]
        assert near.mean() < far.mean()


def _write_dem(path, bbox, ridge_lon):
    """DEM en EPSG:4326 con una ladera muy empinada que sube hacia el oeste justo al este de `ridge_lon`."""
    width, height = 600, 500
    west, south, east, north = bbox
    lon = np.linspace(west - 0.05, east + 0.05, width)
    steep = (lon > ridge_lon) & (lon < ridge_lon + 0.01)
    metres_per_column = (lon[1] - lon[0]) * 111_000 * np.cos(np.radians(27))
    # Altura acumulada de este a oeste: dentro de la franja sube 70° hacia el oeste.
    rise = np.cumsum(np.where(steep, np.tan(np.radians(70)) * metres_per_column, 0)[::-1])[::-1]
    dem = np.broadcast_to(1500.0 + rise[None, :], (height, width)).astype(np.float32)
    transform = rasterio.transform.from_bounds(west - 0.05, south - 0.05, east + 0.05, north + 0.05, width, height)
    with rasterio.open(path, "w", driver="GTiff", width=width, height=height, count=1, dtype="float32",
                       crs="EPSG:4326", transform=transform) as out:
        out.write(dem, 1)


def test_pipeline_marks_terrain_and_never_calls_it_change(tmp_path):
    spec = SeriesSpec(48, "A", 15, ("20260617", "20260629", "20260711"))
    paths = generate_series(spec, BBOX, tmp_path / "raw", radar_grid=True)
    dem = tmp_path / "dem.tif"
    _write_dem(dem, BBOX, ridge_lon=-105.6)
    manifest = process_series(paths, AOI, "T048A-F015", tmp_path / "out", "PROVISIONAL", dem_sources=[dem])
    assert any("calculados con el DEM" in notice for notice in manifest["notices"])
    for pair in manifest["pairs"]:
        assert pair["stats"]["counts"]["terrain"] > 0
        assert pair["stats"]["counts"]["change_probable"] + pair["stats"]["counts"]["no_change"] > 0
    schema = json.loads((ROOT / "contracts" / "artifact-manifest.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(manifest, schema)


def test_pipeline_says_when_terrain_could_not_be_computed(series, tmp_path):
    paths, _ = series
    manifest = process_series(paths[:2], AOI, "T048A-F015", tmp_path, "PROVISIONAL", dem_sources=[tmp_path / "nada.tif"])
    assert any("no se marcaron: el recorte no trae radarGrid" in notice for notice in manifest["notices"])
    manifest = process_series(paths[:2], AOI, "T048A-F015", tmp_path, "PROVISIONAL")
    assert any("no se marcaron: no hay DEM" in notice for notice in manifest["notices"])
    assert all(pair["stats"]["counts"]["terrain"] == 0 for pair in manifest["pairs"])


def test_terrain_takes_precedence_and_blocks_change():
    terrain = np.zeros(SHAPE, bool)
    terrain[40:60, 40:60] = True
    looks = np.full(SHAPE, 20.0, np.float32)
    looks[50:70, 50:70] = 1
    before = scene(rng=np.random.default_rng(1))
    after = before.hh.copy()
    after[5:25, 5:25] *= 10  # +10 dB fuera del relieve: cambio
    after[40:60, 40:60] *= 10  # +10 dB sobre el relieve: no debe contarse como cambio
    result = compare(before, scene(hh=after, hv=before.hv.copy(), looks=looks), terrain=terrain)
    assert (result.state[terrain] == TERRAIN).all()
    assert result.state[65, 65] == LOW_LOOKS
    assert result.state[15, 15] == CHANGE_PROBABLE
    assert result.stats["counts"]["terrain"] == int(terrain.sum())


def test_terrain_is_skipped_when_radar_grid_uses_another_projection(tmp_path):
    spec = SeriesSpec(48, "A", 15, ("20260617", "20260629"))
    paths = generate_series(spec, BBOX, tmp_path / "raw", radar_grid=True)
    for path in paths:
        with h5py.File(path, "r+") as handle:
            handle["/science/LSAR/GCOV/metadata/radarGrid/projection"].attrs["epsg_code"] = 32614
    dem = tmp_path / "dem.tif"
    _write_dem(dem, BBOX, ridge_lon=-105.6)
    manifest = process_series(paths, AOI, "T048A-F015", tmp_path / "out", "PROVISIONAL", dem_sources=[dem])
    assert any("radarGrid está en EPSG:32614 y la malla en EPSG:32613" in notice for notice in manifest["notices"])
    assert all(pair["stats"]["counts"]["terrain"] == 0 for pair in manifest["pairs"])


def test_pipeline_publishes_the_dem_of_the_aoi_in_its_native_grid(series, tmp_path):
    paths, _ = series  # sin radarGrid: el relieve de la interfaz no depende de poder marcar layover
    dem = tmp_path / "dem.tif"
    _write_dem(dem, BBOX, ridge_lon=-105.6)
    manifest = process_series(paths[:2], AOI, "T048A-F015", tmp_path / "out", "PROVISIONAL", dem_sources=[dem])
    published = manifest["dem"]
    assert published["layer"] == "parral/dem.tif"
    assert published["vertical_datum"] == "EGM2008" and published["units"] == "m"
    assert "Copernicus" in published["attribution"]
    with rasterio.open(dem) as source, rasterio.open(tmp_path / "out" / published["layer"]) as cog:
        assert cog.crs == source.crs and published["crs"] == "EPSG:4326"
        assert cog.res == pytest.approx(source.res)  # sin remuestrear a la malla del radar
        west, south, east, north = cog.bounds
        assert west < BBOX[0] - 0.009 and south < BBOX[1] - 0.009 and east > BBOX[2] + 0.009 and north > BBOX[3] + 0.009
        assert west > BBOX[0] - 0.02 and north < BBOX[3] + 0.02  # recortado, no la tesela entera
        assert cog.overviews(1) and cog.profile.get("tiled")
        values = cog.read(1)
        assert np.isfinite(values).all() and values.max() > 1500
    schema = json.loads((ROOT / "contracts" / "artifact-manifest.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(manifest, schema)


def test_pipeline_omits_the_dem_when_there_is_none_or_it_does_not_cover_the_aoi(series, tmp_path):
    paths, _ = series
    assert "dem" not in process_series(paths[:2], AOI, "T048A-F015", tmp_path / "a", "PROVISIONAL")
    missing = process_series(paths[:2], AOI, "T048A-F015", tmp_path / "b", "PROVISIONAL", dem_sources=[tmp_path / "nada.tif"])
    assert "dem" not in missing
    far = tmp_path / "lejos.tif"
    _write_dem(far, [10.0, 10.0, 10.5, 10.5], ridge_lon=10.2)
    assert "dem" not in process_series(paths[:2], AOI, "T048A-F015", tmp_path / "c", "PROVISIONAL", dem_sources=[far])


def test_synthetic_dem_is_published_as_synthetic_and_never_as_copernicus(series, tmp_path):
    paths, _ = series
    dem = write_synthetic_dem(BBOX, tmp_path / "dem" / "synthetic_dem.tif")
    manifest = process_series(paths[:2], AOI, "T048A-F015", tmp_path / "out", "PROVISIONAL", dem_sources=[dem])
    published = manifest["dem"]
    assert published["data_kind"] == "synthetic" and "sintético" in published["source"]
    assert "Copernicus" not in published["attribution"] and published["vertical_datum"] == "none"
    with rasterio.open(tmp_path / "out" / published["layer"]) as cog:
        assert cog.res == pytest.approx((1 / 3600, 1 / 3600))
        values = cog.read(1)
        assert np.isfinite(values).all() and values.min() >= 1499 and values.max() <= 3001
    schema = json.loads((ROOT / "contracts" / "artifact-manifest.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(manifest, schema)


def test_real_dem_is_declared_real(series, tmp_path):
    paths, _ = series
    dem = tmp_path / "glo30.tif"
    _write_dem(dem, BBOX, ridge_lon=-105.6)
    published = process_series(paths[:2], AOI, "T048A-F015", tmp_path / "out", "PROVISIONAL", dem_sources=[dem])["dem"]
    assert published["data_kind"] == "real" and published["vertical_datum"] == "EGM2008"


def test_a_synthetic_dem_is_never_used_with_real_granules(tmp_path):
    spec = SeriesSpec(48, "A", 15, ("20260617", "20260629"))
    paths = generate_series(spec, BBOX, tmp_path / "raw", radar_grid=True)
    for path in paths:  # se hacen pasar por reales: con radarGrid, un DEM real marcaría relieve
        with h5py.File(path, "r+") as handle:
            handle.attrs["data_kind"] = "real"
    dem = write_synthetic_dem(BBOX, tmp_path / "dem" / "synthetic_dem.tif")
    manifest = process_series(paths, AOI, "T048A-F015", tmp_path / "out", "PROVISIONAL", dem_sources=[dem])
    assert manifest["data_kind"] == "real"
    assert "dem" not in manifest and not (tmp_path / "out" / "parral" / "dem.tif").exists()
    assert any("no se marcaron: no hay DEM" in notice for notice in manifest["notices"])
    assert all(pair["stats"]["counts"]["terrain"] == 0 for pair in manifest["pairs"])


SHIFT_2_DB = 10 ** (2 / 10)


def test_a_scene_wide_shift_is_not_local_change_and_is_published():
    before = scene(rng=np.random.default_rng(1))
    after = scene(hh=np.full(SHAPE, 0.05 * SHIFT_2_DB, np.float32), hv=np.full(SHAPE, 0.01 * SHIFT_2_DB, np.float32),
                  rng=np.random.default_rng(2))
    corrected = compare(before, after)
    assert corrected.stats["scene_shift_hh_db"] == pytest.approx(2, abs=0.3)
    assert corrected.stats["scene_shift_hv_db"] == pytest.approx(2, abs=0.3)
    assert corrected.stats["counts"]["change_probable"] == 0
    raw = compare(before, after, Params(correct_scene_shift=False))
    # Sin corrección no se publica: la presencia de scene_shift_* en el manifiesto significa "ya restado".
    assert "scene_shift_hh_db" not in raw.stats and "scene_shift_hv_db" not in raw.stats
    assert np.nanmedian(raw.change_hh) == pytest.approx(2, abs=0.3)
    assert abs(np.nanmedian(corrected.change_hh)) < 0.3


def test_local_change_on_top_of_a_scene_shift_is_still_found_with_its_size():
    before = scene(rng=np.random.default_rng(1))
    hh = np.full(SHAPE, 0.05 * SHIFT_2_DB, np.float32)
    hh[20:40, 20:40] *= 10 ** (6 / 10)  # +6 dB locales sobre +2 dB de toda la escena
    result = compare(before, scene(hh=hh, rng=np.random.default_rng(2)))
    assert result.state[30, 30] == CHANGE_PROBABLE and result.state[60, 60] == NO_CHANGE
    assert result.stats["mean_change_hh_db"] == pytest.approx(6, abs=1.0)


def test_low_looks_is_judged_on_the_window_not_on_single_pixels():
    looks = np.full(SHAPE, 4.0, np.float32)
    looks[10, 10] = 1.0  # un píxel suelto con pocos looks: la ventana suma de sobra
    looks[50:70, 50:70] = 1.0  # una zona entera con pocos looks: la ventana suma 25
    state = compare(scene(looks=looks, rng=np.random.default_rng(1)), scene(looks=looks, rng=np.random.default_rng(2))).state
    assert state[10, 10] != LOW_LOOKS
    assert state[60, 60] == LOW_LOOKS
    assert (state == LOW_LOOKS).sum() < 20 * 20 + 1


def _stack(n, changed=None):
    """n fechas de la misma superficie con speckle independiente; `changed` = índice de la fecha con +10 dB."""
    scenes = []
    for index in range(n):
        hh = np.ones(SHAPE, np.float32)
        if index == changed:
            hh[20:40, 20:40] *= 10
        scenes.append(scene(hh=hh, hv=hh.copy(), rng=np.random.default_rng(100 + index)))
    return scenes


def _filtered(scenes, window=7):
    valid = np.ones(SHAPE, bool)
    speckle = MultitemporalFilter(SHAPE, window)
    for item in scenes:
        speckle.add(item, valid)
    return [speckle.apply(item, valid) for item in scenes]


def test_multitemporal_filter_reduces_speckle_and_keeps_the_local_mean():
    scenes = _stack(8)
    valid = np.ones(SHAPE, bool)
    before = equivalent_looks(scenes[3].hh, valid, block=10)
    raw_mean = float(scenes[3].hh.mean())
    filtered = _filtered(scenes)
    after = equivalent_looks(filtered[3].hh, valid, block=10)
    assert after > 2 * before
    assert float(filtered[3].hh.mean()) == pytest.approx(raw_mean, rel=0.05)


def test_multitemporal_filter_keeps_a_change_in_its_date_and_barely_leaks_it():
    scenes = _stack(8, changed=5)
    filtered = _filtered(scenes)
    inside, outside = (slice(24, 36), slice(24, 36)), (slice(55, 75), slice(55, 75))
    gain = 10 * np.log10(filtered[5].hh[inside].mean() / filtered[5].hh[outside].mean())
    assert gain == pytest.approx(10, abs=1.0)
    for index in (0, 4, 7):
        leak = 10 * np.log10(filtered[index].hh[inside].mean() / filtered[index].hh[outside].mean())
        assert abs(leak) < 0.5, (index, leak)


def test_multitemporal_filter_leaves_invalid_pixels_untouched():
    scenes = _stack(3)
    valid = np.ones(SHAPE, bool)
    valid[:, :10] = False
    speckle = MultitemporalFilter(SHAPE)
    original = scenes[1].hh.copy()
    for item in scenes:
        speckle.add(item, valid)
    out = speckle.apply(scenes[1], valid)
    assert np.array_equal(out.hh[:, :10], original[:, :10])
    assert not np.array_equal(out.hh[:, 20:], original[:, 20:])


def test_pipeline_with_multitemporal_declares_it_and_still_finds_the_wetting(series, tmp_path):
    paths, _ = series
    params = Params(multitemporal=True)
    manifest = process_series(paths, AOI, "T048A-F015", tmp_path, "PROVISIONAL", params)
    assert any("Filtro multitemporal" in notice and f"{len(paths)} fechas" in notice for notice in manifest["notices"])
    full = next(pair for pair in manifest["pairs"] if pair["kind"] == "full_window")
    assert full["stats"]["counts"]["change_probable"] > 0
    schema = json.loads((ROOT / "contracts" / "artifact-manifest.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(manifest, schema)
    plain = process_series(paths, AOI, "T048A-F015", tmp_path / "plain", "PROVISIONAL")
    assert not any("Filtro multitemporal" in notice for notice in plain["notices"])


def test_excluded_granules_come_from_every_series_of_the_aoi():
    aoi = {"series": [{"id": "a"}, {"id": "b", "exclude": [{"granule": "G1", "reason": "product_defect"}, {"granule": "G2"}]}]}
    assert excluded_granules(aoi) == {"G1": "product_defect", "G2": "sin motivo"}
    assert excluded_granules({"series": [{"id": "a", "exclude": None}]}) == {}


def test_parral_config_excludes_t171_august_13_if_declared():
    import yaml

    aoi = yaml.safe_load((ROOT / "config" / "aois" / "parral.yaml").read_text(encoding="utf-8"))
    bad = "NISAR_L2_PR_GCOV_027_171_D_075_4005_DHDH_A_20260813T014433_20260813T014508_P05023_N_F_J_001"
    assert excluded_granules(aoi)[bad] == "product_defect"  # lo declaró Antena en el PR 22


def test_pipeline_skips_excluded_granules_by_their_internal_id_and_says_so(series, tmp_path):
    paths, _ = series
    bad = read_meta_path(paths[1])
    renamed = tmp_path / "renombrado.h5"  # el nombre en disco no importa
    shutil.copy(paths[1], renamed)
    inputs = [paths[0], renamed, *paths[2:]]
    manifest = process_series(inputs, AOI, "T048A-F015", tmp_path / "out", "PROVISIONAL",
                              exclude={bad.granule_id: "product_defect"})
    assert bad.date not in [item["date"] for item in manifest["dates"]]
    assert len(manifest["dates"]) == len(paths) - 1
    assert all(bad.granule_id not in pair["granules"] for pair in manifest["pairs"])
    assert any(f"{bad.date} (product_defect)" in notice for notice in manifest["notices"])


def test_excluded_granule_is_skipped_by_name_without_opening_it(series, tmp_path):
    paths, _ = series
    bad = read_meta_path(paths[1])
    corrupt = tmp_path / f"{bad.granule_id}.h5"  # mismo nombre que escribe ingest, pero el archivo está roto
    corrupt.write_bytes(b"no es un HDF5")
    inputs = [paths[0], corrupt, *paths[2:]]
    manifest = process_series(inputs, AOI, "T048A-F015", tmp_path / "out", "PROVISIONAL",
                              exclude={bad.granule_id: "product_defect"})
    assert len(manifest["dates"]) == len(paths) - 1
    assert any(f"{bad.date} (product_defect)" in notice for notice in manifest["notices"])


def test_a_corrupt_granule_that_is_not_excluded_still_fails(series, tmp_path):
    paths, _ = series
    corrupt = tmp_path / "otro.h5"
    corrupt.write_bytes(b"no es un HDF5")
    with pytest.raises(OSError):
        process_series([paths[0], corrupt, *paths[2:]], AOI, "T048A-F015", tmp_path / "out", "PROVISIONAL", exclude={})


def test_pair_publishes_the_spread_of_the_difference_whatever_the_shift_correction():
    before = scene(rng=np.random.default_rng(1))
    after = scene(hh=np.full(SHAPE, 0.05 * SHIFT_2_DB, np.float32), hv=np.full(SHAPE, 0.01 * SHIFT_2_DB, np.float32),
                  rng=np.random.default_rng(2))
    corrected = compare(before, after)
    raw = compare(before, after, Params(correct_scene_shift=False))
    for name in ("noise_hh_db", "noise_hv_db"):
        assert corrected.stats[name] > 0
        # Restar una constante no cambia la MAD: el valor es el mismo con corrección o sin ella.
        assert raw.stats[name] == pytest.approx(corrected.stats[name], abs=1e-3)
        assert corrected.stats[name] == pytest.approx(raw.stats[name], rel=1e-3)
    d = corrected.change_hh[np.isfinite(corrected.change_hh)]
    assert corrected.stats["noise_hh_db"] == pytest.approx(1.4826 * np.median(np.abs(d - np.median(d))), rel=0.05)


def test_spread_grows_with_speckle_and_is_none_without_observable_pixels():
    calm = compare(scene(rng=np.random.default_rng(1)), scene(rng=np.random.default_rng(2)))
    extra = np.random.default_rng(3).gamma(2, 0.5, SHAPE).astype(np.float32)  # speckle de 2 looks encima
    noisy = compare(scene(rng=np.random.default_rng(1)), scene(hh=0.05 * extra, rng=np.random.default_rng(2)))
    assert noisy.stats["noise_hh_db"] > 1.5 * calm.stats["noise_hh_db"]
    assert noisy.stats["noise_hv_db"] == pytest.approx(calm.stats["noise_hv_db"], rel=0.05)
    blind = compare(scene(mask=np.zeros(SHAPE, np.uint8), rng=np.random.default_rng(1)),
                    scene(mask=np.zeros(SHAPE, np.uint8), rng=np.random.default_rng(2)))
    assert blind.stats["noise_hh_db"] is None and blind.stats["noise_hv_db"] is None


def test_vegetation_signatures_hv_up_or_down_with_hh_stable():
    from processor.change import signature_counts

    hh = np.array([0.5, -0.5, 3.0, 0.0, -3.0, 0.1], np.float32)
    hv = np.array([3.0, -3.0, 0.0, 0.0, -3.0, 2.5], np.float32)
    c = signature_counts(hh, hv)
    assert c["hv_up_hh_stable"] == 2 and c["hv_down_hh_stable"] == 1
    assert c["hh_up_hv_stable"] == 1 and c["hh_down_hv_down"] == 1 and c["other"] == 1


def test_resign_updates_existing_manifests_from_their_cogs(tmp_path):
    import json

    import rasterio
    from rasterio.transform import from_origin

    from processor.resign import resign_all

    pair_dir = tmp_path / "z" / "S" / "pairs" / "a_b"
    pair_dir.mkdir(parents=True)
    profile = dict(driver="GTiff", width=3, height=1, count=1, crs="EPSG:32613", transform=from_origin(0, 0, 10, 10))
    for name, data, dtype in (("state", [[1, 1, 0]], "uint8"), ("change_hh", [[0.0, 0.2, 5.0]], "float32"), ("change_hv", [[3.0, -4.0, 5.0]], "float32")):
        with rasterio.open(pair_dir / f"{name}.tif", "w", dtype=dtype, **profile) as dst:
            dst.write(np.array(data, dtype), 1)
    layers = {k: f"z/S/pairs/a_b/{k}.tif" for k in ("state", "change_hh", "change_hv")}
    manifest = tmp_path / "z" / "S" / "manifest.json"
    manifest.write_text(json.dumps({"pairs": [{"layers": layers, "stats": {"signature_counts": {"other": 2}}}]}), encoding="utf-8")
    assert resign_all(tmp_path) == {"z\S\manifest.json" if "\\" in str(tmp_path) else "z/S/manifest.json": 1}
    counts = json.loads(manifest.read_text(encoding="utf-8"))["pairs"][0]["stats"]["signature_counts"]
    assert counts["hv_up_hh_stable"] == 1 and counts["hv_down_hh_stable"] == 1 and counts["other"] == 0
