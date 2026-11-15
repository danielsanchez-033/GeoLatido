"""Generador de historias científicas: 17 secciones, cada afirmación con su evidencia.

Determinista, sin modelo de lenguaje: cada frase se arma con plantillas a partir de los resultados guardados en la
investigación. Toda cifra viene de un registro de evidencia (`evidence`) y la afirmación que la contiene lo cita
por id. Si un dato no existe, la frase lo dice; no hay frase de relleno con números.

Un modelo de lenguaje podría reescribir el estilo de `claims[].text` más adelante, pero solo con los mismos ids de
evidencia y sin añadir cifras: `check_traceability` lo comprobaría.
"""
from __future__ import annotations

import re

from .products import BY_ID

SECTIONS = [
    ("title", "Título"),
    ("question", "Pregunta de investigación"),
    ("geography", "Contexto geográfico"),
    ("importance", "Importancia del fenómeno"),
    ("period", "Periodo estudiado"),
    ("sources", "Fuentes de datos"),
    ("methodology", "Metodología"),
    ("initial_state", "Estado inicial"),
    ("transformations", "Transformaciones observadas"),
    ("events", "Acontecimientos relacionados"),
    ("evolution", "Evolución temporal"),
    ("findings", "Hallazgos"),
    ("interpretation", "Interpretación científica"),
    ("uncertainty", "Incertidumbre"),
    ("implications", "Implicaciones"),
    ("conclusions", "Conclusiones"),
    ("references", "Fuentes y referencias"),
]

IMPORTANCE = {
    "mining": "La minería transforma la superficie (tajos, jales, caminos) y puede alterar el drenaje y la estabilidad del terreno cercano a donde vive la gente.",
    "flood": "Las lluvias intensas pueden inundar calles y cauces en horas; saber qué observó un satélite, y qué no, ayuda a no sacar conclusiones falsas.",
    "landslide": "Las laderas empinadas con lluvia acumulada pueden moverse; la deformación lenta a veces precede a un deslizamiento, pero no siempre.",
    "deformation": "La subsidencia y la deformación lenta afectan a infraestructura y a viviendas; se miden con interferometría, no con potencia.",
    "glacier": "Los glaciares de salida de Groenlandia aportan hielo al océano; su velocidad, su frente y su elevación son magnitudes distintas.",
    "surface_change": "El radar ve cambios de la superficie de día y de noche y a través de las nubes, pero no dice por sí solo qué los causó.",
}

NUM = re.compile(r"\d")
CONF = {"low": "baja", "medium": "media"}
STATES = {"change_probable": "cambio probable", "no_detectable_change": "sin cambio detectable", "not_observable": "no observable"}


def pct(x: float | None) -> str:
    return "—" if x is None else f"{x * 100:.2f} %".replace(".", ",")


def num(x: float | None, nd: int = 2) -> str:
    return "—" if x is None else f"{x:.{nd}f}".replace(".", ",")


class Builder:
    def __init__(self):
        self.evidence: dict[str, dict] = {}
        self.sections: dict[str, list[dict]] = {k: [] for k, _ in SECTIONS}
        self.map: dict[str, dict | None] = {k: None for k, _ in SECTIONS}

    def ev(self, eid: str, kind: str, label: str, **details) -> str:
        if eid not in self.evidence:
            self.evidence[eid] = {"id": eid, "kind": kind, "label": label, **details}
        return eid

    def say(self, section: str, text: str, evidence: list[str] | None = None, kind: str = "statement"):
        self.sections[section].append({"text": text, "evidence": evidence or [], "kind": kind})


