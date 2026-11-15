"""De una pregunta en lenguaje natural a un plan de investigación.

Reglas deterministas (español e inglés), sin modelo de lenguaje: así cada decisión del plan se puede explicar.
Lo que no se entiende no se adivina: queda en `unresolved` para que la persona lo elija a mano.
"""
from __future__ import annotations

import datetime as dt
import re

from .places import find_in_text, norm
from .products import products_for

PHENOMENA: dict[str, tuple[str, ...]] = {
    "mining": ("miner", "mina", "minas", "jales", "relave", "tailings", "mining", "mine "),
    "flood": ("inund", "flood", "agua", "water", "lluvia", "lluvias", "tormenta", "storm", "rain", "precipit", "hidrolog"),
    "landslide": ("desliz", "deslave", "landslide", "ladera", "pendiente", "slope", "inestab", "derrumbe"),
    "deformation": ("deformac", "subsiden", "hundimiento", "deformation", "subsidence", "desplazamiento del terreno", "insar"),
    "glacier": ("glaciar", "glacier", "hielo", "ice ", "groenlandia", "greenland", "retroceso glaciar"),
}

PROFILE_FOR: dict[str, str] = {
    "mining": "mining_terrain",
    "flood": "flood_hydrology",
    "landslide": "landslide_slope",
    "deformation": "landslide_slope",
    "glacier": "glacier_climate",
}

WORD_NUMBERS = {
    "un": 1, "uno": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6, "siete": 7, "ocho": 8, "nueve": 9,
    "diez": 10, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}

COMPARE = ("compar", "versus", " vs ", "frente a", "diferencias entre", "difference between", "differences between")


def _period(t: str, today: dt.date) -> tuple[dt.date | None, dt.date | None, str | None]:
    m = re.search(r"(?:entre|between|de|from)\s+(19|20)(\d{2})\s+(?:y|a|and|to|-)\s+(19|20)(\d{2})", t)
    if m:
        a, b = int(m.group(1) + m.group(2)), int(m.group(3) + m.group(4))
        return dt.date(min(a, b), 1, 1), min(dt.date(max(a, b), 12, 31), today), "explicit_years"
    m = re.search(r"(?:ultim[oa]s|last|past)\s+(\d+|\w+)\s+(anos|ano|years|year|meses|months)", t)
    if m:
        n = int(m.group(1)) if m.group(1).isdigit() else WORD_NUMBERS.get(m.group(1))
        if n:
            days = n * (30 if m.group(2).startswith(("mes", "month")) else 365)
            return today - dt.timedelta(days=days), today, "relative"
    m = re.search(r"\b(?:en|in|durante|during)\s+(19|20)(\d{2})\b", t)
    if m:
        y = int(m.group(1) + m.group(2))
        return dt.date(y, 1, 1), min(dt.date(y, 12, 31), today), "single_year"
    m = re.search(r"\bdesde\s+(19|20)(\d{2})\b|\bsince\s+(19|20)(\d{2})\b", t)
    if m:
        y = int("".join(g for g in m.groups() if g))
        return dt.date(y, 1, 1), today, "since_year"
    return None, None, None


def parse_question(question: str, today: dt.date | None = None) -> dict:
    today = today or dt.date.today()
    t = " " + norm(question) + " "
    unresolved: list[str] = []
    decisions: list[str] = []

    places = find_in_text(question)
    comparative = any(k in t for k in COMPARE) and len(places) >= 2
    if not places:
        unresolved.append("area")
    else:
        decisions.append("Lugares reconocidos en el nomenclátor: " + ", ".join(p.name for p in places) + ".")

    phenomena = [ph for ph, keys in PHENOMENA.items() if any(k in t for k in keys)]
    if any(p.id in ("greenland", "sermeq_kujalleq", "helheim") for p in places) and "glacier" not in phenomena:
        phenomena.append("glacier")
    if not phenomena:
        phenomena = ["surface_change"]
        decisions.append("No se nombró un fenómeno: se investiga el cambio de superficie en general.")

    start, end, how = _period(t, today)
    if start is None:
        unresolved.append("period")
        decisions.append("No se dio periodo: se usa el último año como propuesta.")
        start, end = today - dt.timedelta(days=365), today
    else:
        decisions.append(f"Periodo interpretado ({how}): {start.isoformat()} a {end.isoformat()}.")

    profiles = sorted({PROFILE_FOR[p] for p in phenomena if p in PROFILE_FOR}) or ["general_change"]
    products = products_for(phenomena)
    notes: list[str] = []
    nisar_start = dt.date(2025, 8, 1)
    if start < nisar_start:
        notes.append(
            "NISAR publica datos científicos desde la segunda mitad de 2025: antes de esa fecha la serie solo puede "
            "venir de otros sensores (por ejemplo Sentinel-1 desde 2014 o Landsat), que no se analizan en esta pila."
        )

    return {
        "question": question,
        "areas": [p.to_dict() for p in places],
        "comparative": comparative,
        "period": {"start": start.isoformat(), "end": end.isoformat()},
        "phenomena": phenomena,
        "profiles": profiles,
        "products": [p.id for p in products],
        "methods": _methods(phenomena),
        "expected_outputs": _expected(phenomena),
        "unresolved": unresolved,
        "decisions": decisions,
        "notes": notes,
        "parser": "rules-v1",
    }


def _methods(phenomena: list[str]) -> list[str]:
    m = ["catalog_discovery", "acquisition_compatibility"]
    m += ["pairwise_backscatter_change", "temporal_trend_theil_sen", "robust_anomaly_mad", "change_point_mean_shift"]
    if "flood" in phenomena:
        m.append("water_extent_contrast_dswx")
    if any(p in phenomena for p in ("deformation", "landslide", "mining", "glacier")):
        m.append("insar_capability_assessment")
    m.append("event_spatiotemporal_correlation")
    if any(p in phenomena for p in ("flood", "landslide")):
        m.append("susceptibility_factor_inventory")
    return m


def _expected(phenomena: list[str]) -> list[str]:
    out = ["acquisition_catalog", "temporal_series", "anomalies", "events", "story"]
    if any(p in phenomena for p in ("flood", "landslide")):
        out.append("susceptibility_inventory")
    return out
