"""Simple matplotlib helpers to plot simulation timeseries returned by simulate_with_simpy,
and averaged visualizations across multiple simulations using Result.

Functions:
- plot_state_counts(times_hr, state_counts): stacked area of absolute counts per state.
- plot_state_percent(times_hr, percent_in_system): stacked area of percent-in-system per state.
- plot_resource_occupancy(resource_timeseries, resource_metrics=None): line plots of occupancy and optional percent-of-capacity.

New options:
- exclude_terminal (bool) on result-based state plots to omit terminal/absorbing states inferred from events.
"""
from typing import Dict, List, Optional, Tuple, Mapping, Sequence, Set, cast
import numpy as np
import matplotlib.pyplot as plt
from .simpy_adapter import Result
from matplotlib.axes import Axes
from matplotlib.figure import Figure, SubFigure
import matplotlib.colors as mcolors

# Type aliases for series inputs
StateSeries = Mapping[str, Sequence[float | int]]


def plot_state_counts(times_hr: List[float], state_counts: StateSeries, ax=None):
    names = list(state_counts.keys())
    if not names:
        raise ValueError('no states to plot')
    data = np.vstack([state_counts[n] for n in names])
    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 4))
    else:
        fig = ax.figure
    ax.stackplot(times_hr, data, labels=names)
    ax.set_xlabel('Time (hr)')
    ax.set_ylabel('Count')
    ax.legend(loc='upper left')
    ax.set_title('State counts over time')
    return fig, ax


def plot_state_percent(times_hr: List[float], percent_in_system: Mapping[str, Sequence[float]], ax=None):
    names = list(percent_in_system.keys())
    if not names:
        raise ValueError('no states to plot')
    data = np.vstack([percent_in_system[n] for n in names])
    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 4))
    else:
        fig = ax.figure
    ax.stackplot(times_hr, data, labels=names)
    ax.set_xlabel('Time (hr)')
    ax.set_ylabel('Percent (%)')
    ax.legend(loc='upper left')
    ax.set_ylim(0, 100)
    ax.set_title('Percent of in-system by state (stacked)')
    return fig, ax


def plot_resource_occupancy(resource_timeseries: Dict[str, Dict], resource_metrics: Optional[Dict[str, Dict]] = None, ax=None):
    """Plot occupancy time-series for each resource role.

    resource_timeseries: mapping role -> {"times_hr": [...], "occupancy": [...]}
    resource_metrics (optional): mapping role -> {"capacity": int, ...} used to plot percent of capacity.
    """
    roles = list(resource_timeseries.keys())
    n = len(roles)
    if n == 0:
        raise ValueError('no resources to plot')
    axes_list: List[Axes]
    fig: Figure | SubFigure
    if ax is None:
        fig, axes = plt.subplots(nrows=n, figsize=(10, 3 * n), sharex=True)
        if isinstance(axes, np.ndarray):
            axes_list = cast(List[Axes], list(axes))
        else:
            axes_list = [cast(Axes, axes)]
    else:
        if isinstance(ax, np.ndarray):
            axes_list = cast(List[Axes], list(ax))
        elif isinstance(ax, (list, tuple)):
            axes_list = [cast(Axes, a) for a in ax]
        else:
            axes_list = [cast(Axes, ax)]
    fig = axes_list[0].figure

    for i, role in enumerate(roles):
        a = axes_list[i]
        ts = resource_timeseries[role]
        times = list(map(float, ts.get('times_hr', [])))
        occ = np.array(ts.get('occupancy', []), dtype=float)
        a.plot(times, occ, label=f'{role} occupancy')
        cap = None
        if resource_metrics and role in resource_metrics:
            cap = resource_metrics[role].get('capacity')
        if cap:
            pct = occ / float(cap) * 100.0
            a.plot(times, pct, linestyle='--', label=f'{role} % of capacity')
            a.set_ylabel('Occupancy / %')
        else:
            a.set_ylabel('Occupancy')
        a.legend()
        a.set_title(f'Resource: {role}')
    axes_list[-1].set_xlabel('Time (hr)')
    # fig is guaranteed above
    tl = getattr(fig, 'tight_layout', None)
    if callable(tl):
        try:
            tl()
        except Exception:
            pass
    return fig, axes_list


