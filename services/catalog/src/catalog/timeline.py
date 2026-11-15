"""Línea de tiempo de una zona: cuándo se adquirió cada pasada, cuándo se publicó y qué huecos hay."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from .pairing import DATA_GAP, Series, crosses_gap

# Ciclo de repetición de NISAR. La siguiente pasada se estima con él y se marca como estimación.
CYCLE_DAYS = 12


@dataclass(frozen=True)
class Pass:
    series: str
    granule_id: str
    acquired_at: datetime
    published_at: datetime | None
    latency_hours: float | None
    contains_aoi: bool


@dataclass(frozen=True)
class Interval:
    series: str
    start: datetime
    end: datetime
    days: int
    crosses_gap: bool


@dataclass(frozen=True)
class Gap:
    start: date
    end: date
    source: str


@dataclass(frozen=True)
class NextPass:
    series: str
    expected_at: datetime
    basis: str


@dataclass(frozen=True)
class Timeline:
    passes: list[Pass]
    intervals: list[Interval]
    gaps: list[Gap]
    next_pass_estimates: list[NextPass]


def _latency_hours(acquired: datetime, published: datetime | None) -> float | None:
    if published is None:
        return None
    return round((published - acquired).total_seconds() / 3600, 1)


def _next_pass(last: datetime, now: datetime) -> datetime:
    cycle = timedelta(days=CYCLE_DAYS)
    # Primera repetición del ciclo estrictamente posterior a `now`.
    return last + cycle * (max(0, (now - last) // cycle) + 1)


def build_timeline(series: list[Series], window_start: date, window_end: date, now: datetime) -> Timeline:
    passes: list[Pass] = []
    intervals: list[Interval] = []
    estimates: list[NextPass] = []
    for item in series:
        for granule in item.granules:
            passes.append(
                Pass(
                    series=item.id,
                    granule_id=granule.id,
                    acquired_at=granule.acquired_at,
                    published_at=granule.published_at,
                    latency_hours=_latency_hours(granule.acquired_at, granule.published_at),
                    contains_aoi=item.contains_aoi,
                )
            )
        for first, second in zip(item.granules, item.granules[1:]):
            intervals.append(
                Interval(
                    series=item.id,
                    start=first.acquired_at,
                    end=second.acquired_at,
                    days=(second.start - first.start).days,
                    crosses_gap=crosses_gap(first.start, second.start),
                )
            )
        estimates.append(
            NextPass(series=item.id, expected_at=_next_pass(item.granules[-1].acquired_at, now), basis="12-day cycle")
        )

    gap_start, gap_end = DATA_GAP
    gaps = [Gap(gap_start, gap_end, "ASF")] if gap_start <= window_end and gap_end >= window_start else []
    return Timeline(
        passes=sorted(passes, key=lambda p: p.acquired_at),
        intervals=intervals,
        gaps=gaps,
        next_pass_estimates=estimates,
    )
