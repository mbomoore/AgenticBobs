"""Adapter utilities to run a ProcessModel with SimPy or to analyze it analytically.

This initial adapter includes a function to compute the transition matrix and a small
simulator shim that does not require SimPy to run quick smoke tests. Full SimPy
integration can be added later.
"""
from typing import Tuple, Dict, Any, Optional, List, Callable, NamedTuple, Union, Set
import numpy as np
from dataclasses import dataclass, field
from .core import ProcessModel
from .resources import TimedResource
from .metrics import Metric


def simulate_markov_chain(model: ProcessModel, steps: int = 100, start_state: int = 0) -> Dict[str, Any]:
    """A simple discrete-time Markov chain simulator that uses the transition matrix.

    Returns a dict with visit counts and a simple trace (state indices over time).
    """
    P = model.transition_matrix()
    n = P.shape[0]
    state = start_state
    visits = [0] * n
    trace = []
    rng = np.random.default_rng()
    for _ in range(steps):
        visits[state] += 1
        trace.append(state)
        probs = P[state]
        if probs.sum() == 0:
            # absorbing state, stay
            continue
        state = int(rng.choice(n, p=probs))
    return {"visits": visits, "trace": trace}


def simulate_with_simpy(
    model: ProcessModel,
    runs: int = 100,
    seed: int | None = None,
    arrival_rate_per_min: Optional[float] = None,
    end_time_min: Optional[float] = None,
) -> Dict[str, Any]:
    """Run the model with SimPy. Each run simulates one entity progressing through states.

    Optional arrival_rate_per_min: if provided, entities are spawned according to an
    exponential interarrival distribution with mean 1/arrival_rate_per_min (units: minutes).
    Optional end_time_min: if provided, the simulation will run until this time (minutes).

    NOTE: The ProcessModel state times are in hours; arrival/end times are minutes and
    converted to hours internally for scheduling and env.run().

    Returns a dict with 'events' (list of (time_hr, run_id, state_name)) and summary series.
    Also includes 'detailed_events' for richer analysis and optional wait/service split series.
    """
    try:
        import simpy
    except Exception as e:
        raise ImportError("simpy is required for simulate_with_simpy") from e

    # --- Input normalization & setup ---
    P = model.transition_matrix()
    states = model.states
    state_names = [s.name for s in states]
    end_time_hr = _min_to_hr(end_time_min)
    env, rng = _init_env(seed)
    timed_resources = _init_timed_resources(env, states)

    # --- Process factories ---
    events: List[Event] = []
    detailed_events: List[DetailedEvent] = []
    entity_proc = _make_entity_process(P, states, timed_resources, rng, events, detailed_events)
    arrival_proc = _make_arrival_process(runs, arrival_rate_per_min, end_time_hr, rng, entity_proc)

    # --- Run ---
    env.process(arrival_proc(env))
    if end_time_hr is not None:
        env.run(until=end_time_hr)
    else:
        env.run()

    # --- Post-process ---
    counts = _counts_from_events(events)
    sim_end_hr = _resolve_sim_end_hr(events, timed_resources, float(env.now), end_time_hr)
    grid = _build_time_grid(sim_end_hr, resolution_min=1.0)
    state_series = _state_counts_from_events(events, grid, state_names)
    state_series.percent = _percent_from_state_counts(state_series.counts)
    resource_series = _resource_series_from_timelines(timed_resources, grid)
    resource_metrics = _resource_metrics(timed_resources, sim_end_hr)

    # Build wait/service split series from detailed events
    wait_series, service_series = _wait_service_series_from_detailed_events(detailed_events, grid, state_names)

    # Compute terminal states from transition matrix (absorbing rows)
    terminals = _terminal_states_from_matrix(P, state_names)

    # Resource cost map by state
    state_costs = _state_resource_costs(states)

    summary = SimulationSummary(
        events=events,
        counts=counts,
        resource_metrics=resource_metrics,
        simulation_time_hr=sim_end_hr,
        grid=grid,
        state_series=state_series,
        resource_series=resource_series,
    )

    out = _to_legacy_dict(summary)
    out.update({
        "detailed_events": [(ev.kind, ev.time_hr, ev.run_id, ev.state, ev.role) for ev in detailed_events],
        "state_wait_counts_timeseries": wait_series,
        "state_service_counts_timeseries": service_series,
        "terminal_states": list(terminals),
        "state_resource_costs_per_hr": state_costs,
    })
    return out


