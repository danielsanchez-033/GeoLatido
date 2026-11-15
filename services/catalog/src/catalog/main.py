"""API del catálogo: zonas, series comparables, línea de tiempo y referencias externas."""
from __future__ import annotations

import os
from collections.abc import Callable
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Annotated, Literal, TypeVar

import httpx
import yaml
from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from pydantic import AfterValidator, BaseModel, Field

from .cmr import CmrSource, GranuleSource
from . import opera, plan
from .optical import COLLECTION, LICENSE_URL, EarthSearchSource, SceneSource, group_acquisitions, window
from .pairing import Granule, Series, build_series, closed_ring, series_id
from .timeline import build_timeline
from . import search as passes_search
from . import world

T = TypeVar("T")

# Lo que puede pasar al leer un servicio externo: sin red, error HTTP, o un cuerpo que no es
# JSON (ValueError) o no trae lo esperado (KeyError). Todo acaba en 502, nunca en datos parciales.
UPSTREAM_ERRORS = (httpx.HTTPError, ValueError, KeyError)


def _upstream(call: Callable[[], T], detail: str) -> T:
    try:
        return call()
    except UPSTREAM_ERRORS as exc:
        raise HTTPException(502, detail) from exc


def _as_utc(value: datetime) -> datetime:
    """Toda hora de la API sale en UTC. Una hora sin zona es un fallo del código, no se adivina."""
    if value.tzinfo is None:
        raise ValueError("hora sin zona horaria")
    return value.astimezone(timezone.utc)


UtcDatetime = Annotated[datetime, AfterValidator(_as_utc)]


class WorldGranuleOut(BaseModel):
    id: str = Field(description="Nombre del gránulo (título en CMR).")
    acquired_at: UtcDatetime = Field(description="Inicio de la adquisición, UTC, del nombre del gránulo.")
    date: date
    track: int
    direction: Literal["A", "D"]
    frame: int
    mode: str
    polarization: str
    size_mb: float
    footprint: list[list[float]] = Field(
        description="Anillo cerrado [lon, lat] de la huella en CMR, 5 decimales. Vacío si CMR no da polígono."
    )
    bbox: list[float] | None = Field(description="Caja [oeste, sur, este, norte] de la huella, o null sin huella.")
    browse_url: str | None = Field(
        description="Vista previa _LATLON.png de ASF: pública, sin cuenta. No es un producto georreferenciado: su caja "
        "en el mapa es la de la huella y se dice aproximada."
    )
    thumbnail_url: str | None = Field(description="Miniatura de esa vista previa.")
    data_url: str = Field(description="HDF5 completo en ASF; pide una cuenta de Earthdata.")
    vertex_url: str = Field(description="El gránulo en ASF Data Search Vertex.")
    earthdata_search_url: str = Field(description="El gránulo en NASA Earthdata Search.")


class WorldSearchOut(BaseModel):
    bbox: list[float]
    from_: date = Field(alias="from")
    to: date
    direction: Literal["A", "D"] | None
    total: int = Field(description="Gránulos que CMR encuentra en el rectángulo y las fechas, sin filtrar por dirección.")
    granules: list[WorldGranuleOut] = Field(description="Los más recientes primero, como mucho `limit`.")
    collection: str
    sources: list[str] = Field(description="Recursos oficiales usados: CMR (NASA Earthdata Search) y ASF.")
    data_kind: Literal["real"] = "real"

    model_config = {"populate_by_name": True}


class Aoi(BaseModel):
    id: str
    name: str
    bbox: list[float]
    collection: str
    maturity: str


class SeriesGranule(BaseModel):
    id: str
    date: date
    size_mb: float
    download_url: str


class ExcludedGranule(BaseModel):
    id: str = Field(description="granule_id excluido, el título de CMR sin extensión.")
    date: date
    acquired_at: UtcDatetime = Field(description="Inicio de la adquisición, en UTC.")
    reason: str = Field(description="Código del motivo. product_defect: el fallo está en el producto publicado.")
    evidence: str = Field(description="Cómo se comprobó.")
    checked_on: date = Field(description="Fecha de la comprobación.")


class FootprintGeometry(BaseModel):
    type: Literal["Polygon"]
    coordinates: list[list[list[float]]] = Field(
        description="Un solo anillo [lon, lat] en WGS84, cerrado y con 5 decimales, tal como lo da CMR."
    )


class FootprintProperties(BaseModel):
    series: str
    track: int
    direction: str = Field(description="A ascendente o D descendente.")
    frame: int
    granule_id: str = Field(description="Gránulo del que sale la huella.")
    basis: Literal["latest_granule"] = Field(
        description="La huella es la del gránulo más reciente de la serie con polígono en CMR. Todos los de una "
        "serie son del mismo marco, así que sus huellas casi coinciden."
    )


