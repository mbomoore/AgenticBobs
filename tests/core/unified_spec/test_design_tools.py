"""Tests for the design-copilot tool palette."""

from copy import deepcopy

from agentic_process_automation.core.unified_spec.design_tools import (
    SimulationResult,
    WorkGraphSummary,
    diagnose_workgraph,
    find_bottleneck,
    inspect_workgraph,
    propose_binding_change,
    simulate_under_binding,
    suggest_combinator,
)
from agentic_process_automation.core.unified_spec.models import (
    Combinator,
    ExecutionBinding,
    ExecutionRule,
    View,
    WorkGraph,
    WorkUnit,
)


def _two_step_graph(approve_impl: str = "human") -> WorkGraph:
    return WorkGraph(
        name="Demo",
        case_schema={"rfps": {"id": "int"}, "scores": {}, "decisions": {}},
        views=[
            View(name="new_rfps", reads=["SELECT * FROM rfps"], writes=[]),
            View(name="score_results", reads=["SELECT * FROM scores"], writes=["scores.v"]),
            View(name="decision_results", reads=["SELECT * FROM decisions"], writes=["decisions.x"]),
        ],
        work_units=[
            WorkUnit(
                name="triage", params={}, inputs=["new_rfps"], outputs=["score_results"],
                preconditions="True", done="SELECT 1 FROM scores",
                write_set=["scores.v"],
            ),
            WorkUnit(
                name="approve", params={}, inputs=["score_results"], outputs=["decision_results"],
                preconditions="True", done="SELECT 1 FROM decisions",
                write_set=["decisions.x"],
            ),
        ],
        execution_bindings=[
            ExecutionBinding(
                target="triage",
                rules=[ExecutionRule(condition="True", impl_kind="agent")],
            ),
            ExecutionBinding(
                target="approve",
                rules=[ExecutionRule(condition="True", impl_kind=approve_impl)],
            ),
        ],
    )


# ---------- inspect_workgraph ----------


def test_inspect_summarises_work_units_and_bindings():
    summary = inspect_workgraph(_two_step_graph())
    assert isinstance(summary, WorkGraphSummary)
    assert summary.n_work_units == 2
    assert summary.n_bindings == 2
    impls = {wu.name: wu.impl_kind for wu in summary.work_units}
    assert impls == {"triage": "agent", "approve": "human"}


def test_inspect_flags_unbound_work_units():
    wg = _two_step_graph()
    wg.execution_bindings = [wg.execution_bindings[0]]  # drop the approve binding
    summary = inspect_workgraph(wg)
    assert "approve" in summary.unbound_work_units


# ---------- diagnose_workgraph ----------


def test_diagnose_workgraph_returns_clean_report_on_healthy_graph():
    report = diagnose_workgraph(_two_step_graph())
    assert report.lint_issues == []
    assert report.routing_issues == []


# ---------- simulate_under_binding ----------


def test_simulate_returns_bottlenecks_and_cost():
    result = simulate_under_binding(_two_step_graph())
    assert isinstance(result, SimulationResult)
    assert result.starting_state == "triage"
    assert result.expected_total_cost > 0
    assert result.bottlenecks[0].work_unit == "approve"
    assert "Done" in result.per_state_visits


def test_find_bottleneck_extracts_names():
    result = simulate_under_binding(_two_step_graph())
    names = find_bottleneck(result)
    assert names[0] == "approve"


# ---------- propose_binding_change ----------


def test_propose_binding_change_does_not_mutate_input():
    wg = _two_step_graph()
    original_impl = wg.execution_bindings[1].rules[0].impl_kind
    candidate = propose_binding_change(wg, "approve", "agent")
    assert wg.execution_bindings[1].rules[0].impl_kind == original_impl
    assert candidate is not wg
    assert candidate.execution_bindings[1].rules[0].impl_kind == "agent"


def test_propose_binding_change_adds_binding_when_missing():
    wg = _two_step_graph()
    wg.execution_bindings = [wg.execution_bindings[0]]
    candidate = propose_binding_change(wg, "approve", "agent")
    approve_bindings = [
        b for b in candidate.execution_bindings if b.target == "approve"
    ]
    assert len(approve_bindings) == 1


def test_propose_binding_change_rejects_unknown_work_unit():
    try:
        propose_binding_change(_two_step_graph(), "nonexistent", "agent")
    except ValueError:
        return
    raise AssertionError("expected ValueError for unknown work_unit")


def test_propose_binding_change_rejects_invalid_impl_kind():
    try:
        propose_binding_change(_two_step_graph(), "approve", "spaceship")
    except ValueError:
        return
    raise AssertionError("expected ValueError for invalid impl_kind")


# ---------- end-to-end before/after comparison ----------


def test_flipping_bottleneck_reduces_total_cost_and_duration():
    wg = _two_step_graph()
    before = simulate_under_binding(wg)
    worst = before.bottlenecks[0].work_unit
    candidate = propose_binding_change(wg, worst, "agent")
    after = simulate_under_binding(candidate)
    assert after.expected_total_cost < before.expected_total_cost
    assert after.expected_total_duration_hours < before.expected_total_duration_hours


# ---------- suggest_combinator ----------


def test_suggest_combinator_returns_none_when_no_combinators():
    assert suggest_combinator(_two_step_graph(), "new_rfps") is None


def test_suggest_combinator_finds_adjacent_map_fusion():
    wg = _two_step_graph()
    wg.combinators = [
        Combinator(type="map", work_unit="triage", over="new_rfps"),
        Combinator(type="map", work_unit="approve", over="new_rfps"),
    ]
    opportunity = suggest_combinator(wg, "new_rfps")
    assert opportunity is not None
    assert opportunity.kind == "map_map_fuse"