# ----------------------------
# Types & small records (internal)
# ----------------------------

# Aliases
TimeHr = float
Minutes = float
RunId = int
StateName = str
RoleName = str
Occupancy = int


class Event(NamedTuple):
    time_hr: TimeHr
    run_id: RunId
    state: StateName


class ResourceTimelineEvent(NamedTuple):
    time_hr: TimeHr
    delta: int


@dataclass
class SimulationGrid:
    times_hr: List[TimeHr]
    res_hr: TimeHr


@dataclass
class StateSeries:
    counts: Dict[StateName, List[int]]
    percent: Dict[StateName, List[float]]


@dataclass
class ResourceSeries:
    series: Dict[RoleName, Dict[str, Any]]  # {"times_hr": [...], "occupancy": [...]}


@dataclass
class ResourceMetrics:
    capacity: int
    total_acquired: int
    total_time_held: float
    utilization: float
    utilization_env: float


@dataclass
class SimulationSummary:
    events: List[Event]
    counts: Dict[StateName, int]
    resource_metrics: Dict[RoleName, ResourceMetrics]
    simulation_time_hr: TimeHr
    grid: SimulationGrid
    state_series: StateSeries
    resource_series: ResourceSeries


class DetailedEvent(NamedTuple):
    kind: str  # 'state_enter' | 'service_start' | 'service_end' | 'state_exit'
    time_hr: TimeHr
    run_id: RunId
    state: StateName
    role: Optional[RoleName]


# ----------------------------
# Helper functions (pure/semantic)
# ----------------------------

def _min_to_hr(minutes: Optional[Minutes]) -> Optional[TimeHr]:
    return None if minutes is None else float(minutes) / 60.0


def _init_env(seed: Optional[int]):
    import simpy  # type: ignore

    env = simpy.Environment()
    rng = np.random.default_rng(seed)
    return env, rng


def _init_timed_resources(env, states) -> Dict[RoleName, TimedResource]:
    resources: Dict[RoleName, TimedResource] = {}
    for st in states:
        if getattr(st, "resource", None):
            role = getattr(st.resource, "role", str(st.resource))
            cap = getattr(st.resource, "capacity", 1)
            if role not in resources:
                resources[role] = TimedResource(env, capacity=int(cap))
    return resources


def _make_entity_process(
    P: np.ndarray,
    states,
    timed_resources: Dict[RoleName, TimedResource],
    rng: np.random.Generator,
    sink: List[Event],
    detailed_sink: List[DetailedEvent],
) -> Callable[[Any, RunId], Any]:
    nstates = len(states)

    def entity_process(env, run_id: RunId):
        current = 0
        while True:
            st = states[current]
            now = float(env.now)
            sink.append(Event(now, run_id, st.name))
            detailed_sink.append(DetailedEvent("state_enter", now, run_id, st.name, getattr(getattr(st, "resource", None), "role", None)))
            delay = float(getattr(st, "time", 0.0))
            if delay > 0:
                res = getattr(st, "resource", None)
                if res is not None:
                    role = getattr(res, "role", str(res))
                    tr = timed_resources.get(role)
                    if tr is not None:
                        # Explicitly manage acquire to record waiting vs service
                        req = tr.request()
                        yield req
                        start = float(env.now)
                        tr.total_acquired += 1
                        try:
                            tr.timeline.append((start, 1))
                        except Exception:
                            pass
                        detailed_sink.append(DetailedEvent("service_start", start, run_id, st.name, role))
                        try:
                            if delay > 0:
                                yield env.timeout(delay)
                        finally:
                            tr._res.release(req)  # type: ignore[attr-defined]
                            end = float(env.now)
                            tr.total_time_held += (end - start)
                            try:
                                tr.timeline.append((end, -1))
                            except Exception:
                                pass
                            detailed_sink.append(DetailedEvent("service_end", end, run_id, st.name, role))
                            detailed_sink.append(DetailedEvent("state_exit", end, run_id, st.name, role))
                    else:
                        t0 = float(env.now)
                        yield env.timeout(delay)
                        detailed_sink.append(DetailedEvent("state_exit", float(env.now), run_id, st.name, None))
                else:
                    t0 = float(env.now)
                    yield env.timeout(delay)
                    detailed_sink.append(DetailedEvent("state_exit", float(env.now), run_id, st.name, None))
            probs = P[current]
            if probs.sum() == 0:
                break
            current = int(rng.choice(nstates, p=probs))

    return entity_process


