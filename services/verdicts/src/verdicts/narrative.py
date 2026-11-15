"""Plantillas deterministas: mismo dato, mismo texto, sin generar afirmaciones nuevas."""
from __future__ import annotations

import os
from pathlib import Path

from typing import Literal

from . import rules

Lang = Literal["es", "en"]

CAUSES = {
    "es": {
        "outside_scene": "la zona queda fuera de la pasada",
        "invalid_or_partial": "datos inválidos o parcialmente enfocados",
        "input_exception": "anomalía en los datos de entrada",
        "low_looks": "muy pocas muestras de radar por píxel",
        "no_data": "píxeles sin dato utilizable",
        "terrain": "relieve que oculta o distorsiona la señal",
        "no_acquisition_during_event": "no hubo ninguna pasada dentro de la duración supuesta del evento",
        "outside_series_window": "el evento queda fuera del periodo con datos",
        "timing_uncertain": "sin la hora UTC del evento o de la pasada no se sabe si la pasada cayó dentro de la duración supuesta",
    },
    "en": {
        "outside_scene": "the area falls outside the pass",
        "invalid_or_partial": "invalid or partially focused data",
        "input_exception": "input data anomaly",
        "low_looks": "too few radar samples per pixel",
        "no_data": "pixels without usable data",
        "terrain": "terrain hides or distorts the signal",
        "no_acquisition_during_event": "no pass fell within the event's assumed duration",
        "outside_series_window": "the event falls outside the period with data",
        "timing_uncertain": "without the UTC time of the event or the pass, it is unknown whether the pass fell within the assumed duration",
    },
}

# Posibles explicaciones por firma, en palabras de todos los días (2026-11-15). HH responde sobre todo al suelo y
# al agua; HV, a las hojas, ramas y troncos (dispersión de volumen en banda L). Orientan, no identifican la causa.
HYPOTHESES = {
    "es": {
        "surface_moisture_or_flooded_vegetation": "El suelo se ve más húmedo, o hay agua bajo las plantas (sube la señal del suelo, HH; la de las plantas, HV, no cambia).",
        "more_vegetation_wetting_or_water_retreat": "Más plantas, suelo mojado por la lluvia o agua que se retiró (suben las dos señales, HH y HV).",
        "vegetation_loss_smoother_surface_or_new_water": "Menos plantas, terreno más liso (por ejemplo, desmonte o arado) o agua nueva (bajan las dos señales, HH y HV).",
        "drying_or_open_water": "El suelo se secó, o apareció agua tranquila (baja la señal del suelo, HH).",
        "vegetation_growth": "Crecieron plantas, cultivos o árboles (sube la señal de las hojas y ramas, HV, y la del suelo, HH, no cambia).",
        "vegetation_loss": "Se perdieron plantas, cultivos o árboles, por ejemplo por cosecha, tala o incendio (baja la señal de las hojas y ramas, HV; HH no cambia).",
        "mixed_signature": "Las señales se mezclan y no apuntan a una explicación clara.",
    },
    "en": {
        "surface_moisture_or_flooded_vegetation": "The ground looks wetter, or there is water under plants (the ground signal, HH, rises; the plant signal, HV, does not change).",
        "more_vegetation_wetting_or_water_retreat": "More plants, ground wet from rain, or water that pulled back (both signals, HH and HV, rise).",
        "vegetation_loss_smoother_surface_or_new_water": "Fewer plants, smoother ground (for example clearing or ploughing) or new water (both signals, HH and HV, fall).",
        "drying_or_open_water": "The ground dried, or calm water appeared (the ground signal, HH, falls).",
        "vegetation_growth": "Plants, crops or trees grew (the leaf-and-branch signal, HV, rises and the ground signal, HH, does not change).",
        "vegetation_loss": "Plants, crops or trees were lost, for example by harvest, logging or fire (the leaf-and-branch signal, HV, falls; HH does not change).",
        "mixed_signature": "The signals are mixed and point to no clear explanation.",
    },
}


def hypothesis_text(name: str, share: float, lang: Lang) -> str:
    """Una posible explicación con la parte de lo que cambió que tiene esa firma."""
    lead = "Posible explicación para el {p} de lo que cambió: " if lang == "es" else "Possible explanation for {p} of what changed: "
    return lead.format(p=_fraction(round(share, 2), lang)) + HYPOTHESES[lang][name]


SYNTHETIC_PREFIX = {"es": "[DATOS SINTÉTICOS] ", "en": "[SYNTHETIC DATA] "}


