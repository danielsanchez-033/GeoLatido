"""Plan de observación de NISAR que deja `ingest plan` en data/plan/<zona>.json.

catalog no lee NASA ni el token: solo une ese archivo con la siguiente pasada estimada por el ciclo.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

SCHEMA = "observation-plan/1"
# Diferencia máxima entre la hora estimada por catalog y la del archivo para considerarlas la misma pasada.
MATCH_TOLERANCE = timedelta(seconds=60)


@dataclass(frozen=True)
class PlanStatus:
    status: str
    plan: str | None = None
    config_id: str | None = None
    same_config: bool | None = None
    checked_at: datetime | None = None


UNKNOWN = PlanStatus(status="unknown")


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def load_plan(plan_dir: Path, aoi_id: str) -> dict | None:
    """El archivo de la zona, o None si no existe o no se puede leer: entonces todo queda unknown."""
    path = plan_dir / f"{aoi_id}.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) and data.get("schema") == SCHEMA else None


def status_for(plan: dict | None, series_id: str, expected_at: datetime) -> PlanStatus:
    """Estado del plan para la pasada de `series_id` que catalog estima en `expected_at`."""
    if plan is None:
        return UNKNOWN
    try:
        checked_at = _parse_time(plan["checked_at"])
        for series in plan["series"]:
            if series["catalog_series"] != series_id:
                continue
            for item in series["passes"]:
                if abs(_parse_time(item["expected_at"]) - expected_at) < MATCH_TOLERANCE:
                    return PlanStatus(
                        status=item["status"],
                        plan=item.get("plan"),
                        config_id=item.get("config_id"),
                        same_config=item.get("same_config"),
                        checked_at=checked_at,
                    )
    except (KeyError, TypeError, ValueError):
        return UNKNOWN
    return UNKNOWN
