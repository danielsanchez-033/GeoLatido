"""Prueba de lenguaje (RF-BAL-03): ningún texto afirma causas, daños ni confirmaciones.

Revisa los textos de dos formas complementarias:

1. Todos los literales de cadena de los módulos que redactan (sin docstrings), para
   que una rama nueva de una plantilla no se escape aunque ninguna prueba la ejecute.
2. Los textos ya renderizados con todas las combinaciones de estado, causa, tipo de par,
   hueco, latencia, idioma y sintético, para atrapar frases armadas con variables.

Para corregir la lista, edita FORBIDDEN. Si una frase concreta debe permitirse, añádela a
ALLOWED con su motivo y anótalo en specs/03-balanza/plan.md: queda revisable en el PR.
"""
from __future__ import annotations

import ast
import itertools
import re
import unicodedata
from pathlib import Path

import pytest

from verdicts import narrative, rules

SOURCES = [Path(narrative.__file__), Path(narrative.__file__).with_name("main.py")]

# Patrones sobre texto en minúsculas y sin tildes (ver _normalize): "daño" se busca como "dano".
FORBIDDEN = {
    "confirmación": r"\bconfirm\w*",  # confirmado, confirma, confirmación; confirmed, confirms
    "causa afirmada (es)": r"\b(causad|provocad|ocasionad|originad)[oa]s? por\b",
    "causa afirmada (en)": r"\b(caused|triggered|produced) by\b",
    # Voz activa: "la tormenta causó el cambio". "causa" sola no, porque es el sustantivo de "no identifica la causa".
    "causa en voz activa (es)": (
        r"\b(causo|causaron|provocan?|provoco|provocaron|ocasionan?|ocasiono|ocasionaron|origino|originaron)\b"
    ),
    "causa en voz activa (en)": r"\bcaused\b",
    "debido a": r"\bdebid[oa]s? a\b",
    "se debe a": r"\bse deben? a\b",
    "a causa de": r"\b(a causa|por culpa) de\b",
    "due to": r"\bdue to\b",
    "because of": r"\b(because of|as a result of)\b",
    "daño (es)": r"\bdan(o|os|ad[oa]s?|ar|an|aron|en|ino\w*)\b",
    "damage (en)": r"\bdamag\w*",
    "destrucción (es)": r"\bdestru\w*",
    "destruction (en)": r"\bdestr(oy|uct)\w*",
    "certeza (es)": r"\b(sin (ninguna )?duda|definitivamente|con (total )?certeza|indudablemente)\b",
    "certeza (en)": r"\b(without (a )?doubt|undoubtedly|definitely|certainly)\b",
}

# Frases exactas permitidas pese a contener un patrón prohibido, con su motivo. Vacía a propósito.
ALLOWED: dict[str, str] = {}


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def violations(text: str) -> list[str]:
    clean = _normalize(text)
    for phrase in ALLOWED:
        clean = clean.replace(_normalize(phrase), " ")
    return [name for name, pattern in FORBIDDEN.items() if re.search(pattern, clean)]


def _docstrings(tree: ast.AST) -> set[int]:
    ids = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                ids.add(id(body[0].value))
    return ids


def literal_texts() -> list[tuple[str, str]]:
    found = []
    for path in SOURCES:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        skip = _docstrings(tree)
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in skip:
                found.append((f"{path.name}:{node.lineno}", node.value))
    return found


def _decisions() -> list[rules.Decision]:
    states = [rules.Decision(rules.CHANGE_PROBABLE, None, 0.9, 0.12),
              rules.Decision(rules.NO_DETECTABLE_CHANGE, None, 0.95, 0.0),
              # Por debajo de MIN_CHANGED_FRACTION, pero con píxeles sobre el umbral (T-BAL-09).
              rules.Decision(rules.NO_DETECTABLE_CHANGE, None, 0.95, 0.03)]
    states += [rules.Decision(rules.NOT_OBSERVABLE, cause, 0.2, 0.0) for cause in rules.UNOBSERVABLE_CAUSES]
    return states


def _event_statuses() -> list[rules.EventStatus]:
    from datetime import date

    before, after = date(2026, 6, 29), date(2026, 7, 8)
    return [
        rules.EventStatus(rules.OBSERVABLE, None, before, after),
        rules.EventStatus(rules.OBSERVABLE, None, before, after, seen_by=after),
        rules.EventStatus(rules.NOT_OBSERVABLE, "no_acquisition_during_event", before, after),
        rules.EventStatus(rules.NOT_OBSERVABLE, "timing_uncertain", before, after),
        rules.EventStatus(rules.NOT_OBSERVABLE, "outside_series_window", before, None),
        rules.EventStatus(rules.NOT_OBSERVABLE, "outside_series_window", None, after),
    ]


# T-BAL-06: cada origen de la persistencia supuesta, con cada tipo de evento.
PERSISTENCES = [None, rules.persistence(None, None), rules.persistence(None, 30)] + [
    rules.persistence(kind, None) for kind in rules.PERSISTENCE_BY_EVENT_TYPE
]

