"""Evaluaciones que dicen qué se puede afirmar con los datos disponibles: InSAR, susceptibilidad y comparación.

Ninguna produce una puntuación de riesgo ni un desplazamiento: este proyecto no lee fase ni tiene los factores
(geología, red hidrográfica, uso de suelo, inventario de deslizamientos) para hacerlo con rigor. Lo que sí hacen es
inventariar qué entradas existen para el área, de qué fuente, y qué faltaría.
"""
from __future__ import annotations

TERMS = {
    "susceptibility": "Propensión del terreno a un fenómeno por sus condiciones (pendiente, geología, drenaje). No dice cuándo.",
    "hazard": "Probabilidad de que el fenómeno ocurra con cierta intensidad en un periodo. Requiere frecuencia observada.",
    "exposure": "Personas, viviendas e infraestructura situadas donde el fenómeno puede ocurrir.",
    "vulnerability": "Cuánto daño sufriría lo expuesto ante el fenómeno. Requiere datos socioeconómicos y constructivos.",
    "risk": "Combinación de amenaza, exposición y vulnerabilidad. No se calcula en esta plataforma.",
}


def _product(discovery: list[dict], area_id: str, pid: str) -> dict | None:
    for d in discovery:
        if d["area"] == area_id:
            return next((p for p in d["products"] if p["product"] == pid), None)
    return None


def _status(p: dict | None) -> str:
    return "not_queried" if p is None else p["status"]


def insar(area: dict, discovery: list[dict]) -> dict:
    gunw = _product(discovery, area["id"], "nisar_gunw")
    disp = _product(discovery, area["id"], "opera_disp_s1")
    slc = _product(discovery, area["id"], "s1a_slc")
    options = []
    if disp and disp["status"] == "found":
        options.append({
            "path": "opera_disp_s1",
            "what": f"{disp['hits']} productos OPERA DISP-S1 con desplazamiento LOS ya calculado (Sentinel-1, banda C).",
            "next_step": "Leer las capas de desplazamiento y coherencia con una cuenta de Earthdata (MintPy o xarray).",
        })
    if gunw and gunw["status"] == "found":
        options.append({
            "path": "nisar_gunw",
            "what": f"{gunw['hits']} interferogramas NISAR GUNW (banda L) con fase desenvuelta y coherencia.",
            "next_step": "Serie temporal con MintPy sobre los GUNW de una misma pista y marco.",
        })
    if slc and slc["status"] == "found":
        options.append({
            "path": "s1a_slc",
            "what": f"{slc['hits']} escenas SLC de Sentinel-1A: materia prima para procesar con ISCE2/ISCE3 o HyP3.",
            "next_step": "Pedir pares a HyP3 (INSAR_GAMMA o INSAR_ISCE_BURST) con una cuenta de Earthdata.",
        })
    return {
        "area": area["id"],
        "status": "not_processed_here",
        "displacement_available": False,
        "reason": "Los artefactos de este proyecto son NISAR GCOV: potencia sin fase. No se generan interferogramas ni "
        "desplazamientos aquí, y no se simulan.",
        "products": {"nisar_gunw": _status(gunw), "opera_disp_s1": _status(disp), "s1a_slc": _status(slc)},
        "options": options,
        "caveats": [
            "El desplazamiento interferométrico es en la línea de vista (LOS), no vertical: separar vertical y este-oeste "
            "exige combinar órbitas ascendente y descendente.",
            "La decorrelación (vegetación, cambios de superficie, nieve) deja zonas sin medida.",
            "Layover y sombra en laderas empinadas impiden medir.",
            "La atmósfera (vapor de agua) puede imitar deformación; hace falta corregirla o promediar muchas fechas.",
        ],
        "tools_evaluated": {
            "HyP3 (ASF)": "Procesado en la nube de pares Sentinel-1 bajo demanda; requiere cuenta de Earthdata.",
            "ISCE2 / ISCE3": "Procesadores de JPL; ISCE3 es el de NISAR. Pesados para esta pila de 16 GB.",
            "MintPy": "Series temporales a partir de interferogramas (GUNW, HyP3, ISCE).",
            "ESA SNAP": "Interfaz gráfica y gpt; útil para Sentinel-1, no integrado en contenedores aquí.",
        },
    }


