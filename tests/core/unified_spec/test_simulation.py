"""Tests for the WorkGraph simulator, the Markov layer, the steady-state
helpers, and binding-aware cost weighting.

Includes a cross-check against the legacy `sim/core.py` Markov engine to
prove the port preserves the math.
"""

import math

import numpy as np
import pytest

from agentic_process_automation.core.sim.core import ProcessModel, State as LegacyState
from agentic_process_automation.core.unified_spec.models import (
    ExecutionBinding,
    ExecutionRule,
    View,
    WorkGraph,
    WorkUnit,
)
from agentic_process_automation.core.unified_spec.simulation import (
    ExecutorCost,
    SteadyStateReport,
    WGState,
    WGTransition,
    WorkGraphProcessModel,
    cost_for_work_unit,
    detect_warmup_index,
    is_stationary,
    moving_avg,
    sliding_slope,
    state_visits,
    transition_matrix,
)
from agentic_process_automation.core.unified_spec.simulation.steady_state import (
    steady_state_report,
)


# ---------- Markov visitation (direct) ----------


def test_transition_matrix_shape_and_values():
    states = [WGState("A"), WGState("B"), WGState("Done")]
    transitions = [
        WGTransition("A", "B", 0.7),
        WGTransition("A", "Done", 0.3),
        WGTransition("B", "Done", 1.0),
    ]
    P = transition_matrix(states, transitions)
    assert P.shape == (3, 3)
    np.testing.assert_allclose(P[0], [0.0, 0.7, 0.3])
    np.testing.assert_allclose(P[1], [0.0, 0.0, 1.0])
    np.testing.assert_allclose(P[2], [0.0, 0.0, 0.0])


def test_state_visits_on_three_state_absorbing_chain():
    """A → B (p=0.7), A → Done (p=0.3), B → Done (p=1.0).

    Expected raw counts from (I-P)^{-1}: visit(A) = 1, visit(B) = 0.7,
    visit(Done) = 1.0.
    """
    states = [WGState("A"), WGState("B"), WGState("Done")]
    transitions = [
        WGTransition("A", "B", 0.7),
        WGTransition("A", "Done", 0.3),
        WGTransition("B", "Done", 1.0),
    ]
    visits = dict(
        (s.name, v) for s, v in state_visits(states, transitions, starting_index=0)
    )
    assert math.isclose(visits["A"], 1.0, abs_tol=1e-9)
    assert math.isclose(visits["B"], 0.7, abs_tol=1e-9)
    assert math.isclose(visits["Done"], 1.0, abs_tol=1e-9)


def test_state_visits_matches_legacy_process_model():
    """Cross-check: the new Markov layer agrees with sim/core.py to 1e-9."""
    p_legacy = ProcessModel("legacy")
    with p_legacy:
        a = LegacyState("A")
        b = LegacyState("B")
        success = LegacyState("Success")
        p_legacy.add_transition(a >> 0.6 >> b)
        p_legacy.add_transition(a >> 0.4 >> success)
        p_legacy.add_transition(b >> 1.0 >> success)
    legacy_visits = {s.name: v for s, v in p_legacy.state_visits()}

    states = [WGState("A"), WGState("B"), WGState("Success")]
    transitions = [
        WGTransition("A", "B", 0.6),
        WGTransition("A", "Success", 0.4),
        WGTransition("B", "Success", 1.0),
    ]
    new_visits = {
        s.name: v
        for s, v in state_visits(
            states, transitions, starting_index=0, success_state_name="Success"
        )
    }

    for name in legacy_visits:
        assert math.isclose(legacy_visits[name], new_visits[name], abs_tol=1e-9), name


# ---------- WorkGraphProcessModel inference ----------


def _scoring_workgraph() -> WorkGraph:
    return WorkGraph(
        name="Score and Approve",
        case_schema={"rfps": {"id": "int"}, "scores": {"v": "float"}, "decisions": {}},
        views=[
            View(name="new_rfps", reads=["SELECT * FROM rfps"], writes=[]),
            View(name="score_results", reads=["SELECT * FROM scores"], writes=["scores.v"]),
            View(name="decision_results", reads=["SELECT * FROM decisions"], writes=["decisions.x"]),
        ],
        work_units=[
            WorkUnit(
                name="score",
                params={},
                inputs=["new_rfps"],
                outputs=["score_results"],
                preconditions="True",
                done="SELECT 1 FROM scores",
            ),
            WorkUnit(
                name="approve",
                params={},
                inputs=["score_results"],
                outputs=["decision_results"],
                preconditions="True",
                done="SELECT 1 FROM decisions",
            ),
        ],
        execution_bindings=[
            ExecutionBinding(
                target="score",
                rules=[ExecutionRule(condition="True", impl_kind="agent")],
            ),
            ExecutionBinding(
                target="approve",
                rules=[ExecutionRule(condition="True", impl_kind="human")],
            ),
        ],
    )


def test_from_work_graph_infers_view_dependency_chain():
    wg = _scoring_workgraph()
    model = WorkGraphProcessModel.from_work_graph(wg)

    names = [s.name for s in model.states]
    assert names == ["score", "approve", "Done"]

    succ_score = sorted(
        (t.to_state, round(t.prob, 6))
        for t in model.transitions
        if t.from_state == "score"
    )
    assert succ_score == [("approve", 1.0)]
    succ_approve = [
        (t.to_state, round(t.prob, 6))
        for t in model.transitions
        if t.from_state == "approve"
    ]
    assert succ_approve == [("Done", 1.0)]