def _make_arrival_process(
    runs: int,
    arrival_rate_per_min: Optional[float],
    end_time_hr: Optional[TimeHr],
    rng: np.random.Generator,
    spawn: Callable[[Any, RunId], Any],
) -> Callable[[Any], Any]:
    def arrival_process(env):
        if arrival_rate_per_min is None:
            for i in range(runs):
                env.process(spawn(env, i))
            return

        i = 0
        while i < runs:
            env.process(spawn(env, i))
            i += 1
            if i >= runs or (arrival_rate_per_min is not None and arrival_rate_per_min <= 0):
                break
            interarrival_min = float(rng.exponential(1.0 / float(arrival_rate_per_min)))
            interarrival_hr = interarrival_min / 60.0
            if end_time_hr is not None and (float(env.now) + interarrival_hr) > end_time_hr:
                break
            yield env.timeout(interarrival_hr)

    return arrival_process


def _counts_from_events(events: List[Event]) -> Dict[StateName, int]:
    counts: Dict[StateName, int] = {}
    for ev in events:
        counts[ev.state] = counts.get(ev.state, 0) + 1
    return counts


def _resolve_sim_end_hr(
    events: List[Event],
    resources: Dict[RoleName, TimedResource],
    env_now: TimeHr,
    end_time_hr: Optional[TimeHr],
) -> TimeHr:
    if end_time_hr is not None:
        return float(end_time_hr)
    last_event_time = max((ev.time_hr for ev in events), default=0.0)
    last_resource_time = 0.0
    for tr in resources.values():
        if getattr(tr, "timeline", None):
            last_resource_time = max(last_resource_time, max(t for t, _ in tr.timeline))
    return max(last_event_time, last_resource_time, float(env_now))


def _build_time_grid(sim_end_hr: TimeHr, resolution_min: float = 1.0) -> SimulationGrid:
    res_hr: TimeHr = float(resolution_min) / 60.0
    # Preserve legacy behavior: ensure at least 2 steps
    n_steps = max(1, int(sim_end_hr / res_hr) + 1)
    times = [i * res_hr for i in range(n_steps + 1)]
    return SimulationGrid(times_hr=times, res_hr=res_hr)


def _state_counts_from_events(
    events: List[Event],
    grid: SimulationGrid,
    state_names: List[StateName],
) -> StateSeries:
    times = grid.times_hr
    res_hr = grid.res_hr
    counts = {name: [0] * len(times) for name in state_names}

    events_sorted = sorted(events, key=lambda e: (e.time_hr, e.run_id))
    runs_events: Dict[RunId, List[Tuple[TimeHr, StateName]]] = {}
    for ev in events_sorted:
        runs_events.setdefault(ev.run_id, []).append((float(ev.time_hr), ev.state))

    sim_end_hr = times[-1] if times else 0.0
    for rid, evs in runs_events.items():
        evs = sorted(evs)
        evs.append((sim_end_hr, "__END__"))
        for (t0, sname), (t1, _) in zip(evs[:-1], evs[1:]):
            i0 = int(t0 / res_hr)
            i1 = int(t1 / res_hr)
            i0 = max(0, min(i0, len(times) - 1))
            i1 = max(0, min(i1, len(times) - 1))
            if sname == "__END__":
                continue
            for i in range(i0, i1 + 1):
                counts[sname][i] += 1

    return StateSeries(counts=counts, percent={name: [0.0] * len(times) for name in state_names})