class SeriesFootprint(BaseModel):
    type: Literal["Feature"]
    geometry: FootprintGeometry
    properties: FootprintProperties


class SeriesOut(BaseModel):
    id: str
    track: int
    direction: str
    frame: int
    mode: str
    polarization: str
    crid: str
    maturity: str
    contains_aoi: bool
    max_gap_days: int
    spans_data_gap: bool
    granules: list[SeriesGranule] = Field(description="Fechas utilizables, sin las excluidas.")
    footprint: SeriesFootprint | None = Field(
        default=None,
        description="Huella de la serie como Feature GeoJSON, para situarla en el globo y filtrar por área "
        "(RF-INT-16 y RF-BUS-10). null si CMR no da polígono para ninguna de sus fechas.",
    )
    excluded: list[ExcludedGranule] = Field(
        description="Gránulos de la serie que existen en CMR pero se declararon inservibles en la zona."
    )


class TimelinePass(BaseModel):
    series: str
    granule_id: str
    acquired_at: UtcDatetime = Field(description="Inicio de la adquisición, en UTC.")
    published_at: UtcDatetime | None = Field(
        description="Última actualización del gránulo en CMR, en UTC. Aproxima la publicación."
    )
    latency_hours: float | None = Field(description="Horas entre la adquisición y published_at.")
    contains_aoi: bool = Field(description="La huella de la serie contiene la zona completa.")


class TimelineInterval(BaseModel):
    series: str
    start: UtcDatetime
    end: UtcDatetime
    days: int = Field(description="Días entre dos pasadas consecutivas de la misma serie.")
    crosses_gap: bool = Field(description="El intervalo atraviesa un hueco de adquisición conocido.")


class TimelineGap(BaseModel):
    start: date = Field(description="Primer día sin adquisiciones, incluido.")
    end: date = Field(description="Último día sin adquisiciones, incluido.")
    source: str


class ObservationPlan(BaseModel):
    status: Literal["planned", "partial", "not_planned", "no_plan", "unknown"] = Field(
        description=(
            "Qué dice el plan diario de NISAR (NISAR_COP) para la hora estimada. planned: una observación L-SAR "
            "cubre de 10 s antes a 40 s después. partial: la cubre solo en parte. not_planned: hay plan y no la "
            "cubre. no_plan: no hay plan publicado para esa hora. unknown: catalog no tiene el resumen de "
            "`ingest plan` o no coincide con esta pasada. Un plan no garantiza la adquisición: en el hueco de "
            "2026-07-27 a 2026-08-02 hubo planes y no se adquirió nada."
        )
    )
    plan: str | None = Field(description="Título del gránulo de NISAR_COP que se usó, con su versión.")
    config_id: str | None = Field(description="LSAR_CONFIG_ID de la observación planificada.")
    same_config: bool | None = Field(
        description="La configuración coincide con la del plan de la última pasada adquirida. null si falta alguna."
    )
    checked_at: UtcDatetime | None = Field(description="Cuándo consultó ingest el plan, en UTC.")


class NextPassEstimate(BaseModel):
    series: str
    expected_at: UtcDatetime = Field(description="Estimación, no plan de observación: última pasada más N ciclos.")
    basis: Literal["12-day cycle"]
    observation_plan: ObservationPlan = Field(
        description="Si el plan de observación de NISAR incluye esta pasada. No cambia expected_at."
    )


class ExcludedPass(ExcludedGranule):
    series: str


class TimelineOut(BaseModel):
    aoi: str
    published_at_basis: Literal["cmr_updated"] = Field(
        description="published_at es la fecha 'updated' de CMR, una aproximación a la publicación real."
    )
    passes: list[TimelinePass]
    intervals: list[TimelineInterval]
    gaps: list[TimelineGap]
    next_pass_estimates: list[NextPassEstimate]
    excluded: list[ExcludedPass] = Field(
        description="Pasadas que existen pero se declararon inservibles; no están en passes ni en intervals."
    )


