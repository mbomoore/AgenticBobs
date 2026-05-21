"""Tests for the unified `diagnose()` surface — feeds it a healthy graph
and a deliberately-broken one and asserts the right issue classes surface."""

from agentic_process_automation.core.unified_spec.diagnose import (
    DiagnosticReport,
    diagnose,
)
from agentic_process_automation.core.unified_spec.models import (
    Combinator,
    ExecutionBinding,
    ExecutionRule,
    View,
    WorkGraph,
    WorkUnit,
)


def _healthy_graph() -> WorkGraph:
    return WorkGraph(
        name="Healthy",
        case_schema={"rfps": {"id": "int"}, "scores": {}, "decisions": {}},
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
                write_set=["scores.v"],
            ),
            WorkUnit(
                name="approve",
                params={},
                inputs=["score_results"],
                outputs=["decision_results"],
                preconditions="True",
                done="SELECT 1 FROM decisions",
                write_set=["decisions.x"],
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


def _broken_graph() -> WorkGraph:
    """One WorkUnit unreachable (no incoming view), two adjacent maps,
    plus two overlapping non-disjoint bindings on `score`."""
    return WorkGraph(
        name="Broken",
        case_schema={"rfps": {"id": "int"}, "scores": {}},
        views=[
            View(name="new_rfps", reads=["SELECT * FROM rfps"], writes=[]),
            View(name="score_results", reads=["SELECT * FROM scores"], writes=["scores.v"]),
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
                name="orphan",
                params={},
                inputs=[],
                outputs=[],
                preconditions="True",
                done="True",
            ),
        ],
        combinators=[
            Combinator(type="map", work_unit="score", over="new_rfps"),
            Combinator(type="map", work_unit="orphan", over="new_rfps"),
        ],
        execution_bindings=[
            ExecutionBinding(
                target="score",
                rules=[ExecutionRule(condition="value > 100000", impl_kind="human")],
            ),
            ExecutionBinding(
                target="score",
                rules=[ExecutionRule(condition="status = 'new'", impl_kind="agent")],
            ),
        ],
    )


def test_diagnose_returns_report():
    report = diagnose(_healthy_graph(), run_reachability=False)
    assert isinstance(report, DiagnosticReport)
    assert report.work_graph_name == "Healthy"


def test_diagnose_healthy_graph_has_no_lint_or_routing_issues():
    report = diagnose(_healthy_graph(), run_reachability=False)
    assert report.lint_issues == []
    assert report.routing_issues == []


def test_diagnose_finds_lint_issues_on_broken_graph():
    report = diagnose(_broken_graph(), run_reachability=False)
    kinds = {issue.kind for issue in report.lint_issues}
    assert "SINK_WU" in kinds or "UNREACHABLE_WU" in kinds


def test_diagnose_finds_routing_ambiguity_on_broken_graph():
    report = diagnose(_broken_graph(), run_reachability=False)
    assert len(report.routing_issues) >= 1
    assert any(issue.target == "score" for issue in report.routing_issues)


def test_diagnose_finds_combinator_fusion_on_broken_graph():
    """Two adjacent maps over the same source should surface as fusion bait."""
    report = diagnose(_broken_graph(), run_reachability=False)
    assert any(
        op.kind == "map_map_fuse" for op in report.fusion_opportunities
    )


def test_diagnose_bottlenecks_on_healthy_graph_picks_human_step():
    report = diagnose(_healthy_graph(), run_reachability=False)
    assert report.bottlenecks
    assert report.bottlenecks[0].work_unit == "approve"
    assert report.bottlenecks[0].expected_time_hours > 0


def test_summary_lists_each_section():
    text = diagnose(_broken_graph(), run_reachability=False).summary()
    assert "WorkGraph 'Broken'" in text
    assert "lint issues" in text
    assert "routing ambiguities" in text
    assert "fusion opportunities" in text


def test_is_clean_distinguishes_healthy_from_broken():
    assert diagnose(_healthy_graph(), run_reachability=False).is_clean()
    assert not diagnose(_broken_graph(), run_reachability=False).is_clean()
