from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
import math


@dataclass
class SteadyStateReport:
    warmup_index: int
    times_hr: List[float]
    per_role: Dict[str, Dict[str, float]]  # avg_occupancy, utilization, capacity, suggested_capacity


def _moving_avg(x: List[float], window: int) -> List[float]:
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


def _sliding_slope(x: List[float], y: List[float], window: int) -> List[float]:
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


def detect_warmup_index(times_hr: List[float], series: List[float], *,
                        window: int = 30, slope_rel_eps: float = 0.01, consecutive: int = 3,
                        value_rel_frac: float = 0.85) -> int:
    """Detect a warm-up cutoff using a slope-based stationarity heuristic (Welch-style)."""
    if not times_hr or not series or len(times_hr) != len(series):
        return 0
    w_ma = max(2, min(window, len(series) // 2 or 2))
    ma = _moving_avg(series, window=w_ma)
    # Use a smaller window for slope to respond faster once the series stabilizes
    w_slope = max(5, min(max(5, window // 2), len(ma)))
    slopes = _sliding_slope(times_hr, ma, window=w_slope)
    # Use final level (tail) to scale thresholds and a value proximity criterion
    tail_k = max(5, min(w_slope, len(ma)))
    final_level = max(1e-9, sum(ma[-tail_k:]) / float(tail_k))
    thresh = abs(final_level) * float(slope_rel_eps)
    min_value = final_level * float(value_rel_frac)
    valid_start = w_slope - 1  # only meaningful after we have a full window

    # Candidate 1: value-only criterion (moving average reaches close to final level)
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

    # Candidate 2: slope-only criterion
    ok_slope = 0
    i_slope_idx: Optional[int] = None
    for i in range(valid_start, len(slopes)):
        s = slopes[i]
        if abs(s) <= thresh:
            ok_slope += 1
            if ok_slope >= max(1, consecutive):
                i_slope_idx = max(0, i - consecutive + 1)
                break
        else:
            ok_slope = 0

    # Combine: require both when possible by choosing the later index; fall back sensibly
    if i_value_idx is not None and i_slope_idx is not None:
        return max(i_value_idx, i_slope_idx)
    if i_value_idx is not None:
        return i_value_idx
    if i_slope_idx is not None:
        return i_slope_idx
    return max(0, len(series) // 4)


def is_stationary(times_hr: List[float], series: List[float], *, window: int = 30, slope_rel_eps: float = 0.01) -> bool:
    idx = detect_warmup_index(times_hr, series, window=window, slope_rel_eps=slope_rel_eps)
    tail = series[idx:]
    if not tail:
        return True
    ma_tail = _moving_avg(tail, window=max(2, min(window, max(2, len(tail) // 2))))
    if not ma_tail:
        return True
    tail_times = times_hr[idx:]
    slopes = _sliding_slope(tail_times, ma_tail, window=max(5, min(window, len(ma_tail))))
    level = max(1e-9, sum(ma_tail) / max(1, len(ma_tail)))
    thresh = abs(level) * float(slope_rel_eps)
    return all(abs(s) <= thresh for s in slopes[-max(3, min(10, len(slopes))):])


def steady_state_report_from_result(result: Any, *, window: int = 30, slope_rel_eps: float = 0.01,
                                    target_util: Optional[float] = 0.85) -> SteadyStateReport:
    """Compute a steady-state diagnostics report using resource occupancy series."""
    run = result.per_simulation[0] if getattr(result, 'per_simulation', None) else result
    times = getattr(run, 'times_hr', None) or []
    res_series = getattr(run, 'resource_timeseries', {}) or {}
    if not times or not res_series:
        return SteadyStateReport(warmup_index=0, times_hr=[], per_role={})

    total_occ = [0.0] * len(times)
    for role, s in res_series.items():
        occ = s.get('occupancy') or [0] * len(times)
        for i, v in enumerate(occ):
            total_occ[i] += float(v)

    idx = detect_warmup_index(times, total_occ, window=window, slope_rel_eps=slope_rel_eps)

    per_role: Dict[str, Dict[str, float]] = {}
    # Try to get capacities from result.resource_metrics if available
    res_metrics = getattr(run, 'resource_metrics', {}) or {}
    for role, s in res_series.items():
        occ_raw = s.get('occupancy') or [0.0] * len(times)
        occ = [float(v) for v in occ_raw]
        # Compute a role-specific warm-up index as well; start from the later of the two
        role_idx = detect_warmup_index(times, occ, window=window, slope_rel_eps=slope_rel_eps)
        start_i = max(0, min(len(occ), max(idx, role_idx)))
        tail = occ[start_i:] if start_i < len(occ) else []
        avg_occ = float(sum(tail)) / max(1, len(tail)) if tail else 0.0
        capacity = float(s.get('capacity')) if 'capacity' in s else float('nan')
        if math.isnan(capacity):
            try:
                capacity = float(res_metrics.get(role, {}).get('capacity', float('nan')))
            except Exception:
                capacity = float('nan')
        util = (avg_occ / capacity) if capacity and not math.isnan(capacity) and capacity > 0 else float('nan')
        suggested = math.ceil(avg_occ / float(target_util)) if (target_util and target_util > 0) else float('nan')
        per_role[role] = {
            'avg_occupancy': avg_occ,
            'capacity': capacity,
            'utilization': util,
            'suggested_capacity': float(suggested) if suggested == suggested else suggested,
        }

    return SteadyStateReport(warmup_index=idx, times_hr=times, per_role=per_role)