LATENCY_UNKNOWN = {
    "es": {
        "synthetic": "La latencia de publicación no aplica a datos sintéticos.",
        "catalog_unavailable": "No se conoce la latencia de publicación: el catálogo no respondió.",
        "granule_not_in_catalog": "No se conoce la latencia de publicación: el gránulo no aparece en el catálogo.",
        "not_published": "No se conoce la latencia de publicación: el catálogo no da fecha de publicación.",
    },
    "en": {
        "synthetic": "Publication latency does not apply to synthetic data.",
        "catalog_unavailable": "Publication latency is unknown: the catalog did not respond.",
        "granule_not_in_catalog": "Publication latency is unknown: the granule is not in the catalog.",
        "not_published": "Publication latency is unknown: the catalog gives no publication date.",
    },
}


# Zona con la que se fijó MIN_CHANGED_FRACTION (T-BAL-09). Las demás zonas usan el mismo mínimo sin calibrarlo.
REFERENCE_AOI = "parral"
REFERENCE_NAME = "Hidalgo del Parral"
_NAMES = {REFERENCE_AOI: REFERENCE_NAME}
ONLINE_ZONES = Path(os.environ.get("ONLINE_ZONES_DIR", "/data/aois-online"))


def zone_name(aoi: str) -> str | None:
    """Nombre legible de la zona: Parral fijo, y el `name:` del YAML de las zonas procesadas en línea (lo escribe
    `online`). Sin YAML legible, None y el texto dice «la zona». Solo se abre un archivo con el id tal cual si es
    un nombre de archivo simple."""
    if aoi in _NAMES:
        return _NAMES[aoi]
    if not aoi or "/" in aoi or "\\" in aoi or aoi.startswith("."):
        return None
    try:
        for line in (ONLINE_ZONES / f"{aoi}.yaml").read_text(encoding="utf-8").splitlines():
            if line.startswith("name:"):
                return line[5:].strip().strip("'\"") or None
    except OSError:
        return None
    return None


def _where(zone: str | None, lang: Lang) -> str:
    if lang == "es":
        return f" en {zone}" if zone else " de la zona"
    return f" in {zone}" if zone else " of the area"


def _calibration(aoi: str, lang: Lang) -> str:
    if lang == "es":
        if aoi == REFERENCE_AOI:
            return ("Ese 5 % se fijó con 16 pares reales de esta misma zona: por debajo, el radar da cifras parecidas "
                    "aunque nada cambie (es su «ruido»), así que no lo contamos como cambio.")
        return (f"Ese 5 % se fijó con 16 pares reales de {REFERENCE_NAME}, la zona de referencia del proyecto, y aquí "
                "se aplica sin calibrar: por debajo, el radar da cifras parecidas aunque nada cambie (es su «ruido»), "
                "así que no lo contamos como cambio.")
    if aoi == REFERENCE_AOI:
        return ("That 5 % was set with 16 real pairs from this same area: below it, the radar gives similar figures even "
                "when nothing changes (its “noise”), so we do not count it as change.")
    return (f"That 5 % was set with 16 real pairs from {REFERENCE_NAME}, the project's reference area, and is applied "
            "here without calibration: below it, the radar gives similar figures even when nothing changes (its "
            "“noise”), so we do not count it as change.")


def _days(count: int, lang: Lang) -> str:
    if lang == "es":
        return f"{count} día" if count == 1 else f"{count} días"
    return f"{count} day" if count == 1 else f"{count} days"


def _hours(value: float, lang: Lang) -> str:
    # Se muestra el valor de catalog tal cual (un decimal), sin redondear más.
    text = f"{value:.1f}"
    return text.replace(".", ",") if lang == "es" else text


def freshness_text(age_days: int, latency_hours: float | None, latency_status: str, lang: Lang) -> str:
    """Edad de la imagen más reciente y latencia de publicación, o por qué no se conoce."""
    if lang == "es":
        age = f"La imagen más reciente tiene {_days(age_days, lang)}."
        if latency_status == "available" and latency_hours is not None:
            latency = (
                f"Se publicó {_hours(latency_hours, lang)} horas después de adquirirse "
                "(aproximación con la fecha de actualización de CMR)."
            )
        else:
            latency = LATENCY_UNKNOWN[lang][latency_status]
    else:
        age = f"The most recent image is {_days(age_days, lang)} old."
        if latency_status == "available" and latency_hours is not None:
            latency = (
                f"It was published {_hours(latency_hours, lang)} hours after acquisition "
                "(approximated with the CMR update date)."
            )
        else:
            latency = LATENCY_UNKNOWN[lang][latency_status]
    return f"{age} {latency}"