def generate(research: dict) -> dict:
    b = Builder()
    plan = research["plan"]
    areas = plan["areas"]
    period = plan["period"]
    disc = research.get("discovery") or []
    analyses = research.get("analysis") or []
    events = research.get("events") or []
    corr = research.get("correlations") or []
    synthetic = any(p["data_kind"] == "synthetic" for a in analyses for p in a.get("processed", []))

    m_plan = b.ev("method:plan", "method", "Interpretación de la pregunta (reglas deterministas)", parser=plan.get("parser"), decisions=plan.get("decisions", []))
    names = " y ".join(a["name"] for a in areas) or "un área sin resolver"
    b.say("title", f"{'Comparación: ' if plan.get('comparative') else ''}{names}, {period['start'][:4]}–{period['end'][:4]}", [m_plan])
    if synthetic:
        b.say("title", "Esta historia usa datos sintéticos: no describe observaciones reales.", [], "warning")
    b.say("question", plan["question"], [m_plan])
    for d in plan.get("decisions", []):
        b.say("question", d, [m_plan], "decision")

    for a in areas:
        eid = b.ev(f"place:{a['id']}", "external_source", a["name"], bbox=a["bbox"], source=a["source"], approximate=a.get("approximate", False))
        w, s, e, n = a["bbox"]
        b.say("geography", f"{a['name']}: caja de {num(w, 3)}° a {num(e, 3)}° de longitud y {num(s, 3)}° a {num(n, 3)}° de latitud ({'delimitación aproximada' if a.get('approximate') else 'delimitación de la fuente'}).", [eid])
        if a.get("note"):
            b.say("geography", a["note"], [eid], "caveat")
        b.map["geography"] = b.map["geography"] or {"bbox": a["bbox"]}

    for ph in plan["phenomena"]:
        b.say("importance", IMPORTANCE.get(ph, IMPORTANCE["surface_change"]), [], "context")

    b.say("period", f"Del {period['start']} al {period['end']}.", [m_plan])
    for note in plan.get("notes", []):
        b.say("period", note, [m_plan], "caveat")

    # Fuentes: un registro por producto y área, con lo que dijo CMR.
    processed_areas = {a["area"] for a in analyses if a.get("processed")}
    for d in disc:
        for p in d["products"]:
            eid = b.ev(f"product:{d['area']}:{p['product']}", "product", f"{p['short_name']} en {d['area']}", **{k: p[k] for k in ("status", "hits", "first_date", "last_date", "distinct_dates", "median_revisit_days", "polarizations_seen", "access", "sensor", "level")})
            if p["status"] == "found":
                analyzed = p["analyzed_here"] and d["area"] in processed_areas
                span = f"del {p['first_date']} al {p['last_date']}" if p["listed"] >= (p["hits"] or 0) else f"los {p['listed']} más recientes listados van del {p['first_date']} al {p['last_date']}"
                acceso = {"public": "público", "earthdata_login": "con cuenta de Earthdata", "eodms_login": "con cuenta de EODMS"}.get(p["access"], p["access"])
                cuantos = f"al menos {p['hits']}" if p.get("hits_is_lower_bound") else str(p["hits"])
                b.say("sources", f"{p['sensor']} — {p['level']} ({p['short_name']}): {cuantos} productos en {d['area']}; {span}; acceso {acceso}. {'Analizado en esta plataforma.' if analyzed else 'Solo descubierto, no analizado aquí.'}", [eid])
            elif p["status"] == "none_found":
                b.say("sources", f"{p['short_name']}: ningún producto en {d['area']} para el periodo.", [eid])
            else:
                b.say("sources", f"{p['short_name']}: el catálogo no respondió; no se sabe si hay datos.", [eid], "caveat")
        for c in d.get("compatibility", []):
            b.say("sources", c["detail"], [b.ev(f"method:compat:{d['area']}:{c['code']}", "method", "Comprobación de compatibilidad", code=c["code"])], "caveat")

    m_change = b.ev("method:change", "method", "Detección de cambio por par (processor + verdicts)", detail="HH/HV en dB, suavizado 5×5, umbral por par, desplazamiento de escena restado, celdas de 1 km; estado por fracción observada y fracción con cambio.")
    m_temp = b.ev("method:temporal", "method", "Análisis temporal", detail="Theil-Sen, media móvil de 3, anomalías por MAD (z ≥ 3,5), un punto de cambio por desplazamiento de la media, huecos.")
    m_corr = b.ev("method:correlation", "method", "Correlación con acontecimientos", detail="Niveles: temporal, espacial; estadística no calculada; causalidad nunca afirmada.")
    b.say("methodology", "1) Se buscaron en el catálogo CMR de NASA los productos de cada fuente que cubren cada área y periodo, sin descargarlos.", [m_plan])
    b.say("methodology", "2) Donde este proyecto procesó NISAR GCOV, cada par de fechas se clasificó en cambio probable, sin cambio detectable o no observable.", [m_change])
    b.say("methodology", "3) La fracción de cambio de los pares consecutivos se trató como serie temporal: tendencia, anomalías, punto de cambio y huecos.", [m_temp])
    b.say("methodology", "4) Los acontecimientos verificados se cruzaron en tiempo y lugar con los pares, sin inferir causas.", [m_corr])

    any_series = False
    for an in analyses:
        for blk in an.get("series", []):
            pts = blk["points"]
            if not pts:
                continue
            any_series = True
            first = pts[0]
            eid0 = b.ev(f"calc:{blk['aoi']}:{blk['series']}:{first['pair_id']}", "calculation", f"Par {first['from']} → {first['to']} ({blk['series']})", **first, data_kind=blk["data_kind"], verdict_path=f"/api/verdicts/aois/{blk['aoi']}/series/{blk['series']}/verdicts/{first['pair_id']}")
            acq0 = b.ev(f"acq:{first['granules'][0]}" if first["granules"] else "acq:unknown", "acquisition", first["granules"][0] if first["granules"] else "desconocida")
            b.say("initial_state", f"La serie {blk['series']} ({'sintética' if blk['data_kind'] == 'synthetic' else 'real'}) empieza el {first['from']}. En su primer par, hasta el {first['to']}, el {pct(first['changed_fraction'])} de lo observado mostró cambio probable (estado del par: {STATES.get(first['state'], first['state'])}).", [eid0, acq0, m_change])
            b.map["initial_state"] = b.map["initial_state"] or {"aoi": blk["aoi"], "series": blk["series"], "pair_id": first["pair_id"]}
            for p in pts:
                if p["state"] == "change_probable":
                    eid = b.ev(f"calc:{blk['aoi']}:{blk['series']}:{p['pair_id']}", "calculation", f"Par {p['from']} → {p['to']} ({blk['series']})", **p, data_kind=blk["data_kind"], verdict_path=f"/api/verdicts/aois/{blk['aoi']}/series/{blk['series']}/verdicts/{p['pair_id']}")
                    b.say("transformations", f"Entre el {p['from']} y el {p['to']} ({blk['series']}): cambio probable en el {pct(p['changed_fraction'])} de lo observado; cambio medio de HH {num(p['mean_change_hh_db'])} dB.", [eid, m_change])
                    b.map["transformations"] = b.map["transformations"] or {"aoi": blk["aoi"], "series": blk["series"], "pair_id": p["pair_id"]}
            for fw in blk.get("full_window", []):
                fid = b.ev(f"calc:{blk['aoi']}:{blk['series']}:{fw['pair_id']}", "calculation", f"Ventana completa {fw['from']} → {fw['to']} ({blk['series']})", **fw, data_kind=blk["data_kind"], verdict_path=f"/api/verdicts/aois/{blk['aoi']}/series/{blk['series']}/verdicts/{fw['pair_id']}")
                b.say("transformations", f"De la primera a la última fecha ({fw['from']} → {fw['to']}, {blk['series']}): {pct(fw['changed_fraction'])} de lo observado con cambio; estado {STATES.get(fw['state'], fw['state'])}. Acumula todo lo ocurrido entre medias, incluido el cambio que cada par por separado no supera.", [fid, m_change])
                b.map["transformations"] = b.map["transformations"] or {"aoi": blk["aoi"], "series": blk["series"], "pair_id": fw["pair_id"]}
            if blk["not_observable_pairs"]:
                b.say("transformations", f"{len(blk['not_observable_pairs'])} pares de {blk['series']} no fueron observables: ahí no se puede decir si hubo cambio.", [m_change], "caveat")
            a = blk.get("analysis")
            if a:
                ta = b.ev(f"calc:temporal:{blk['series']}", "calculation", f"Serie temporal de {blk['series']}", **{k: a[k] for k in ("n", "span_days", "median", "robust_spread", "theil_sen_per_30d", "change_point", "anomalies", "gaps")}, series_label=a["label"])
                b.say("evolution", f"{blk['series']}: {a['n']} pares observados en {a['span_days']} días; mediana de la fracción de cambio {pct(a['median'])}; pendiente de Theil-Sen {pct(a['theil_sen_per_30d']) if a['theil_sen_per_30d'] is not None else 'no calculable (pocos puntos)'} por 30 días.", [ta, m_temp])
                if a["change_point"]:
                    cp = a["change_point"]
                    b.say("evolution", f"Candidato a punto de cambio en {cp['date']}: la media pasa de {pct(cp['mean_before'])} a {pct(cp['mean_after'])}. Es un candidato estadístico, no un cambio confirmado.", [ta, m_temp])
                else:
                    b.say("evolution", "No aparece un punto de cambio claro en la serie con el criterio usado.", [ta, m_temp])
                for g in a["gaps"]:
                    b.say("evolution", f"Hueco de observación del {g['from']} al {g['to']} ({g['days']} días){' que cruza el hueco declarado por ASF' if g['declared_gap'] else ''}: falta de datos, no estabilidad.", [ta], "caveat")
                b.say("evolution", "La serie es demasiado corta para hablar de estacionalidad o de diferencias entre años." if a["seasonality"] == "insufficient_span" else "Estacionalidad no calculada.", [ta], "caveat")
                b.map["evolution"] = b.map["evolution"] or {"aoi": blk["aoi"], "series": blk["series"]}
    if not any_series:
        b.say("initial_state", "Ninguna serie procesada por esta plataforma cubre las áreas y el periodo: no hay estado inicial medido.", [], "caveat")
        b.say("transformations", "Sin series procesadas no se pueden describir transformaciones. La disponibilidad de datos (Fuentes) no es una medición.", [], "caveat")
        b.say("evolution", "Sin serie temporal medida.", [], "caveat")
    for an in analyses:
        for lim in an.get("limitations", []):
            b.say("uncertainty", lim, [], "caveat")

    # Acontecimientos y correlación. Con muchas fuentes abiertas puede haber cientos (sismos): la historia cuenta
    # todos los del registro, los que caen en un par observado y hasta MAX_POR_FUENTE de cada otra fuente.
    MAX_POR_FUENTE = 6
    by_id = {}
    for evset in events:
        for e in evset["events"]:
            by_id[e["id"]] = e
    en_pares = {c["event_id"] for c in corr for link in c["links"] if link["event_inside_interval"]}
    por_origen: dict[str, list[dict]] = {}
    for e in by_id.values():
        por_origen.setdefault(e["origin"], []).append(e)
    elegidos: list[dict] = []
    for origen, lista in por_origen.items():
        lista.sort(key=lambda e: (e["id"] not in en_pares, -(e.get("magnitude") or 0), e["date"]), reverse=False)
        tope = len(lista) if origen == "registry" else MAX_POR_FUENTE
        elegidos += lista[:tope]
        if len(lista) > tope:
            sid = b.ev(f"calc:events_count:{origen}", "calculation", f"Acontecimientos de {origen}", total=len(lista), shown=tope, ids=[e["id"] for e in lista])
            b.say("events", f"{len(lista) - tope} acontecimientos más de {origen} en el área y el periodo (en el registro de evidencia).", [sid])
    for evset in events:
        for st in evset.get("sources", []):
            # Las fuentes sin credencial no se citan: no se consultaron y la API lo dice en events[].sources.
            if st["status"] == "error":
                b.say("events", f"{st['name']}: no respondió en {evset['area']}; puede faltar algún acontecimiento.", [], "caveat")
    _dedupe(b.sections["events"])
    for e in sorted(elegidos, key=lambda e: e["date"]):
        srcs = [s for s in e.get("sources", []) if s.get("url")]
        eid = b.ev(f"event:{e['id']}", "external_source", e.get("title") or e["id"], date=e["date"], urls=[s["url"] for s in srcs], origin=e["origin"], confidence=e.get("confidence"), geometry_precision=e.get("geometry_precision"))
        b.say("events", f"{e['date']}: {e.get('title')} ({e['origin']}). {e.get('description') or ''}".strip(), [eid])
        if e.get("observability"):
            o = e["observability"]
            oid = b.ev(f"calc:event_obs:{e['id']}", "calculation", f"Observabilidad de {e['id']} (verdicts /events)", **{k: o.get(k) for k in ("state", "cause", "previous_pass", "next_pass", "persistence_hours")})
            b.say("events", f"¿Pudo verlo NISAR? {o.get('state')}{' (' + o['cause_label'] + ')' if o.get('cause_label') else ''}: pasada anterior {o.get('previous_pass')}, siguiente {o.get('next_pass')}, con una persistencia supuesta de {o.get('persistence_hours')} h.", [oid, eid])
        for u in e.get("unknown", []):
            b.say("events", f"Sin verificar: {u}", [eid], "caveat")
        if e.get("bbox") and not b.map["events"]:
            b.map["events"] = {"bbox": e["bbox"]}
    for e in by_id.values():  # los no listados siguen citables por la correlación
        if f"event:{e['id']}" not in b.evidence:
            b.ev(f"event:{e['id']}", "external_source", e.get("title") or e["id"], date=e["date"], urls=[x["url"] for x in e.get("sources", []) if x.get("url")], origin=e["origin"])
    if not by_id:
        b.say("events", "No se encontraron acontecimientos en ninguna de las fuentes consultadas para estas áreas y fechas.", [m_corr])
    for c in corr:
        for link in c["links"]:
            if link["event_inside_interval"]:
                b.say("events", f"{c['event_id']} cae dentro del par {link['pair_id']} ({link['series']}), que salió {STATES.get(link['pair_state'], link['pair_state'])}. Nivel de relación: {link['level']}. Coincidir no prueba causa.", [f"event:{c['event_id']}", m_corr])

    # Hallazgos.
    findings = [f for an in analyses for f in an.get("findings", [])]
    for f in findings:
        eid = b.ev(f"finding:{f['id']}", "calculation", f"Hallazgo {f['id']}", **{k: f[k] for k in ("start", "end", "magnitude", "confidence", "confidence_reasons", "detection", "geometry_kind", "verdict_path", "data_kind")})
        acq = [b.ev(f"acq:{g}", "acquisition", g) for g in f["granules"]]
        b.say("findings", f"{f['start']} → {f['end']} ({f['series']}): {pct(f['magnitude']['changed_fraction'])} de lo observado con cambio probable; confianza {CONF.get(f['confidence'], f['confidence'])} ({'; '.join(f['confidence_reasons']) or 'sin motivos de reserva, pero sin calibrar'}).", [eid, *acq, m_change])
        b.map["findings"] = b.map["findings"] or {"aoi": f["aoi"], "series": f["series"], "pair_id": f["pair_id"]}
        for h in f["hypotheses"][:3]:
            b.say("interpretation", f"Hipótesis compatible con {f['pair_id']}: {h}", [eid], "hypothesis")
        for lim in f["limitations"]:
            b.say("uncertainty", f"{f['pair_id']}: {lim}", [eid], "caveat")
    if not findings:
        b.say("findings", "No hay hallazgos de cambio en las series procesadas para este periodo, o no hay series procesadas.", [m_change])

    ins = research.get("insar") or []
    for i in ins:
        iid = b.ev(f"method:insar:{i['area']}", "method", f"Evaluación InSAR de {i['area']}", products=i["products"])
        b.say("interpretation", f"{i['area']}: {i['reason']}", [iid], "caveat")
        for o in i["options"]:
            b.say("implications", f"Siguiente paso posible en {i['area']}: {o['what']} {o['next_step']}", [iid])
    risk = research.get("risk") or []
    for r in risk:
        rid = b.ev(f"method:susceptibility:{r['area']}", "method", f"Inventario de factores de {r['area']}", factors=r["factors"])
        missing = [f["factor"] for f in r["factors"] if f["status"] in ("missing", "not_in_artifacts", "not_processed")]
        if r["factors"]:
            b.say("implications", f"{r['area']}: {r['statement']} Faltan: {', '.join(missing) or 'ninguno'}.", [rid], "caveat")

    b.say("uncertainty", "Ningún umbral de decisión se ha contrastado con verdad de campo (calibrated: false).", [m_change], "caveat")
    b.say("uncertainty", "El cambio de radar puede deberse a humedad del suelo, vegetación, geometría de observación o ruido, además de a una transformación real.", [m_change], "caveat")

    comp = research.get("comparison")
    if comp and len(comp["areas"]) > 1:
        cid = b.ev("calc:comparison", "calculation", "Comparación entre áreas", rows=comp["areas"])
        for row in comp["areas"]:
            b.say("conclusions", f"{row['name']}: {row['nisar_gcov_acquisitions'] if row['nisar_gcov_acquisitions'] is not None else 'sin dato de'} adquisiciones NISAR GCOV, {row['observed_pairs']} pares observados por esta plataforma, {row['pairs_change_probable']} con cambio probable.", [cid])
        b.say("conclusions", comp["warning"], [cid], "caveat")
    n_change = sum(1 for f in findings if f["verdict_state"] == "change_probable")
    b.say("conclusions", f"Hallazgos con cambio probable: {n_change}. Todo cambio se presenta como observación del radar con sus límites, no como causa ni como daño." if any_series else "Con los datos procesados disponibles no se puede responder la pregunta con mediciones; la historia documenta qué datos existen para hacerlo.", [m_change])

    citadas = {eid for claims in b.sections.values() for c in claims for eid in c["evidence"]}
    for e in b.evidence.values():
        if e["id"] not in citadas:
            continue
        if e["kind"] == "external_source":
            for u in e.get("urls") or []:
                b.say("references", f"{e['label']}: {u}", [e["id"]])
        if e["kind"] == "product":
            sn = e["label"].split(" en ")[0]
            b.say("references", f"NASA CMR, colección {sn}: https://cmr.earthdata.nasa.gov/search/collections.json?short_name={sn}", [e["id"]])
    _dedupe(b.sections["references"])

    chapters = [
        {"key": k, "title": t, "claims": b.sections[k], "map": b.map[k]}
        for k, t in SECTIONS
    ]
    story = {
        "research_id": research["id"],
        "title": b.sections["title"][0]["text"],
        "data_kind": "synthetic" if synthetic else "real_or_catalog",
        "chapters": chapters,
        "evidence": list(b.evidence.values()),
        "generator": "template-v1",
    }
    story["traceability"] = check_traceability(story)
    return story