# -----------------------
# Aggregation helpers
# -----------------------

def _align_and_average_series(series_list: List[Tuple[List[float], List[float]]]) -> Tuple[List[float], List[float]]:
    """Align multiple (times, values) series by index using the longest times as reference.

    Shorter series are padded with their last value to match the longest length.
    Returns (times_ref, mean_values).
    """
    if not series_list:
        return [], []
    # choose the longest times as reference
    ref_times, _ = max(series_list, key=lambda tv: len(tv[0]))
    L = len(ref_times)
    acc = np.zeros(L, dtype=float)
    cnt = np.zeros(L, dtype=float)
    for times, vals in series_list:
        if not times:
            continue
        vals_arr = np.array(vals, dtype=float)
        # pad or trim to L
        if len(vals_arr) < L:
            pad_val = vals_arr[-1] if len(vals_arr) > 0 else 0.0
            pad = np.full(L - len(vals_arr), pad_val, dtype=float)
            vals_pad = np.concatenate([vals_arr, pad])
        else:
            vals_pad = vals_arr[:L]
        acc += vals_pad
        cnt += 1.0
    cnt[cnt == 0] = 1.0
    mean_vals = (acc / cnt).tolist()
    return list(ref_times), mean_vals


def _infer_terminal_states(res: Result) -> Set[str]:
    """Infer terminal states from observed event transitions across runs.

    We derive an adjacency by pairing consecutive events per run_id; any state that
    appears as a predecessor (i.e., followed by another state) is considered to have
    an outgoing transition. Terminal states are those that never appear as a predecessor.

    This approach avoids misclassifying states as terminal when simulations end early.
    """
    seen_states: Set[str] = set()
    has_outgoing: Set[str] = set()
    for sim in res.per_simulation:
        # group events by run id
        by_run: Dict[int, List[Tuple[float, str]]] = {}
        for ev in sim.events:
            try:
                t, rid, sname = ev  # type: ignore[misc]
            except Exception:
                continue
            t = float(t)
            rid = int(rid)
            sname = str(sname)
            seen_states.add(sname)
            by_run.setdefault(rid, []).append((t, sname))
        for rid, seq in by_run.items():
            if not seq or len(seq) < 2:
                continue
            seq.sort(key=lambda x: x[0])
            for (_, s_from), (_, s_to) in zip(seq[:-1], seq[1:]):
                if s_from != s_to:
                    has_outgoing.add(s_from)
    # terminals are those seen but never observed with an outgoing transition
    terminals = seen_states - has_outgoing
    return terminals


def average_state_counts(res: Result, *, exclude_terminal: bool = False) -> Tuple[List[float], Dict[str, List[float]]]:
    """Compute mean state counts over time across simulations.

    Returns (times_hr, {state_name: mean_values}).
    """
    if not res.per_simulation:
        return [], {}
    # assume all runs share the same set of state names (filtering optional)
    state_names = list(res.per_simulation[0].state_counts_timeseries.keys())
    if exclude_terminal:
        terms = _infer_terminal_states(res)
        state_names = [n for n in state_names if n not in terms]
        if not state_names:
            return [], {}
    # build mean per state by aligning series by index
    # times per run is in run.times_hr
    times, _ = _align_and_average_series([(r.times_hr, r.times_hr) for r in res.per_simulation])
    out: Dict[str, List[float]] = {}
    for name in state_names:
        series_list = [(r.times_hr, list(map(float, r.state_counts_timeseries.get(name, [])))) for r in res.per_simulation]
        _, mean_vals = _align_and_average_series(series_list)
        out[name] = mean_vals
    return times, out


def average_state_percent(res: Result, *, exclude_terminal: bool = False) -> Tuple[List[float], Dict[str, List[float]]]:
    if not res.per_simulation:
        return [], {}
    state_names = list(res.per_simulation[0].state_percent_timeseries.keys())
    if exclude_terminal:
        terms = _infer_terminal_states(res)
        state_names = [n for n in state_names if n not in terms]
        if not state_names:
            return [], {}
    times, _ = _align_and_average_series([(r.times_hr, r.times_hr) for r in res.per_simulation])
    out: Dict[str, List[float]] = {}
    for name in state_names:
        series_list = [(r.times_hr, list(map(float, r.state_percent_timeseries.get(name, [])))) for r in res.per_simulation]
        _, mean_vals = _align_and_average_series(series_list)
        out[name] = mean_vals
    return times, out