def _fraction(value: float, lang: Lang) -> str:
    """Fracción como porcentaje sin decimales sobrantes: 0.05 -> "5 %"."""
    text = f"{value * 100:.1f}".removesuffix(".0")
    return (text.replace(".", ",") if lang == "es" else text) + " %"


def pair_summary(
    decision: rules.Decision,
    start: str,
    end: str,
    spans_gap: bool,
    lang: Lang,
    synthetic: bool,
    *,
    interval_days: int,
    age_days: int,
    latency_hours: float | None,
    latency_status: str,
    kind: str = "consecutive",
    aoi: str = "",
    zone: str | None = None,
) -> dict:
    where = _where(zone, lang)
    observed = _fraction(round(decision.observed_fraction, 2), lang)
    changed = _fraction(round(decision.changed_fraction, 3), lang)
    span = _days(interval_days, lang)
    if lang == "es":
        if decision.state == rules.CHANGE_PROBABLE:
            detected = f"Del {start} al {end} ({span}), el radar notó un cambio claro en el {changed} de lo que pudo ver{where}: suficiente para decir que algo cambió."
            limits = "No identifica la causa ni mide sus consecuencias; explicarlo requiere otra fuente o verificación en campo."
        elif decision.state == rules.NO_DETECTABLE_CHANGE and decision.changed_fraction > 0:
            detected = (
                f"Del {start} al {end} ({span}), el radar notó cambios en el {changed} de lo que pudo ver{where}. Es "
                f"menos del {_fraction(rules.MIN_CHANGED_FRACTION, lang)} que hace falta para hablar de un cambio. "
                + _calibration(aoi, lang)
            )
            limits = "No demuestra que nada cambiara: lo pequeño, lo breve o lo ocurrido entre pasadas puede no aparecer."
        elif decision.state == rules.NO_DETECTABLE_CHANGE:
            detected = f"Del {start} al {end} ({span}), el radar no notó cambios en lo que pudo ver{where} (el {observed})."
            limits = "No demuestra que nada cambiara: lo pequeño, lo breve o lo ocurrido entre pasadas puede no aparecer."
        else:
            detected = f"No podemos decir qué pasó del {start} al {end} ({span}): el radar solo pudo ver el {observed}{where} ({CAUSES[lang][decision.cause]})."
            limits = "La ausencia de resultado no significa que no haya pasado nada."
        if kind == "full_window":
            context = f"Este par compara la primera y la última fecha de la serie, separadas {span}; resume todo el periodo, no un cambio puntual."
            if spans_gap:
                context += " El periodo incluye el hueco sin adquisiciones del 27 de julio al 10 de agosto de 2026."
        elif spans_gap:
            context = (
                f"Las imágenes están separadas {span} porque el par cruza el hueco sin adquisiciones del "
                "27 de julio al 10 de agosto de 2026; lo ocurrido en ese tiempo puede no verse."
            )
        else:
            context = "Falta contrastar con una fuente independiente."
    else:
        if decision.state == rules.CHANGE_PROBABLE:
            detected = f"From {start} to {end} ({span}), the radar saw a clear change over {changed} of what it could see{where}: enough to say something changed."
            limits = "It does not identify the cause or measure its consequences; explaining it needs another source or field checks."
        elif decision.state == rules.NO_DETECTABLE_CHANGE and decision.changed_fraction > 0:
            detected = (
                f"From {start} to {end} ({span}), the radar saw changes over {changed} of what it could see{where}. "
                f"That is less than the {_fraction(rules.MIN_CHANGED_FRACTION, lang)} needed to call it a change. "
                + _calibration(aoi, lang)
            )
            limits = "It does not prove nothing changed: small, brief or between-pass changes may not appear."
        elif decision.state == rules.NO_DETECTABLE_CHANGE:
            detected = f"From {start} to {end} ({span}), the radar saw no change in what it could see{where} ({observed})."
            limits = "It does not prove nothing changed: small, brief or between-pass changes may not appear."
        else:
            detected = f"We cannot say what happened from {start} to {end} ({span}): the radar could only see {observed}{where} ({CAUSES[lang][decision.cause]})."
            limits = "The lack of a result does not mean nothing happened."
        if kind == "full_window":
            context = f"This pair compares the first and last dates of the series, {span} apart; it sums up the whole period, not a single change."
            if spans_gap:
                context += " The period includes the acquisition gap from 27 July to 10 August 2026."
        elif spans_gap:
            context = (
                f"The images are {span} apart because the pair crosses the acquisition gap from "
                "27 July to 10 August 2026; what happened in that time may not show."
            )
        else:
            context = "It still needs checking against an independent source."
    missing = f"{context} {freshness_text(age_days, latency_hours, latency_status, lang)}"
    prefix = SYNTHETIC_PREFIX[lang] if synthetic else ""
    return {"detected": prefix + detected, "does_not_prove": limits, "missing": missing}