def susceptibility(area: dict, phenomena: list[str], discovery: list[dict], analysis: dict, relief_available: bool) -> dict:
    factors = []

    def add(name, phen, source, status, detail=""):
        factors.append({"factor": name, "phenomenon": phen, "source": source, "status": status, "detail": detail})

    from .sources import inegi_layers

    inegi = inegi_layers(area["bbox"])

    def wms(code: str) -> str:
        layer = next((x for x in inegi if x["code"] == code), None)
        return layer["getmap"] if layer else ""

    want_flood = "flood" in phenomena
    want_slide = any(p in phenomena for p in ("landslide", "deformation", "mining"))
    if want_flood:
        dswx = _product(discovery, area["id"], "opera_dswx_s1")
        add("Extensión de agua (SAR)", "flood", "OPERA DSWx-S1", _status(dswx),
            f"{dswx['hits']} productos en el periodo" if dswx and dswx["hits"] is not None else "")
        gpm = _product(discovery, area["id"], "gpm_imerg_late")
        add("Precipitación diaria", "flood", "GPM IMERG Late", _status(gpm),
            "Descubierta; leer los valores requiere cuenta de Earthdata (no se calcula acumulado aquí).")
        add("Historial de inundaciones", "flood", "config/events + EONET", "partial",
            "Acontecimientos del registro, EONET, GDACS y activaciones de Copernicus EMS; no es un inventario oficial completo.")
        if inegi:
            add("Cuencas", "flood", "INEGI WMS (c402)", "available_layer", wms("c402"))
            add("Red hidrográfica", "flood", "INEGI WMS (c310)", "available_layer", wms("c310"))
            add("Uso de suelo", "flood", "INEGI WMS (c783, serie VII)", "available_layer", wms("c783"))
            add("Asentamientos e infraestructura", "flood", "INEGI WMS (c102, localidades urbanas)", "available_layer", wms("c102"))
        else:
            for f in ("Red hidrográfica", "Cuencas", "Uso de suelo", "Asentamientos e infraestructura"):
                add(f, "flood", "—", "missing", "Fuera de México no hay un conector (fuentes posibles: HydroSHEDS, ESA WorldCover, OSM).")
    if want_slide or want_flood:
        add("Elevación y pendiente", "both", "Copernicus GLO-30 (processor) / NASADEM",
            "available" if relief_available else "not_in_artifacts",
            "El DEM está en los artefactos de la zona" if relief_available else "Los artefactos de esta zona no traen DEM.")
    if want_slide:
        disp = _product(discovery, area["id"], "opera_disp_s1")
        add("Deformación InSAR", "landslide", "OPERA DISP-S1 / NISAR GUNW", _status(disp), "Ver evaluación InSAR: no se procesa aquí.")
        ndvi = _product(discovery, area["id"], "modis_ndvi")
        add("Cobertura vegetal", "landslide", "MODIS MOD13Q1", _status(ndvi))
        add("Cambio superficial (SAR)", "landslide", "NISAR GCOV (este proyecto)",
            "available" if analysis.get("processed") else "not_processed")
        add("Inventario de deslizamientos", "landslide", "NASA Global Landslide Catalog (1988-2016)", "available_catalog",
            "Puntos del catálogo en la pestaña de acontecimientos; no cubre después de 2016.")
        if inegi:
            add("Suelos", "landslide", "INEGI WMS (c416)", "available_layer", wms("c416"))
            add("Humedad del suelo", "landslide", "INEGI WMS (c407)", "available_layer", wms("c407"))
        else:
            add("Humedad del suelo", "landslide", "—", "missing", "Fuente posible: NASA SMAP (cuenta de Earthdata).")
        add("Geología", "landslide", "—", "missing",
            "SGM (GeoInfoMex) no tiene un servicio de mapas comprobado; fuera de México, sin conector.")
    return {
        "area": area["id"],
        "assessment_level": "factor_inventory",
        "score": None,
        "layers": inegi,
        "statement": "Inventario de factores disponibles. No es un mapa de susceptibilidad, ni de amenaza, ni de riesgo, "
        "ni un pronóstico. No genera alertas.",
        "terms": TERMS,
        "factors": factors,
    }


def compare(areas: list[dict], discovery: list[dict], analyses: list[dict], phenomena: list[str]) -> dict:
    rows = []
    for a in areas:
        d = next((x for x in discovery if x["area"] == a["id"]), {"products": []})
        an = next((x for x in analyses if x["area"] == a["id"]), {})
        sar = [p for p in d["products"] if p["kind"] in ("sar", "insar") and p["hits"]]
        changes = [pt["changed_fraction"] for s in an.get("series", []) for pt in s["points"] if pt["state"] != "not_observable"]
        rows.append({
            "area": a["id"],
            "name": a["name"],
            "sar_products_found": [p["product"] for p in sar],
            "nisar_gcov_acquisitions": next((p["hits"] for p in d["products"] if p["product"] == "nisar_gcov"), None),
            "median_revisit_days_nisar": next((p["median_revisit_days"] for p in d["products"] if p["product"] == "nisar_gcov"), None),
            "processed_series": [s["series"] for s in an.get("series", [])],
            "observed_pairs": len(changes),
            "pairs_change_probable": sum(1 for s in an.get("series", []) for pt in s["points"] if pt["state"] == "change_probable"),
            "median_changed_fraction": sorted(changes)[len(changes) // 2] if changes else None,
            "findings": len(an.get("findings", [])),
            "data_quality_notes": an.get("limitations", []),
        })
    return {
        "areas": rows,
        "comparable_indicators": ["nisar_gcov_acquisitions", "median_revisit_days_nisar", "observed_pairs", "pairs_change_probable"],
        "warning": "La fracción de cambio de radar solo es comparable entre áreas procesadas con el mismo método y "
        "sensor. Fenómenos distintos (por ejemplo, minería y glaciares) no se comparan en magnitud física: se comparan "
        "frecuencia de observación, calidad de datos y número de hallazgos.",
        "phenomena": phenomena,
    }