class OpticalTile(BaseModel):
    id: str
    tile: str = Field(description="Tesela MGRS de unos 110 km de lado.")
    acquired_at: UtcDatetime
    cloud_cover: float = Field(description="Porcentaje de nubes de la tesela completa, no de la zona.")
    visual_url: str = Field(description="COG en color verdadero (TCI), legible por HTTPS sin cuenta.")
    bbox: list[float] | None = Field(
        default=None,
        min_length=4,
        max_length=4,
        description="Caja de los datos de la escena en WGS84, [oeste, sur, este, norte], tomada del item STAC de "
        "Earth Search: la de su huella de datos, no la del cuadrado MGRS completo, así que una escena de borde de "
        "franja tiene una caja menor. Como en STAC, si cruza el antimeridiano el oeste es mayor que el este. Sirve "
        "como bounds de la fuente en el mapa, para no pedir teselas fuera de los datos. null si Earth Search no "
        "la da.",
    )


class OpticalAcquisition(BaseModel):
    platform: str
    acquired_at: UtcDatetime = Field(description="Hora UTC de la primera tesela de la adquisición.")
    days_from_date: int = Field(description="Días respecto a la fecha pedida; negativo si es anterior.")
    covers_aoi: bool = Field(description="Las teselas juntas cubren toda la zona.")
    max_cloud_cover: float = Field(description="Mayor nubosidad entre sus teselas. Es de la tesela, no de la zona.")
    tiles: list[OpticalTile]


class OpticalOut(BaseModel):
    aoi: str
    date: date
    days: int
    max_cloud: float
    source: str
    collection: str
    license: str
    license_url: str
    attribution: str = Field(description="Texto de atribución que debe mostrarse junto a la imagen.")
    cloud_cover_basis: Literal["tile"] = Field(
        description="La nubosidad es la de cada tesela MGRS completa; la zona puede estar más o menos nublada."
    )
    acquisitions: list[OpticalAcquisition]


class OperaTileOut(BaseModel):
    id: str = Field(description="Título del gránulo en CMR, sin extensión.")
    tile: str = Field(description="Tesela MGRS sin la T inicial.")
    acquired_at: UtcDatetime = Field(description="time_start de CMR, en UTC.")
    produced_at: UtcDatetime = Field(description="Hora de producción que figura en el título, en UTC.")
    wtr_url: str = Field(description="GeoTIFF B01_WTR, clasificación de agua. Pide cuenta de Earthdata.")
    conf_url: str = Field(description="GeoTIFF B03_CONF, confianza. Pide cuenta de Earthdata. Vacío si CMR no lo publica.")
    browse_url: str | None = Field(description="Vista previa PNG del bucket público de PO.DAAC, sin cuenta ni georreferencia.")
    bbox: list[float] | None = Field(
        default=None,
        min_length=4,
        max_length=4,
        description="Caja de la tesela MGRS en WGS84, [oeste, sur, este, norte], de los boxes de CMR. "
        "Sirve para situar browse_url en el mapa. null si CMR no la publica.",
    )


class OperaAcquisition(BaseModel):
    platform: str
    acquired_at: UtcDatetime = Field(description="time_start de CMR de la primera tesela de la pasada, en UTC.")
    days_from_date: int = Field(description="Días entre la fecha UTC de la pasada y la pedida; negativo si es anterior.")
    covers_aoi: bool = Field(description="Las cajas de sus teselas contienen la zona. No dice si hay datos válidos en toda ella.")
    tiles: list[OperaTileOut]


class OperaOut(BaseModel):
    aoi: str
    date: date
    days: int
    source: str
    collection: str
    doi: str
    attribution: str = Field(description="Texto de atribución que debe mostrarse junto al producto.")
    product_spec_url: str
    min_water_body_ha: float = Field(description="Superficie mínima de una masa de agua abierta que el producto detecta.")
    min_water_body_width_m: float = Field(description="Anchura mínima de una masa de agua abierta que el producto detecta.")
    coverage_basis: Literal["tile_bbox"] = Field(
        description="covers_aoi usa la caja de cada tesela MGRS, no los píxeles válidos."
    )
    data_access: Literal["earthdata_login"] = Field(
        description="wtr_url y conf_url piden cuenta de Earthdata; browse_url no."
    )
    acquisitions: list[OperaAcquisition] = Field(description="Vacía si no hay productos en la ventana.")


def _load_aois(aoi_dir: Path | list[Path]) -> dict[str, dict]:
    """Zonas de una o varias carpetas (AOI_DIR admite varias separadas por ':'): las de config/aois y las que crea
    el procesado en línea en data/aois-online (2026-11-15). Si un id se repite, gana la primera carpeta."""
    result: dict[str, dict] = {}
    dirs = aoi_dir if isinstance(aoi_dir, list) else [aoi_dir]
    paths = [p for d in dirs if d.exists() for p in sorted(d.glob("*.yaml"))]
    for path in reversed(paths):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        result[data["id"]] = data
    return result