EVENT_TYPES = {
    "es": {"urban_storm": "una tormenta urbana", "river_flood": "una crecida de río", "wildfire": "un incendio"},
    "en": {"urban_storm": "an urban storm", "river_flood": "a river flood", "wildfire": "a wildfire"},
}


def persistence_text(persistence: rules.Persistence, lang: Lang) -> str:
    """Declara de dónde sale la duración usada: siempre es un supuesto, nunca una medición."""
    hours = persistence.hours
    if lang == "es":
        if persistence.source == "event_type":
            return (f"Supuesto: el evento dura {hours} h, valor inicial sin calibrar para "
                    f"{EVENT_TYPES[lang][persistence.event_type]}; no se midió.")
        if persistence.source == "user":
            return f"Supuesto: el evento dura {hours} h, según la consulta; no se midió."
        return (f"Supuesto: el evento dura {hours} h, valor por omisión sin calibrar; no se midió. "
                "Indicar el tipo de evento cambia la duración supuesta.")
    if persistence.source == "event_type":
        return (f"Assumption: the event lasts {hours} h, an initial uncalibrated value for "
                f"{EVENT_TYPES[lang][persistence.event_type]}; it was not measured.")
    if persistence.source == "user":
        return f"Assumption: the event lasts {hours} h, as given in the query; it was not measured."
    return (f"Assumption: the event lasts {hours} h, an uncalibrated default; it was not measured. "
            "Giving the event type changes the assumed duration.")


def event_summary(
    status: rules.EventStatus,
    event: str,
    lang: Lang,
    synthetic: bool,
    persistence: rules.Persistence | None = None,
) -> dict:
    previous = status.previous_pass.isoformat() if status.previous_pass else "-"
    following = status.next_pass.isoformat() if status.next_pass else "-"
    seen = status.seen_by.isoformat() if status.seen_by else following
    uncertain = status.cause == "timing_uncertain"
    if lang == "es":
        if status.state == rules.OBSERVABLE:
            detected = f"Hubo una pasada el {seen}, dentro de la duración supuesta del evento del {event}."
            limits = "Que haya pasada no garantiza que el evento se vea; hay que consultar el veredicto de ese par."
            missing = "Revisar el par que incluye esa fecha."
        else:
            detected = f"El evento del {event} no es observable: {CAUSES[lang][status.cause]}. Pasada anterior: {previous}; siguiente: {following}."
            if uncertain:
                limits = "La pasada pudo caer dentro de la duración supuesta del evento o fuera; con estos datos no se puede afirmar ninguna de las dos."
                missing = "Indicar la hora UTC de inicio del evento permite decidirlo."
            else:
                limits = "Esto no indica que el evento no ocurriera; indica que el radar no pudo registrarlo."
                missing = "Haría falta una fuente con mayor frecuencia o reportes locales."
    else:
        if status.state == rules.OBSERVABLE:
            detected = f"A pass occurred on {seen}, within the assumed duration of the {event} event."
            limits = "A pass does not guarantee the event is visible; check that pair's verdict."
            missing = "Review the pair that includes that date."
        else:
            detected = f"The {event} event is not observable: {CAUSES[lang][status.cause]}. Previous pass: {previous}; next: {following}."
            if uncertain:
                limits = "The pass may have fallen inside or outside the event's assumed duration; these data cannot tell which."
                missing = "Giving the event's UTC start time makes it decidable."
            else:
                limits = "This does not mean the event did not happen; the radar could not record it."
                missing = "It would need a more frequent source or local reports."
    if persistence is not None:
        limits = f"{limits} {persistence_text(persistence, lang)}"
    prefix = SYNTHETIC_PREFIX[lang] if synthetic else ""
    return {"detected": prefix + detected, "does_not_prove": limits, "missing": missing}