def _resource_series_from_timelines(
    resources: Dict[RoleName, TimedResource],
    grid: SimulationGrid,
) -> ResourceSeries:
    times = grid.times_hr
    res_hr = grid.res_hr
    series: Dict[RoleName, Dict[str, Any]] = {}
    for role, tr in resources.items():
        occ = [0] * len(times)
        tl = sorted(getattr(tr, "timeline", []), key=lambda x: x[0])
        cur = 0
        idx = 0
        for t_event, delta in tl:
            i_event = int(float(t_event) / res_hr)
            i_event = max(0, min(i_event, len(times) - 1))
            for j in range(idx, i_event + 1):
                occ[j] = cur
            cur += int(delta)
            idx = i_event + 1
        for j in range(idx, len(times)):
            occ[j] = cur
        series[role] = {"times_hr": times, "occupancy": occ}
    return ResourceSeries(series=series)


def _percent_from_state_counts(counts: Dict[StateName, List[int]]) -> Dict[StateName, List[float]]:
    names = list(counts.keys())
    if not names:
        return {}
    length = len(counts[names[0]])
    percent = {name: [0.0] * length for name in names}
    for i in range(length):
        total = sum(counts[name][i] for name in names)
        if total <= 0:
            continue
        for name in names:
            percent[name][i] = counts[name][i] / float(total) * 100.0
    return percent


def _resource_metrics(
    resources: Dict[RoleName, TimedResource],
    sim_end_hr: TimeHr,
) -> Dict[RoleName, ResourceMetrics]:
    out: Dict[RoleName, ResourceMetrics] = {}
    sim_time_for_util = float(sim_end_hr) if float(sim_end_hr) > 0 else 0.0
    for role, tr in resources.items():
        if sim_time_for_util <= 0 or int(tr.capacity) <= 0:
            util = 0.0
        else:
            util = float(tr.total_time_held) / (sim_time_for_util * int(tr.capacity))
            util = 0.0 if util < 0 else (1.0 if util > 1.0 else util)
        out[role] = ResourceMetrics(
            capacity=int(tr.capacity),
            total_acquired=int(tr.total_acquired),
            total_time_held=float(tr.total_time_held),
            utilization=float(util),
            utilization_env=float(getattr(tr, "utilization", 0.0)),
        )
    return out


def _to_legacy_dict(summary: SimulationSummary) -> Dict[str, Any]:
    events_legacy = [(ev.time_hr, ev.run_id, ev.state) for ev in summary.events]
    resource_metrics_legacy: Dict[str, Dict[str, Any]] = {}
    for role, m in summary.resource_metrics.items():
        resource_metrics_legacy[role] = {
            "capacity": m.capacity,
            "total_acquired": m.total_acquired,
            "total_time_held": m.total_time_held,
            "utilization": m.utilization,
            "utilization_env": m.utilization_env,
        }
    return {
        "events": events_legacy,
        "counts": summary.counts,
        "resource_metrics": resource_metrics_legacy,
        "simulation_time_hr": summary.simulation_time_hr,
        "times_hr": summary.grid.times_hr,
        "state_counts_timeseries": summary.state_series.counts,
        "state_percent_timeseries": summary.state_series.percent,
        "resource_timeseries": summary.resource_series.series,
    }


# ----------------------------
# New structured simulate API
# ----------------------------

