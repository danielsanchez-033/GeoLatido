"""Plan de observación de NISAR (NISAR_COP) para las próximas pasadas de una zona.

El XML diario no trae pista ni marco: la hora de la pasada sale del ciclo de 12 días y el plan
dice si a esa hora hay una observación L-SAR. Un plan no garantiza la adquisición.
"""
from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Protocol
from urllib.parse import quote, urlencode

import aiohttp

from .fetch import FetchError, select_series

SCHEMA = "observation-plan/1"
COLLECTION = "NISAR_COP"
CMR_GRANULES = "https://cmr.earthdata.nasa.gov/search/granules.json"
CYCLE = timedelta(days=12)
# La pasada sobre el marco dura unos 35 s y su hora varió menos de 3 s entre junio y octubre de 2026.
BEFORE, AFTER = timedelta(seconds=10), timedelta(seconds=40)
RADAR_TYPES = {"lsar", "joint"}


@dataclass(frozen=True)
class Observation:
    kind: str
    start: datetime
    end: datetime
    config_id: str | None


@dataclass(frozen=True)
class PlanFile:
    title: str
    url: str


class PlanSource(Protocol):
    def plans(self, start: datetime, end: datetime) -> list[PlanFile]: ...

    def observations(self, plan: PlanFile) -> list[Observation]: ...


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _plan_time(text: str) -> datetime:
    """`2026-326T00:18:56.000000` (año y día del año, UTC)."""
    return datetime.strptime(text.strip(), "%Y-%jT%H:%M:%S.%f").replace(tzinfo=timezone.utc)


def parse_plan(xml: bytes) -> list[Observation]:
    root = ET.fromstring(xml)
    return [
        Observation(
            kind=(item.findtext("TYPE") or "").strip(),
            start=_plan_time(item.findtext("REF_START_DATETIME") or ""),
            end=_plan_time(item.findtext("REF_END_DATETIME") or ""),
            config_id=(item.findtext("LSAR_CONFIG_ID") or "").strip() or None,
        )
        for item in root.iter("OBS")
    ]


def latest_versions(entries: list[dict]) -> list[PlanFile]:
    """De cada día, la versión mayor (`..._v02` sobre `..._v01`), con su XML público de NISAR/DCOP."""
    best: dict[str, tuple[int, PlanFile]] = {}
    for entry in entries:
        title = entry.get("title", "")
        base, _, version = title.rpartition("_v")
        if not title.startswith("dcop_") or not version.isdigit():
            continue
        url = next(
            (
                link["href"]
                for link in entry.get("links", [])
                if link.get("href", "").startswith("https://") and "/NISAR/DCOP/" in link["href"]
                and link["href"].endswith(".xml")
            ),
            None,
        )
        if url and (base not in best or int(version) > best[base][0]):
            best[base] = (int(version), PlanFile(title, url))
    return [item for _, item in sorted(best.values(), key=lambda pair: pair[1].title)]


def classify(observations: list[Observation], expected: datetime, has_plan: bool) -> tuple[str, Observation | None]:
    start, end = expected - BEFORE, expected + AFTER
    radar = [item for item in observations if item.kind in RADAR_TYPES]
    for item in radar:
        if item.start <= start and item.end >= end:
            return "planned", item
    touching = [item for item in radar if item.start < end and item.end > start]
    if touching:
        return "partial", touching[0]
    return ("not_planned" if has_plan else "no_plan"), None


def predicted_passes(last: datetime, now: datetime, days: int) -> list[datetime]:
    horizon = now + timedelta(days=days)
    passes, current = [], last + CYCLE
    while current <= horizon:
        passes.append(current)
        current += CYCLE
    return passes


def _check(source: PlanSource, expected: datetime, cache: dict[str, list[Observation]]) -> tuple[str, PlanFile | None, Observation | None]:
    files = source.plans(expected - BEFORE, expected + AFTER)
    observations: list[Observation] = []
    for item in files:
        if item.title not in cache:
            cache[item.title] = source.observations(item)
        observations += cache[item.title]
    status, observation = classify(observations, expected, bool(files))
    used = next((f for f in files if observation and observation in cache[f.title]), files[0] if files else None)
    return status, used, observation