# --- T-BAL-04: contraste óptico Sentinel-2 ------------------------------------------------

OPTICAL_ROLE = {
    "es": {"before": ("de antes", "la primera fecha de radar"), "after": ("de después", "la segunda fecha de radar")},
    "en": {"before": ("before", "the first radar date"), "after": ("after", "the second radar date")},
}


def _percent(value: float, lang: Lang) -> str:
    text = f"{value:.1f}".removesuffix(".0")
    return (text.replace(".", ",") if lang == "es" else text) + " %"


def _optical_side(
    side: str,
    status: str,
    acquired: str | None,
    days: int | None,
    cloud: float | None,
    lang: Lang,
    max_cloud: float,
    search_days: int,
) -> str:
    role, radar = OPTICAL_ROLE[lang][side]
    window = _days(search_days, lang)
    limit = _percent(max_cloud, lang)
    if lang == "es":
        if status == "catalog_unavailable":
            return f"No se sabe si hay imagen óptica Sentinel-2 {role}: el catálogo no respondió."
        if status == "none_in_window":
            return f"No hay imagen óptica Sentinel-2 {role} a {window} o menos de {radar}."
        offset = f"el mismo día que {radar}" if days == 0 else f"{_days(abs(days), lang)} {'antes' if side == 'before' else 'después'} de {radar}"
        text = f"Imagen óptica Sentinel-2 {role}: {acquired}, {offset}, con hasta {_percent(cloud, lang)} de nubes por tesela."
        if status == "cloudy":
            text += f" Es la menos nublada: ninguna a {window} o menos cubre la zona con {limit} de nubes o menos."
        elif status == "partial_coverage":
            text += f" Solo cubre parte de la zona: ninguna a {window} o menos la cubre entera."
        return text
    if status == "catalog_unavailable":
        return f"It is unknown whether there is a Sentinel-2 optical image {role} {radar}: the catalog did not respond."
    if status == "none_in_window":
        return f"There is no Sentinel-2 optical image within {window} {role} {radar}."
    offset = f"the same day as {radar}" if days == 0 else f"{_days(abs(days), lang)} {'before' if side == 'before' else 'after'} {radar}"
    text = f"Optical image {role} (Sentinel-2): {acquired}, {offset}, with up to {_percent(cloud, lang)} cloud per tile."
    if status == "cloudy":
        text += f" It is the least cloudy: none within {window} covers the area with {limit} cloud or less."
    elif status == "partial_coverage":
        text += f" It covers only part of the area: none within {window} covers all of it."
    return text


def optical_text(
    before: tuple[str, str | None, int | None, float | None],
    after: tuple[str, str | None, int | None, float | None],
    lang: Lang,
    *,
    max_cloud: float,
    search_days: int,
) -> str:
    """Cada lado es (estado, fecha, días respecto a la fecha de radar, nubosidad máxima por tesela)."""
    if before[0] == after[0] == "catalog_unavailable":
        if lang == "es":
            return "No se sabe si hay imágenes ópticas Sentinel-2: el catálogo no respondió."
        return "It is unknown whether there are Sentinel-2 optical images: the catalog did not respond."
    parts = [
        _optical_side(side, *values, lang, max_cloud, search_days)
        for side, values in (("before", before), ("after", after))
    ]
    if any(values[1] is not None for values in (before, after)):
        if lang == "es":
            parts.append(
                "La nubosidad es la de cada tesela completa, no la de la zona. "
                "La imagen óptica sirve de contexto y no explica por sí sola la señal de radar."
            )
        else:
            parts.append(
                "Cloud cover is for each whole tile, not for the area. "
                "The optical image gives context and does not explain the radar signal on its own."
            )
    return " ".join(parts)


# --- T-BAL-08: contraste con OPERA DSWx-S1 ------------------------------------------------

WATER_ROLE = {
    "es": {"before": "la primera fecha de radar", "after": "la segunda fecha de radar"},
    "en": {"before": "the first radar date", "after": "the second radar date"},
}