LATENCIES = [("available", 37.3)] + [(status, None) for status in narrative.LATENCY_UNKNOWN["es"]]


def rendered_texts() -> list[tuple[str, dict]]:
    """Cada resumen posible, con una etiqueta que dice qué combinación lo produjo."""
    found = []
    for lang, synthetic in itertools.product(("es", "en"), (True, False)):
        for decision, kind, gap, days, (status, hours) in itertools.product(
            _decisions(), ("consecutive", "full_window"), (True, False), (1, 12), LATENCIES
        ):
            summary = narrative.pair_summary(
                decision, "2026-06-29", "2026-07-11", gap, lang, synthetic, interval_days=days,
                age_days=days, latency_hours=hours, latency_status=status, kind=kind,
            )
            found.append((f"pair {lang} {decision.state}/{decision.cause} {kind} gap={gap} {status}", summary))
        for status, assumed in itertools.product(_event_statuses(), PERSISTENCES):
            summary = narrative.event_summary(status, "2026-07-01", lang, synthetic, assumed)
            source = assumed.source if assumed else "none"
            found.append((f"event {lang} {status.state}/{status.cause} {source}/{assumed and assumed.event_type}", summary))
    for lang, before, after in itertools.product(("es", "en"), OPTICAL_SIDES, OPTICAL_SIDES):
        text = narrative.optical_text(before, after, lang, max_cloud=30.0, search_days=10)
        found.append((f"optical {lang} {before[0]}/{after[0]}", {"optical": text}))
    found += water_texts()
    # T-BAL-07: fechas marcadas por el QA de Eco y desplazamiento de la escena, en cada sentido.
    for lang in ("es", "en"):
        for hh, hv in ((1.89, 1.6), (-2.1, None), (None, None)):
            text = narrative.quality_flag_text("2026-10-15", hh, hv, 1.5, lang)
            found.append((f"qa {lang} {hh}/{hv}", {"qa": text}))
        for (hh, hv, same), corrected in itertools.product(
            ((1.8, 1.7, True), (-1.9, 0.4, False), (None, 2.0, None)), (False, True)
        ):
            text = narrative.scene_shift_text(hh, hv, same, lang, corrected)
            found.append((f"shift {lang} {hh}/{hv}/{same} corrected={corrected}", {"shift": text}))
        # Pasadas excluidas por catalog: motivo conocido y desconocido, dentro del par o usada por él.
        for reason, used in itertools.product(("product_defect", "otro_motivo"), (True, False)):
            text = narrative.excluded_pass_text("2026-08-13", reason, used, lang)
            found.append((f"excluded {lang} {reason} used={used}", {"excluded": text}))
    return found


# T-BAL-08: cada estado del contraste con DSWx-S1, con producto antes, el mismo día y después.
WATER_SIDES = [{"status": "catalog_unavailable"}, {"status": "none_in_window"}] + [
    {"status": status, "product_date": "2026-06-27", "days": days, "compared": 0.211, "minimum": 0.5}
    for status in narrative.WATER_NOT_COMPARED["es"]
    for days in (-2, 0, 3)
] + [
    {"status": "compared", "product_date": "2026-06-27", "days": -2, "assessment": assessment, "basis": basis,
     "iou": iou, "radar": radar, "reference": reference}
    for assessment, basis, iou, radar, reference in (
        ("agree", "little_water", None, 0.0, 0.0004),
        ("agree", "water_overlap", 0.71, 0.021, 0.018),
        ("disagree", "water_overlap", 0.0, 0.012, 0.0),
        ("disagree", "water_overlap", 0.23, 0.04, 0.009),
    )
]


def water_texts() -> list[tuple[str, dict]]:
    found = []
    for lang, before, after in itertools.product(("es", "en"), WATER_SIDES, WATER_SIDES):
        text = narrative.water_text(
            before, after, lang, search_days=7, min_water_body_ha=3, min_water_body_width_m=200,
            hh_db=-15.0, hv_db=-23.0,
        )
        label = f"water {lang} {before['status']}/{before.get('assessment')} {after['status']}/{after.get('assessment')}"
        found.append((label, {"water": text}))
    return found


# RF-BAL-07: un desacuerdo con DSWx-S1 se presenta como desacuerdo entre métodos, nunca como error de una fuente.
ERROR_WORDS = r"\b(error\w*|erróne\w*|erroneo\w*|incorrect\w*|equivoc\w*|fall[oóaeé]\w*|wrong|mistak\w*|fail\w*|false)\b"


def test_water_disagreement_is_never_called_an_error():
    failures = [
        f"{label}: {summary['water']!r}"
        for label, summary in water_texts()
        if re.search(ERROR_WORDS, _normalize(summary["water"]))
    ]
    assert not failures, "\n".join(failures)
    disagree = [s["water"] for label, s in water_texts() if "compared/disagree" in label]
    assert disagree and all(
        "desacuerdo entre dos métodos" in text or "disagreement between two methods" in text for text in disagree
    )


