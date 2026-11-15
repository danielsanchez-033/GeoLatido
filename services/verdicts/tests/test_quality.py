"""QA de Eco en el veredicto (T-BAL-07, RF-BAL-09) y aviso de desplazamiento de la escena."""
import json

import jsonschema
import pytest
from fastapi.testclient import TestClient

from test_verdicts import CODES, ROOT, VERDICT, _clock, counts, manifest_root  # noqa: F401  (fixture)
from verdicts import quality
from verdicts.main import create_app


def _qa(median_hh, median_hv, deviation_hh=0.0, deviation_hv=0.0, flagged=False):
    return {
        "valid_fraction": 0.85, "median_hh_db": median_hh, "median_hv_db": median_hv,
        "deviation_hh_db": deviation_hh, "deviation_hv_db": deviation_hv,
        "flags": ["radiometric_outlier"] if flagged else [],
    }


def _with_qa(manifest_root, before, after, **pair_changes):
    path = manifest_root / "parral/T048A-F015/manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    for item, qa in zip(manifest["dates"], (before, after)):
        if qa is not None:
            item["qa"] = qa
    manifest["pairs"][0].update(pair_changes)
    schema = json.loads((ROOT / "contracts" / "artifact-manifest.schema.json").read_text(encoding="utf-8"))
    allowed = schema["properties"]["pairs"]["items"]["properties"]["stats"]["properties"]
    # stats.scene_shift_* llegan con el PR 39 de Eco. Hasta que el esquema los tenga, se valida sin ellos;
    # después, esta comprobación vuelve a cubrir el manifiesto completo sin tocar nada.
    checked = json.loads(json.dumps(manifest))
    for name in ("scene_shift_hh_db", "scene_shift_hv_db"):
        if name not in allowed:
            checked["pairs"][0]["stats"].pop(name, None)
    jsonschema.validate(checked, schema)
    path.write_text(json.dumps(manifest), encoding="utf-8")


def _get(manifest_root, lang="es"):
    return TestClient(create_app(manifest_root, clock=_clock)).get(VERDICT, params={"lang": lang}).json()


# Como 10-03 → 10-15 en T048 real (MEMORY.md): toda la escena sube unos 1,8 dB y Eco marca la segunda fecha.
MONSOON = (_qa(-11.2, -18.9), _qa(-9.4, -17.1, 1.89, 1.6, flagged=True))


def test_scene_shift_is_the_difference_of_medians():
    shift = quality.scene_shift(*MONSOON)
    assert shift.hh_db == pytest.approx(1.8) and shift.hv_db == pytest.approx(1.8)
    assert shift.same_direction is True and shift.exceeds_threshold is True


@pytest.mark.parametrize("hh, hv, same, exceeds", [
    (-10.5, -18.0, True, False),   # +0,7 dB: como los pares de 2-3 % de cambio
    (-12.8, -16.0, False, True),   # HH baja, HV sube 2,9 dB
    (-11.2, -18.9, None, False),   # no se movió
    (-9.7, -18.9, None, False),    # justo 1,5 dB: el umbral es estricto, como el QA de Eco
])
def test_scene_shift_threshold_and_direction(hh, hv, same, exceeds):
    shift = quality.scene_shift(_qa(-11.2, -18.9), _qa(hh, hv))
    assert shift.same_direction is same and shift.exceeds_threshold is exceeds


def test_missing_qa_or_median_gives_no_shift():
    assert quality.scene_shift(None, MONSOON[1]) is None
    shift = quality.scene_shift(_qa(None, -18.9), _qa(-9.0, -17.0))
    assert shift.hh_db is None and shift.same_direction is None and shift.exceeds_threshold is True


