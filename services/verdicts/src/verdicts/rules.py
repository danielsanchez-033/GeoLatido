"""Reglas de decisión. MIN_CHANGED_FRACTION se fijó con el ruido de pares reales; los demás umbrales son supuestos sin calibrar."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone

CHANGE_PROBABLE = "change_probable"
NO_DETECTABLE_CHANGE = "no_detectable_change"
NOT_OBSERVABLE = "not_observable"
OBSERVABLE = "observable"

MIN_OBSERVED_FRACTION = 0.5
# Fijado sobre el ruido de 16 pares consecutivos reales de Parral (T-BAL-09, 2026-11-13), sin verdad de campo.
# Con el cambio ya corregido por el desplazamiento de la escena (T-ECO-07), 14 de los 16 quedan entre 0,58 % y
# 4,64 %, siguiendo a la dispersión de cada par (1,4826 · MAD de HH entre 0,76 y 1,32 dB): ese es el suelo de
# ruido medido, que no se puede separar del cambio difuso (humedad, vegetación). El 5 % queda por encima de
# todos ellos; los otros dos son T048 08-16→08-28 (5,18 %, HH 1,27 dB) y 08-28→09-09 (9,56 %, HH 1,59 dB).
# Tabla por par en el PR 39 de Eco y en MEMORY.md.
MIN_CHANGED_FRACTION = 0.05
MIN_SIGNATURE_SHARE = 0.2

SIGNATURE_HYPOTHESIS = {
    "hh_up_hv_stable": "surface_moisture_or_flooded_vegetation",
    "hh_up_hv_up": "more_vegetation_wetting_or_water_retreat",
    "hh_down_hv_down": "vegetation_loss_smoother_surface_or_new_water",
    "hh_down_hv_stable": "drying_or_open_water",
    "hv_up_hh_stable": "vegetation_growth",
    "hv_down_hh_stable": "vegetation_loss",
    "other": "mixed_signature",
}

UNOBSERVABLE_CAUSES = ("outside_scene", "invalid_or_partial", "input_exception", "low_looks", "no_data", "terrain")


@dataclass(frozen=True)
class Decision:
    state: str
    cause: str | None
    observed_fraction: float
    changed_fraction: float


@dataclass(frozen=True)
class EventStatus:
    state: str
    cause: str | None
    previous_pass: date | None
    next_pass: date | None
    seen_by: date | None = None  # pasada que cae seguro dentro del evento, si la hay
    next_pass_at: datetime | None = None


def decide(counts: dict[str, int]) -> Decision:
    observed = counts.get("no_change", 0) + counts.get("change_probable", 0)
    total = sum(counts.values())
    observed_fraction = observed / total if total else 0.0
    changed_fraction = counts.get("change_probable", 0) / observed if observed else 0.0

    if observed_fraction < MIN_OBSERVED_FRACTION:
        cause = max(UNOBSERVABLE_CAUSES, key=lambda name: counts.get(name, 0))
        return Decision(NOT_OBSERVABLE, cause, observed_fraction, changed_fraction)
    state = CHANGE_PROBABLE if changed_fraction >= MIN_CHANGED_FRACTION else NO_DETECTABLE_CHANGE
    return Decision(state, None, observed_fraction, changed_fraction)


def signature_shares(signature_counts: dict[str, int]) -> list[tuple[str, float]]:
    """(hipótesis, parte de lo que cambió) de las firmas relevantes, de mayor a menor."""
    total = sum(signature_counts.values())
    if not total:
        return []
    relevant = [
        (count / total, name)
        for name, count in signature_counts.items()
        if name in SIGNATURE_HYPOTHESIS and count / total >= MIN_SIGNATURE_SHARE
    ]
    return [(SIGNATURE_HYPOTHESIS[name], share) for share, name in sorted(relevant, reverse=True)]


def hypotheses(signature_counts: dict[str, int]) -> list[str]:
    """Firmas relevantes por área, de mayor a menor. Orientan, no identifican la causa."""
    total = sum(signature_counts.values())
    if not total:
        return []
    relevant = [
        (count, name)
        for name, count in signature_counts.items()
        if name in SIGNATURE_HYPOTHESIS and count / total >= MIN_SIGNATURE_SHARE
    ]
    return [SIGNATURE_HYPOTHESIS[name] for _, name in sorted(relevant, reverse=True)]


DAY = timedelta(days=1)

# Persistencias supuestas por tipo de evento, en horas. Valores iniciales sin calibrar: se
# devuelven siempre como supuesto en la respuesta, nunca como medición.
PERSISTENCE_BY_EVENT_TYPE = {
    "urban_storm": 6,
    "river_flood": 72,
    "wildfire": 240,
}
DEFAULT_PERSISTENCE_HOURS = 24


@dataclass(frozen=True)
class Persistence:
    hours: int
    source: str  # "event_type", "user" o "default"
    event_type: str | None


def persistence(event_type: str | None, hours: int | None) -> Persistence:
    """Horas que se suponen para el evento: las indicadas, las del tipo o el valor por omisión."""
    if hours is not None:
        return Persistence(hours, "user", event_type)
    if event_type is not None:
        return Persistence(PERSISTENCE_BY_EVENT_TYPE[event_type], "event_type", event_type)
    return Persistence(DEFAULT_PERSISTENCE_HOURS, "default", None)


def _span(day: date, at: datetime | None) -> tuple[datetime, datetime]:
    """Intervalo UTC en que cae algo: el instante si se conoce la hora, o el día completo si no."""
    if at is not None:
        return at, at
    start = datetime.combine(day, time.min, tzinfo=timezone.utc)
    return start, start + DAY - timedelta(microseconds=1)


def event_status(
    dates: list[date],
    event: date,
    persistence_hours: int,
    event_time: time | None = None,
    pass_times: dict[date, datetime] | None = None,
) -> EventStatus:
    """Decide si alguna pasada cayó mientras duraba el evento, comparando en horas UTC.

    Sin hora del evento, puede empezar en cualquier momento de su día UTC; sin hora de la
    pasada, también. "observable" exige que la pasada caiga dentro del evento en todos los
    casos posibles; si solo cae en algunos, se declara timing_uncertain.
    """
    times = pass_times or {}
    duration = timedelta(hours=persistence_hours)
    start_lo, start_hi = _span(
        event, datetime.combine(event, event_time, tzinfo=timezone.utc) if event_time else None
    )
    ordered = sorted(set(dates))
    spans = [(day, *_span(day, times.get(day))) for day in ordered]
    # La siguiente es la primera que pudo ser posterior al inicio del evento; la anterior, la de antes.
    following = [item for item in spans if item[2] >= start_lo]
    earlier = [item for item in spans if item[2] < start_lo]
    previous_pass = earlier[-1][0] if earlier else None
    next_pass = following[0][0] if following else None
    next_at = times.get(next_pass) if next_pass else None
    if next_pass is None or previous_pass is None:
        return EventStatus(NOT_OBSERVABLE, "outside_series_window", previous_pass, next_pass, None, next_at)
    candidates = [item for item in following if item[1] <= start_hi + duration]
    for day, pass_lo, pass_hi in candidates:
        if pass_lo >= start_hi and pass_hi <= start_lo + duration:
            return EventStatus(OBSERVABLE, None, previous_pass, next_pass, day, next_at)
    if candidates:
        return EventStatus(NOT_OBSERVABLE, "timing_uncertain", previous_pass, next_pass, None, next_at)
    return EventStatus(NOT_OBSERVABLE, "no_acquisition_during_event", previous_pass, next_pass, None, next_at)