@dataclass
class SingleRunResult:
    """Raw outputs for a single simulation run with SimPy.

    Mirrors the legacy dict from simulate_with_simpy and holds per-run metric outputs.
    """

    events: List[tuple]
    counts: Dict[str, int]
    resource_metrics: Dict[str, Dict[str, Any]]
    simulation_time_hr: float
    times_hr: List[float]
    state_counts_timeseries: Dict[str, List[int]]
    state_percent_timeseries: Dict[str, List[float]]
    resource_timeseries: Dict[str, Dict[str, Any]]
    # Optional enhanced fields
    detailed_events: List[tuple] = field(default_factory=list)
    state_wait_counts_timeseries: Dict[str, List[int]] = field(default_factory=dict)
    state_service_counts_timeseries: Dict[str, List[int]] = field(default_factory=dict)
    terminal_states: List[str] = field(default_factory=list)
    state_resource_costs_per_hr: Dict[str, float] = field(default_factory=dict)
    metrics: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    seed: Optional[int] = None


@dataclass
class Result:
    """Container for results across one or many simulations.

    per_simulation holds raw run outputs; aggregated can be filled by callers if desired.
    """

    per_simulation: List[SingleRunResult]
    aggregated: Dict[str, Any] = field(default_factory=dict)
    meta: Dict[str, Any] = field(default_factory=dict)


def simulate(
    model: Union[ProcessModel, "SimulationRequest"],
    *,
    parameters: Optional["SimulationParameters"] = None,
    settings: Optional["SimulationSettings"] = None,
) -> Result:
    """Run SimPy across one or more simulations with explicit structured inputs.

    Accepts either:
      - a SimulationRequest, or
      - a ProcessModel plus SimulationParameters and SimulationSettings.

    Returns a Result for visualizers and downstream analysis.
    """

    # Structured input only: build a request from (model, parameters, settings) or pass-through
    req = _build_request(model, parameters, settings)

    # Provide default posthoc summary metrics if none supplied
    metrics = req.settings.metrics or [
        _metric_avg_cycle_time(),
        _metric_state_service_costs(),
        _metric_waiting_service_breakdown(),
    ]
    per_run_seeds = _derive_seeds(req.settings.simulations, req.settings.seed, req.settings.seeds)
    per_sim_results: List[SingleRunResult] = []

    for i in range(req.settings.simulations):
        run_seed = per_run_seeds[i]
        raw = simulate_with_simpy(
            req.model,
            runs=req.parameters.runs,
            seed=run_seed,
            arrival_rate_per_min=req.parameters.arrival_rate_per_min,
            end_time_min=req.parameters.end_time_min,
        )
        run = _single_run_from_dict(raw, seed=run_seed)
        _compute_metrics_for_run(run, metrics, req.settings.target_samples)
        per_sim_results.append(run)

    meta = {
        "runs": req.parameters.runs,
        "simulations": req.settings.simulations,
        "seed": req.settings.seed,
        "seeds": req.settings.seeds,
        "arrival_rate_per_min": req.parameters.arrival_rate_per_min,
        "end_time_min": req.parameters.end_time_min,
        "target_samples": req.settings.target_samples,
        "model": getattr(req.model, "name", None),
        "structured": True,
        "parameters": {
            "runs": req.parameters.runs,
            "arrival_rate_per_min": req.parameters.arrival_rate_per_min,
            "end_time_min": req.parameters.end_time_min,
        },
        "settings": {
            "simulations": req.settings.simulations,
            "seed": req.settings.seed,
            "seeds": req.settings.seeds,
            "target_samples": req.settings.target_samples,
            "metrics": [m.name for m in (metrics or [])],
        },
    }
    return Result(per_simulation=per_sim_results, aggregated={}, meta=meta)


# ---------- helpers ----------

def _derive_seeds(simulations: int, seed: Optional[int], seeds: Optional[List[int]]) -> List[Optional[int]]:
    if seeds is not None:
        if len(seeds) < simulations:
            return list(seeds) + [None] * (simulations - len(seeds))
        return list(seeds[:simulations])
    if seed is None:
        return [None] * simulations
    rng = np.random.default_rng(seed)
    return [int(s) for s in rng.integers(0, 2**31 - 1, size=simulations)]


