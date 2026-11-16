"""API de veredictos: el contrato principal que consume el frontend."""
from __future__ import annotations

import json
import logging
import os
import threading
import datetime as dt
from contextlib import asynccontextmanager
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable, Literal
from urllib.parse import quote

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from . import export, narrative, optical, quality, rules, search, water
from .catalog import (
    CatalogUnavailable,
    FootprintSource,
    HttpFootprints,
    HttpOpera,
    HttpOptical,
    HttpTimeline,
    OperaReference,
    OperaSource,
    OpticalReference,
    OpticalSource,
    ExcludedPass,
    PassTime,
    TimelineSource,
    granule_key,
)
from .store import OutsideLayer, Store

TILES_PREFIX = "/tiles/cog/tiles/WebMercatorQuad/{z}/{x}/{y}.png"
STATE_COLORS = {
    "0": "#00000000",
    "1": "#e4572eff",
    "10": "#6b7280b3",
    "11": "#6b7280b3",
    "12": "#6b7280b3",
    "13": "#6b7280b3",
    "14": "#6b7280b3",
    "15": "#6b7280b3",
}


class Summary(BaseModel):
    detected: str
    does_not_prove: str
    missing: str


LatencyStatus = Literal["available", "synthetic", "catalog_unavailable", "granule_not_in_catalog", "not_published"]


class PassFreshness(BaseModel):
    date: dt.date
    granule: str
    acquired_at: dt.datetime | None = Field(
        description="Inicio de la adquisición en UTC, según la línea de tiempo de catalog. null si no se conoce."
    )
    published_at: dt.datetime | None = Field(
        description="Fecha 'updated' de CMR en UTC: aproxima la publicación. null si no se conoce."
    )
    publication_latency_hours: float | None = Field(
        description="Horas entre la adquisición y published_at, tal como las da catalog. null si no se conoce."
    )
    latency_status: LatencyStatus = Field(
        description="Por qué hay o no hay latencia: dato real disponible, dato sintético, catalog sin respuesta, "
        "gránulo ausente del catálogo o gránulo sin fecha de publicación."
    )
    age_days: int = Field(description="Días entre la fecha de la pasada y reference_date.")


class Freshness(BaseModel):
    reference_date: dt.date = Field(description="Fecha UTC con la que se calcula age_days (hoy, al responder).")
    published_at_basis: Literal["cmr_updated"] = "cmr_updated"
    before: PassFreshness
    after: PassFreshness


class DateQuality(BaseModel):
    date: dt.date
    valid_fraction: float = Field(description="Fracción de píxeles válidos de la fecha, según Eco.")
    median_hh_db: float | None
    median_hv_db: float | None
    deviation_hh_db: float | None = Field(description="Mediana de la fecha menos la mediana de las medianas de la serie.")
    deviation_hv_db: float | None
    flags: list[str] = Field(description="radiometric_outlier: la fecha se aparta de la serie más que el umbral de Eco. Aviso, no exclusión.")


class PairQuality(BaseModel):
    source: Literal["manifest_qa"] = Field("manifest_qa", description="Copiado de dates[].qa del manifiesto de Eco (T-ECO-03).")
    before: DateQuality | None = Field(description="QA de from_date. null si el manifiesto no lo trae.")
    after: DateQuality | None = Field(description="QA de to_date. null si el manifiesto no lo trae.")


class ExcludedPassOut(BaseModel):
    granule: str = Field(description="granule_id que catalog excluye.")
    series: str
    date: dt.date
    reason: str = Field(description="Código del motivo según catalog; product_defect: fallo en el producto publicado.")
    evidence: str = Field(description="Cómo lo comprobó Antena.")


class Receipt(BaseModel):
    data_kind: Literal["real", "synthetic"]
    maturity: str
    series: str
    track: int
    direction: str
    frame: int
    mode: str
    polarization: str
    crid: str
    granules: list[str]
    spans_data_gap: bool
    notices: list[str]
    freshness: Freshness
    quality: PairQuality = Field(description="Control de calidad de Eco de las dos fechas (RF-BAL-09).")
    excluded_passes: list[ExcludedPassOut] = Field(
        description="Pasadas de esta serie que catalog excluye, entre from_date y to_date ambas incluidas. "
        "Vacía con datos sintéticos o si catalog no respondió."
    )


class OpticalTileOut(BaseModel):
    tile: str = Field(description="Tesela MGRS de unos 110 km de lado.")
    cloud_cover: float = Field(description="Porcentaje de nubes de la tesela completa, no de la zona.")
    visual_url: str = Field(description="COG en color verdadero (TCI) en el bucket público de Sentinel-2.")
    tile_url: str = Field(description="Plantilla XYZ por el gateway: TiTiler lee visual_url.")
    bbox: list[float] | None = Field(
        default=None,
        min_length=4,
        max_length=4,
        description="Caja de los datos de la escena en WGS84, [oeste, sur, este, norte], vía catalog: la del item STAC "
        "de Earth Search o, si falta, la de su huella; no la del cuadrado MGRS completo. Sirve como bounds de la "
        "fuente en el mapa, para no pedir teselas fuera de los datos. Si oeste > este, cruza el antimeridiano. "
        "null si catalog no la da o no es válida.",
    )


class OpticalScene(BaseModel):
    platform: str
    acquired_at: dt.datetime = Field(description="Hora UTC de la primera tesela de la adquisición.")
    days_from_radar: int = Field(description="Días respecto a radar_date; negativo si es anterior.")
    covers_aoi: bool = Field(description="Las teselas juntas cubren toda la zona.")
    max_cloud_cover: float = Field(description="Mayor nubosidad entre sus teselas. Es de la tesela, no de la zona.")
    attribution: str = Field(description="Texto de atribución que debe mostrarse junto a la imagen.")
    tiles: list[OpticalTileOut]


OpticalStatus = Literal["clear", "cloudy", "partial_coverage", "none_in_window", "catalog_unavailable"]


class OpticalSide(BaseModel):
    status: OpticalStatus = Field(
        description="clear: cubre la zona con nubosidad <= max_cloud_cover. cloudy: la menos nublada que cubre la "
        "zona, por encima del límite. partial_coverage: ninguna cubre la zona entera. none_in_window: ninguna a "
        "search_days o menos. catalog_unavailable: catalog no respondió."
    )
    radar_date: dt.date
    radar_acquired_at: dt.datetime | None = Field(
        description="Hora UTC de la pasada de radar. Si se conoce, antes y después se comparan al segundo; "
        "si es null, se compara por día UTC y una escena del mismo día cuenta en los dos lados."
    )
    scene: OpticalScene | None


class OpticalEvidence(BaseModel):
    data_kind: Literal["real"] = Field("real", description="Las escenas ópticas son siempre datos reales.")
    source: str | None = Field(description="Buscador de escenas usado por catalog. null si no respondió.")
    collection: str | None
    license: str | None
    license_url: str | None
    cloud_cover_basis: Literal["tile"] = "tile"
    max_cloud_cover: float = Field(description="Nubosidad máxima por tesela, en %. Valor inicial sin calibrar.")
    search_days: int = Field(description="Días máximos entre la escena óptica y su fecha de radar.")
    before: OpticalSide = Field(description="Escena más cercana a from_date que no es posterior a la pasada.")
    after: OpticalSide = Field(description="Escena más cercana a to_date que no es anterior a la pasada.")
    text: str = Field(description="Resumen en el idioma pedido de qué escenas hay y con cuántas nubes.")


class WaterTileOut(BaseModel):
    id: str = Field(description="Título del producto DSWx-S1 en CMR. Es el que cita el recibo.")
    tile: str = Field(description="Tesela MGRS.")
    browse_url: str | None = Field(description="Vista previa PNG pública de PO.DAAC, sin georreferencia. null si no hay.")
    bbox: list[float] | None = Field(
        default=None,
        min_length=4,
        max_length=4,
        description="Caja de la tesela MGRS en WGS84, [oeste, sur, este, norte], de los boxes de CMR vía catalog. "
        "Sirve para situar browse_url en el mapa. Si oeste > este, cruza el antimeridiano. null si catalog no la da.",
    )


class WaterReference(BaseModel):
    platform: str
    acquired_at: dt.datetime = Field(description="Hora UTC de la primera tesela de la pasada de Sentinel-1.")
    days_from_radar: int = Field(description="Días respecto a radar_date; negativo si es anterior.")
    covers_aoi: bool = Field(
        description="Las cajas de sus teselas contienen la zona. No dice si hay datos válidos en toda ella."
    )
    tiles: list[WaterTileOut]


class WaterComparison(BaseModel):
    comparable_pixels: int = Field(description="Píxeles de la malla de DSWx-S1 con dato de radar y clase 0, 1 o 3 en B01_WTR.")
    not_comparable_pixels: int = Field(
        description="Píxeles de la zona sin dato en alguna fuente o enmascarados por DSWx-S1 (HAND, layover o sombra)."
    )
    compared_fraction: float = Field(
        description="comparable_pixels entre todos los píxeles de la zona. Por debajo de min_compared_fraction "
        "no hay assessment (status partial_overlap)."
    )
    both_water: int
    radar_only_water: int
    reference_only_water: int
    both_not_water: int
    agreement_fraction: float = Field(description="Fracción de los píxeles comparables en que las dos fuentes dicen lo mismo.")
    water_iou: float | None = Field(
        description="Píxeles con agua en las dos entre los píxeles con agua en alguna. null si ninguna ve agua."
    )
    radar_water_fraction: float
    reference_water_fraction: float