def _exclusions(aoi: dict) -> dict[str, dict]:
    """granule_id -> entrada de `exclude` de cualquier serie de la zona."""
    return {
        entry["granule"]: entry
        for item in aoi.get("series", [])
        for entry in item.get("exclude") or []
    }


def _split(aoi: dict, granules: list[Granule]) -> tuple[list[Granule], list[tuple[Granule, dict]]]:
    rules = _exclusions(aoi)
    usable = [g for g in granules if g.id not in rules]
    excluded = sorted(((g, rules[g.id]) for g in granules if g.id in rules), key=lambda pair: pair[0].acquired_at)
    return usable, excluded


def _excluded_fields(granule: Granule, entry: dict) -> dict:
    return {
        "id": granule.id,
        "date": granule.start,
        "acquired_at": granule.acquired_at,
        "reason": entry["reason"],
        "evidence": " ".join(str(entry["evidence"]).split()),
        "checked_on": entry["checked_on"],
    }


def _footprint_of(series: Series) -> SeriesFootprint | None:
    granule = series.footprint_granule
    if granule is None:
        return None
    return SeriesFootprint(
        type="Feature",
        geometry=FootprintGeometry(type="Polygon", coordinates=[closed_ring(granule.footprint)]),
        properties=FootprintProperties(
            series=series.id,
            track=series.track,
            direction=series.direction,
            frame=series.frame,
            granule_id=granule.id,
            basis="latest_granule",
        ),
    )


# --- Búsqueda de pasadas (T-ANT-16, RF-BUS-07) ---

# Perfiles en orden de capacidad (specs/06-acceso). Sin cuenta, `public`.
ROLE_ORDER = ("public", "student", "researcher")
STUDENT_LIMIT = 50


class PassOut(BaseModel):
    aoi: str
    series: str = Field(description="Id completo de la serie, como en /aois/{id}/series.")
    kind: Literal["acquired", "excluded", "estimated"] = Field(
        description="acquired: pasada publicada y utilizable. excluded: publicada pero declarada inservible en la "
        "zona. estimated: siguiente pasada estimada por el ciclo de 12 días, no adquirida."
    )
    at: UtcDatetime = Field(description="Hora UTC: de adquisición, o la estimada si kind es estimated.")
    date: date
    track: int
    direction: Literal["A", "D"]
    frame: int
    granule_id: str | None = Field(description="Gránulo de CMR; null en las estimadas.")
    published_at: UtcDatetime | None = Field(description="Fecha 'updated' de CMR, en UTC; aproxima la publicación.")
    latency_hours: float | None = Field(description="Horas entre la adquisición y published_at.")
    orbit_precision: Literal["P", "M", "N", "F"] | None = Field(
        description="Letra que sigue al CRID en el nombre del gránulo: P precisa, M media, N casi en tiempo real y "
        "F pronóstico, según la guía de ASF. ORBIT_TYPE de CMR no coincide con ella. null en las estimadas."
    )
    contains_aoi: bool | None = Field(description="La huella de la serie contiene la zona; null en las excluidas.")
    excluded_reason: str | None = Field(description="Motivo de la exclusión; null si no está excluida.")
    observation_plan: Literal["planned", "partial", "not_planned", "no_plan", "unknown"] = Field(
        description="Estado en el plan de observación de NISAR (NISAR_COP). El resumen de `ingest plan` solo "
        "cubre las pasadas que siguen a la última adquirida, así que las adquiridas y excluidas salen unknown."
    )
    data_kind: Literal["real"] = Field(description="Siempre real: catalog solo lee CMR, nunca datos sintéticos.")


class PassSearchOut(BaseModel):
    query: dict = Field(description="La consulta tal como se aplicó, sin los valores por omisión vacíos.")
    total: int = Field(description="Pasadas que cumplen la consulta, en todas las páginas.")
    next_cursor: str | None = Field(description="Cursor opaco de la página siguiente; null en la última.")
    orbit_precision_basis: Literal["granule_name"] = "granule_name"
    results: list[PassOut]


def _role_allows(role: str | None, required: str) -> bool:
    role = role if role in ROLE_ORDER else "public"
    return ROLE_ORDER.index(role) >= ROLE_ORDER.index(required)


def requiere_perfil(role: str | None, required: str) -> JSONResponse | None:
    """403 con el perfil necesario si `X-Auth-Role` no llega (specs/06-acceso, RF-ACC-08). La pone el gateway."""
    if _role_allows(role, required):
        return None
    names = {"student": "Estudiante", "researcher": "Investigador"}
    return JSONResponse(
        status_code=403,
        content={
            "detail": f"Hace falta una cuenta con el perfil {names[required]} o superior.",
            "required_role": required,
        },
    )


