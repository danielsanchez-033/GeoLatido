"""Análisis temporal reproducible, en Python puro (sin dependencias).

Métodos: pendiente de Theil-Sen, media móvil, anomalías por desviación robusta (MAD), un punto de cambio por
desplazamiento de la media y huecos de observación. Ningún hueco se interpreta como estabilidad: se lista aparte.
"""
from __future__ import annotations

import datetime as dt
import statistics

MAD_SCALE = 1.4826
ANOMALY_Z = 3.5
MIN_POINTS_TREND = 4
MIN_SEGMENT = 3


def median(xs: list[float]) -> float:
    return statistics.median(xs)


def mad(xs: list[float]) -> float:
    m = median(xs)
    return MAD_SCALE * median([abs(x - m) for x in xs])


def theil_sen(points: list[tuple[dt.date, float]]) -> float | None:
    """Pendiente mediana entre todos los pares de puntos, en unidades por 30 días."""
    if len(points) < MIN_POINTS_TREND:
        return None
    slopes = []
    for i in range(len(points)):
        for j in range(i + 1, len(points)):
            dd = (points[j][0] - points[i][0]).days
            if dd:
                slopes.append((points[j][1] - points[i][1]) / dd * 30)
    return median(slopes) if slopes else None


def moving_average(values: list[float], window: int = 3) -> list[float | None]:
    out: list[float | None] = []
    for i in range(len(values)):
        if i + 1 < window:
            out.append(None)
        else:
            out.append(sum(values[i + 1 - window : i + 1]) / window)
    return out


def robust_anomalies(points: list[tuple[dt.date, float]], z: float = ANOMALY_Z) -> list[dict]:
    if len(points) < 5:
        return []
    vals = [v for _, v in points]
    m, s = median(vals), mad(vals)
    if s == 0:
        return []
    return [
        {"date": d.isoformat(), "value": v, "robust_z": round((v - m) / s, 2)}
        for d, v in points
        if abs(v - m) / s >= z
    ]


def change_point(points: list[tuple[dt.date, float]]) -> dict | None:
    """Mejor partición en dos tramos por reducción de la suma de cuadrados. Se informa solo si la diferencia de medias
    supera dos veces la dispersión robusta de los residuos; es un candidato, no una prueba."""
    n = len(points)
    if n < 2 * MIN_SEGMENT:
        return None
    vals = [v for _, v in points]

    def sse(xs):
        mu = sum(xs) / len(xs)
        return sum((x - mu) ** 2 for x in xs)

    best = None
    total = sse(vals)
    for k in range(MIN_SEGMENT, n - MIN_SEGMENT + 1):
        a, b = vals[:k], vals[k:]
        gain = total - sse(a) - sse(b)
        if best is None or gain > best[0]:
            best = (gain, k)
    if best is None:
        return None
    k = best[1]
    a, b = vals[:k], vals[k:]
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    resid = [x - ma for x in a] + [x - mb for x in b]
    spread = mad(resid) or 1e-12
    if abs(mb - ma) < 2 * spread:
        return None
    return {
        "date": points[k][0].isoformat(),
        "mean_before": round(ma, 6),
        "mean_after": round(mb, 6),
        "shift": round(mb - ma, 6),
        "residual_spread": round(spread, 6),
        "status": "candidate",
    }


def gaps(dates: list[dt.date], declared: list[tuple[dt.date, dt.date]] = ()) -> list[dict]:
    if len(dates) < 2:
        return []
    deltas = [(b - a).days for a, b in zip(dates, dates[1:])]
    med = statistics.median(deltas)
    out = []
    for a, b, d in zip(dates, dates[1:], deltas):
        crosses = any(s < b and e > a for s, e in declared)
        if d > 1.5 * med or crosses:
            out.append({"from": a.isoformat(), "to": b.isoformat(), "days": d, "declared_gap": crosses})
    return out


def classify(slope: float | None, cp: dict | None, n_anom: int, span_days: int) -> str:
    """Etiqueta descriptiva de la serie, con la evidencia que la sostiene."""
    if slope is None:
        return "insufficient_points"
    if cp:
        return "abrupt_shift_candidate"
    if n_anom:
        return "isolated_anomalies"
    return "no_trend_detected" if abs(slope) < 1e-9 else "gradual_trend_candidate"


def analyze_series(points: list[tuple[dt.date, float]], declared_gaps: list[tuple[dt.date, dt.date]] = ()) -> dict:
    points = sorted(points)
    dates = [d for d, _ in points]
    vals = [v for _, v in points]
    span = (dates[-1] - dates[0]).days if len(dates) > 1 else 0
    slope = theil_sen(points)
    anomalies = robust_anomalies(points)
    cp = change_point(points)
    return {
        "n": len(points),
        "span_days": span,
        "median": round(median(vals), 6) if vals else None,
        "robust_spread": round(mad(vals), 6) if len(vals) > 1 else None,
        "theil_sen_per_30d": round(slope, 6) if slope is not None else None,
        "moving_average_3": [None if v is None else round(v, 6) for v in moving_average(vals)],
        "anomalies": anomalies,
        "change_point": cp,
        "gaps": gaps(dates, declared_gaps),
        "seasonality": "insufficient_span" if span < 730 else "not_computed",
        "interannual": "insufficient_span" if span < 730 else "not_computed",
        "label": classify(slope, cp, len(anomalies), span),
        "methods": {
            "trend": "Theil-Sen (mediana de pendientes por pares), por 30 días",
            "anomaly": f"|x − mediana| / (1,4826·MAD) ≥ {ANOMALY_Z}",
            "change_point": f"una partición por mínima suma de cuadrados, tramos ≥ {MIN_SEGMENT}, |Δmedia| ≥ 2·MAD de residuos",
            "gaps": "intervalo > 1,5 × mediana o cruce de un hueco declarado por ASF",
        },
    }