WaterStatus = Literal[
    "compared", "synthetic", "no_credentials", "none_in_window", "catalog_unavailable", "read_failed", "no_overlap",
    "partial_overlap",
]


class WaterSide(BaseModel):
    status: WaterStatus = Field(
        description="compared: se comparó píxel a píxel. synthetic: el radar es sintético y no se compara. "
        "no_credentials: verdicts no tiene token de Earthdata para leer B01_WTR. none_in_window: ningún producto a "
        "search_days o menos. catalog_unavailable: catalog no respondió. read_failed: no se pudo leer el producto o "
        "el radar. no_overlap: sin píxeles válidos en común, aunque reference.covers_aoi sea true (la caja de la "
        "tesela no garantiza datos). partial_overlap: se comparó menos de "
        "min_compared_fraction de la zona; hay conteos pero no assessment."
    )
    radar_date: dt.date
    reference: WaterReference | None = Field(
        description="Pasada DSWx-S1 elegida: la más cercana a radar_date, antes o después; primero las que cubren la zona."
    )
    assessment: Literal["agree", "disagree"] | None = Field(
        description="Acuerdo o desacuerdo entre dos métodos sobre dónde hay agua. disagree no dice cuál acierta. "
        "null si no se comparó."
    )
    assessment_basis: Literal["little_water", "water_overlap"] | None = Field(
        description="little_water: ninguna fuente ve agua en min_water_fraction o más de los píxeles comparables, "
        "y eso cuenta como acuerdo. water_overlap: se decide con water_iou frente a min_water_iou."
    )
    comparison: WaterComparison | None


class RadarWaterRule(BaseModel):
    hh_db_below: float = Field(description="Un píxel es agua para el radar si HH está por debajo de este valor y...")
    hv_db_below: float = Field(description="...HV por debajo de este. Umbrales de T-ECO-06, sin calibrar.")
    resampling: Literal["average"] = Field(
        "average", description="El radar de 10 m se promedia en la malla de DSWx-S1 (30 m) antes de aplicar los umbrales."
    )
    calibrated: bool = Field(False, description="Siempre false.")


class WaterEvidence(BaseModel):
    data_kind: Literal["real"] = Field("real", description="Los productos DSWx-S1 son siempre datos reales.")
    source: str | None = Field(description="Buscador usado por catalog. null si no respondió.")
    collection: str | None
    doi: str | None
    attribution: str | None = Field(description="Texto de atribución que debe mostrarse junto al producto.")
    product_spec_url: str | None
    min_water_body_ha: float | None = Field(description="Superficie mínima de agua abierta que DSWx-S1 detecta.")
    min_water_body_width_m: float | None = Field(description="Anchura mínima de agua abierta que DSWx-S1 detecta.")
    search_days: int = Field(description="Días máximos entre el producto DSWx-S1 y su fecha de radar.")
    reference_water_classes: list[int] = Field(
        description="Clases de B01_WTR que cuentan como agua: 1 agua abierta y 3 vegetación inundada."
    )
    radar_rule: RadarWaterRule
    min_water_fraction: float = Field(
        description="Si ninguna fuente llega a esta fracción de agua, coinciden en que no hay agua apreciable. Sin calibrar."
    )
    min_water_iou: float = Field(description="water_iou mínimo para hablar de acuerdo. Sin calibrar.")
    min_compared_fraction: float = Field(
        description="Fracción mínima de la zona con dato en las dos fuentes para dar acuerdo o desacuerdo. "
        "covers_aoi no basta: mira la caja de la tesela, no los píxeles válidos."
    )
    before: WaterSide = Field(description="Producto más cercano a from_date.")
    after: WaterSide = Field(description="Producto más cercano a to_date.")
    text: str = Field(description="Resumen en el idioma pedido: qué productos hay, si coinciden y sus límites.")


class SceneShiftOut(BaseModel):
    basis: Literal["pair_stats", "qa_median_difference"] = Field(
        description="pair_stats: stats.scene_shift_* del par, que processor mide desde T-ECO-07 y ya restó del "
        "cambio. qa_median_difference: mediana de to_date menos la de from_date, del QA de Eco, sin restar."
    )
    corrected: bool = Field(
        description="true: el porcentaje de cambio ya descuenta este desplazamiento (basis pair_stats). "
        "false: no lo descuenta y puede reflejarlo."
    )
    hh_db: float | None
    hv_db: float | None
    same_direction: bool | None = Field(description="HH y HV se mueven en el mismo sentido. null si falta alguna o alguna no se movió.")
    threshold_db: float = Field(description="Por encima de este valor absoluto, el veredicto avisa. Sin calibrar.")
    exceeds_threshold: bool = Field(
        description="Si es true, summary.does_not_prove avisa del cambio de nivel de toda la escena: que ya se "
        "descontó (corrected) o que el porcentaje puede reflejarlo. No cambia el estado."
    )
    calibrated: bool = Field(False, description="Siempre false.")


class NoiseOut(BaseModel):
    """Dispersión de la diferencia del par (RF-BUS-09), copiada de stats.noise_* del manifiesto de Eco (T-ECO-09)."""

    basis: Literal["pair_stats"] = Field(
        "pair_stats", description="Siempre pair_stats: stats.noise_hh_db y noise_hv_db del par en el manifiesto."
    )
    hh_db: float | None = Field(
        description="Desviación robusta de la diferencia HH (1,4826 · MAD alrededor de la mediana), en dB, sobre los "
        "píxeles observables, tras suavizar 5 × 5 y antes del umbral y del filtro de grupos. null si falta."
    )
    hv_db: float | None = Field(description="Igual que hh_db, para HV.")
    caveat: str = Field(
        description="Advertencia fija: no es ruido del instrumento. Incluye también cambio real repartido "
        "(humedad, vegetación) y textura, así que un valor alto no prueba que el cambio sea ruido."
    )
    calibrated: bool = Field(False, description="Siempre false: no hay un umbral de ruido contrastado.")


NOISE_CAVEAT = (
    "No es ruido del instrumento: es la dispersión de la diferencia entre las dos fechas sobre lo observable, e "
    "incluye también cambio real repartido (humedad, vegetación) y textura."
)


def noise_from_stats(stats: dict) -> NoiseOut | None:
    """evidence.noise si el manifiesto trae alguna de stats.noise_*; si no, null (manifiestos anteriores a T-ECO-09)."""
    hh, hv = stats.get("noise_hh_db"), stats.get("noise_hv_db")
    if hh is None and hv is None:
        return None
    return NoiseOut(hh_db=hh, hv_db=hv, caveat=NOISE_CAVEAT)


class DecisionRule(BaseModel):
    min_observed_fraction: float = Field(description="Por debajo de esta fracción observada, not_observable.")
    min_changed_fraction: float = Field(
        description="Desde esta fracción de lo observado con cambio, change_probable; por debajo, "
        "no_detectable_change. Fijado en el 5 % con el ruido de 16 pares consecutivos reales de Parral, "
        "que tras corregir el desplazamiento de la escena quedan entre 0,58 % y 4,64 % salvo dos (T-BAL-09)."
    )
    calibrated: bool = Field(
        False,
        description="Siempre false: min_changed_fraction se fijó con el ruido medido en pares reales, pero ninguno de "
        "los dos umbrales se ha contrastado con verdad de campo.",
    )


class Evidence(BaseModel):
    observed_fraction: float
    changed_fraction: float
    decision_rule: DecisionRule = Field(description="Umbrales con los que se decidió el estado de este veredicto.")
    threshold_hh_db: float | None
    threshold_hv_db: float | None
    mean_change_hh_db: float | None
    mean_change_hv_db: float | None
    pixel_counts: dict[str, int]
    signature_counts: dict[str, int]
    optical: OpticalEvidence
    scene_shift: SceneShiftOut | None = Field(
        description="Cambio de nivel de toda la escena entre las dos fechas. null si el manifiesto no trae QA."
    )
    water: WaterEvidence = Field(
        description="Contraste del agua del radar con OPERA DSWx-S1 (RF-BAL-07). Un desacuerdo es un dato, no un fallo."
    )
    noise: NoiseOut | None = Field(
        None,
        description="Dispersión de la diferencia del par en HH y HV (RF-BUS-09, T-BAL-14). null si el manifiesto no "
        "trae stats.noise_* (artefactos anteriores a T-ECO-09). No es ruido del instrumento: ver caveat. No cambia "
        "el estado.",
    )


class Layers(BaseModel):
    state: str
    change_hh: str
    change_hv: str


class Verdict(BaseModel):
    id: str
    aoi: str
    series: str
    kind: Literal["consecutive", "full_window"]
    from_date: dt.date
    to_date: dt.date
    interval_days: int = Field(description="Días entre from_date y to_date.")
    state: Literal["change_probable", "no_detectable_change", "not_observable"]
    cause: str | None
    cause_label: str | None
    summary: Summary
    hypotheses: list[str]
    evidence: Evidence
    layers: Layers
    receipt: Receipt


# Relieve (T-BAL-15, RF-INT-12): TiTiler codifica el DEM como Terrain-RGB de Mapbox, que MapLibre lee como
# raster-dem con encoding "mapbox": altura = -10000 + (R * 65536 + G * 256 + B) * 0,1 m.
RELIEF_QUERY = "algorithm=terrainrgb&resampling=bilinear"
RELIEF_EXAGGERATION = 1.0


