import math
from typing import Optional, Any

import numpy as np
import pytest

from sim_dsl.core import ProcessModel, State
from sim_dsl import simulate, Metric
from sim_dsl.simpy_adapter import SimulationParameters, SimulationSettings


def build_simple_model():
    p = ProcessModel("simple")
    with p:
        a = State("A", time=0.1)
        b = State("B", time=0.0)
        p.add_transition(a >> 1.0 >> b)
    return p


def test_simulate_periodic_metric_default_50_samples():
    model = build_simple_model()

    # metric that samples number of events recorded so far at time t (post-run periodic)
    def sample_events(time_hr: Optional[float], run_result: dict) -> int:
        # count events that happened at or before time_hr
        if time_hr is None:
            return len(run_result.get("events", []))
        return sum(1 for t, *_ in run_result.get("events", []) if float(t) <= float(time_hr))

    m = Metric(name="events", sampler=sample_events, sample_mode="periodic")
    params = SimulationParameters(runs=5)
    settings = SimulationSettings(simulations=1, seed=123, metrics=[m])
    res = simulate(model, parameters=params, settings=settings)

    assert len(res.per_simulation) == 1
    run = res.per_simulation[0]
    mres = run.metrics["events"]
    # default target is 50
    assert "times_hr" in mres and "values" in mres
    assert len(mres["times_hr"]) == 50
    assert len(mres["values"]) == 50
    # monotonic non-decreasing
    vals = list(mres["values"]) 
    assert all(vals[i] <= vals[i+1] for i in range(len(vals)-1))


def test_simulate_multiple_simulations_and_seed_list():
    model = build_simple_model()

    def total_events(_: Optional[float], run_result: dict) -> int:
        return len(run_result.get("events", []))

    m = Metric(name="total_events", sampler=total_events, sample_mode="posthoc")

    params = SimulationParameters(runs=3)
    settings = SimulationSettings(simulations=2, seeds=[1, 2], metrics=[m])
    res = simulate(model, parameters=params, settings=settings)
    assert len(res.per_simulation) == 2
    # ensure each run has posthoc metric stored under 'value'
    vals = []
    for r in res.per_simulation:
        assert "total_events" in r.metrics
        assert set(r.metrics["total_events"].keys()) == {"value"}
        vals.append(r.metrics["total_events"]["value"])
    # If seeds differ, values can differ; but they should be integers >= runs (at least one state per entity)
    assert all(isinstance(v, int) and v >= 3 for v in vals)


def test_simulate_target_samples_override():
    model = build_simple_model()

    def sample_count(_: Optional[float], run_result: dict) -> int:
        return len(run_result.get("counts", {}))

    m = Metric(name="kinds", sampler=sample_count, sample_mode="periodic")
    params = SimulationParameters(runs=2)
    settings = SimulationSettings(simulations=1, target_samples=10, metrics=[m])
    res = simulate(model, parameters=params, settings=settings)
    run = res.per_simulation[0]
    mres = run.metrics["kinds"]
    assert len(mres["times_hr"]) == 10
    assert len(mres["values"]) == 10
