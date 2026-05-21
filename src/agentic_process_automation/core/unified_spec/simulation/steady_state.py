"""
Steady-state diagnostics, ported from `core/sim/steady_state.py:14-158`.

Moving-average, sliding-slope regression, and Welch-style warm-up detection
are pure functions. They work on any (times, series) pair so the simulator
can feed them either resource-occupancy traces or visit-count traces from
the Markov layer.

The legacy `steady_state_report_from_result` reached into a SimPy result
object; here we accept the occupancy series directly so the unified spec
isn't coupled to the SimPy harness.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class SteadyStateReport:
    warmup_index: int
    times_hr: List[float]
    per_role: Dict[str, Dict[str, float]]


def moving_avg(x: List[float], window: int) -> List[float]:
    if not x:
        return []
    window = max(1, min(window, len(x)))
    if window == 1:
        return list(x)
    out: List[float] = []
    s = sum(x[:window])
    out.extend([s / window] * (window - 1))
    for i in range(window, len(x) + 1):
        out.append(s / window)
        if i < len(x):
            s += x[i] - x[i - window]
    return out


def sliding_slope(x: List[float], y: List[float], window: int) -> List[float]:
    n = len(y)
    window = max(2, min(window, n))
    slopes = [0.0] * n
    if window < 2:
        return slopes
    for i in range(window - 1, n):
        xs = x[i - window + 1 : i + 1]
        ys = y[i - window + 1 : i + 1]
        x_mean = sum(xs) / window
        y_mean = sum(ys) / window
        num = sum((xs[j] - x_mean) * (ys[j] - y_mean) for j in range(window))
        den = sum((xs[j] - x_mean) ** 2 for j in range(window)) or 1e-12
        slopes[i] = num / den
    return slopes


def detect_warmup_index(
    times_hr: List[float],
    series: List[float],
    *,
    window: int = 30,
    slope_rel_eps: float = 0.01,
    consecutive: int = 3,
    value_rel_frac: float = 0.85,
) -> int:
    """Welch-style warm-up cutoff combining a value-proximity test with a slope test."""
    if not times_hr or not series or len(times_hr) != len(series):
        return 0
    w_ma = max(2, min(window, len(series) // 2 or 2))
    ma = moving_avg(series, window=w_ma)
    w_slope = max(5, min(max(5, window // 2), len(ma)))
    slopes = sliding_slope(times_hr, ma, window=w_slope)
    tail_k = max(5, min(w_slope, len(ma)))
    final_level = max(1e-9, sum(ma[-tail_k:]) / float(tail_k))
    thresh = abs(final_level) * float(slope_rel_eps)
    min_value = final_level * float(value_rel_frac)
    valid_start = w_slope - 1

    ok_value = 0
    i_value_idx: Optional[int] = None
    for i in range(valid_start, len(ma)):
        if ma[i] >= min_value:
            ok_value += 1
            if ok_value >= max(1, consecutive):
                i_value_idx = max(0, i - consecutive + 1)
                break
        else:
            ok_value = 0

    ok_slope = 0
    i_slope_idx: Optional[int] = None
    for i in range(valid_start, len(slopes)):
        if abs(slopes[i]) <= thresh:
            ok_slope += 1
            if ok_slope >= max(1, consecutive):
                i_slope_idx = max(0, i - consecutive + 1)
                break
        else:
            ok_slope = 0

    if i_value_idx is not None and i_slope_idx is not None:
        return max(i_value_idx, i_slope_idx)
    if i_value_idx is not None:
        return i_value_idx
    if i_slope_idx is not None:
        return i_slope_idx
    return max(0, len(series) // 4)


def is_stationary(
    times_hr: List[float],
    series: List[float],
    *,
    window: int = 30,
    slope_rel_eps: float = 0.01,
) -> bool:
    idx = detect_warmup_index(
        times_hr, series, window=window, slope_rel_eps=slope_rel_eps
    )
    tail = series[idx:]
    if not tail:
        return True
    ma_tail = moving_avg(tail, window=max(2, min(window, max(2, len(tail) // 2))))
    if not ma_tail:
        return True
    tail_times = times_hr[idx:]
    slopes = sliding_slope(
        tail_times, ma_tail, window=max(5, min(window, len(ma_tail)))
    )
    level = max(1e-9, sum(ma_tail) / max(1, len(ma_tail)))
    thresh = abs(level) * float(slope_rel_eps)
    return all(abs(s) <= thresh for s in slopes[-max(3, min(10, len(slopes))) :])


def steady_state_report(
    times_hr: List[float],
    occupancy_by_role: Dict[str, List[float]],
    *,
    capacity_by_role: Optional[Dict[str, float]] = None,
    window: int = 30,
    slope_rel_eps: float = 0.01,
    target_util: Optional[float] = 0.85,
) -> SteadyStateReport:
    """Build a per-role steady-state report from an occupancy time-series.

    Decoupled from the legacy SimPy result object — pass the occupancy series
    directly. `capacity_by_role` is optional; missing capacities surface as
    NaN utilisation / suggested-capacity values.
    """
    if not times_hr or not occupancy_by_role:
        return SteadyStateReport(warmup_index=0, times_hr=[], per_role={})

    total_occ = [0.0] * len(times_hr)
    for series in occupancy_by_role.values():
        for i, v in enumerate(series):
            total_occ[i] += float(v)

    idx = detect_warmup_index(
        times_hr, total_occ, window=window, slope_rel_eps=slope_rel_eps
    )

    capacities = capacity_by_role or {}
    per_role: Dict[str, Dict[str, float]] = {}
    for role, series in occupancy_by_role.items():
        occ = [float(v) for v in series]
        role_idx = detect_warmup_index(
            times_hr, occ, window=window, slope_rel_eps=slope_rel_eps
        )
        start_i = max(0, min(len(occ), max(idx, role_idx)))
        tail = occ[start_i:] if start_i < len(occ) else []
        avg_occ = sum(tail) / max(1, len(tail)) if tail else 0.0
        capacity = capacities.get(role, float("nan"))
        util = (
            avg_occ / capacity
            if capacity and not math.isnan(capacity) and capacity > 0
            else float("nan")
        )
        suggested = (
            math.ceil(avg_occ / float(target_util))
            if (target_util and target_util > 0)
            else float("nan")
        )
        per_role[role] = {
            "avg_occupancy": avg_occ,
            "capacity": capacity,
            "utilization": util,
            "suggested_capacity": float(suggested) if suggested == suggested else suggested,
        }

    return SteadyStateReport(warmup_index=idx, times_hr=times_hr, per_role=per_role)