class ReliefOut(BaseModel):
    """Plantilla de teselas de relieve con el DEM de la zona que publica Eco (T-ECO-10)."""

    tiles: str = Field(
        description="Plantilla XYZ por el gateway, con algorithm=terrainrgb. Se pide como fuente raster-dem de MapLibre "
        "con encoding mapbox y tileSize 256."
    )
    encoding: Literal["mapbox"] = Field(
        "mapbox", description="Terrain-RGB: altura = -10000 + (R * 65536 + G * 256 + B) * 0,1 m."
    )
    data_kind: Literal["real", "synthetic"] = Field(
        description="dem.data_kind del manifiesto (T-ECO-13); real si falta. synthetic: DEM inventado de la pila "
        "sintética, que no describe ningún relieve real; la interfaz debe decirlo y no atribuirlo a Copernicus."
    )
    tile_size: int = Field(256, description="Píxeles por lado de cada tesela.")
    exaggeration: float = Field(
        RELIEF_EXAGGERATION, description="Exageración vertical por omisión (RF-INT-12): 1, sin exagerar. Si la "
        "interfaz la cambia, debe mostrar el factor en pantalla."
    )
    source: str = Field(description="Fuente del DEM, del manifiesto (dem.source).")
    crs: str = Field(description="CRS del COG del DEM, que no es el del radar.")
    vertical_datum: str = Field(description="Referencia de las alturas. EGM2008: sobre el geoide, no el elipsoide.")
    units: Literal["m"] = "m"
    attribution: str = Field(description="Texto de atribución que exige la licencia; la interfaz lo muestra junto al relieve.")


def relief_from_manifest(manifest: dict) -> ReliefOut | None:
    """relief si el manifiesto trae dem (T-ECO-10); null si no (artefactos anteriores o sin DEM)."""
    dem = manifest.get("dem")
    if not dem:
        return None
    return ReliefOut(
        tiles=_tile_url(dem["layer"], RELIEF_QUERY),
        data_kind=dem.get("data_kind", "real"),
        source=dem["source"],
        crs=dem["crs"],
        vertical_datum=dem["vertical_datum"],
        units=dem["units"],
        attribution=dem["attribution"],
    )


class SeriesInfo(BaseModel):
    id: str
    data_kind: Literal["real", "synthetic"]
    maturity: str
    bbox: list[float]
    dates: list[dt.date]
    relief: ReliefOut | None = Field(
        None,
        description="Teselas de relieve con el DEM de la zona (RF-INT-12, T-BAL-15). null si el manifiesto no trae dem. "
        "Es el mismo DEM para todas las series de la zona. Los datos del DEM son los de su fuente aunque el radar "
        "de la serie sea sintético.",
    )


EventType = Literal["urban_storm", "river_flood", "wildfire"]


class PersistenceAssumption(BaseModel):
    persistence_hours: int = Field(description="Horas que se supone que dura el evento. Nunca es una medición.")
    source: Literal["event_type", "user", "default"] = Field(
        description="event_type: valor de la tabla por tipo; user: persistence_hours de la consulta; "
        "default: valor por omisión, sin tipo ni horas."
    )
    event_type: EventType | None
    calibrated: bool = Field(description="Siempre false: las persistencias son valores iniciales sin calibrar.")
    hours_by_event_type: dict[str, int] = Field(description="Tabla completa de persistencias supuestas, en horas.")
    text: str = Field(description="El supuesto redactado en el idioma pedido; también va en summary.does_not_prove.")


class EventVerdict(BaseModel):
    aoi: str
    event_date: dt.date
    event_time: dt.time | None = Field(
        description="Hora UTC de inicio del evento, si se indicó. Sin ella, puede empezar en cualquier momento de su día."
    )
    event_type: EventType | None = Field(description="Tipo de evento indicado en la consulta, si lo hay.")
    persistence_hours: int
    assumption: PersistenceAssumption
    state: Literal["observable", "not_observable"] = Field(
        description="Responde otra pregunta que los pares: si alguna pasada cayó mientras duraba el evento, en horas UTC. "
        "observable exige que caiga dentro en todos los casos posibles y no afirma ningún cambio: hay que consultar "
        "el veredicto del par. not_observable lleva su causa; timing_uncertain si solo cae dentro en algunos casos."
    )
    cause: str | None
    cause_label: str | None
    previous_pass: dt.date | None
    next_pass: dt.date | None
    next_pass_acquired_at: dt.datetime | None = Field(
        description="Hora UTC de la siguiente pasada según la línea de tiempo de catalog. null si no se conoce "
        "(datos sintéticos o catalog sin respuesta): entonces se considera todo su día."
    )
    data_kind: Literal["real", "synthetic"]
    excluded_passes: list[ExcludedPassOut] = Field(
        description="Pasadas de las series de la zona que catalog excluye, entre previous_pass y next_pass ambas "
        "incluidas, estén o no en el manifiesto: no cuentan para el evento. Vacía con datos sintéticos o si catalog "
        "no respondió."
    )
    summary: Summary


class PixelDate(BaseModel):
    date: dt.date
    hh_db: float | None
    hv_db: float | None


class PixelChange(BaseModel):
    pair: str
    state: str | None


class PixelSeries(BaseModel):
    aoi: str
    series: str
    lon: float
    lat: float
    data_kind: Literal["real", "synthetic"]
    values: list[PixelDate]
    changes: list[PixelChange]


def _tile_url(relative: str, query: str) -> str:
    return f"{TILES_PREFIX}?url={quote('file:///data/artifacts/' + relative, safe='')}&{query}"


def _optical_tile_url(visual_url: str) -> str:
    return f"{TILES_PREFIX}?url={quote(visual_url, safe='')}"


def _optical_side(
    side: optical.Side, radar_date: str, radar_time: dt.datetime | None, reference: OpticalReference | None
) -> tuple[OpticalSide, tuple]:
    day = dt.date.fromisoformat(radar_date)
    if reference is None:
        chosen = optical.Pick("catalog_unavailable")
    else:
        chosen = optical.pick(reference.acquisitions, side, day, radar_time)
    scene = None
    text_values: tuple = (chosen.status, None, None, None)
    if chosen.acquisition is not None and reference is not None:
        acq = chosen.acquisition
        scene = OpticalScene(
            platform=acq.platform,
            acquired_at=acq.acquired_at,
            days_from_radar=chosen.days_from_radar,
            covers_aoi=acq.covers_aoi,
            max_cloud_cover=acq.max_cloud_cover,
            attribution=reference.attribution,
            tiles=[
                OpticalTileOut(
                    tile=tile.tile,
                    cloud_cover=tile.cloud_cover,
                    visual_url=tile.visual_url,
                    tile_url=_optical_tile_url(tile.visual_url),
                    bbox=list(tile.bbox) if tile.bbox else None,
                )
                for tile in acq.tiles
            ],
        )
        text_values = (chosen.status, acq.acquired_at.date().isoformat(), chosen.days_from_radar, acq.max_cloud_cover)
    side_out = OpticalSide(status=chosen.status, radar_date=day, radar_acquired_at=radar_time, scene=scene)
    return side_out, text_values


def build_optical(
    pair: dict,
    freshness: Freshness,
    lang: narrative.Lang,
    before_ref: OpticalReference | None,
    after_ref: OpticalReference | None,
) -> OpticalEvidence:
    before, before_text = _optical_side("before", pair["from"], freshness.before.acquired_at, before_ref)
    after, after_text = _optical_side("after", pair["to"], freshness.after.acquired_at, after_ref)
    meta = before_ref or after_ref
    return OpticalEvidence(
        source=meta.source if meta else None,
        collection=meta.collection if meta else None,
        license=meta.license if meta else None,
        license_url=meta.license_url if meta else None,
        max_cloud_cover=optical.MAX_CLOUD_COVER,
        search_days=optical.SEARCH_DAYS,
        before=before,
        after=after,
        text=narrative.optical_text(
            before_text, after_text, lang, max_cloud=optical.MAX_CLOUD_COVER, search_days=optical.SEARCH_DAYS
        ),
    )


def _water_side(side: water.Side) -> tuple[WaterSide, dict]:
    reference, values = None, {"status": side.status}
    if side.acquisition is not None:
        acq = side.acquisition
        reference = WaterReference(
            platform=acq.platform,
            acquired_at=acq.acquired_at,
            days_from_radar=side.days_from_radar,
            covers_aoi=acq.covers_aoi,
            tiles=[
                WaterTileOut(
                    id=tile.id, tile=tile.tile, browse_url=tile.browse_url,
                    bbox=list(tile.bbox) if tile.bbox else None,
                )
                for tile in acq.tiles
            ],
        )
        values.update(product_date=acq.acquired_at.date().isoformat(), days=side.days_from_radar)
    comparison, assessment, basis = None, None, None
    found = side.comparison
    if found is not None:
        comparison = WaterComparison(
            comparable_pixels=found.comparable,
            not_comparable_pixels=found.not_comparable,
            compared_fraction=found.compared_fraction,
            both_water=found.both_water,
            radar_only_water=found.radar_only_water,
            reference_only_water=found.reference_only_water,
            both_not_water=found.both_not_water,
            agreement_fraction=found.agreement_fraction,
            water_iou=found.water_iou,
            radar_water_fraction=found.radar_water_fraction,
            reference_water_fraction=found.reference_water_fraction,
        )
        values.update(compared=found.compared_fraction, minimum=water.MIN_COMPARED_FRACTION)
        if side.status == "compared":
            assessment, basis = found.assessment, found.basis
            values.update(
                assessment=assessment, basis=basis, iou=found.water_iou,
                radar=found.radar_water_fraction, reference=found.reference_water_fraction,
            )
    out = WaterSide(
        status=side.status, radar_date=side.radar_date, reference=reference,
        assessment=assessment, assessment_basis=basis, comparison=comparison,
    )
    return out, values