WATER_NOT_COMPARED = {
    "es": {
        "synthetic": "no se compara con datos de radar sintéticos",
        "no_credentials": "no se comparó porque el servicio no tiene acceso a sus archivos (requieren cuenta de Earthdata)",
        "read_failed": "no se pudo leer su capa de agua, así que no se compara",
        "no_overlap": ("no tiene píxeles válidos en común con el radar dentro de la zona: que la caja de sus "
                       "teselas cubra la zona no asegura que el producto tenga datos en ella"),
        "partial_overlap": ("solo se pudo comparar el {compared} de la zona, menos del {minimum} que hace falta para "
                            "hablar de acuerdo o desacuerdo, porque el producto no tiene datos en el resto"),
    },
    "en": {
        "synthetic": "it is not compared with synthetic radar data",
        "no_credentials": "it was not compared because the service has no access to its files (they need an Earthdata account)",
        "read_failed": "its water layer could not be read, so it is not compared",
        "no_overlap": ("it shares no valid pixels with the radar inside the area: its tiles' bounding box "
                       "covering the area does not ensure the product has data there"),
        "partial_overlap": ("only {compared} of the area could be compared, less than the {minimum} needed to "
                            "speak of agreement or disagreement, because the product has no data in the rest"),
    },
}


def _not_compared(status: str, values: dict, lang: Lang) -> str:
    return WATER_NOT_COMPARED[lang][status].format(
        compared=_share(values.get("compared", 0.0), lang), minimum=_share(values.get("minimum", 0.5), lang)
    )


def _share(fraction: float, lang: Lang) -> str:
    if 0 < fraction < 0.001:
        return "< 0,1 %" if lang == "es" else "< 0.1 %"
    return _percent(fraction * 100, lang)


def _water_side(side: str, values: dict, lang: Lang, search_days: int) -> str:
    """values: status, product_date, days, assessment, basis, iou, radar, reference (fracciones)."""
    radar = WATER_ROLE[lang][side]
    status, days = values["status"], values.get("days")
    window = _days(search_days, lang)
    if lang == "es":
        if status == "catalog_unavailable":
            return f"No se sabe si hay producto de agua OPERA DSWx-S1 cerca de {radar}: el catálogo no respondió."
        if status == "none_in_window":
            return f"No hay producto de agua OPERA DSWx-S1 a {window} o menos de {radar}; no hay contraste."
        offset = f"el mismo día que {radar}" if days == 0 else (
            f"{_days(abs(days), lang)} {'antes' if days < 0 else 'después'} de {radar}")
        product = f"OPERA DSWx-S1 del {values['product_date']} ({offset})"
        if status != "compared":
            return f"Hay un producto {product}, pero {_not_compared(status, values, lang)}."
        shares = f"radar {_share(values['radar'], lang)} y DSWx-S1 {_share(values['reference'], lang)} de los píxeles comparables"
        if values["basis"] == "little_water":
            return f"{product} y el radar coinciden: ninguno de los dos ve agua apreciable en la zona ({shares})."
        iou = _share(values["iou"] or 0.0, lang)
        if values["assessment"] == "agree":
            return (f"{product} y el radar coinciden en dónde hay agua: comparten el {iou} de los píxeles "
                    f"que alguno de los dos marca como agua ({shares}).")
        return (f"{product} y el radar no coinciden en dónde hay agua: solo comparten el {iou} de los píxeles "
                f"que alguno de los dos marca como agua ({shares}). Es un desacuerdo entre dos métodos "
                "y no indica cuál de los dos acierta.")
    if status == "catalog_unavailable":
        return f"It is unknown whether there is an OPERA DSWx-S1 water product near {radar}: the catalog did not respond."
    if status == "none_in_window":
        return f"There is no OPERA DSWx-S1 water product within {window} of {radar}; there is no cross-check."
    offset = f"the same day as {radar}" if days == 0 else (
        f"{_days(abs(days), lang)} {'before' if days < 0 else 'after'} {radar}")
    product = f"OPERA DSWx-S1 from {values['product_date']} ({offset})"
    if status != "compared":
        return f"There is a product, {product}, but {_not_compared(status, values, lang)}."
    shares = f"radar {_share(values['radar'], lang)} and DSWx-S1 {_share(values['reference'], lang)} of comparable pixels"
    if values["basis"] == "little_water":
        return f"{product} and the radar agree: neither sees noticeable water in the area ({shares})."
    iou = _share(values["iou"] or 0.0, lang)
    if values["assessment"] == "agree":
        return (f"{product} and the radar agree on where there is water: they share {iou} of the pixels "
                f"either one marks as water ({shares}).")
    return (f"{product} and the radar disagree on where there is water: they share only {iou} of the pixels "
            f"either one marks as water ({shares}). This is a disagreement between two methods "
            "and does not tell which one is right.")