def average_resource_occupancy(res: Result) -> Dict[str, Dict[str, List[float]]]:
    """Compute mean resource occupancy per role across simulations.

    Returns mapping role -> {"times_hr": [...], "occupancy": [...]}.
    Only roles present in at least one run are included; averaging is across runs that have that role.
    """
    roles: set = set()
    for r in res.per_simulation:
        roles.update(r.resource_timeseries.keys())
    out: Dict[str, Dict[str, List[float]]] = {}
    for role in roles:
        series_list: List[Tuple[List[float], List[float]]] = []
        for r in res.per_simulation:
            ts = r.resource_timeseries.get(role)
            if not ts:
                continue
            series_list.append((ts.get("times_hr", []), list(map(float, ts.get("occupancy", [])))))
        times, mean_vals = _align_and_average_series(series_list)
        out[role] = {"times_hr": times, "occupancy": mean_vals}
    return out


# -----------------------
# Plotting from Result
# -----------------------

def plot_state_counts_result(res: Result, mode: str = "mean", ax=None, *, exclude_terminal: bool = False, split_service: bool = False):
    if mode != "mean":
        raise ValueError("Only mode='mean' is supported currently")
    # If splitting and series available, synthesize combined labels/state series
    if split_service and res.per_simulation and res.per_simulation[0].state_wait_counts_timeseries:
        from copy import deepcopy
        # average waiting using the specific wait series
        tmp_wait_runs = []
        for r in res.per_simulation:
            rr = deepcopy(r)
            rr.state_counts_timeseries = r.state_wait_counts_timeseries or {}
            tmp_wait_runs.append(rr)
        times, wait = average_state_counts(Result(per_simulation=tmp_wait_runs), exclude_terminal=exclude_terminal)
        # average service using the specific service series
        tmp_serv_runs = []
        for r in res.per_simulation:
            rr = deepcopy(r)
            rr.state_counts_timeseries = r.state_service_counts_timeseries or {}
            tmp_serv_runs.append(rr)
        _, serv = average_state_counts(Result(per_simulation=tmp_serv_runs), exclude_terminal=exclude_terminal)

        # Determine stable base state order (union of states present)
        base_states = list(dict.fromkeys(list(wait.keys()) + [k for k in serv.keys() if k not in wait]))
        # Prepare interleaved data and labels
        names: List[str] = []
        data_arrays: List[List[float]] = []
        colors: List[Tuple[float, float, float]] = []

        # color palette per base state
        cmap = plt.get_cmap('tab20')
        def base_color(idx: int) -> Tuple[float, float, float]:
            c = cmap(idx % cmap.N)
            return (c[0], c[1], c[2])

        def lighten(rgb: Tuple[float, float, float], factor: float = 0.45) -> Tuple[float, float, float]:
            # blend with white
            r, g, b = rgb
            return (r + (1 - r) * factor, g + (1 - g) * factor, b + (1 - b) * factor)

        zeros = [0.0] * len(times)
        for i, s in enumerate(base_states):
            w_vals = list(map(float, wait.get(s, zeros)))
            s_vals = list(map(float, serv.get(s, zeros)))
            base = base_color(i)
            waiting_col = lighten(base)
            service_col = base
            # Interleave waiting then service for adjacency
            names.append(f"{s} (waiting)")
            data_arrays.append(w_vals)
            colors.append(waiting_col)
            names.append(f"{s} (service)")
            data_arrays.append(s_vals)
            colors.append(service_col)

        if ax is None:
            fig, ax = plt.subplots(figsize=(10, 4))
        else:
            fig = ax.figure
        ax.stackplot(times, np.vstack(data_arrays), labels=names, colors=colors)
        ax.set_xlabel('Time (hr)')
        ax.set_ylabel('Count')
        ax.legend(loc='upper left', ncol=2)
        ax.set_title('State counts over time (waiting vs service)')
        return fig, ax
    times, counts = average_state_counts(res, exclude_terminal=exclude_terminal)
    if not counts:
        raise ValueError('no states to plot after filtering')
    return plot_state_counts(times, counts, ax=ax)