def build_water(
    before: water.Side, after: water.Side, meta: OperaReference | None, lang: narrative.Lang
) -> WaterEvidence:
    before_out, before_values = _water_side(before)
    after_out, after_values = _water_side(after)
    return WaterEvidence(
        source=meta.source if meta else None,
        collection=meta.collection if meta else None,
        doi=meta.doi if meta else None,
        attribution=meta.attribution if meta else None,
        product_spec_url=meta.product_spec_url if meta else None,
        min_water_body_ha=meta.min_water_body_ha if meta else None,
        min_water_body_width_m=meta.min_water_body_width_m if meta else None,
        search_days=water.SEARCH_DAYS,
        reference_water_classes=list(water.WTR_WATER),
        radar_rule=RadarWaterRule(hh_db_below=water.RADAR_WATER_HH_DB, hv_db_below=water.RADAR_WATER_HV_DB),
        min_water_fraction=water.MIN_WATER_FRACTION,
        min_water_iou=water.MIN_WATER_IOU,
        min_compared_fraction=water.MIN_COMPARED_FRACTION,
        before=before_out,
        after=after_out,
        text=narrative.water_text(
            before_values, after_values, lang, search_days=water.SEARCH_DAYS,
            min_water_body_ha=meta.min_water_body_ha if meta else None,
            min_water_body_width_m=meta.min_water_body_width_m if meta else None,
            hh_db=water.RADAR_WATER_HH_DB, hv_db=water.RADAR_WATER_HV_DB,
        ),
    )


def _same_series(catalog_series: str, series: dict) -> bool:
    """catalog nombra la serie con modo, polarización y CRID (T171D-F075-4005-DHDH-P05023); el manifiesto, sin ellos."""
    full = f"{series['id']}-{series['mode']}-{series['polarization']}-{series['crid']}"
    return catalog_series in (series["id"], full)


def _excluded_out(item: ExcludedPass) -> ExcludedPassOut:
    return ExcludedPassOut(
        granule=item.id, series=item.series, date=item.date, reason=item.reason, evidence=item.evidence
    )


def _with_skipped(summary: dict, between: list[ExcludedPass], lang: narrative.Lang) -> dict:
    """En eventos, cita las pasadas excluidas entre la anterior y la siguiente: explican por qué no cuentan."""
    notes = [narrative.excluded_pass_text(item.date.isoformat(), item.reason, False, lang) for item in between]
    if not notes:
        return summary
    return {**summary, "missing": " ".join([summary["missing"], *notes])}


def _date_quality(day: str, qa: dict | None) -> DateQuality | None:
    return None if not qa else DateQuality(date=day, **qa)


def with_quality(
    summary: dict,
    decision: rules.Decision,
    before: tuple[str, dict | None],
    after: tuple[str, dict | None],
    shift: quality.SceneShift | None,
    lang: narrative.Lang,
    excluded_notes: list[str] | None = None,
) -> dict:
    """Añade al resumen las fechas que marca el QA de Eco y el cambio de nivel de toda la escena.

    Las fechas marcadas van en "missing" siempre; el desplazamiento, en "does_not_prove" cuando hay
    algo que interpretar (no en not_observable).
    """
    notes = [
        narrative.quality_flag_text(day, qa["deviation_hh_db"], qa["deviation_hv_db"], quality.SCENE_SHIFT_DB, lang)
        for day, qa in (before, after)
        if quality.flagged(qa)
    ] + list(excluded_notes or [])
    result = dict(summary)
    if notes:
        result["missing"] = " ".join([summary["missing"], *notes])
    if shift is not None and shift.exceeds_threshold and decision.state != rules.NOT_OBSERVABLE:
        text = narrative.scene_shift_text(shift.hh_db, shift.hv_db, shift.same_direction, lang, shift.corrected)
        result["does_not_prove"] = f"{summary['does_not_prove']} {text}"
    return result


# Cambio en dB por tramos, de rojo (bajó) a azul (subió), con -10 a +10 dB llevados a 0-255 por `rescale`. Entre
# -1,5 y +1,5 dB no se pinta: con `rdbu` continua, el blanco opaco de «casi sin cambio» cubría toda la zona y la
# capa tapaba el mapa. De 1,5 a 3 dB (por debajo del umbral mínimo de processor) va tenue; desde 3 dB, fuerte.
CHANGE_DB_BINS = (
    (-99.0, -6.0, (178, 24, 43, 230)),
    (-6.0, -3.0, (214, 96, 77, 210)),
    (-3.0, -1.5, (244, 165, 130, 140)),
    (1.5, 3.0, (146, 197, 222, 140)),
    (3.0, 6.0, (67, 147, 195, 210)),
    (6.0, 99.0, (33, 102, 172, 230)),
)


def _db_to_byte(db: float) -> int:
    return min(256, max(0, round((db + 10) / 20 * 255))) if abs(db) < 99 else (0 if db < 0 else 256)


CHANGE_COLORMAP = [[[_db_to_byte(lo), _db_to_byte(hi)], list(rgba)] for lo, hi, rgba in CHANGE_DB_BINS]


# Velocidad de hundimiento en mm/año (positiva = se aleja del satélite), de 0 a 400 llevada a 0-255. Solo se pinta
# desde el umbral de la zona (`threshold_mm_yr`, lo que se distingue del ruido): con un tramo fijo desde 20 mm/año,
# Parral (incertidumbre de 54 mm/año) salía amarillo en media zona sin hundimiento. De amarillo a marrón oscuro.
SUBSIDENCE_RANGE = (0.0, 400.0)


def _rate_byte(v: float) -> int:
    lo, hi = SUBSIDENCE_RANGE
    return min(256, max(0, round((v - lo) / (hi - lo) * 255)))


def subsidence_colormap(threshold: float) -> list:
    bins = (
        (threshold, threshold * 1.5, (254, 196, 79, 210)),
        (threshold * 1.5, threshold * 2, (236, 112, 20, 225)),
        (threshold * 2, SUBSIDENCE_RANGE[1] + 1, (153, 52, 4, 240)),
    )
    return [[[_rate_byte(lo), 256 if hi > SUBSIDENCE_RANGE[1] else _rate_byte(hi)], list(rgba)] for lo, hi, rgba in bins]


class SubsidenceText(BaseModel):
    detected: str
    does_not_prove: str
    missing: str


class Subsidence(BaseModel):
    """Hundimiento relativo con interferogramas NISAR GUNW (processor subsidence). Sin calibrar."""

    aoi: str
    status: Literal["computed", "no_interferograms"]
    days: int | None = None
    pairs: list[dict] = Field(default_factory=list, description="Interferogramas usados (id y fechas de referencia y secundaria).")
    track: int | None = None
    direction: str | None = None
    valid_fraction: float | None = None
    noise_mm_yr: float | None = Field(None, description="Incertidumbre típica de la velocidad, de la dispersión de los pares.")
    threshold_mm_yr: float | None = Field(None, description="Desde esta velocidad relativa (mm/año, se aleja) se cuenta como hundimiento.")
    sinking_fraction: float | None = Field(None, description="Parte de lo medido que se hunde al menos threshold_mm_yr respecto a la zona.")
    max_rate_mm_yr: float | None = Field(None, description="Percentil 99 de la velocidad: lo más rápido sin píxeles aislados.")
    fastest_point: dict | None = None
    tiles: str | None = Field(None, description="Plantilla XYZ de la velocidad (mm/año), por el gateway.")
    calibrated: bool = False
    sign_check: str | None = None
    summary: SubsidenceText


def _layers(pair: dict) -> Layers:
    colormap = quote(json.dumps(STATE_COLORS, separators=(",", ":")), safe="")
    change = "rescale=-10,10&colormap=" + quote(json.dumps(CHANGE_COLORMAP, separators=(",", ":")), safe="")
    return Layers(
        state=_tile_url(pair["layers"]["state"], f"colormap={colormap}"),
        change_hh=_tile_url(pair["layers"]["change_hh"], change),
        change_hv=_tile_url(pair["layers"]["change_hv"], change),
    )


def _pass_freshness(
    date: str, granule: str, today: dt.date, synthetic: bool, passes: dict[str, PassTime] | None
) -> PassFreshness:
    day = dt.date.fromisoformat(date)
    found = None
    if synthetic:
        status = "synthetic"
    elif passes is None:
        status = "catalog_unavailable"
    else:
        found = passes.get(granule_key(granule))
        if found is None:
            status = "granule_not_in_catalog"
        elif found.latency_hours is None:
            status = "not_published"
        else:
            status = "available"
    return PassFreshness(
        date=day,
        granule=granule,
        acquired_at=found.acquired_at if found else None,
        published_at=found.published_at if found else None,
        publication_latency_hours=found.latency_hours if found else None,
        latency_status=status,
        age_days=(today - day).days,
    )