def water_text(
    before: dict,
    after: dict,
    lang: Lang,
    *,
    search_days: int,
    min_water_body_ha: float | None,
    min_water_body_width_m: float | None,
    hh_db: float,
    hv_db: float,
) -> str:
    """Resumen del contraste de agua: un texto por lado y, si hay producto, sus límites."""
    if before["status"] == after["status"] == "catalog_unavailable":
        if lang == "es":
            return "No se sabe si hay productos de agua OPERA DSWx-S1: el catálogo no respondió."
        return "It is unknown whether there are OPERA DSWx-S1 water products: the catalog did not respond."
    parts = [_water_side(side, values, lang, search_days) for side, values in (("before", before), ("after", after))]
    found = [values for values in (before, after) if values["status"] not in ("catalog_unavailable", "none_in_window")]
    if found and min_water_body_ha is not None and min_water_body_width_m is not None:
        ha = _hours(min_water_body_ha, lang).removesuffix(",0").removesuffix(".0")
        width = _hours(min_water_body_width_m, lang).removesuffix(",0").removesuffix(".0")
        if lang == "es":
            parts.append(f"DSWx-S1 solo detecta masas de agua abiertas de más de {ha} ha y {width} m de ancho: "
                         "no ver agua en él no descarta agua en calles o charcos.")
        else:
            parts.append(f"DSWx-S1 only detects open water bodies larger than {ha} ha and {width} m wide: "
                         "seeing no water in it does not rule out water in streets or puddles.")
    if any(values["status"] == "compared" for values in found):
        hh, hv = _hours(hh_db, lang), _hours(hv_db, lang)
        if lang == "es":
            parts.append(f"El agua del radar es la de los píxeles con HH < {hh} dB y HV < {hv} dB, "
                         "umbrales sin calibrar.")
        else:
            parts.append(f"Radar water means pixels with HH < {hh} dB and HV < {hv} dB, uncalibrated thresholds.")
    return " ".join(parts)


# --- T-BAL-07: control de calidad de Eco y desplazamiento de la escena ----------------------

def _db(value: float | None, lang: Lang) -> str:
    if value is None:
        return "?"
    text = f"{value:+.1f}"
    return text.replace(".", ",") if lang == "es" else text


def quality_flag_text(day: str, deviation_hh: float | None, deviation_hv: float | None, threshold: float, lang: Lang) -> str:
    """Una fecha que el control de calidad de Eco marca como desviada: se avisa, no se excluye."""
    hh, hv, limit = _db(deviation_hh, lang), _db(deviation_hv, lang), _hours(threshold, lang)
    if lang == "es":
        return (f"El control de calidad marca la imagen del {day}: su mediana se aparta {hh} dB en HH y {hv} dB en HV "
                f"de la de la serie, más de {limit} dB (umbral sin calibrar). Es una advertencia, no una exclusión.")
    return (f"Quality control flags the {day} image: its median departs {hh} dB in HH and {hv} dB in HV "
            f"from the series median, more than {limit} dB (uncalibrated threshold). It is a warning, not an exclusion.")


def scene_shift_text(
    hh: float | None, hv: float | None, same_direction: bool | None, lang: Lang, corrected: bool = False
) -> str:
    """Aviso de que el nivel de toda la escena cambió entre las dos fechas.

    corrected: processor ya descontó ese desplazamiento antes de medir el cambio (stats.scene_shift_*).
    """
    if lang == "es":
        together = {True: ", en el mismo sentido", False: ", en sentidos opuestos", None: ""}[same_direction]
        shift = (f"Entre las dos fechas cambió el nivel de toda la escena (mediana de HH {_db(hh, lang)} dB y de HV "
                 f"{_db(hv, lang)} dB{together}), quizá por humedad del suelo o por un efecto radiométrico.")
        if corrected:
            return (f"{shift} Ese desplazamiento general se descontó antes de medir el cambio, suponiendo que es "
                    "igual en toda la zona; si no lo es, parte de lo que queda puede seguir siendo general y no local.")
        return f"{shift} El porcentaje de cambio puede reflejar ese desplazamiento general y no un cambio local."
    together = {True: ", in the same direction", False: ", in opposite directions", None: ""}[same_direction]
    shift = (f"The level of the whole scene changed between the two dates (median HH {_db(hh, lang)} dB and HV "
             f"{_db(hv, lang)} dB{together}), perhaps from soil moisture or a radiometric effect.")
    if corrected:
        return (f"{shift} That general shift was removed before measuring change, assuming it is the same across "
                "the whole area; if it is not, part of what remains may still be general rather than local.")
    return f"{shift} The change percentage may reflect that general shift rather than a local change."


