from __future__ import annotations
import math
from typing import Dict, Any, List

import pytest

from sim_dsl.steady_state import (
    detect_warmup_index,
    is_stationary,
    steady_state_report_from_result,
)


class DummyRun:
    def __init__(self, times_hr: List[float], resource_timeseries: Dict[str, Dict[str, Any]], resource_metrics: Dict[str, Dict[str, Any]]):
        self.times_hr = times_hr
        self.resource_timeseries = resource_timeseries
        self.resource_metrics = resource_metrics


class DummyResult:
    def __init__(self, run: DummyRun):
        self.per_simulation = [run]


def test_detect_warmup_index_plateau():
    # Create a series that ramps up to 10 over ~30 steps, then stays flat
    times = [i * 0.1 for i in range(100)]  # hours
    series = [min(10.0, i * (10.0 / 30.0)) for i in range(100)]
    idx = detect_warmup_index(times, series, window=20, slope_rel_eps=0.01, consecutive=3)
    # Expect warm-up index roughly around the end of the ramp (within a tolerance)
    assert 15 <= idx <= 40


def test_is_stationary_true_on_flat_tail():
    times = [i * 0.1 for i in range(100)]
    series = [5.0 for _ in times]
    assert is_stationary(times, series, window=10, slope_rel_eps=0.001)


def test_is_stationary_false_on_strong_trend():
    times = [i * 0.1 for i in range(100)]
    series = [0.05 * i for i in range(100)]  # strong upward trend
    assert not is_stationary(times, series, window=10, slope_rel_eps=0.001)


def test_steady_state_report_basic_metrics():
    # Two roles, RoleA stabilizes at occupancy 8 (cap 10), RoleB at 2 (cap 4)
    times = [i * 0.1 for i in range(100)]
    occ_role_a = [0.0] * 20 + [8.0] * 80
    occ_role_b = [0.0] * 20 + [2.0] * 80
    resource_timeseries = {
        "RoleA": {"times_hr": times, "occupancy": occ_role_a},
        "RoleB": {"times_hr": times, "occupancy": occ_role_b},
    }
    resource_metrics = {
        "RoleA": {"capacity": 10},
        "RoleB": {"capacity": 4},
    }
    run = DummyRun(times, resource_timeseries, resource_metrics)
    res = DummyResult(run)

    rep = steady_state_report_from_result(res, window=15, slope_rel_eps=0.01, target_util=0.85)
    # Warm-up index should be near the plateau start (~20)
    assert 5 <= rep.warmup_index <= 40

    role_a = rep.per_role["RoleA"]
    role_b = rep.per_role["RoleB"]

    # Avg occupancy approx 8 and 2 respectively
    assert math.isclose(role_a["avg_occupancy"], 8.0, rel_tol=1e-2, abs_tol=1e-2)
    assert math.isclose(role_b["avg_occupancy"], 2.0, rel_tol=1e-2, abs_tol=1e-2)

    # Utilization = avg_occ / capacity
    assert math.isclose(role_a["utilization"], 0.8, rel_tol=1e-2, abs_tol=1e-2)
    assert math.isclose(role_b["utilization"], 0.5, rel_tol=1e-2, abs_tol=1e-2)

    # Suggested capacity at 85% util: ceil(avg_occ / 0.85)
    assert role_a["suggested_capacity"] == 10  # ceil(8/0.85)=10
    assert role_b["suggested_capacity"] == 3   # ceil(2/0.85)=3