def build_freshness(
    manifest: dict, pair: dict, today: dt.date, passes: dict[str, PassTime] | None
) -> Freshness:
    synthetic = manifest["data_kind"] == "synthetic"
    before_granule, after_granule = pair["granules"]
    return Freshness(
        reference_date=today,
        before=_pass_freshness(pair["from"], before_granule, today, synthetic, passes),
        after=_pass_freshness(pair["to"], after_granule, today, synthetic, passes),
    )


def build_verdict(
    manifest: dict,
    pair: dict,
    lang: narrative.Lang,
    today: dt.date | None = None,
    passes: dict[str, PassTime] | None = None,
    optical_refs: dict[dt.date, OpticalReference | None] | None = None,
    water_evidence: WaterEvidence | None = None,
    excluded: list[ExcludedPass] | None = None,
) -> Verdict:
    stats = pair["stats"]
    start, end = dt.date.fromisoformat(pair["from"]), dt.date.fromisoformat(pair["to"])
    used = {granule_key(granule) for granule in pair["granules"]}
    in_pair = [
        item for item in (excluded or [])
        if _same_series(item.series, manifest["series"]) and start <= item.date <= end
    ]
    freshness = build_freshness(manifest, pair, today or dt.datetime.now(dt.timezone.utc).date(), passes)
    refs = optical_refs or {}
    optical_evidence = build_optical(
        pair,
        freshness,
        lang,
        refs.get(dt.date.fromisoformat(pair["from"])),
        refs.get(dt.date.fromisoformat(pair["to"])),
    )
    interval_days = (dt.date.fromisoformat(pair["to"]) - dt.date.fromisoformat(pair["from"])).days
    if water_evidence is None:
        water_evidence = build_water(
            water.Side("catalog_unavailable", dt.date.fromisoformat(pair["from"])),
            water.Side("catalog_unavailable", dt.date.fromisoformat(pair["to"])),
            None,
            lang,
        )
    decision = rules.decide(stats["counts"])
    qa = quality.qa_by_date(manifest)
    qa_before, qa_after = qa.get(pair["from"]), qa.get(pair["to"])
    shift = quality.scene_shift(qa_before, qa_after, stats)
    synthetic = manifest["data_kind"] == "synthetic"
    series = manifest["series"]
    hypotheses = []
    if decision.state == rules.CHANGE_PROBABLE:
        hypotheses = [narrative.hypothesis_text(item, share, lang) for item, share in rules.signature_shares(stats["signature_counts"])]
    return Verdict(
        id=pair["id"],
        aoi=manifest["aoi"],
        series=series["id"],
        kind=pair["kind"],
        from_date=pair["from"],
        to_date=pair["to"],
        interval_days=interval_days,
        state=decision.state,
        cause=decision.cause,
        cause_label=narrative.CAUSES[lang][decision.cause] if decision.cause else None,
        summary=Summary(
            **with_quality(
                narrative.pair_summary(
                    decision,
                    pair["from"],
                    pair["to"],
                    pair["spans_data_gap"],
                    lang,
                    synthetic,
                    interval_days=interval_days,
                    age_days=freshness.after.age_days,
                    latency_hours=freshness.after.publication_latency_hours,
                    latency_status=freshness.after.latency_status,
                    kind=pair["kind"],
                    aoi=manifest["aoi"],
                    zone=narrative.zone_name(manifest["aoi"]),
                ),
                decision,
                (pair["from"], qa_before),
                (pair["to"], qa_after),
                shift,
                lang,
                [
                    narrative.excluded_pass_text(
                        item.date.isoformat(), item.reason, item.id in used or item.date in (start, end), lang
                    )
                    for item in in_pair
                ],
            )
        ),
        hypotheses=hypotheses,
        evidence=Evidence(
            observed_fraction=decision.observed_fraction,
            decision_rule=DecisionRule(
                min_observed_fraction=rules.MIN_OBSERVED_FRACTION, min_changed_fraction=rules.MIN_CHANGED_FRACTION
            ),
            changed_fraction=decision.changed_fraction,
            threshold_hh_db=stats["threshold_hh_db"],
            threshold_hv_db=stats["threshold_hv_db"],
            mean_change_hh_db=stats["mean_change_hh_db"],
            mean_change_hv_db=stats["mean_change_hv_db"],
            pixel_counts=stats["counts"],
            signature_counts=stats["signature_counts"],
            optical=optical_evidence,
            scene_shift=None if shift is None else SceneShiftOut(
                hh_db=shift.hh_db,
                hv_db=shift.hv_db,
                same_direction=shift.same_direction,
                threshold_db=quality.SCENE_SHIFT_DB,
                exceeds_threshold=shift.exceeds_threshold,
                basis=shift.basis,
                corrected=shift.corrected,
            ),
            water=water_evidence,
            noise=noise_from_stats(stats),
        ),
        layers=_layers(pair),
        receipt=Receipt(
            data_kind=manifest["data_kind"],
            maturity=manifest["maturity"],
            series=series["id"],
            track=series["track"],
            direction=series["direction"],
            frame=series["frame"],
            mode=series["mode"],
            polarization=series["polarization"],
            crid=series["crid"],
            granules=pair["granules"],
            spans_data_gap=pair["spans_data_gap"],
            notices=manifest["notices"],
            freshness=freshness,
            quality=PairQuality(
                before=_date_quality(pair["from"], qa_before), after=_date_quality(pair["to"], qa_after)
            ),
            excluded_passes=[_excluded_out(item) for item in in_pair],
        ),
    )