def _single_run_from_dict(d: Dict[str, Any], *, seed: Optional[int]) -> SingleRunResult:
    return SingleRunResult(
        events=d.get("events", []),
        counts=d.get("counts", {}),
        resource_metrics=d.get("resource_metrics", {}),
        simulation_time_hr=float(d.get("simulation_time_hr", 0.0)),
        times_hr=d.get("times_hr", []),
        state_counts_timeseries=d.get("state_counts_timeseries", {}),
        state_percent_timeseries=d.get("state_percent_timeseries", {}),
        resource_timeseries=d.get("resource_timeseries", {}),
    detailed_events=d.get("detailed_events", []),
    state_wait_counts_timeseries=d.get("state_wait_counts_timeseries", {}),
    state_service_counts_timeseries=d.get("state_service_counts_timeseries", {}),
    terminal_states=d.get("terminal_states", []),
    state_resource_costs_per_hr=d.get("state_resource_costs_per_hr", {}),
        metrics={},
        seed=seed,
    )


def _compute_metrics_for_run(run: SingleRunResult, metrics: List[Metric], default_target_samples: Optional[int]):
    default_target = default_target_samples or 50
    duration = max(float(run.simulation_time_hr or 0.0), 0.0)
    for m in metrics:
        if m.sample_mode == "posthoc":
            value = m.sampler(None, _run_to_dict(run))
            # If the metric returns a mapping, store it as-is; otherwise wrap in {'value': scalar}
            if isinstance(value, dict):
                run.metrics[m.name] = value  # e.g., {'value': 1.23, 'n_completed': 10, ...}
            else:
                run.metrics[m.name] = {"value": value}
            continue

        # periodic sampling
        if m.frequency_hz and m.frequency_hz > 0 and duration > 0:
            step_hr = 1.0 / float(m.frequency_hz)
            n = max(1, int(duration / step_hr))
        else:
            target = int(m.target_samples or default_target)
            target = max(1, target)
            n = target
            step_hr = duration / float(n) if n > 0 else 0.0

        if duration <= 0 or step_hr <= 0:
            times = [0.0] * n
        else:
            times = [min(duration, (i + 0.5) * step_hr) for i in range(n)]

        values = [m.sampler(t, _run_to_dict(run)) for t in times]
        run.metrics[m.name] = {"times_hr": times, "values": values}


def _run_to_dict(run: SingleRunResult) -> Dict[str, Any]:
    return {
        "events": run.events,
    "detailed_events": run.detailed_events,
        "counts": run.counts,
        "resource_metrics": run.resource_metrics,
        "simulation_time_hr": run.simulation_time_hr,
        "times_hr": run.times_hr,
        "state_counts_timeseries": run.state_counts_timeseries,
    "state_wait_counts_timeseries": run.state_wait_counts_timeseries,
    "state_service_counts_timeseries": run.state_service_counts_timeseries,
        "state_percent_timeseries": run.state_percent_timeseries,
        "resource_timeseries": run.resource_timeseries,
    "terminal_states": run.terminal_states,
    "state_resource_costs_per_hr": run.state_resource_costs_per_hr,
        "seed": run.seed,
    }


# ----------------------------
# Structured input types for simulate
# ----------------------------

@dataclass
class SimulationParameters:
    """Entity-level simulation parameters (units: minutes for arrival/end)."""

    runs: int = 100
    arrival_rate_per_min: Optional[float] = None
    end_time_min: Optional[float] = None


@dataclass
class SimulationSettings:
    """Global simulation settings and analysis knobs."""

    simulations: int = 1
    seed: Optional[int] = None
    seeds: Optional[List[int]] = None
    target_samples: Optional[int] = None
    metrics: Optional[List[Metric]] = None


