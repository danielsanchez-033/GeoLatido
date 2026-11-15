"""Elige la escena Sentinel-2 más cercana antes y después de un par de radar (T-BAL-04)."""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Literal

from .catalog import OpticalAcquisition

# Valores iniciales sin calibrar; se devuelven en cada veredicto para que se puedan auditar.
MAX_CLOUD_COVER = 30.0
SEARCH_DAYS = 10

Side = Literal["before", "after"]
Status = Literal["clear", "cloudy", "partial_coverage", "none_in_window", "catalog_unavailable"]


@dataclass(frozen=True)
class Pick:
    status: Status
    acquisition: OpticalAcquisition | None = None
    days_from_radar: int | None = None


def _on_side(acq: OpticalAcquisition, side: Side, radar_date: dt.date, radar_time: dt.datetime | None) -> bool:
    # Con la hora de la pasada se compara al segundo; sin ella, el mismo día UTC cuenta en los dos lados.
    if radar_time is not None:
        return acq.acquired_at <= radar_time if side == "before" else acq.acquired_at >= radar_time
    day = acq.acquired_at.date()
    return day <= radar_date if side == "before" else day >= radar_date


def pick(
    acquisitions: tuple[OpticalAcquisition, ...] | list[OpticalAcquisition],
    side: Side,
    radar_date: dt.date,
    radar_time: dt.datetime | None = None,
) -> Pick:
    """Antes: la más cercana a la primera fecha sin pasarla. Después: la más cercana a la segunda sin adelantarla.

    Si ninguna cubre la zona con nubosidad ≤ MAX_CLOUD_COVER, se devuelve la mejor disponible con su
    estado; el dato no se oculta (riesgo del plan de Balanza).
    """
    candidates = [
        (acq, (acq.acquired_at.date() - radar_date).days)
        for acq in acquisitions
        if _on_side(acq, side, radar_date, radar_time) and abs((acq.acquired_at.date() - radar_date).days) <= SEARCH_DAYS
    ]
    if not candidates:
        return Pick("none_in_window")
    closest = lambda item: (abs(item[1]), item[0].max_cloud_cover)  # noqa: E731
    least_cloudy = lambda item: (item[0].max_cloud_cover, abs(item[1]))  # noqa: E731
    clear = [item for item in candidates if item[0].covers_aoi and item[0].max_cloud_cover <= MAX_CLOUD_COVER]
    if clear:
        acq, days = min(clear, key=closest)
        return Pick("clear", acq, days)
    covering = [item for item in candidates if item[0].covers_aoi]
    if covering:
        acq, days = min(covering, key=least_cloudy)
        return Pick("cloudy", acq, days)
    acq, days = min(candidates, key=least_cloudy)
    return Pick("partial_coverage", acq, days)