def build_plan(
    aoi: dict,
    catalog_url: str,
    json_getter: Callable[[str], Any],
    source: PlanSource,
    now: datetime,
    days: int = 30,
) -> dict:
    base = f"{catalog_url.rstrip('/')}/aois/{quote(aoi['id'], safe='')}"
    available = json_getter(f"{base}/series")
    passes = json_getter(f"{base}/timeline")["passes"]
    cache: dict[str, list[Observation]] = {}
    out_series = []
    for wanted in aoi["series"]:
        chosen = select_series(available, wanted)
        times = [
            datetime.fromisoformat(item["acquired_at"].replace("Z", "+00:00"))
            for item in passes
            if item["series"] == chosen["id"]
        ]
        if not times:
            raise FetchError(f"catalog no tiene pasadas de {chosen['id']} en la línea de tiempo")
        last = max(times)
        _, reference_plan, reference = _check(source, last, cache)
        reference_config = reference.config_id if reference else None
        items = []
        for expected in predicted_passes(last, now, days):
            status, used, observation = _check(source, expected, cache)
            config = observation.config_id if observation else None
            items.append(
                {
                    "expected_at": _iso(expected),
                    "status": status,
                    "plan": used.title if used else None,
                    "config_id": config,
                    "same_config": None if config is None or reference_config is None else config == reference_config,
                    "observation": {"start": _iso(observation.start), "end": _iso(observation.end)} if observation else None,
                }
            )
        out_series.append(
            {
                "series": wanted["id"],
                "catalog_series": chosen["id"],
                "last_acquired_at": _iso(last),
                "reference_plan": reference_plan.title if reference_plan else None,
                "reference_config_id": reference_config,
                "passes": items,
            }
        )
    return {
        "schema": SCHEMA,
        "aoi": aoi["id"],
        "source": "NASA CMR (ASF)",
        "collection": COLLECTION,
        "checked_at": _iso(now.replace(microsecond=0)),
        "window_seconds": [-int(BEFORE.total_seconds()), int(AFTER.total_seconds())],
        "series": out_series,
    }


def write_plan(data_dir: Path, body: dict) -> Path:
    target = data_dir / "plan" / f"{body['aoi']}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.name + ".part")
    partial.write_text(json.dumps(body, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    partial.replace(target)
    return target


class CmrPlanSource:
    """Busca los planes en CMR (público) y lee el XML con el token, solo de *.earthdatacloud.nasa.gov."""

    def __init__(
        self,
        token: str,
        json_getter: Callable[[str], Any],
        opener: Callable[[str, str, int], Any],
        is_allowed: Callable[[str], bool],
    ):
        self._token, self._get, self._open, self._allowed = token, json_getter, opener, is_allowed

    def plans(self, start: datetime, end: datetime) -> list[PlanFile]:
        query = urlencode({"short_name": COLLECTION, "temporal": f"{_iso(start)},{_iso(end)}", "page_size": 50})
        return latest_versions(self._get(f"{CMR_GRANULES}?{query}")["feed"]["entry"])

    def observations(self, plan: PlanFile) -> list[Observation]:
        if not self._allowed(plan.url):
            raise FetchError(f"{plan.title}: enlace rechazado, no se envía el token fuera de NASA")
        try:
            with self._open(plan.url, self._token, 4 * 1024 * 1024) as remote:
                return parse_plan(remote.read())
        except ET.ParseError as exc:
            raise FetchError(f"{plan.title}: el XML del plan no se pudo leer") from exc
        except (OSError, aiohttp.ClientError) as exc:
            raise FetchError(f"No se pudo leer {plan.title} ({type(exc).__name__}). Revisa el token de Earthdata.") from exc