def test_monsoon_pair_warns_in_text_evidence_and_receipt(manifest_root):
    _with_qa(manifest_root, *MONSOON)
    body = _get(manifest_root)
    assert body["state"] == "change_probable"  # el aviso no cambia el estado
    shift = body["evidence"]["scene_shift"]
    assert shift["exceeds_threshold"] is True and shift["same_direction"] is True
    assert shift["threshold_db"] == 1.5 and shift["calibrated"] is False
    assert shift["basis"] == "qa_median_difference"
    assert "cambió el nivel de toda la escena (mediana de HH +1,8 dB y de HV +1,8 dB, en el mismo sentido)" in body["summary"]["does_not_prove"]
    assert "no un cambio local" in body["summary"]["does_not_prove"]
    assert "El control de calidad marca la imagen del 2026-07-11" in body["summary"]["missing"]
    assert "2026-06-29" not in body["summary"]["missing"].split("El control de calidad")[-1]
    receipt = body["receipt"]["quality"]
    assert receipt["source"] == "manifest_qa"
    assert receipt["before"]["flags"] == [] and receipt["after"]["flags"] == ["radiometric_outlier"]
    assert receipt["after"]["deviation_hh_db"] == 1.89


def test_monsoon_pair_in_english(manifest_root):
    _with_qa(manifest_root, *MONSOON)
    body = _get(manifest_root, "en")
    assert "The level of the whole scene changed" in body["summary"]["does_not_prove"]
    assert "Quality control flags the 2026-07-11 image" in body["summary"]["missing"]


def test_small_shift_keeps_the_text_unchanged(manifest_root):
    plain = _get(manifest_root)["summary"]
    _with_qa(manifest_root, _qa(-11.2, -18.9), _qa(-10.5, -18.3))
    body = _get(manifest_root)
    assert body["summary"] == plain
    assert body["evidence"]["scene_shift"]["exceeds_threshold"] is False
    assert body["receipt"]["quality"]["after"]["median_hh_db"] == -10.5


def test_manifest_without_qa_declares_it(manifest_root):
    body = _get(manifest_root)
    assert body["evidence"]["scene_shift"] is None
    assert body["receipt"]["quality"] == {"source": "manifest_qa", "before": None, "after": None}


def test_not_observable_pair_does_not_talk_about_the_shift(manifest_root):
    _with_qa(manifest_root, *MONSOON, stats={
        "counts": counts(no_change=100, low_looks=900), "signature_counts": {}, "threshold_hh_db": None,
        "threshold_hv_db": None, "mean_change_hh_db": None, "mean_change_hv_db": None,
    })
    body = _get(manifest_root)
    assert body["state"] == "not_observable"
    assert "toda la escena" not in body["summary"]["does_not_prove"]
    assert "El control de calidad marca" in body["summary"]["missing"]  # la fecha marcada se avisa igual
    assert body["evidence"]["scene_shift"]["exceeds_threshold"] is True


# --- Cambio ya corregido por processor (PR 39 de Eco, T-ECO-07) ------------------------------

# T171 09-18 -> 09-30 real: +2,29 dB en HH; corregido queda un 2,3 % de cambio local.
CORRECTED_STATS = {
    "counts": counts(no_change=977, change_probable=23), "signature_counts": {"hh_up_hv_up": 23},
    "threshold_hh_db": 3.0, "threshold_hv_db": 3.0, "mean_change_hh_db": 3.4, "mean_change_hv_db": 3.1,
    "scene_shift_hh_db": 2.29, "scene_shift_hv_db": 1.9,
}


def test_stats_shift_wins_over_qa_and_is_declared_corrected(manifest_root):
    _with_qa(manifest_root, *MONSOON, stats=CORRECTED_STATS)
    body = _get(manifest_root)
    shift = body["evidence"]["scene_shift"]
    assert shift["basis"] == "pair_stats" and shift["corrected"] is True
    assert shift["hh_db"] == 2.29 and shift["exceeds_threshold"] is True
    text = body["summary"]["does_not_prove"]
    assert "Ese desplazamiento general se descontó antes de medir el cambio" in text
    assert "puede reflejar ese desplazamiento" not in text
    english = _get(manifest_root, "en")["summary"]["does_not_prove"]
    assert "That general shift was removed before measuring change" in english