def _pass_rows(aoi: dict, granules: list[Granule], now: datetime, observation: dict | None) -> list:
    usable, excluded = _split(aoi, granules)
    series_list = build_series(usable, aoi["bbox"], min_dates=1)
    by_id = {item.id: item for item in series_list}
    result = build_timeline(
        series_list, date.fromisoformat(aoi["window"]["start"]), date.fromisoformat(aoi["window"]["end"]), now
    )
    rows = [
        passes_search.PassRow(
            aoi=aoi["id"], series=item.series, kind="acquired", at=item.acquired_at,
            track=by_id[item.series].track, direction=by_id[item.series].direction, frame=by_id[item.series].frame,
            granule_id=item.granule_id, published_at=item.published_at, latency_hours=item.latency_hours,
            contains_aoi=item.contains_aoi,
            plan_status=plan.status_for(observation, item.series, item.acquired_at).status,
        )
        for item in result.passes
    ]
    for granule, entry in excluded:
        latency = (granule.published_at - granule.acquired_at).total_seconds() / 3600 if granule.published_at else None
        series = series_id(*granule.group_key)
        rows.append(
            passes_search.PassRow(
                aoi=aoi["id"], series=series, kind="excluded", at=granule.acquired_at,
                track=granule.track, direction=granule.direction, frame=granule.frame,
                granule_id=granule.id, published_at=granule.published_at,
                latency_hours=round(latency, 1) if latency is not None else None,
                excluded_reason=entry["reason"],
                plan_status=plan.status_for(observation, series, granule.acquired_at).status,
            )
        )
    for item in result.next_pass_estimates:
        source = by_id[item.series]
        rows.append(
            passes_search.PassRow(
                aoi=aoi["id"], series=item.series, kind="estimated", at=item.expected_at,
                track=source.track, direction=source.direction, frame=source.frame,
                contains_aoi=source.contains_aoi,
                plan_status=plan.status_for(observation, item.series, item.expected_at).status,
            )
        )
    return rows