def plot_state_percent_result(res: Result, mode: str = "mean", ax=None, *, exclude_terminal: bool = False, split_service: bool = False):
    if mode != "mean":
        raise ValueError("Only mode='mean' is supported currently")
    # When splitting, percent across all states still sums to 100; we can display stacked percent for waiting and service separately if desired.
    if split_service and res.per_simulation and res.per_simulation[0].state_wait_counts_timeseries:
        from copy import deepcopy
        # Average wait and service counts from their specific series
        tmp_wait_runs = []
        for r in res.per_simulation:
            rr = deepcopy(r)
            rr.state_counts_timeseries = r.state_wait_counts_timeseries or {}
            tmp_wait_runs.append(rr)
        times, wait = average_state_counts(Result(per_simulation=tmp_wait_runs), exclude_terminal=exclude_terminal)
        tmp_serv_runs = []
        for r in res.per_simulation:
            rr = deepcopy(r)
            rr.state_counts_timeseries = r.state_service_counts_timeseries or {}
            tmp_serv_runs.append(rr)
        _, serv = average_state_counts(Result(per_simulation=tmp_serv_runs), exclude_terminal=exclude_terminal)

        base_states = list(dict.fromkeys(list(wait.keys()) + [k for k in serv.keys() if k not in wait]))
        if not base_states:
            raise ValueError('no states to plot after filtering')
        # totals across all states (wait+service)
        total_arrays = []
        for s in base_states:
            w = np.array(wait.get(s, [0.0] * len(times)), dtype=float)
            sv = np.array(serv.get(s, [0.0] * len(times)), dtype=float)
            total_arrays.append(w + sv)
        totals = np.sum(np.vstack(total_arrays), axis=0)
        totals[totals == 0] = 1.0  # avoid div by zero

        names: List[str] = []
        data_arrays: List[List[float]] = []
        colors: List[Tuple[float, float, float]] = []
        cmap = plt.get_cmap('tab20')
        def base_color(idx: int) -> Tuple[float, float, float]:
            c = cmap(idx % cmap.N)
            return (c[0], c[1], c[2])
        def lighten(rgb: Tuple[float, float, float], factor: float = 0.45) -> Tuple[float, float, float]:
            r, g, b = rgb
            return (r + (1 - r) * factor, g + (1 - g) * factor, b + (1 - b) * factor)
        zeros = np.zeros(len(times), dtype=float)
        for i, s in enumerate(base_states):
            w = np.array(wait.get(s, zeros), dtype=float)
            sv = np.array(serv.get(s, zeros), dtype=float)
            pct_w = (w / totals * 100.0).tolist()
            pct_s = (sv / totals * 100.0).tolist()
            base = base_color(i)
            waiting_col = lighten(base)
            service_col = base
            names.append(f"{s} (waiting)")
            data_arrays.append(pct_w)
            colors.append(waiting_col)
            names.append(f"{s} (service)")
            data_arrays.append(pct_s)
            colors.append(service_col)

        if ax is None:
            fig, ax = plt.subplots(figsize=(10, 4))
        else:
            fig = ax.figure
        ax.stackplot(times, np.vstack(data_arrays), labels=names, colors=colors)
        ax.set_xlabel('Time (hr)')
        ax.set_ylabel('Percent (%)')
        ax.legend(loc='upper left', ncol=2)
        ax.set_ylim(0, 100)
        ax.set_title('Percent of in-system by state (waiting vs service)')
        return fig, ax
    times, pct = average_state_percent(res, exclude_terminal=exclude_terminal)
    if not pct:
        raise ValueError('no states to plot after filtering')
    return plot_state_percent(times, pct, ax=ax)


def plot_resource_occupancy_result(res: Result, mode: str = "mean", ax=None):
    if mode != "mean":
        raise ValueError("Only mode='mean' is supported currently")
    occ = average_resource_occupancy(res)
    # capacity can't be averaged robustly without assumptions; omit for mean view
    return plot_resource_occupancy(occ, resource_metrics=None, ax=ax)
