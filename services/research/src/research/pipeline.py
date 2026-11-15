"""Orquestación de una investigación en pasos asíncronos y cancelables.

Pasos: discover (CMR), analyze (verdicts, temporal, acontecimientos, InSAR, susceptibilidad, comparación) y story.
Cada paso guarda su resultado en el documento de la investigación; se puede repetir uno sin repetir los anteriores.
Como mucho RESEARCH_MAX_JOBS investigaciones a la vez; las demás esperan en cola.
"""
from __future__ import annotations

import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from . import analysis as an
from . import assess, discovery, events, story
from .products import BY_ID
from .store import Store, now

STEPS = ("discover", "analyze", "story")


class Cancelled(Exception):
    pass


@dataclass
class Deps:
    cmr: discovery.CmrSource
    verdicts: an.VerdictsSource
    eonet: events.EonetSource | None
    registry: list[dict] = field(default_factory=list)
    providers: list = field(default_factory=list)
    stac: discovery.StacSource | None = None
    artifact_root: Path | None = None
    discovery_limit: int = 100


class Runner:
    def __init__(self, store: Store, deps: Deps, workers: int | None = None):
        self.store = store
        self.deps = deps
        self.pool = ThreadPoolExecutor(max_workers=workers or int(os.environ.get("RESEARCH_MAX_JOBS", "2")))
        self._cancel: dict[str, threading.Event] = {}
        self._lock = threading.Lock()

    # --- trabajos -------------------------------------------------------------------------------------------------
    def submit(self, rid: str, steps: list[str], wait: bool = False) -> dict:
        doc = self.store.get_research(rid)
        if doc is None:
            raise KeyError(rid)
        with self._lock:
            job = doc.get("job") or {}
            if job.get("state") in ("queued", "running"):
                return job
            job = {"id": "J-" + uuid.uuid4().hex[:8], "steps": steps, "state": "queued", "step": None, "queued_at": now(), "error": None, "log": []}
            doc["job"] = job
            self.store.save_research(doc)
            self._cancel[rid] = threading.Event()
        fut = self.pool.submit(self._run, rid, steps)
        if wait:
            fut.result()
            return self.store.get_research(rid)["job"]
        return job

    def cancel(self, rid: str) -> bool:
        ev = self._cancel.get(rid)
        if ev is None:
            return False
        ev.set()
        return True

    def _check(self, rid: str):
        ev = self._cancel.get(rid)
        if ev is not None and ev.is_set():
            raise Cancelled()

    def _set(self, rid: str, **kw) -> dict:
        doc = self.store.get_research(rid)
        doc["job"].update(kw)
        return self.store.save_research(doc)

    def _run(self, rid: str, steps: list[str]):
        self._set(rid, state="running", started_at=now())
        try:
            for step in STEPS:
                if step not in steps:
                    continue
                self._check(rid)
                self._set(rid, step=step)
                getattr(self, f"step_{step}")(rid)
            self._set(rid, state="done", step=None, finished_at=now())
        except Cancelled:
            self._set(rid, state="cancelled", finished_at=now())
        except Exception as e:  # noqa: BLE001 - el estado del trabajo lleva el error
            self._set(rid, state="failed", error=f"{type(e).__name__}: {e}"[:500], finished_at=now())
        finally:
            self._cancel.pop(rid, None)

    # --- pasos -------------------------------------------------------------------------------------------------------
    def step_discover(self, rid: str):
        doc = self.store.get_research(rid)
        plan = doc["plan"]
        prods = [BY_ID[p] for p in plan["products"] if p in BY_ID]
        out = []
        for area in plan["areas"]:
            self._check(rid)
            d = discovery.discover(self.deps.cmr, prods, area, plan["period"]["start"], plan["period"]["end"], self.deps.discovery_limit, self.deps.stac)
            d["compatibility"] = discovery.compatibility(d["acquisitions"])
            d["queried_at"] = now()
            out.append(d)
        doc = self.store.get_research(rid)
        doc["discovery"] = out
        self.store.save_research(doc)

    def step_analyze(self, rid: str):
        doc = self.store.get_research(rid)
        plan = doc["plan"]
        if doc.get("discovery") is None:
            self.step_discover(rid)
            doc = self.store.get_research(rid)
        start, end = plan["period"]["start"], plan["period"]["end"]
        lang = plan.get("lang", "es")
        analyses, evsets, corr, ins, risk = [], [], [], [], []
        for area in plan["areas"]:
            self._check(rid)
            a = an.analyze_area(self.deps.verdicts, area, start, end, lang, self.deps.artifact_root)
            analyses.append(a)
            evs = events.gather(area, start, end, self.deps.registry, self.deps.eonet, self.deps.providers)
            for e in evs["events"]:
                if e.get("origin") == "registry" and e.get("verdicts_event_type"):
                    aoi = next((p["aoi"] for p in a["processed"]), None)
                    if aoi:
                        params = {"event_type": e["verdicts_event_type"], "lang": lang}
                        if e.get("time_utc"):
                            params["time"] = e["time_utc"]
                        try:
                            e["observability"] = self.deps.verdicts.event(aoi, e["date"], params)
                        except Exception as ex:  # noqa: BLE001
                            evs["errors"].append({"source": "verdicts/events", "error": type(ex).__name__})
            evsets.append(evs)
            corr += events.correlate(evs["events"], a["findings"], a["series"])
            ins.append(assess.insar(area, doc["discovery"]))
            relief = any(p.get("relief") for p in a["processed"])
            risk.append(assess.susceptibility(area, plan["phenomena"], doc["discovery"], a, relief))
        doc = self.store.get_research(rid)
        doc.update(
            analysis=analyses,
            events=evsets,
            correlations=_dedupe_corr(corr),
            insar=ins,
            risk=risk,
            comparison=assess.compare(plan["areas"], doc["discovery"], analyses, plan["phenomena"]),
            analyzed_at=now(),
        )
        self.store.save_research(doc)

    def step_story(self, rid: str):
        doc = self.store.get_research(rid)
        if doc.get("analysis") is None:
            self.step_analyze(rid)
            doc = self.store.get_research(rid)
        s = self.store.create_story(story.generate(doc))
        doc = self.store.get_research(rid)
        doc["story_ids"] = [s["id"], *doc.get("story_ids", [])]
        self.store.save_research(doc)


def _dedupe_corr(items: list[dict]) -> list[dict]:
    seen: dict[str, dict] = {}
    for c in items:
        if c["event_id"] in seen:
            known = {(link["series"], link["pair_id"]) for link in seen[c["event_id"]]["links"]}
            seen[c["event_id"]]["links"] += [link for link in c["links"] if (link["series"], link["pair_id"]) not in known]
        else:
            seen[c["event_id"]] = c
    return list(seen.values())
