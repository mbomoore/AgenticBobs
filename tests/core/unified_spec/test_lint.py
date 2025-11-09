import pytest
from src.agentic_process_automation.core.unified_spec.lint import lint_static, LintIssue
from src.agentic_process_automation.core.unified_spec.models import Spec, View, WorkUnit

def test_lint_static_view_invariant_mutation():
    """A read-only view declares a mutation-like invariant."""
    spec = Spec(
        views={"v1": View(name="v1", reads=["a"], writes=[], invariants=["update a"])},
        work_units={},
    )
    issues = lint_static(spec)
    assert any(issue.kind == "VIEW_INVARIANT_MUTATION" for issue in issues)

def test_lint_static_write_outside_view():
    """A work unit's write_set is not a subset of its output views' writes."""
    spec = Spec(
        views={"v1": View(name="v1", reads=[], writes=["a"])},
        work_units={
            "wu1": WorkUnit(
                name="wu1",
                params={},
                inputs=[],
                outputs=["v1"],
                preconditions="True",
                done="False",
                write_set=["b"],
            )
        },
    )
    issues = lint_static(spec)
    assert any(issue.kind == "WRITE_OUTSIDE_VIEW" for issue in issues)

def test_lint_static_side_effect_policy_weak():
    """A work unit with side-effects has a weak conflict policy."""
    spec = Spec(
        views={},
        work_units={
            "wu1": WorkUnit(
                name="wu1",
                params={},
                inputs=[],
                outputs=[],
                preconditions="True",
                done="False",
                side_effects="external_io",
                conflict_policy="merge",
            )
        },
    )
    issues = lint_static(spec)
    assert any(issue.kind == "SIDE_EFFECT_POLICY_WEAK" for issue in issues)

def test_lint_static_unreachable_wu():
    """A work unit has no incoming views."""
    spec = Spec(
        views={"v1": View(name="v1", reads=[], writes=[])},
        work_units={"wu1": WorkUnit(name="wu1", params={}, inputs=[], outputs=["v1"], preconditions="True", done="False")},
    )
    issues = lint_static(spec)
    assert any(issue.kind == "UNREACHABLE_WU" for issue in issues)

def test_lint_static_sink_wu():
    """A work unit produces no views consumed downstream."""
    spec = Spec(
        views={"v1": View(name="v1", reads=[], writes=[])},
        work_units={"wu1": WorkUnit(name="wu1", params={}, inputs=["v1"], outputs=[], preconditions="True", done="False")},
    )
    issues = lint_static(spec)
    assert any(issue.kind == "SINK_WU" for issue in issues)

def test_lint_static_cycle_no_measure():
    """Cyclic work units without a termination measure."""
    spec = Spec(
        views={
            "v1": View(name="v1", reads=[], writes=[]),
            "v2": View(name="v2", reads=[], writes=[]),
        },
        work_units={
            "wu1": WorkUnit(name="wu1", params={}, inputs=["v1"], outputs=["v2"], preconditions="True", done="False"),
            "wu2": WorkUnit(name="wu2", params={}, inputs=["v2"], outputs=["v1"], preconditions="True", done="False"),
        },
    )
    issues = lint_static(spec)
    assert any(issue.kind == "CYCLE_NO_MEASURE" for issue in issues)