@dataclass
class SimulationRequest:
    model: ProcessModel
    parameters: SimulationParameters = field(default_factory=SimulationParameters)
    settings: SimulationSettings = field(default_factory=SimulationSettings)


def _build_request(
    model: Union[ProcessModel, SimulationRequest],
    parameters: Optional[SimulationParameters],
    settings: Optional[SimulationSettings],
) -> SimulationRequest:
    if isinstance(model, SimulationRequest):
        return model
    params = parameters or SimulationParameters()
    sett = settings or SimulationSettings()
    return SimulationRequest(model=model, parameters=params, settings=sett)


# ----------------------------
# Enhanced analysis helpers
# ----------------------------

def _terminal_states_from_matrix(P: np.ndarray, state_names: List[str]) -> Set[str]:
    terms: Set[str] = set()
    for i, name in enumerate(state_names):
        if float(P[i].sum()) == 0.0:
            terms.add(name)
    return terms


def _state_resource_costs(states) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for st in states:
        res = getattr(st, "resource", None)
        rate = float(getattr(res, "cost", 0.0)) if res is not None else 0.0
        out[st.name] = rate
    return out


def _wait_service_series_from_detailed_events(
    detailed: List[DetailedEvent],
    grid: SimulationGrid,
    state_names: List[str],
) -> Tuple[Dict[str, List[int]], Dict[str, List[int]]]:
    # Build intervals per state for waiting and service
    times = grid.times_hr
    res_hr = grid.res_hr
    wait_counts = {name: [0] * len(times) for name in state_names}
    service_counts = {name: [0] * len(times) for name in state_names}

    # Organize per run/state
    by_run_state: Dict[int, Dict[str, List[Tuple[str, float]]]] = {}
    for kind, t, rid, sname, role in detailed:
        rid = int(rid)
        sname = str(sname)
        by_run_state.setdefault(rid, {}).setdefault(sname, []).append((str(kind), float(t)))
    for rid, per_state in by_run_state.items():
        for sname, seq in per_state.items():
            seq.sort(key=lambda x: x[1])
            # Derive intervals:
            # waiting: from state_enter to service_start (if any)
            # service: from service_start to service_end (if any)
            t_enter = None
            t_service_start = None
            t_service_end = None
            for kind, t in seq:
                if kind == "state_enter":
                    t_enter = t
                elif kind == "service_start":
                    t_service_start = t
                elif kind == "service_end":
                    t_service_end = t
                elif kind == "state_exit":
                    # use as fallback end if service_end missing
                    if t_service_end is None:
                        t_service_end = t
            # waiting interval (only for resource-backed states)
            if t_enter is not None and t_service_start is not None and t_service_start > t_enter:
                i0 = max(0, min(int(t_enter / res_hr), len(times) - 1))
                i1 = max(0, min(int(t_service_start / res_hr), len(times) - 1))
                for i in range(i0, i1 + 1):
                    wait_counts[sname][i] += 1
            # service interval
            if t_service_start is not None and t_service_end is not None and t_service_end >= t_service_start:
                i0 = max(0, min(int(t_service_start / res_hr), len(times) - 1))
                i1 = max(0, min(int(t_service_end / res_hr), len(times) - 1))
                for i in range(i0, i1 + 1):
                    service_counts[sname][i] += 1
            # states without resources: treat full [enter, exit] as service
            elif t_service_start is None and t_enter is not None and t_service_end is not None and t_service_end > t_enter:
                i0 = max(0, min(int(t_enter / res_hr), len(times) - 1))
                i1 = max(0, min(int(t_service_end / res_hr), len(times) - 1))
                for i in range(i0, i1 + 1):
                    service_counts[sname][i] += 1

    return wait_counts, service_counts


# ----------------------------
# Default summary metrics
# ----------------------------