def create_app(
    aoi_dir: Path | None = None,
    source: GranuleSource | None = None,
    clock: Callable[[], datetime] | None = None,
    optical_source: SceneSource | None = None,
    opera_source: opera.OperaSource | None = None,
    plan_dir: Path | None = None,
    world_source: world.WorldSource | None = None,
) -> FastAPI:
    directory = aoi_dir or [Path(p) for p in os.environ.get("AOI_DIR", "/config/aois").split(":") if p]
    plans = plan_dir or Path(os.environ.get("PLAN_DIR", "/data/plan"))
    granule_source = source or CmrSource()
    scene_source = optical_source or EarthSearchSource()
    water_source = opera_source or opera.CmrOperaSource()
    world_search = world_source or world.CmrWorldSource()
    now = clock or (lambda: datetime.now(timezone.utc))
    app = FastAPI(title="NISAR catalog", version="0.1.0")

    def aoi_or_404(aoi_id: str) -> dict:
        aoi = _load_aois(directory).get(aoi_id)
        if aoi is None:
            raise HTTPException(404, f"Zona desconocida: {aoi_id}")
        return aoi

    def granules_for(aoi: dict) -> list[Granule]:
        return _upstream(
            lambda: granule_source.granules(
                aoi["collection"], aoi["bbox"], aoi["window"]["start"], aoi["window"]["end"]
            ),
            "El catálogo CMR no respondió o su respuesta no se pudo leer",
        )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/aois", response_model=list[Aoi])
    def aois() -> list[dict]:
        return list(_load_aois(directory).values())

    @app.get("/aois/{aoi_id}/series", response_model=list[SeriesOut])
    def series(aoi_id: str, min_dates: int = Query(2, ge=2)) -> list[SeriesOut]:
        aoi = aoi_or_404(aoi_id)
        usable, excluded = _split(aoi, granules_for(aoi))
        return [
            SeriesOut(
                id=item.id,
                track=item.track,
                direction=item.direction,
                frame=item.frame,
                mode=item.mode,
                polarization=item.polarization,
                crid=item.crid,
                maturity=aoi["maturity"],
                contains_aoi=item.contains_aoi,
                max_gap_days=item.max_gap_days,
                spans_data_gap=item.spans_data_gap,
                granules=[
                    SeriesGranule(id=g.id, date=g.start, size_mb=g.size_mb, download_url=g.download_url)
                    for g in item.granules
                ],
                footprint=_footprint_of(item),
                excluded=[
                    ExcludedGranule(**_excluded_fields(g, entry))
                    for g, entry in excluded
                    if g.group_key == (item.track, item.direction, item.frame, item.mode, item.polarization, item.crid)
                ],
            )
            for item in build_series(usable, aoi["bbox"], min_dates)
        ]

    @app.get("/aois/{aoi_id}/timeline", response_model=TimelineOut)
    def timeline(aoi_id: str) -> TimelineOut:
        aoi = aoi_or_404(aoi_id)
        usable, excluded = _split(aoi, granules_for(aoi))
        # Una sola pasada también cuenta: dice cuándo se pudo observar la zona.
        series_list = build_series(usable, aoi["bbox"], min_dates=1)
        result = build_timeline(
            series_list,
            date.fromisoformat(aoi["window"]["start"]),
            date.fromisoformat(aoi["window"]["end"]),
            now(),
        )
        observation = plan.load_plan(plans, aoi["id"])
        return TimelineOut(
            aoi=aoi["id"],
            published_at_basis="cmr_updated",
            passes=[TimelinePass(**vars(item)) for item in result.passes],
            intervals=[TimelineInterval(**vars(item)) for item in result.intervals],
            gaps=[TimelineGap(**vars(item)) for item in result.gaps],
            next_pass_estimates=[
                NextPassEstimate(
                    **vars(item),
                    observation_plan=ObservationPlan(**vars(plan.status_for(observation, item.series, item.expected_at))),
                )
                for item in result.next_pass_estimates
            ],
            excluded=[ExcludedPass(series=series_id(*g.group_key), **_excluded_fields(g, entry)) for g, entry in excluded],
        )

    @app.get("/aois/{aoi_id}/references/optical", response_model=OpticalOut)
    def optical(
        aoi_id: str,
        date: date = Query(description="Fecha de referencia, normalmente la de una pasada NISAR."),
        days: int = Query(7, ge=0, le=30, description="Días antes y después de la fecha."),
        max_cloud: float = Query(
            30, ge=0, le=100, description="Nubosidad máxima por tesela, en %. Valor inicial sin calibrar."
        ),
    ) -> OpticalOut:
        aoi = aoi_or_404(aoi_id)
        start, end = window(date, days)
        scenes = _upstream(
            lambda: scene_source.scenes(aoi["bbox"], start, end),
            "Earth Search no respondió o su respuesta no se pudo leer; no hay escenas ópticas",
        )
        acquisitions = group_acquisitions(scenes, aoi["bbox"], date, max_cloud)
        years = sorted({acq.acquired_at.year for acq in acquisitions}) or [date.year]
        return OpticalOut(
            aoi=aoi["id"],
            date=date,
            days=days,
            max_cloud=max_cloud,
            source="Earth Search v1 (Element 84)",
            collection=COLLECTION,
            license="Datos Copernicus Sentinel: acceso libre con atribución",
            license_url=LICENSE_URL,
            attribution=f"Contiene datos modificados de Copernicus Sentinel {', '.join(map(str, years))}",
            cloud_cover_basis="tile",
            acquisitions=[
                OpticalAcquisition(
                    platform=acq.platform,
                    acquired_at=acq.acquired_at,
                    days_from_date=acq.days_from_date,
                    covers_aoi=acq.covers_aoi,
                    max_cloud_cover=acq.max_cloud_cover,
                    tiles=[
                        OpticalTile(
                            id=tile.id,
                            tile=tile.tile,
                            acquired_at=tile.acquired_at,
                            cloud_cover=tile.cloud_cover,
                            visual_url=tile.visual_url,
                            bbox=list(tile.bbox) if tile.bbox else None,
                        )
                        for tile in acq.tiles
                    ],
                )
                for acq in acquisitions
            ],
        )

    @app.get("/aois/{aoi_id}/references/opera", response_model=OperaOut)
    def opera_water(
        aoi_id: str,
        date: date = Query(description="Fecha de referencia, normalmente la de una pasada NISAR."),
        days: int = Query(7, ge=0, le=30, description="Días antes y después de la fecha."),
    ) -> OperaOut:
        aoi = aoi_or_404(aoi_id)
        start, end = window(date, days)
        tiles = _upstream(
            lambda: water_source.tiles(aoi["bbox"], start, end),
            "CMR no respondió o su respuesta no se pudo leer; no hay referencias OPERA",
        )
        passes = opera.group_passes(tiles, aoi["bbox"], date)
        years = sorted({p.acquired_at.year for p in passes}) or [date.year]
        return OperaOut(
            aoi=aoi["id"],
            date=date,
            days=days,
            source="NASA CMR",
            collection=opera.COLLECTION,
            doi=opera.DOI,
            attribution=(
                "OPERA Dynamic Surface Water Extent from Sentinel-1 (v1), NASA JPL OPERA, distribuido por PO.DAAC. "
                f"Contiene datos modificados de Copernicus Sentinel {', '.join(map(str, years))}"
            ),
            product_spec_url=opera.PRODUCT_SPEC_URL,
            min_water_body_ha=opera.MIN_WATER_BODY_HA,
            min_water_body_width_m=opera.MIN_WATER_BODY_WIDTH_M,
            coverage_basis="tile_bbox",
            data_access="earthdata_login",
            acquisitions=[
                OperaAcquisition(
                    platform=p.platform,
                    acquired_at=p.acquired_at,
                    days_from_date=p.days_from_date,
                    covers_aoi=p.covers_aoi,
                    tiles=[
                        OperaTileOut(
                            id=t.id,
                            tile=t.tile,
                            acquired_at=t.acquired_at,
                            produced_at=t.produced_at,
                            wtr_url=t.wtr_url,
                            conf_url=t.conf_url,
                            browse_url=t.browse_url,
                            bbox=list(t.box) if t.box else None,
                        )
                        for t in p.tiles
                    ],
                )
                for p in passes
            ],
        )

    @app.get(
        "/search/passes",
        response_model=PassSearchOut,
        responses={
            403: {"description": "Perfil insuficiente: sin cuenta (public) o limit > 50 sin perfil researcher. "
                  "El cuerpo trae required_role."},
            422: {"description": "Parámetro o cursor no válido."},
        },
        openapi_extra={"security": [{"bearer": []}], "x-required-role": "student"},
    )
    def search_passes(
        x_auth_role: str | None = Header(default=None, include_in_schema=False),
        aoi: list[str] | None = Query(None, description="Zonas; por omisión, todas. Se puede repetir."),
        series: list[str] | None = Query(None, description="Series por id completo o corto (T048A-F015). Se puede repetir."),
        from_: date | None = Query(None, alias="from", description="Primer día, incluido (UTC)."),
        to: date | None = Query(None, description="Último día, incluido (UTC)."),
        direction: Literal["A", "D"] | None = Query(None, description="A ascendente o D descendente."),
        min_latency_hours: float | None = Query(None, ge=0, description="Sin latencia conocida no pasa el filtro."),
        max_latency_hours: float | None = Query(None, ge=0, description="Sin latencia conocida no pasa el filtro."),
        orbit_precision: list[Literal["P", "M", "N", "F"]] | None = Query(None, description="Se puede repetir."),
        kind: list[Literal["acquired", "excluded", "estimated"]] | None = Query(None, description="Se puede repetir."),
        plan_status: list[Literal["planned", "partial", "not_planned", "no_plan", "unknown"]] | None = Query(
            None, alias="plan", description="Estado en el plan de observación. Se puede repetir."
        ),
        sort: Literal["date", "-date", "latency", "-latency"] = Query("date", description="Sin latencia, al final."),
        limit: int = Query(STUDENT_LIMIT, ge=1, le=500, description="Más de 50 por página pide el perfil researcher."),
        cursor: str | None = Query(None, description="next_cursor de la página anterior."),
    ) -> PassSearchOut | JSONResponse:
        """Pasadas de las zonas filtradas por fecha, dirección, latencia, precisión de órbita, exclusión y plan.

        Perfil mínimo student (specs/06-acceso). Mientras el gateway no tenga cuentas (AUTH_ENABLED=0) todo el
        mundo es public y responde 403 con el perfil necesario.
        """
        denied = requiere_perfil(x_auth_role, "student")
        if denied is None and limit > STUDENT_LIMIT:
            denied = requiere_perfil(x_auth_role, "researcher")
        if denied is not None:
            return denied
        try:
            offset = passes_search.decode_cursor(cursor) if cursor else 0
        except ValueError as error:
            raise HTTPException(422, str(error)) from None
        known = _load_aois(directory)
        for item in aoi or []:
            if item not in known:
                raise HTTPException(404, f"Zona desconocida: {item}")
        selected = [known[item] for item in (aoi or sorted(known))]
        rows = []
        for zone in selected:
            rows += _pass_rows(zone, granules_for(zone), now(), plan.load_plan(plans, zone["id"]))
        query = passes_search.PassQuery(
            aoi=tuple(aoi or ()), series=tuple(series or ()), start=from_, end=to, direction=direction,
            min_latency_hours=min_latency_hours, max_latency_hours=max_latency_hours,
            orbit_precision=tuple(orbit_precision or ()), kind=tuple(kind or ()), plan=tuple(plan_status or ()),
            sort=sort, offset=offset, limit=limit,
        )
        page, total, following = passes_search.search(rows, query)
        return PassSearchOut(
            query=query.interpreted(),
            total=total,
            next_cursor=passes_search.encode_cursor(following) if following is not None else None,
            results=[
                PassOut(
                    aoi=row.aoi, series=row.series, kind=row.kind, at=row.at, date=row.at.date(),
                    track=row.track, direction=row.direction, frame=row.frame, granule_id=row.granule_id,
                    published_at=row.published_at, latency_hours=row.latency_hours,
                    orbit_precision=row.orbit_precision, contains_aoi=row.contains_aoi,
                    excluded_reason=row.excluded_reason, observation_plan=row.plan_status, data_kind="real",
                )
                for row in page
            ],
        )

    @app.get(
        "/search/world",
        response_model=WorldSearchOut,
        response_model_by_alias=True,
        responses={422: {"description": "Rectángulo o fechas no válidos."}, 502: {"description": "CMR no respondió."}},
    )
    def search_world(
        bbox: str = Query(..., description="oeste,sur,este,norte en WGS84; sin cruzar el antimeridiano."),
        from_: date | None = Query(None, alias="from", description="Primer día (UTC). Por omisión, 90 días antes de `to`."),
        to: date | None = Query(None, description="Último día (UTC), incluido. Por omisión, hoy."),
        direction: Literal["A", "D"] | None = Query(None, description="A ascendente o D descendente."),
        limit: int = Query(60, ge=1, le=world.MAX_RESULTS),
    ) -> WorldSearchOut:
        """Pasadas NISAR GCOV en cualquier parte del mundo, sin descargar nada y sin cuenta (buscador mundial).

        Usa CMR, el catálogo detrás de NASA Earthdata Search, y las vistas previas públicas de ASF. Abierta a todos:
        solo son metadatos públicos.
        """
        try:
            caja = [float(v) for v in bbox.split(",")]
        except ValueError:
            raise HTTPException(422, "bbox debe ser oeste,sur,este,norte") from None
        if len(caja) != 4 or not all(-180 <= caja[i] <= 180 for i in (0, 2)) or not all(-90 <= caja[i] <= 90 for i in (1, 3)):
            raise HTTPException(422, "bbox fuera de rango")
        if caja[0] >= caja[2] or caja[1] >= caja[3]:
            raise HTTPException(422, "bbox: oeste < este y sur < norte, sin cruzar el antimeridiano")
        fin = to or now().date()
        inicio = from_ or date.fromordinal(fin.toordinal() - 90)
        if inicio > fin:
            raise HTTPException(422, "from posterior a to")
        page = _upstream(
            lambda: world_search.search(caja, inicio.isoformat(), fin.isoformat(), direction, limit),
            "El catálogo CMR no respondió o su respuesta no se pudo leer",
        )
        salida = []
        for g in page.granules:
            anillo = closed_ring(g.footprint) if len(g.footprint) >= 3 else []
            caja_g = (
                [min(p[0] for p in anillo), min(p[1] for p in anillo), max(p[0] for p in anillo), max(p[1] for p in anillo)]
                if anillo
                else None
            )
            salida.append(
                WorldGranuleOut(
                    id=g.id, acquired_at=g.acquired_at, date=g.acquired_at.date(), track=g.track,
                    direction=g.direction, frame=g.frame, mode=g.mode, polarization=g.polarization,
                    size_mb=round(g.size_mb, 1), footprint=anillo, bbox=caja_g, browse_url=g.browse_url,
                    thumbnail_url=g.thumbnail_url, data_url=g.data_url, vertex_url=world.vertex_url(g.id),
                    earthdata_search_url=world.earthdata_search_url(g.id),
                )
            )
        return WorldSearchOut(
            bbox=caja, **{"from": inicio}, to=fin, direction=direction, total=page.total, granules=salida,
            collection=world.COLLECTION,
            sources=["NASA CMR (Earthdata Search)", "ASF DAAC (Vertex) browse images"],
        )

    def openapi_with_bearer() -> dict:
        # Las rutas nuevas declaran el esquema bearer (specs/06-acceso, RF-ACC-08); las anteriores no.
        if app.openapi_schema is None:
            schema = get_openapi(title=app.title, version=app.version, routes=app.routes)
            schema.setdefault("components", {})["securitySchemes"] = {
                "bearer": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
            }
            app.openapi_schema = schema
        return app.openapi_schema

    app.openapi = openapi_with_bearer
    return app


app = create_app()