# --- Pasadas excluidas por catalog (excluded[] de la línea de tiempo, Antena) ----------------

EXCLUSION_REASONS = {
    "es": {"product_defect": "defecto del producto publicado"},
    "en": {"product_defect": "defect in the published product"},
}


def excluded_pass_text(day: str, reason: str, used_by_pair: bool, lang: Lang) -> str:
    """Una pasada que existe pero catalog declaró inservible: se dice, no se oculta."""
    label = EXCLUSION_REASONS[lang].get(reason, reason)
    if lang == "es":
        if used_by_pair:
            return (f"El catálogo excluye la pasada del {day} ({label}) y este par la usa: "
                    "su resultado no debe interpretarse.")
        return f"Además falta la pasada del {day} de esta serie: el catálogo la excluye ({label})."
    if used_by_pair:
        return (f"The catalog excludes the {day} pass ({label}) and this pair uses it: "
                "its result should not be interpreted.")
    return f"The {day} pass of this series is also missing: the catalog excludes it ({label})."


def subsidence_text(data: dict, zone: str | None, lang: Lang) -> dict:
    """Hundimiento en palabras de todos los días: qué se midió, qué se ve y qué no prueba (subsidence.json)."""
    where = _where(zone, lang)
    if data.get("status") != "computed":
        if lang == "es":
            return {"detected": f"No hay interferogramas NISAR suficientes{where} para medir si el suelo se hunde.",
                    "does_not_prove": "Sin medida no se puede decir si el suelo se hunde o no.", "missing": ""}
        return {"detected": f"There are not enough NISAR interferograms{where} to measure whether the ground is sinking.",
                "does_not_prove": "Without a measurement we cannot say whether the ground is sinking.", "missing": ""}
    days = data["days"]
    share = _fraction(round(data["sinking_fraction"], 3), lang)
    threshold = round(data["threshold_mm_yr"])
    fastest = round(data["max_rate_mm_yr"]) if data.get("max_rate_mm_yr") is not None else None
    noise = round(data["noise_mm_yr"]) if data.get("noise_mm_yr") is not None else None
    sinking = data["sinking_fraction"] >= 0.01
    if lang == "es":
        if sinking:
            detected = (f"En {days} días, parte del suelo{where} se alejó del satélite más que el resto: el {share} de lo "
                        f"medido se hunde al menos {threshold} mm al año respecto al resto de la zona, y lo más rápido "
                        f"llega a unos {fastest} mm al año. Es la huella típica de un hundimiento.")
        else:
            detected = (f"En {days} días no se ve que el suelo{where} se hunda más que el resto de la zona: nada supera "
                        f"los {threshold} mm al año que podemos distinguir del ruido.")
        return {
            "detected": detected,
            "does_not_prove": (
                "Es un movimiento relativo, respecto al resto de la zona, y en la dirección en que mira el satélite: no "
                "separa hundir de moverse de lado. El vapor de agua del aire puede sumar centímetros en un par."
            ),
            "missing": (f"La incertidumbre típica es de unos {noise} mm al año; con más fechas bajará. Falta comparar con "
                        "GPS o nivelación en campo." if noise is not None else "Falta comparar con GPS o nivelación en campo."),
        }
    if sinking:
        detected = (f"Over {days} days, part of the ground{where} moved away from the satellite more than the rest: "
                    f"{share} of what was measured is sinking at least {threshold} mm a year relative to the rest of the "
                    f"area, and the fastest reaches about {fastest} mm a year. That is the typical mark of subsidence.")
    else:
        detected = (f"Over {days} days the ground{where} does not appear to sink more than the rest of the area: nothing "
                    f"goes beyond the {threshold} mm a year we can tell apart from noise.")
    return {
        "detected": detected,
        "does_not_prove": (
            "It is relative motion, compared with the rest of the area, along the direction the satellite looks: it does "
            "not separate sinking from sideways motion. Water vapour in the air can add centimetres in a pair."
        ),
        "missing": (f"The typical uncertainty is about {noise} mm a year; more dates will lower it. A comparison with GPS "
                    "or field levelling is missing." if noise is not None else "A comparison with GPS or field levelling is missing."),
    }