def test_stats_shift_works_without_qa(manifest_root):
    _with_qa(manifest_root, None, None, stats=CORRECTED_STATS)
    shift = _get(manifest_root)["evidence"]["scene_shift"]
    assert shift["basis"] == "pair_stats" and shift["corrected"] is True


def test_qa_shift_is_declared_uncorrected(manifest_root):
    _with_qa(manifest_root, *MONSOON)
    shift = _get(manifest_root)["evidence"]["scene_shift"]
    assert shift["basis"] == "qa_median_difference" and shift["corrected"] is False


# --- MIN_CHANGED_FRACTION del 5 %, fijado con el ruido de pares reales (T-BAL-09) -------------------------------------

def test_below_five_percent_is_no_detectable_change_and_says_why(manifest_root):
    _with_qa(manifest_root, None, None, stats=CORRECTED_STATS)
    body = _get(manifest_root)
    assert body["state"] == "no_detectable_change"
    assert body["evidence"]["decision_rule"] == {
        "min_observed_fraction": 0.5, "min_changed_fraction": 0.05, "calibrated": False,
    }
    detected = body["summary"]["detected"]
    assert "el radar notó cambios en el 2,3 % de lo que pudo ver en Hidalgo del Parral. Es menos del 5 % que hace falta para hablar de un cambio" in detected
    assert "Ese 5 % se fijó con 16 pares reales de esta misma zona" in detected
    assert "sin calibrar" not in detected
    english = _get(manifest_root, "en")["summary"]["detected"]
    assert "what it could see in Hidalgo del Parral. That is less than the 5 % needed to call it a change" in english
    assert "set with 16 real pairs from this same area" in english and "uncalibrated" not in english


def test_other_zones_are_named_and_say_the_minimum_comes_from_parral(tmp_path, monkeypatch):
    """Una zona procesada en línea: el texto habla de ella, no de Parral, y dice de dónde sale el mínimo."""
    from verdicts import narrative

    (tmp_path / "z-guadalajara-jalisco-e9f150.yaml").write_text("id: z-guadalajara-jalisco-e9f150\nname: Guadalajara, Jalisco\n", encoding="utf-8")
    monkeypatch.setattr(narrative, "ONLINE_ZONES", tmp_path)
    assert narrative.zone_name("z-guadalajara-jalisco-e9f150") == "Guadalajara, Jalisco"
    assert narrative.zone_name("../secreto") is None and narrative.zone_name("z-no-existe") is None
    es = narrative._calibration("z-guadalajara-jalisco-e9f150", "es")
    assert "16 pares reales de Hidalgo del Parral, la zona de referencia" in es and "aquí se aplica sin calibrar" in es
    assert narrative._where("Guadalajara, Jalisco", "es") == " en Guadalajara, Jalisco"
    assert narrative._where(None, "en") == " of the area"


def test_t048_pair_at_9_6_percent_stays_change_probable(manifest_root):
    # T048 08-28 -> 09-09, el único par consecutivo real que queda alto tras corregir.
    stats = dict(CORRECTED_STATS, counts=counts(no_change=904, change_probable=96), scene_shift_hh_db=1.61)
    _with_qa(manifest_root, None, None, stats=stats)
    body = _get(manifest_root)
    assert body["state"] == "change_probable" and body["evidence"]["changed_fraction"] == pytest.approx(0.096)



def test_vegetation_hypotheses_are_plain_and_carry_their_share():
    from verdicts import narrative, rules

    shares = rules.signature_shares({"hv_up_hh_stable": 60, "hh_up_hv_up": 30, "other": 10})
    assert [n for n, _ in shares] == ["vegetation_growth", "more_vegetation_wetting_or_water_retreat"]
    text = narrative.hypothesis_text(*shares[0], "es")
    assert text.startswith("Posible explicación para el 60 % de lo que cambió: Crecieron plantas, cultivos o árboles")
    assert narrative.hypothesis_text("vegetation_loss", 0.25, "en").startswith("Possible explanation for 25 % of what changed: Plants, crops or trees were lost")