def _metric_avg_cycle_time() -> Metric:
    def sampler(_t: Optional[float], run: Dict[str, Any]) -> Dict[str, Any]:
        events = run.get("detailed_events") or []
        terminals = set(run.get("terminal_states") or [])
        # group by run_id
        by_run: Dict[int, List[Tuple[str, float, str]]] = {}
        for kind, t, rid, sname, role in events:
            by_run.setdefault(int(rid), []).append((str(kind), float(t), str(sname)))
        cycles: List[float] = []
        for rid, seq in by_run.items():
            seq.sort(key=lambda x: x[1])
            t0 = None
            for kind, t, sname in seq:
                if kind == "state_enter" and t0 is None:
                    t0 = t
                if kind == "state_enter" and sname in terminals and t0 is not None:
                    cycles.append(t - t0)
                    break
        mean = float(np.mean(cycles)) if cycles else 0.0
        return {"value": mean, "n_completed": len(cycles), "n_entities": len(by_run)}

    return Metric(name="avg_cycle_time_hr", sampler=sampler, sample_mode="posthoc")


def _metric_state_service_costs() -> Metric:
    def sampler(_t: Optional[float], run: Dict[str, Any]) -> Dict[str, Any]:
        events = run.get("detailed_events") or []
        rates = run.get("state_resource_costs_per_hr") or {}
        # accumulate service hours per state from service_start -> service_end
        per_state_hours: Dict[str, float] = {}
        by_run_state: Dict[int, Dict[str, List[Tuple[str, float]]]] = {}
        for kind, t, rid, sname, role in events:
            by_run_state.setdefault(int(rid), {}).setdefault(str(sname), []).append((str(kind), float(t)))
        for rid, per in by_run_state.items():
            for sname, seq in per.items():
                seq.sort(key=lambda x: x[1])
                t_start = None
                t_end = None
                for kind, t in seq:
                    if kind == "service_start":
                        t_start = t
                    elif kind == "service_end":
                        t_end = t
                if t_start is not None and t_end is not None and t_end >= t_start:
                    per_state_hours[sname] = per_state_hours.get(sname, 0.0) + (t_end - t_start)
        by_state_cost = {s: float(per_state_hours.get(s, 0.0)) * float(rates.get(s, 0.0)) for s in set(list(rates.keys()) + list(per_state_hours.keys()))}
        total = float(sum(by_state_cost.values()))
        return {"by_state": by_state_cost, "total_cost": total}

    return Metric(name="state_service_costs", sampler=sampler, sample_mode="posthoc")


def _metric_waiting_service_breakdown() -> Metric:
    def sampler(_t: Optional[float], run: Dict[str, Any]) -> Dict[str, Any]:
        events = run.get("detailed_events") or []
        by_run_state: Dict[int, Dict[str, List[Tuple[str, float]]]] = {}
        for kind, t, rid, sname, role in events:
            by_run_state.setdefault(int(rid), {}).setdefault(str(sname), []).append((str(kind), float(t)))
        out: Dict[str, Dict[str, float]] = {}
        for rid, per in by_run_state.items():
            for sname, seq in per.items():
                seq.sort(key=lambda x: x[1])
                t_enter = None
                t_start = None
                t_end = None
                t_exit = None
                for kind, t in seq:
                    if kind == "state_enter":
                        t_enter = t
                    elif kind == "service_start":
                        t_start = t
                    elif kind == "service_end":
                        t_end = t
                    elif kind == "state_exit":
                        t_exit = t
                waiting = 0.0
                service = 0.0
                if t_enter is not None and t_start is not None and t_start > t_enter:
                    waiting += (t_start - t_enter)
                if t_start is not None and t_end is not None and t_end >= t_start:
                    service += (t_end - t_start)
                out.setdefault(sname, {"waiting_hr": 0.0, "service_hr": 0.0})
                out[sname]["waiting_hr"] += float(waiting)
                out[sname]["service_hr"] += float(service)
        return {"by_state": out}

    return Metric(name="waiting_service_breakdown", sampler=sampler, sample_mode="posthoc")
