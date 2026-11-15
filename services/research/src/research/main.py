"""API de investigación (`/api/research/` en el gateway).

Rutas nuevas, aditivas: no cambian las de catalog ni las de verdicts, a las que llama por HTTP.
"""
from __future__ import annotations

import datetime as dt
import os
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field, field_validator, model_validator

from . import analysis, discovery, events, nlq, places, sources, story
from .pipeline import STEPS, Deps, Runner
from .products import BY_ID, PHENOMENON_PRODUCTS, PRODUCTS
from .store import Store

Phenomenon = Literal["surface_change", "mining", "flood", "landslide", "deformation", "glacier"]

PROFILES = {
    "mining_terrain": {"phenomena": ["mining", "deformation"], "case": "parral", "label": "Minería y terreno"},
    "flood_hydrology": {"phenomena": ["flood"], "case": "parral", "label": "Inundación e hidrología"},
    "landslide_slope": {"phenomena": ["landslide", "deformation"], "case": "sur_chihuahua", "label": "Deslizamientos y laderas"},
    "glacier_climate": {"phenomena": ["glacier"], "case": "sermeq_kujalleq", "label": "Glaciares y clima"},
}


class AreaIn(BaseModel):
    id: str | None = Field(None, description="Id de un lugar del nomenclátor (GET /places).")
    name: str | None = None
    bbox: list[float] | None = Field(None, description="[oeste, sur, este, norte] en WGS84.")

    @field_validator("bbox")
    @classmethod
    def _bbox(cls, v):
        if v is None:
            return v
        if len(v) != 4:
            raise ValueError("bbox necesita 4 números")
        w, s, e, n = v
        if not (-180 <= w < e <= 180 and -90 <= s < n <= 90):
            raise ValueError("bbox fuera de rango o con oeste ≥ este / sur ≥ norte")
        return v

    @model_validator(mode="after")
    def _one(self):
        if not self.id and not self.bbox:
            raise ValueError("Cada área necesita id o bbox")
        return self


class PeriodIn(BaseModel):
    start: dt.date
    end: dt.date

    @model_validator(mode="after")
    def _order(self):
        if self.start > self.end:
            raise ValueError("start posterior a end")
        if self.end > dt.date.today():
            raise ValueError("end en el futuro: no hay observaciones del futuro")
        return self


class ResearchIn(BaseModel):
    question: str | None = Field(None, max_length=1000)
    areas: list[AreaIn] | None = Field(None, max_length=4)
    period: PeriodIn | None = None
    phenomena: list[Phenomenon] | None = None
    products: list[str] | None = None
    profile: Literal["mining_terrain", "flood_hydrology", "landslide_slope", "glacier_climate"] | None = None
    lang: Literal["es", "en"] = "es"
    run: bool = Field(False, description="true: lanza descubrimiento, análisis e historia al crearla.")

    @model_validator(mode="after")
    def _something(self):
        if not self.question and not self.areas and not self.profile:
            raise ValueError("Hace falta una pregunta, un perfil o al menos un área")
        return self


def build_plan(body: ResearchIn) -> dict:
    question = body.question or ""
    if body.profile and not question:
        prof = PROFILES[body.profile]
        case = next(p for p in places.GAZETTEER if p.id == prof["case"])
        question = f"{prof['label']}: {case.name}"
    plan = nlq.parse_question(question)
    if body.profile:
        prof = PROFILES[body.profile]
        plan["phenomena"] = list(dict.fromkeys([*prof["phenomena"], *[p for p in plan["phenomena"] if p != "surface_change"]]))
        if not plan["areas"]:
            plan["areas"] = [next(p for p in places.GAZETTEER if p.id == prof["case"]).to_dict()]
        plan["profiles"] = [body.profile]
        plan["decisions"].append(f"Perfil elegido: {prof['label']}.")
    if body.areas:
        areas = []
        for a in body.areas:
            known = next((p for p in places.GAZETTEER if p.id == a.id), None) if a.id else None
            if known and not a.bbox:
                areas.append(known.to_dict())
            else:
                areas.append({
                    "id": a.id or f"custom_{len(areas) + 1}",
                    "name": a.name or a.id or f"Área {len(areas) + 1}",
                    "bbox": a.bbox or list(known.bbox),
                    "source": "elegida por la persona",
                    "aoi": None,
                    "approximate": False,
                    "note": "",
                })
        plan["areas"] = areas
        plan["unresolved"] = [u for u in plan["unresolved"] if u != "area"]
        plan["decisions"].append("Áreas elegidas a mano: " + ", ".join(a["name"] for a in areas) + ".")
    if body.period:
        plan["period"] = {"start": body.period.start.isoformat(), "end": body.period.end.isoformat()}
        plan["unresolved"] = [u for u in plan["unresolved"] if u != "period"]
        plan["decisions"].append(f"Periodo elegido a mano: {plan['period']['start']} a {plan['period']['end']}.")
    if body.phenomena:
        plan["phenomena"] = list(body.phenomena)
    from .products import products_for

    plan["products"] = [p for p in (body.products or [x.id for x in products_for(plan["phenomena"])]) if p in BY_ID]
    plan["comparative"] = plan["comparative"] or len(plan["areas"]) > 1
    plan["lang"] = body.lang
    return plan