def _dedupe(claims: list[dict]):
    seen = set()
    keep = []
    for c in claims:
        if c["text"] not in seen:
            seen.add(c["text"])
            keep.append(c)
    claims[:] = keep


# Secciones donde una cifra puede venir de la pregunta o del contexto sin evidencia numérica propia.
FREE_NUMBERS = {"question", "importance"}


def check_traceability(story: dict) -> dict:
    """Toda afirmación con cifras debe citar al menos una evidencia existente; toda evidencia citada debe existir."""
    ids = {e["id"] for e in story["evidence"]}
    unsupported, dangling = [], []
    for ch in story["chapters"]:
        for c in ch["claims"]:
            for eid in c["evidence"]:
                if eid not in ids:
                    dangling.append({"chapter": ch["key"], "evidence": eid})
            if ch["key"] not in FREE_NUMBERS and NUM.search(c["text"]) and not c["evidence"]:
                unsupported.append({"chapter": ch["key"], "text": c["text"]})
    return {"ok": not unsupported and not dangling, "unsupported_numeric_claims": unsupported, "dangling_evidence": dangling}


def to_markdown(story: dict) -> str:
    lines = [f"# {story['title']}", ""]
    if story["data_kind"] == "synthetic":
        lines += ["> **Datos sintéticos**: esta historia no describe observaciones reales.", ""]
    for ch in story["chapters"][1:]:
        lines += [f"## {ch['title']}", ""]
        for c in ch["claims"]:
            refs = " ".join(f"[{e}]" for e in c["evidence"])
            prefix = {"caveat": "⚠ ", "hypothesis": "Hipótesis: ", "warning": "⚠ "}.get(c["kind"], "")
            lines.append(f"- {prefix}{c['text']} {refs}".rstrip())
        lines.append("")
    lines += ["## Registro de evidencia", ""]
    for e in story["evidence"]:
        lines.append(f"- **{e['id']}** ({e['kind']}): {e['label']}")
    lines += ["", f"Generado con `{story['generator']}`. Trazabilidad: {'correcta' if story['traceability']['ok'] else 'con fallos'}."]
    return "\n".join(lines) + "\n"


__all__ = ["generate", "to_markdown", "check_traceability", "BY_ID"]