def test_transition_hints_override_uniform_default():
    wg = WorkGraph(
        name="Branch",
        case_schema={},
        views=[
            View(name="A_view", writes=["A.x"]),
            View(name="B_view", reads=["A.x"]),
            View(name="C_view", reads=["A.x"]),
        ],
        work_units=[
            WorkUnit(name="A", params={}, inputs=[], outputs=["A_view"], preconditions="True", done="True"),
            WorkUnit(name="B", params={}, inputs=["A_view"], outputs=[], preconditions="True", done="True"),
            WorkUnit(name="C", params={}, inputs=["A_view"], outputs=[], preconditions="True", done="True"),
        ],
    )

    model = WorkGraphProcessModel.from_work_graph(
        wg, transition_hints={("A", "B"): 0.8, ("A", "C"): 0.2}
    )
    branch_probs = {
        t.to_state: t.prob for t in model.transitions if t.from_state == "A"
    }
    assert math.isclose(branch_probs["B"], 0.8, abs_tol=1e-9)
    assert math.isclose(branch_probs["C"], 0.2, abs_tol=1e-9)


def test_bottleneck_shifts_when_binding_flips_to_agent():
    """Flipping the slow human-bound `approve` step to an agent moves the
    bottleneck to `score`. This is the headline use case for the copilot."""
    wg = _scoring_workgraph()
    model_human = WorkGraphProcessModel.from_work_graph(wg).annotate_with_costs(wg)
    bottlenecks_human = model_human.bottlenecks(starting_state="score", top_k=2)
    assert bottlenecks_human[0][0] == "approve"

    wg.execution_bindings[1].rules[0].impl_kind = "agent"
    model_all_agent = WorkGraphProcessModel.from_work_graph(wg).annotate_with_costs(wg)
    bottlenecks_agent = model_all_agent.bottlenecks(starting_state="score", top_k=2)
    assert bottlenecks_agent[0][1] < bottlenecks_human[0][1]


def test_expected_total_cost_changes_with_binding():
    wg = _scoring_workgraph()
    cost_with_human = (
        WorkGraphProcessModel.from_work_graph(wg)
        .annotate_with_costs(wg)
        .expected_total_cost(starting_state="score")
    )
    wg.execution_bindings[1].rules[0].impl_kind = "agent"
    cost_all_agent = (
        WorkGraphProcessModel.from_work_graph(wg)
        .annotate_with_costs(wg)
        .expected_total_cost(starting_state="score")
    )
    assert cost_all_agent < cost_with_human


def test_process_model_rejects_bad_row_sums():
    with pytest.raises(ValueError):
        WorkGraphProcessModel(
            states=[WGState("A"), WGState("Done")],
            transitions=[WGTransition("A", "Done", 0.5)],
        )


# ---------- Binding-aware costs ----------


def test_cost_for_work_unit_picks_human_binding():
    wg = _scoring_workgraph()
    cost = cost_for_work_unit(wg, "approve")
    assert cost.impl_kind == "human"
    assert cost.expected_duration_hours > 0


def test_cost_overrides_take_precedence():
    wg = _scoring_workgraph()
    cost = cost_for_work_unit(
        wg,
        "score",
        overrides={
            "agent": ExecutorCost(
                impl_kind="agent",
                expected_duration_hours=0.1,
                cost_per_invocation=1.0,
            )
        },
    )
    assert cost.expected_duration_hours == 0.1
    assert cost.cost_per_invocation == 1.0


def test_cost_for_unknown_work_unit_falls_back_to_agent():
    wg = _scoring_workgraph()
    cost = cost_for_work_unit(wg, "nonexistent")
    assert cost.impl_kind == "agent"


# ---------- Steady-state primitives ----------


def test_moving_avg_basic():
    out = moving_avg([1.0, 2.0, 3.0, 4.0, 5.0], window=3)
    assert len(out) == 5
    assert math.isclose(out[-1], 4.0, abs_tol=1e-9)


def test_sliding_slope_constant_series_has_zero_slope():
    xs = [float(i) for i in range(10)]
    ys = [5.0] * 10
    slopes = sliding_slope(xs, ys, window=4)
    assert all(abs(s) < 1e-9 for s in slopes if s != 0.0)


def test_detect_warmup_finds_late_stabilisation():
    times = [float(i) for i in range(100)]
    rising = [min(1.0, 0.02 * i) for i in range(100)]
    idx = detect_warmup_index(times, rising, window=10)
    assert 30 <= idx <= 80


def test_is_stationary_on_stable_tail():
    times = [float(i) for i in range(120)]
    series = [0.5 + (0.001 if i < 60 else 0.0) for i in range(120)]
    assert is_stationary(times, series, window=10) is True


def test_steady_state_report_aggregates_per_role():
    times = [float(i) for i in range(120)]
    occ = {
        "human": [min(2.0, 0.05 * i) for i in range(120)],
        "agent": [min(0.5, 0.01 * i) for i in range(120)],
    }
    report = steady_state_report(
        times,
        occ,
        capacity_by_role={"human": 3.0, "agent": 1.0},
    )
    assert isinstance(report, SteadyStateReport)
    assert set(report.per_role.keys()) == {"human", "agent"}
    assert report.per_role["human"]["avg_occupancy"] > 0
    assert report.per_role["human"]["utilization"] <= 1.0