def _providers() -> list:
    todos = sources.default_providers()
    elegidos = os.environ.get("RESEARCH_EVENT_PROVIDERS", "").strip()
    if not elegidos:
        return todos
    ids = {x.strip() for x in elegidos.split(",")}
    return [p for p in todos if p.id in ids]


def default_deps() -> Deps:
    root = os.environ.get("ARTIFACT_ROOT")
    return Deps(
        cmr=discovery.HttpCmr(),
        stac=discovery.HttpEodms(),
        verdicts=analysis.HttpVerdicts(),
        eonet=events.HttpEonet() if os.environ.get("RESEARCH_EONET", "1") == "1" else None,
        registry=events.load_registry(),
        # Proveedores abiertos de acontecimientos; RESEARCH_EVENT_PROVIDERS=usgs,gdacs limita la lista, "none" la vacía.
        providers=_providers(),
        artifact_root=Path(root) if root else None,
        discovery_limit=int(os.environ.get("RESEARCH_DISCOVERY_LIMIT", "100")),
    )


def create_app(store: Store | None = None, deps: Deps | None = None, geocoder: places.Geocoder | None = None) -> FastAPI:
    app = FastAPI(
        title="Dancing with the SAR — investigación",
        version="0.1.0",
        description="De una pregunta a una investigación reproducible y a una historia con evidencia por afirmación. "
        "Ninguna cifra sin evidencia; ninguna causa afirmada por coincidir en fechas.",
    )
    st = store or Store(Path(os.environ.get("RESEARCH_DATA_DIR", "./data/research")) / "research.db")
    runner = Runner(st, deps or default_deps())
    geo = geocoder or places.Geocoder()
    app.state.runner = runner

    def get_or_404(rid: str) -> dict:
        doc = st.get_research(rid)
        if doc is None:
            raise HTTPException(404, "Investigación inexistente")
        return doc

    def story_or_404(sid: str) -> dict:
        s = st.get_story(sid)
        if s is None:
            raise HTTPException(404, "Historia inexistente")
        return s

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/places")
    def search_places(q: str = Query(..., min_length=2, max_length=200)):
        local = [p.to_dict() for p in places.search_gazetteer(q)]
        try:
            remote = geo.search(q)
            geo_status = "ok" if geo.enabled else "disabled"
        except Exception as e:  # noqa: BLE001
            remote, geo_status = [], f"unavailable: {type(e).__name__}"
        return {"query": q, "results": local + remote, "geocoder": geo_status}

    @app.get("/places/reverse")
    def reverse_place(lat: float = Query(..., ge=-90, le=90), lon: float = Query(..., ge=-180, le=180),
                      lang: str = Query("es", pattern="^(es|en)$")):
        """Nombre del lugar en un punto (Nominatim). `place` es null si no hay geocodificador o nada cerca."""
        try:
            place = geo.reverse(lat, lon, lang)
            geo_status = "ok" if geo.enabled else "disabled"
        except Exception as e:  # noqa: BLE001
            place, geo_status = None, f"unavailable: {type(e).__name__}"
        return {"lat": lat, "lon": lon, "place": place, "geocoder": geo_status}

    @app.get("/sources")
    def event_sources():
        """Proveedores de acontecimientos y capas: cuáles están activos y cuáles esperan una credencial."""
        d = runner.deps
        return {
            "events": [
                {"id": "registry", "name": "Registro verificado (config/events)", "enabled": True, "count": len(d.registry)},
                {"id": "eonet", "name": "NASA EONET", "enabled": d.eonet is not None},
                *[p.describe() for p in d.providers],
            ],
            "layers": [{"id": "inegi_wms", "name": "INEGI (México), WMS", "url": sources.INEGI_WMS,
                        "layers": [{"code": k, "title": v[0]} for k, v in sources.INEGI_LAYERS.items()]}],
        }

    @app.get("/profiles")
    def profiles():
        return [{"id": k, **v} for k, v in PROFILES.items()]

    @app.get("/products")
    def products():
        return {
            "products": [p.__dict__ | {"polarizations": list(p.polarizations), "phenomena": list(p.phenomena)} for p in PRODUCTS],
            "by_phenomenon": {k: list(v) for k, v in PHENOMENON_PRODUCTS.items()},
            "checked_on": "2026-11-15",
        }

    @app.post("/research/parse")
    def parse(body: ResearchIn):
        return build_plan(body)

    @app.post("/research", status_code=201)
    def create(body: ResearchIn):
        plan = build_plan(body)
        if not plan["areas"]:
            raise HTTPException(422, {"detail": "No se reconoció ningún lugar. Elige uno en /places o da un bbox.", "plan": plan})
        doc = st.create_research({"plan": plan, "status": "created", "story_ids": []})
        if body.run:
            runner.submit(doc["id"], list(STEPS))
            doc = st.get_research(doc["id"])
        return doc

    @app.get("/research")
    def list_research(limit: int = Query(20, ge=1, le=100)):
        return [
            {"id": d["id"], "question": d["plan"]["question"], "areas": [a["name"] for a in d["plan"]["areas"]], "period": d["plan"]["period"],
             "created_at": d["created_at"], "job": d.get("job"), "story_ids": d.get("story_ids", [])}
            for d in st.list_research(limit)
        ]

    @app.get("/research/{rid}")
    def get(rid: str):
        return get_or_404(rid)

    @app.get("/research/{rid}/status")
    def status(rid: str):
        d = get_or_404(rid)
        return {
            "id": rid,
            "job": d.get("job"),
            "done": {"discover": d.get("discovery") is not None, "analyze": d.get("analysis") is not None, "story": bool(d.get("story_ids"))},
            "story_ids": d.get("story_ids", []),
        }

    def launch(rid: str, steps: list[str]):
        get_or_404(rid)
        return JSONResponse(runner.submit(rid, steps), status_code=202)

    @app.post("/research/{rid}/discover-data", status_code=202)
    def discover(rid: str):
        return launch(rid, ["discover"])

    @app.post("/research/{rid}/analyze", status_code=202)
    def analyze(rid: str):
        return launch(rid, ["analyze"])

    @app.post("/research/{rid}/generate-story", status_code=202)
    def gen_story(rid: str):
        return launch(rid, ["story"])

    @app.post("/research/{rid}/run", status_code=202)
    def run_all(rid: str):
        return launch(rid, list(STEPS))

    @app.post("/research/{rid}/cancel")
    def cancel(rid: str):
        get_or_404(rid)
        return {"cancel_requested": runner.cancel(rid)}

    def section(rid: str, key: str):
        d = get_or_404(rid)
        if d.get(key) is None:
            raise HTTPException(409, f"Falta el paso que produce '{key}': lanza /discover-data o /analyze")
        return d[key]

    @app.get("/research/{rid}/acquisitions")
    def acquisitions(rid: str, product: str | None = None, area: str | None = None):
        out = []
        for d in section(rid, "discovery"):
            if area and d["area"] != area:
                continue
            out.append({"area": d["area"], "products": d["products"], "compatibility": d.get("compatibility", []),
                        "acquisitions": [a for a in d["acquisitions"] if not product or a["product"] == product], "errors": d["errors"]})
        return out

    @app.get("/research/{rid}/timeline")
    def timeline(rid: str):
        return [{"area": a["area"], "series": a["series"], "limitations": a["limitations"]} for a in section(rid, "analysis")]

    @app.get("/research/{rid}/anomalies")
    def anomalies(rid: str):
        return [f for a in section(rid, "analysis") for f in a["findings"]]

    @app.get("/research/{rid}/events")
    def research_events(rid: str):
        d = get_or_404(rid)
        return {"events": section(rid, "events"), "correlations": d.get("correlations", [])}

    @app.get("/research/{rid}/risk")
    def risk(rid: str):
        return section(rid, "risk")

    @app.get("/research/{rid}/insar")
    def insar(rid: str):
        return section(rid, "insar")

    @app.get("/research/{rid}/comparison")
    def comparison(rid: str):
        return section(rid, "comparison")

    @app.get("/stories")
    def stories(research_id: str | None = None):
        return [{"id": s["id"], "research_id": s["research_id"], "title": s["title"], "created_at": s["created_at"], "data_kind": s["data_kind"]}
                for s in st.list_stories(research_id)]

    @app.get("/stories/{sid}")
    def get_story(sid: str):
        return story_or_404(sid)

    @app.get("/stories/{sid}/evidence")
    def story_evidence(sid: str):
        s = story_or_404(sid)
        return {"evidence": s["evidence"], "traceability": s["traceability"]}

    @app.get("/stories/{sid}/export")
    def export(sid: str, format: Literal["md", "json"] = "md"):
        s = story_or_404(sid)
        if format == "json":
            r = get_or_404(s["research_id"])
            return JSONResponse({"story": s, "research": r}, headers={"Content-Disposition": f'attachment; filename="{sid}.json"'})
        return PlainTextResponse(story.to_markdown(s), media_type="text/markdown; charset=utf-8",
                                 headers={"Content-Disposition": f'attachment; filename="{sid}.md"'})

    return app