def create_app(
    artifact_root: Path | None = None,
    timeline: TimelineSource | None = None,
    clock: Callable[[], dt.datetime] | None = None,
    optical_source: OpticalSource | None = None,
    opera_source: OperaSource | None = None,
    water_contrast: water.WaterContrast | None = None,
    warm_cache: bool | None = None,
    build_index: bool | None = None,
    footprint_source: FootprintSource | None = None,
) -> FastAPI:
    root = artifact_root or Path(os.environ.get("ARTIFACT_ROOT", "/data/artifacts"))
    store = Store(root, hide_synthetic=os.environ.get("VERDICTS_HIDE_SYNTHETIC", "") == "1")
    if timeline is None and os.environ.get("CATALOG_URL"):
        timeline = HttpTimeline(os.environ["CATALOG_URL"])
    if optical_source is None and os.environ.get("CATALOG_URL"):
        optical_source = HttpOptical(os.environ["CATALOG_URL"])
    if opera_source is None and os.environ.get("CATALOG_URL"):
        opera_source = HttpOpera(os.environ["CATALOG_URL"])
    if footprint_source is None and os.environ.get("CATALOG_URL"):
        footprint_source = HttpFootprints(os.environ["CATALOG_URL"])
    # Con EARTHDATA_TOKEN, verdicts lee B01_WTR de PO.DAAC y compara; sin él, lista y lo declara.
    contrast = water_contrast or water.contrast_from_env(root, os.environ.get)
    now = clock or (lambda: dt.datetime.now(dt.timezone.utc))
    if warm_cache is None:
        warm_cache = os.environ.get("VERDICTS_WARM_CACHE") == "1"
    if build_index is None:
        build_index = os.environ.get("VERDICTS_SEARCH_INDEX") == "1"
    log = logging.getLogger(__name__)
    # Índice de búsqueda (T-BAL-11). Sin token, el contraste con OPERA no descarga nada y entra desde el
    # principio; con token, entra cuando termina de calentarse y hasta entonces cada fila dice not_available.
    index_state: dict = {"index": None, "water_ready": contrast.fetcher is None}
    index_lock = threading.Lock()

    def startup() -> None:
        try:
            if build_index:
                rebuild_index()
            if warm_cache and contrast.fetcher is not None:
                warm_water()
                index_state["water_ready"] = True
                if build_index:
                    rebuild_index()
        except Exception:  # noqa: BLE001 - el arranque en segundo plano nunca debe tumbar el servicio
            log.exception("No se pudo preparar el índice de búsqueda; se calculará con la primera consulta")

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        # Calcula en segundo plano todos los veredictos para la búsqueda y, con token y radar real, el
        # contraste con OPERA. La API responde desde el primer momento; una búsqueda que llegue antes de que
        # termine el índice lo calcula ella misma.
        if build_index or (warm_cache and contrast.fetcher is not None):
            threading.Thread(target=startup, name="warm-up", daemon=True).start()
        yield

    app = FastAPI(title="NISAR verdicts", version="0.1.0", lifespan=lifespan)

    def passes_for(manifest: dict) -> dict[str, PassTime] | None:
        """Pasadas de catalog, o None si no hay catálogo o no respondió. Los sintéticos no se buscan."""
        if manifest["data_kind"] == "synthetic" or timeline is None:
            return None
        try:
            return timeline.passes(manifest["aoi"])
        except CatalogUnavailable:
            return None

    def excluded_for(manifest: dict) -> list[ExcludedPass]:
        """Pasadas excluidas por catalog; vacía con sintéticos o sin catalog, igual que passes_for."""
        if manifest["data_kind"] == "synthetic" or timeline is None:
            return []
        try:
            return timeline.excluded(manifest["aoi"])
        except CatalogUnavailable:
            return []

    def optical_for(aoi: str, days: set[dt.date]) -> dict[dt.date, OpticalReference | None]:
        """Escenas por fecha de radar, en paralelo. Una fecha sin respuesta queda en None.

        Se buscan también con datos sintéticos: las fechas son pasadas reales y la escena declara data_kind real.
        """
        if optical_source is None or not days:
            return {}

        def fetch(day: dt.date) -> OpticalReference | None:
            try:
                return optical_source.scenes(aoi, day, optical.SEARCH_DAYS)
            except CatalogUnavailable:
                return None

        ordered = sorted(days)
        with ThreadPoolExecutor(max_workers=min(8, len(ordered))) as pool:
            return dict(zip(ordered, pool.map(fetch, ordered)))

    def opera_for(aoi: str, days: set[dt.date]) -> dict[dt.date, OperaReference | None]:
        """Productos DSWx-S1 por fecha de radar, en paralelo. Se listan también con radar sintético."""
        if opera_source is None or not days:
            return {}

        def fetch(day: dt.date) -> OperaReference | None:
            try:
                return opera_source.products(aoi, day, water.SEARCH_DAYS)
            except CatalogUnavailable:
                return None

        ordered = sorted(days)
        with ThreadPoolExecutor(max_workers=min(8, len(ordered))) as pool:
            return dict(zip(ordered, pool.map(fetch, ordered)))

    def water_sides(manifest: dict, days: set[dt.date]) -> tuple[dict[dt.date, water.Side], OperaReference | None]:
        """Contraste por fecha de radar: cada fecha se compara una vez aunque esté en varios pares.

        En secuencia: rasterio en varios hilos mezcla sus avisos de GDAL; la caché evita repetir lecturas.
        """
        refs = opera_for(manifest["aoi"], days)
        sides = contrast.sides(manifest, {day: refs.get(day) for day in days})
        meta = next((ref for ref in refs.values() if ref is not None), None)
        return sides, meta

    def water_for(pair: dict, sides: dict[dt.date, water.Side], meta, lang: narrative.Lang) -> WaterEvidence:
        start, end = dt.date.fromisoformat(pair["from"]), dt.date.fromisoformat(pair["to"])
        return build_water(sides[start], sides[end], meta, lang)

    def pair_days(pairs: list[dict]) -> set[dt.date]:
        return {dt.date.fromisoformat(pair[key]) for pair in pairs for key in ("from", "to")}

    def warm_water() -> None:
        for aoi in store.aois():
            for manifest in store.manifests(aoi):
                if manifest["data_kind"] != "real":
                    continue
                try:
                    water_sides(manifest, pair_days(manifest["pairs"]))
                except Exception:  # noqa: BLE001 - calentar nunca debe tumbar el servicio
                    log.exception("No se pudo calentar el contraste de %s", aoi)

    def series_verdicts(manifest: dict, lang: narrative.Lang, include_water: bool = True) -> list[Verdict]:
        """Todos los veredictos de una serie, como en /verdicts. Sin include_water no se mira OPERA."""
        today, passes, excluded = now().date(), passes_for(manifest), excluded_for(manifest)
        days = pair_days(manifest["pairs"])
        refs = optical_for(manifest["aoi"], days)
        if not include_water:
            return [build_verdict(manifest, pair, lang, today, passes, refs, None, excluded) for pair in manifest["pairs"]]
        sides, meta = water_sides(manifest, days)
        return [
            build_verdict(manifest, pair, lang, today, passes, refs, water_for(pair, sides, meta, lang), excluded)
            for pair in manifest["pairs"]
        ]

    def rebuild_index() -> search.Index:
        include_water = bool(index_state["water_ready"])
        rows: list[search.SearchResult] = []
        docs: dict[str, dict[search.Key, str]] = {lang: {} for lang in search.LANGS}
        series_keys: dict[tuple[str, str], tuple[int, str, int]] = {}
        series_bbox: dict[tuple[str, str], list[float]] = {}
        full: dict[search.Key, Verdict] = {}
        cells_paths: dict[search.Key, str] = {}
        for aoi in store.aois():
            for manifest in store.manifests(aoi):
                info = manifest["series"]
                series_keys[(manifest["aoi"], info["id"])] = (int(info["track"]), info["direction"], int(info["frame"]))
                series_bbox[(manifest["aoi"], info["id"])] = list(manifest["bbox"])
                for pair in manifest["pairs"]:
                    if pair.get("cells"):
                        cells_paths[(manifest["aoi"], info["id"], pair["id"])] = pair["cells"]
                for lang in search.LANGS:
                    for verdict in series_verdicts(manifest, lang, include_water):
                        if lang == "es":
                            rows.append(search.row_from_verdict(verdict, include_water))
                            full[(verdict.aoi, verdict.series, verdict.id)] = verdict
                        docs[lang][(verdict.aoi, verdict.series, verdict.id)] = search.verdict_text(verdict)
        text = search.TextIndex(docs)
        with index_lock:
            previous = index_state["index"]
            generation = previous.generation + 1 if previous is not None else 1
            built = search.Index(
                rows=rows, water_included=include_water, built_at=now(), generation=generation, text=text,
                series_keys=series_keys, series_bbox=series_bbox, verdicts=full, cells_paths=cells_paths,
            )
            index_state["index"] = built
        log.info("Índice de búsqueda: %d veredictos, contraste con OPERA %s", len(rows),
                 "incluido" if include_water else "pendiente")
        return built

    def current_index() -> search.Index:
        found = index_state["index"]
        return found if found is not None else rebuild_index()

    def verdict_for(manifest: dict, pair: dict, lang: narrative.Lang) -> Verdict:
        days = pair_days([pair])
        refs = optical_for(manifest["aoi"], days)
        sides, meta = water_sides(manifest, days)
        return build_verdict(
            manifest, pair, lang, now().date(), passes_for(manifest), refs, water_for(pair, sides, meta, lang),
            excluded_for(manifest),
        )

    def manifests_or_404(aoi: str) -> list[dict]:
        manifests = store.manifests(aoi)
        if not manifests:
            raise HTTPException(404, f"Sin artefactos para la zona: {aoi}")
        return manifests

    def manifest_or_404(aoi: str, series: str) -> dict:
        for manifest in manifests_or_404(aoi):
            if manifest["series"]["id"] == series:
                return manifest
        raise HTTPException(404, f"Serie desconocida: {series}")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/aois", response_model=list[str])
    def aois() -> list[str]:
        return store.aois()

    @app.get("/aois/{aoi}/subsidence", response_model=Subsidence)
    def subsidence(aoi: str, lang: narrative.Lang = "es") -> Subsidence:
        """Hundimiento relativo de la zona con NISAR GUNW, si se calculó. 404 si la zona no existe o no lo tiene."""
        if aoi not in store.aois():
            raise HTTPException(404, "Zona desconocida")
        path = root / aoi / "subsidence" / "subsidence.json"
        if not path.is_file():
            raise HTTPException(404, "Esta zona aún no tiene cálculo de hundimiento")
        data = json.loads(path.read_text(encoding="utf-8"))
        layer = data.get("rate_layer")
        tiles = None
        if layer and (root / layer).is_file():
            threshold = float(data.get("threshold_mm_yr") or 20.0)
            cmap = json.dumps(subsidence_colormap(threshold), separators=(",", ":"))
            tiles = _tile_url(layer, f"rescale={SUBSIDENCE_RANGE[0]:g},{SUBSIDENCE_RANGE[1]:g}&colormap=" + quote(cmap, safe=""))
        return Subsidence(
            aoi=aoi, status=data.get("status", "no_interferograms"), days=data.get("days"), pairs=data.get("pairs", []),
            track=data.get("track"), direction=data.get("direction"), valid_fraction=data.get("valid_fraction"),
            noise_mm_yr=data.get("noise_mm_yr"), threshold_mm_yr=data.get("threshold_mm_yr"),
            sinking_fraction=data.get("sinking_fraction"), max_rate_mm_yr=data.get("max_rate_mm_yr"),
            fastest_point=data.get("fastest_point"), tiles=tiles, calibrated=False, sign_check=data.get("sign_check"),
            summary=SubsidenceText(**narrative.subsidence_text(data, narrative.zone_name(aoi), lang)),
        )

    @app.get("/aois/{aoi}/series", response_model=list[SeriesInfo])
    def series(aoi: str) -> list[SeriesInfo]:
        return [
            SeriesInfo(
                id=manifest["series"]["id"],
                data_kind=manifest["data_kind"],
                maturity=manifest["maturity"],
                bbox=manifest["bbox"],
                dates=[item["date"] for item in manifest["dates"]],
                relief=relief_from_manifest(manifest),
            )
            for manifest in manifests_or_404(aoi)
        ]

    @app.get("/aois/{aoi}/series/{series_id}/verdicts", response_model=list[Verdict])
    def verdicts(aoi: str, series_id: str, lang: narrative.Lang = "es") -> list[Verdict]:
        return series_verdicts(manifest_or_404(aoi, series_id), lang)

    @app.get("/aois/{aoi}/series/{series_id}/verdicts/{pair_id}", response_model=Verdict)
    def verdict(aoi: str, series_id: str, pair_id: str, lang: narrative.Lang = "es") -> Verdict:
        manifest = manifest_or_404(aoi, series_id)
        for pair in manifest["pairs"]:
            if pair["id"] == pair_id:
                return verdict_for(manifest, pair, lang)
        raise HTTPException(404, f"Par desconocido: {pair_id}")

    @app.get("/aois/{aoi}/events", response_model=EventVerdict)
    def event(
        request: Request,
        aoi: str,
        date: dt.date,
        persistence_hours: int = Query(
            24, ge=1, le=720,
            description="Horas que dura el evento. Si se da, manda sobre event_type. Sin ninguno de los dos, 24 h.",
        ),
        event_type: EventType | None = Query(
            None, description="Tipo de evento: fija una persistencia supuesta (urban_storm 6 h, river_flood 72 h, wildfire 240 h)."
        ),
        time: dt.time | None = Query(None, description="Hora UTC de inicio del evento, HH:MM. Opcional."),
        lang: narrative.Lang = "es",
    ) -> EventVerdict:
        # El 24 por omisión se mantiene en el contrato; solo cuenta como "user" si la consulta lo trae.
        explicit = persistence_hours if "persistence_hours" in request.query_params else None
        assumed = rules.persistence(event_type, explicit)
        manifests = manifests_or_404(aoi)
        passes, pass_times, excluded = [], {}, {}
        for manifest in manifests:
            known = passes_for(manifest) or {}
            series_excluded = [item for item in excluded_for(manifest) if _same_series(item.series, manifest["series"])]
            # Se citan aunque el manifiesto ya no traiga esa fecha (Eco aparta los gránulos defectuosos).
            excluded.update({item.id: item for item in series_excluded})
            for item in manifest["dates"]:
                day = dt.date.fromisoformat(item["date"])
                # Una pasada que catalog declara inservible no cuenta como observación del evento. Se reconoce
                # por gránulo o por fecha: una serie pasa como mucho una vez al día.
                if any(ex.id == granule_key(item["granule"]) or ex.date == day for ex in series_excluded):
                    continue
                passes.append(day)
                found = known.get(granule_key(item["granule"]))
                if found is not None:
                    pass_times[day] = found.acquired_at
        event_time = time.replace(tzinfo=None) if time else None
        status = rules.event_status(passes, date, assumed.hours, event_time, pass_times)
        synthetic = any(manifest["data_kind"] == "synthetic" for manifest in manifests)
        low, high = status.previous_pass or dt.date.min, status.next_pass or dt.date.max
        between = sorted((item for item in excluded.values() if low <= item.date <= high), key=lambda item: item.date)
        return EventVerdict(
            aoi=aoi,
            event_date=date,
            event_time=event_time,
            event_type=event_type,
            persistence_hours=assumed.hours,
            assumption=PersistenceAssumption(
                persistence_hours=assumed.hours,
                source=assumed.source,
                event_type=assumed.event_type,
                calibrated=False,
                hours_by_event_type=dict(rules.PERSISTENCE_BY_EVENT_TYPE),
                text=narrative.persistence_text(assumed, lang),
            ),
            state=status.state,
            cause=status.cause,
            cause_label=narrative.CAUSES[lang][status.cause] if status.cause else None,
            previous_pass=status.previous_pass,
            next_pass=status.next_pass,
            next_pass_acquired_at=status.next_pass_at,
            data_kind="synthetic" if synthetic else "real",
            excluded_passes=[_excluded_out(item) for item in between],
            summary=Summary(**_with_skipped(
                narrative.event_summary(status, date.isoformat(), lang, synthetic, assumed), between, lang
            )),
        )

    @app.get("/aois/{aoi}/series/{series_id}/pixel", response_model=PixelSeries)
    def pixel(
        aoi: str,
        series_id: str,
        lon: float = Query(ge=-180, le=180),
        lat: float = Query(ge=-90, le=90),
    ) -> PixelSeries:
        manifest = manifest_or_404(aoi, series_id)
        names = {code: name for name, code in manifest["state_codes"].items()}
        values, changes = [], []
        try:
            for item in manifest["dates"]:
                values.append(
                    PixelDate(
                        date=item["date"],
                        hh_db=store.sample(item["hh_db"], lon, lat),
                        hv_db=store.sample(item["hv_db"], lon, lat),
                    )
                )
            for pair in manifest["pairs"]:
                if pair["kind"] == "consecutive":
                    code = store.sample(pair["layers"]["state"], lon, lat)
                    changes.append(PixelChange(pair=pair["id"], state=None if code is None else names.get(int(code))))
        except OutsideLayer as exc:
            raise HTTPException(404, "El punto queda fuera de la serie") from exc
        return PixelSeries(
            aoi=aoi, series=series_id, lon=lon, lat=lat, data_kind=manifest["data_kind"], values=values, changes=changes
        )

    cells_cache: dict[str, list | None] = {}

    def cells_for(relative: str | None) -> list | None:
        """Celdas de 1 km de un par, leídas una vez. None si no hay archivo o no se puede leer."""
        if relative is None:
            return None
        if relative not in cells_cache:
            try:
                path = (root / relative).resolve()
                if root.resolve() not in path.parents:
                    raise ValueError(f"ruta fuera de los artefactos: {relative}")
                cells_cache[relative] = search.prepare_cells(json.loads(path.read_text(encoding="utf-8")))
            except (OSError, ValueError, KeyError, TypeError, IndexError):
                log.exception("No se pudieron leer las celdas %s", relative)
                cells_cache[relative] = None
        return cells_cache[relative]

    def with_area(index: search.Index, rows: list[search.SearchResult], bbox) -> list[search.SearchResult]:
        """Cada fila con su estado dentro del rectángulo (T-BAL-18). Las filas del índice no se modifican."""
        return [
            row.model_copy(update={"area": search.area_result(
                bbox, cells_for(index.cells_paths.get(search.row_key(row))), rules.MIN_OBSERVED_FRACTION,
                rules.MIN_CHANGED_FRACTION, rules.UNOBSERVABLE_CAUSES,
            )})
            for row in rows
        ]

    def footprints_for(index: search.Index) -> dict[tuple[str, str], tuple | str]:
        """Por (zona, serie) de cada fila: los polígonos de su huella en catalog, o el motivo de que no haya."""
        result: dict[tuple[str, str], tuple | str] = {}
        for aoi in sorted({row.aoi for row in index.rows}):
            try:
                found = {
                    (item.track, item.direction, item.frame): item.polygons
                    for item in (footprint_source.footprints(aoi) if footprint_source else [])
                }
                failed = None if footprint_source else search.CATALOG_UNAVAILABLE
            except CatalogUnavailable:
                found, failed = {}, search.CATALOG_UNAVAILABLE
            for (row_aoi, series_id), key in index.series_keys.items():
                if row_aoi != aoi:
                    continue
                polygons = found.get(key)
                result[(aoi, series_id)] = failed or (polygons if polygons else search.FOOTPRINT_UNAVAILABLE)
        return result

    def denied(required: search.Role, why: str) -> JSONResponse:
        return JSONResponse(status_code=403, content={"detail": why, "required_role": required})

    @dataclass
    class SearchRequest:
        """Consulta común a la búsqueda y a la exportación, ya interpretada. denied: 403 que hay que devolver."""

        role: search.Role
        filters: search.Filters
        sort: str
        order: str
        denied: JSONResponse | None = None

    def search_request(
        x_auth_role: str | None = Header(None, include_in_schema=False),
        aoi: str | None = Query(None, description="Zona."),
        series_id: str | None = Query(None, description="Serie, p. ej. T048A-F015."),
        direction: Literal["A", "D"] | None = Query(None, description="Dirección de la órbita."),
        kind: Literal["consecutive", "full_window"] | None = Query(None),
        date_from: dt.date | None = Query(None, description="from_date del par igual o posterior."),
        date_to: dt.date | None = Query(None, description="to_date del par igual o anterior."),
        interval_min: int | None = Query(None, ge=0, description="interval_days mínimo."),
        interval_max: int | None = Query(None, ge=0, description="interval_days máximo."),
        state: list[Literal["change_probable", "no_detectable_change", "not_observable"]] | None = Query(
            None, description="Uno o varios estados."
        ),
        cause: list[str] | None = Query(None, description="Una o varias causas de not_observable."),
        changed_min: float | None = Query(None, ge=0, le=1, description="changed_fraction mínima (0 a 1)."),
        changed_max: float | None = Query(None, ge=0, le=1, description="changed_fraction máxima (0 a 1)."),
        scene_shift_exceeds: bool | None = Query(
            None, description="Desplazamiento de la escena sobre el umbral. Las filas sin desplazamiento no se evalúan."
        ),
        quality_flag: bool | None = Query(
            None, description="Solo researcher. true: alguna fecha con radiometric_outlier; false: ninguna."
        ),
        water: search.WaterFilter | None = Query(
            None, description="Contraste con OPERA. Las filas con water not_available quedan fuera y se cuentan en "
            "query.not_evaluated.",
        ),
        max_cloud_cover: float | None = Query(
            None, ge=0, le=100, description="Nubosidad máxima por tesela de las dos escenas ópticas, en %."
        ),
        noise_hh_min: float | None = Query(
            None, ge=0, description="Solo researcher. evidence.noise.hh_db mínima, en dB. Las filas sin ruido no se "
            "evalúan y se cuentan en query.not_evaluated.",
        ),
        noise_hh_max: float | None = Query(None, ge=0, description="Solo researcher. evidence.noise.hh_db máxima, en dB."),
        noise_hv_min: float | None = Query(None, ge=0, description="Solo researcher. evidence.noise.hv_db mínima, en dB."),
        noise_hv_max: float | None = Query(None, ge=0, description="Solo researcher. evidence.noise.hv_db máxima, en dB."),
        data_kind: Literal["real", "synthetic"] | None = Query(None),
        q: str | None = Query(
            None, max_length=200, description="Texto libre sobre los textos del veredicto (summary, hipótesis, causa), "
            "su identificador y los granule_id, en el idioma de lang (RF-BUS-02). Cada palabra cuenta como prefijo, "
            "todas deben aparecer, sin distinguir mayúsculas ni acentos. Sin palabras, no hay resultados.",
        ),
        lang: narrative.Lang = Query("es", description="Idioma de los textos en los que busca q."),
        bbox: str | None = Query(
            None, description="Rectángulo WGS84 'oeste,sur,este,norte' (RF-BUS-10): series cuya huella de catalog "
            "(T-ANT-17) toca el rectángulo. Si no hay huella, la fila no se evalúa y se cuenta en "
            "query.not_evaluated. Dice qué series cubren el área, no que el veredicto hable de ella: el veredicto "
            "sigue siendo de toda la zona.",
            examples=["-105.8,26.85,-105.6,27.0"],
        ),
        sort: search.SortKey = Query(
            "date", description="date ordena por to_date. noise_hh y noise_hv son solo para researcher; las filas "
            "sin ruido van al final en los dos sentidos.",
        ),
        order: Literal["asc", "desc"] = Query("desc"),
    ) -> SearchRequest:
        role = search.role_from_header(x_auth_role)
        empty = search.Filters()
        if role == "public":
            return SearchRequest(role, empty, sort, order,
                                 denied("student", "La búsqueda pide una cuenta de estudiante o de investigación."))
        try:
            area = search.parse_bbox(bbox) if bbox is not None else None
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        filters = search.Filters(
            aoi=aoi, series_id=series_id, direction=direction, kind=kind, date_from=date_from, date_to=date_to,
            interval_min=interval_min, interval_max=interval_max, state=tuple(state or ()), cause=tuple(cause or ()),
            changed_min=changed_min, changed_max=changed_max, scene_shift_exceeds=scene_shift_exceeds,
            quality_flag=quality_flag, water=water, max_cloud_cover=max_cloud_cover, data_kind=data_kind,
            noise_hh_min=noise_hh_min, noise_hh_max=noise_hh_max, noise_hv_min=noise_hv_min,
            noise_hv_max=noise_hv_max,
            q=q, lang=lang if q is not None else None, bbox=area,
        )
        if role != "researcher":
            used = [name for name in search.RESEARCHER_FILTERS if getattr(filters, name) is not None]
            if used:
                return SearchRequest(role, filters, sort, order,
                                     denied("researcher", f"Filtro solo para investigación: {', '.join(used)}."))
            if sort in search.RESEARCHER_SORTS:
                return SearchRequest(role, filters, sort, order,
                                     denied("researcher", f"Ordenar por {sort} es solo para investigación."))
        return SearchRequest(role, filters, sort, order)

    def run_search(request: SearchRequest) -> tuple[search.Index, list[search.SearchResult], dict]:
        """Filas que cumplen la consulta, ya ordenadas, y las que no se pudieron evaluar."""
        index = current_index()
        filters = request.filters
        text_hits = None
        if filters.q is not None:
            text_hits = index.text.match(filters.q, filters.lang or "es") if index.text is not None else set()
        matched, not_evaluated = search.apply(
            index.rows, filters, text_hits, footprints_for(index) if filters.bbox is not None else None
        )
        return index, search.order(matched, request.sort, request.order), not_evaluated

    @app.get(
        "/search/verdicts",
        response_model=search.SearchPage,
        responses={
            400: {"description": "Cursor ilegible, de otra consulta o de un índice anterior."},
            422: {"description": "Parámetro no válido, p. ej. un bbox mal formado."},
            403: {"model": search.AccessDenied, "description": "Perfil insuficiente; required_role dice cuál hace falta."},
        },
        openapi_extra={"security": [{"bearerAuth": []}], "x-required-role": "student"},
        summary="Búsqueda de veredictos (student y researcher)",
        description="Filtra, ordena y pagina todos los veredictos precalculados (RF-BUS-01, 03 a 05). Cada fila "
        "copia los campos del veredicto completo y enlaza a él. public recibe 403; student, sin los filtros de calidad "
        "y de ruido ni el orden por ruido, y con 50 resultados por página como máximo; researcher, todo y hasta 500. Un filtro sin resultados "
        "devuelve una lista vacía con total 0, nunca 404.",
    )
    def search_verdicts(
        request: SearchRequest = Depends(search_request),
        limit: int = Query(search.DEFAULT_LIMIT, ge=1, le=search.PAGE_LIMIT["researcher"]),
        cursor: str | None = Query(None, description="next_cursor de la página anterior, con la misma consulta."),
    ):
        if request.denied is not None:
            return request.denied
        role, filters, sort, order = request.role, request.filters, request.sort, request.order
        if role != "researcher" and limit > search.PAGE_LIMIT[role]:
            return denied(
                "researcher", f"Más de {search.PAGE_LIMIT[role]} resultados por página es solo para investigación."
            )
        index, ordered, not_evaluated = run_search(request)
        print_ = search.fingerprint(filters, sort, order)
        try:
            offset = search.decode_cursor(cursor, print_, index.generation) if cursor else 0
        except search.InvalidCursor as exc:
            raise HTTPException(400, str(exc)) from exc
        following = offset + limit
        return search.SearchPage(
            total=len(ordered),
            results=(ordered[offset:following] if filters.bbox is None
                     else with_area(index, ordered[offset:following], filters.bbox)),
            next_cursor=search.encode_cursor(following, print_, index.generation) if following < len(ordered) else None,
            query=search.SearchQuery(
                filters=filters.applied(), sort=sort, order=order, limit=limit, role=role,
                not_evaluated=not_evaluated, water_contrast="included" if index.water_included else "pending",
                indexed_at=index.built_at,
            ),
        )

    @app.get(
        "/search/verdicts/export",
        responses={
            200: {
                "description": "Archivo en streaming. CSV: una fila por veredicto, la consulta en las cabeceras "
                "X-Export-*. JSON: {metadata, results}. GeoJSON: FeatureCollection con metadata y la caja de la "
                "zona como geometría de cada Feature.",
                "content": {"text/csv": {}, "application/json": {}, "application/geo+json": {}},
            },
            403: {"model": search.AccessDenied, "description": "Solo researcher; required_role dice cuál hace falta."},
            422: {"description": "Parámetro no válido, p. ej. un bbox mal formado."},
        },
        openapi_extra={"security": [{"bearerAuth": []}], "x-required-role": "researcher"},
        summary="Exportación de la búsqueda de veredictos (researcher)",
        description="Los mismos filtros y orden que /search/verdicts, sin paginar (RF-BUS-06). Cada fila copia el "
        "veredicto completo: data_kind, los dos granule_id, interval_days, la regla de decisión con sus umbrales y "
        "calibrated, y los supuestos declarados (assumptions, todos sin calibrar salvo que digan lo contrario). La "
        "consulta, el perfil, la hora y el total van en metadata (JSON y GeoJSON) y en las cabeceras X-Export-*.",
    )
    def export_verdicts(
        format: export.Format = Query(..., description="csv, geojson o json."),
        request: SearchRequest = Depends(search_request),
    ):
        if request.role != "researcher":
            return denied("researcher", "La exportación es solo para investigación.")
        if request.denied is not None:
            return request.denied
        index, ordered, not_evaluated = run_search(request)
        generated = now()
        metadata = {
            "export_version": export.EXPORT_VERSION,
            "generated_at": generated.isoformat().replace("+00:00", "Z"),
            "indexed_at": index.built_at.isoformat().replace("+00:00", "Z"),
            "total": len(ordered),
            "data_kinds": sorted({row.data_kind for row in ordered}),
            "query": {"filters": request.filters.applied(), "sort": request.sort, "order": request.order,
                      "role": request.role},
            "not_evaluated": {name: item.model_dump() for name, item in not_evaluated.items()},
            "water_contrast": "included" if index.water_included else "pending",
            "source": "/search/verdicts/export de verdicts (nisar-veredictos, Apache-2.0)",
            "notice": "Cada fila copia un veredicto completo, que es la referencia: verdict_path lleva a él. Los "
            "umbrales no se han contrastado con verdad de campo (decision_calibrated y assumptions). Las filas con "
            "data_kind synthetic son datos sintéticos, no observaciones.",
        }

        def records():
            for row in ordered:
                key = search.row_key(row)
                yield export.record(row, index.verdicts[key]), export.bbox_polygon(
                    index.series_bbox.get((row.aoi, row.series_id))
                )

        if format == "csv":
            body = export.stream_csv(item for item, _ in records())
        elif format == "json":
            body = export.stream_json(metadata, (item for item, _ in records()))
        else:
            body = export.stream_geojson(metadata, records())
        return StreamingResponse(
            (chunk.encode("utf-8") for chunk in body),
            media_type=export.MEDIA_TYPES[format],
            headers=export.headers(format, metadata, generated),
        )

    def openapi_with_security() -> dict:
        if app.openapi_schema is None:
            schema = FastAPI.openapi(app)
            schema.setdefault("components", {})["securitySchemes"] = {
                "bearerAuth": {
                    "type": "http", "scheme": "bearer", "bearerFormat": "JWT",
                    "description": "Token de acceso de auth (specs/06-acceso). El gateway lo valida y pasa el perfil "
                    "en X-Auth-Role; sin token la petición es public. Las rutas que no lo declaran no lo piden.",
                }
            }
            app.openapi_schema = schema
        return app.openapi_schema

    app.openapi = openapi_with_security

    return app


app = create_app()