@pytest.mark.parametrize("bad", ["El radar se equivoca.", "DSWx-S1 tiene un error.", "The radar is wrong.",
                                 "The product failed.", "La máscara falla."])
def test_error_checker_catches_error_wording(bad):
    assert re.search(ERROR_WORDS, _normalize(bad))


# T-BAL-04: cada estado del contraste óptico, con escena el mismo día y con días de distancia.
OPTICAL_SIDES = [
    ("catalog_unavailable", None, None, None),
    ("none_in_window", None, None, None),
] + [
    (status, "2026-06-28", days, 26.6)
    for status in ("clear", "cloudy", "partial_coverage")
    for days in (0, 1, 4)
]


def test_rendering_covers_every_cause_and_latency_in_both_languages():
    # Si alguien añade una causa o un estado de latencia, debe aparecer en las plantillas de ambos idiomas.
    for table in (narrative.CAUSES, narrative.HYPOTHESES, narrative.LATENCY_UNKNOWN, narrative.EVENT_TYPES):
        assert table["es"].keys() == table["en"].keys()
    assert narrative.EVENT_TYPES["es"].keys() == rules.PERSISTENCE_BY_EVENT_TYPE.keys()
    assert set(rules.UNOBSERVABLE_CAUSES) <= narrative.CAUSES["es"].keys()
    assert set(rules.SIGNATURE_HYPOTHESIS.values()) == narrative.HYPOTHESES["es"].keys()


@pytest.mark.parametrize("where, text", literal_texts(), ids=lambda value: value if ":" in str(value) else None)
def test_no_literal_asserts_causes_damage_or_confirmation(where, text):
    assert not violations(text), f"{where}: {text!r} contiene {violations(text)}"


def test_no_rendered_summary_asserts_causes_damage_or_confirmation():
    failures = [
        f"{label} [{field}]: {text!r} -> {violations(text)}"
        for label, summary in rendered_texts()
        for field, text in summary.items()
        if violations(text)
    ]
    assert not failures, "\n".join(failures)


@pytest.mark.parametrize("bad", [
    "El cambio está confirmado.",
    "Cambio causado por la tormenta.",
    "Hay daño en las calles.",
    "Se observan DAÑOS en la zona.",
    "Inundación provocada por el río.",
    "Debido a la lluvia, cambió la señal.",
    "Confirmed flooding.",
    "Change caused by the storm.",
    "The storm damaged the road.",
    "Due to the rain, the signal changed.",
    "Sin duda hubo un cambio.",
    # Causas en voz activa (revisión del PR 17).
    "La tormenta causó el cambio.",
    "La lluvia provocó la inundación.",
    "Las lluvias provocaron el cambio.",
    "El río ocasionó la crecida.",
    "El cambio se debe a la lluvia.",
    "A causa de la tormenta, cambió la señal.",
    "Por culpa de la lluvia cambió la señal.",
    "Se dañaron las calles.",
    "The storm caused the change.",
    "The signal changed because of the storm.",
    "As a result of the rain, the signal changed.",
])
def test_checker_catches_forbidden_language(bad):
    assert violations(bad)


@pytest.mark.parametrize("fine", [
    "Hipótesis: más humedad en superficie.",
    "No identifica la causa.",
    "It does not identify the cause.",
    "Se dan dos fechas.",  # "dan" no es "daño"
    "La causa no se conoce.",  # el sustantivo "causa" se permite
    "The cause is unknown.",
])
def test_checker_allows_hypotheses_and_plain_negations(fine):
    assert not violations(fine)


def test_every_synthetic_text_carries_its_prefix_and_real_ones_do_not():
    prefixes = tuple(narrative.SYNTHETIC_PREFIX.values())
    # El prefijo va solo al inicio de "detected"; los demás campos nunca lo llevan. El texto óptico
    # tampoco: las escenas Sentinel-2 son reales aunque el radar sea sintético.
    for label, summary in rendered_texts():
        for field, text in summary.items():
            if field != "detected":
                assert not text.startswith(prefixes), f"{label} [{field}]"
    for lang in ("es", "en"):
        for decision in _decisions():
            args = dict(interval_days=12, age_days=3, latency_hours=None, latency_status="synthetic")
            fake = narrative.pair_summary(decision, "2026-06-29", "2026-07-11", False, lang, True, **args)
            real = narrative.pair_summary(decision, "2026-06-29", "2026-07-11", False, lang, False, **args)
            assert fake["detected"] == narrative.SYNTHETIC_PREFIX[lang] + real["detected"]
            assert not real["detected"].startswith(prefixes)
        for status in _event_statuses():
            fake = narrative.event_summary(status, "2026-07-01", lang, True)
            real = narrative.event_summary(status, "2026-07-01", lang, False)
            assert fake["detected"] == narrative.SYNTHETIC_PREFIX[lang] + real["detected"]
