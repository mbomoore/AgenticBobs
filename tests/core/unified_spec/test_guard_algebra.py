"""Tests for the guard algebra: parse, to_sql, implies, disjoint, and the
Dispatcher routing-consistency check."""

from agentic_process_automation.core.unified_spec import guard_algebra
from agentic_process_automation.core.unified_spec.dispatcher import (
    Dispatcher,
    RoutingIssue,
)
from agentic_process_automation.core.unified_spec.guard_algebra import (
    And_,
    Atom,
    FalseLit,
    Not_,
    Or_,
    TrueLit,
)
from agentic_process_automation.core.unified_spec.models import (
    ExecutionBinding,
    ExecutionRule,
    WorkGraph,
    WorkUnit,
)


# ---------- parser ----------


def test_parse_true_false_literals():
    assert guard_algebra.parse("True") == TrueLit()
    assert guard_algebra.parse("False") == FalseLit()


def test_parse_numeric_comparison():
    assert guard_algebra.parse("value > 100000") == Atom("value", ">", 100000)


def test_parse_string_equality():
    assert guard_algebra.parse("status = 'new'") == Atom("status", "=", "new")


def test_parse_and_or_not_with_parens():
    expr = guard_algebra.parse(
        "value > 100000 AND (status = 'new' OR NOT priority = 'low')"
    )
    assert isinstance(expr, And_)
    assert expr.children[0] == Atom("value", ">", 100000)
    rhs = expr.children[1]
    assert isinstance(rhs, Or_)
    assert rhs.children[0] == Atom("status", "=", "new")
    assert isinstance(rhs.children[1], Not_)
    assert rhs.children[1].child == Atom("priority", "=", "low")


def test_parse_rejects_full_select():
    try:
        guard_algebra.parse("SELECT 1 FROM rfps WHERE value > 100")
    except ValueError:
        return
    raise AssertionError("parse should reject SELECT statements")


# ---------- to_sql preserves interpreter behaviour ----------


def test_to_sql_passes_through_select():
    sql = "SELECT 1 FROM rfps WHERE status = 'new'"
    assert guard_algebra.to_sql(sql) == sql


def test_to_sql_wraps_dotted_predicate():
    assert (
        guard_algebra.to_sql("rfps.summary IS NOT NULL")
        == "SELECT 1 FROM rfps WHERE rfps.summary IS NOT NULL"
    )


def test_to_sql_rejects_predicate_without_entity():
    try:
        guard_algebra.to_sql("value > 100000")
    except ValueError:
        return
    raise AssertionError("to_sql should reject bare predicates without entity prefix")


# ---------- implies ----------


def test_implies_stronger_to_weaker_numeric():
    assert guard_algebra.implies("value > 100000", "value > 50000") is True


def test_implies_weaker_to_stronger_is_false():
    assert guard_algebra.implies("value > 50000", "value > 100000") is False


def test_implies_with_and_decomposition():
    assert (
        guard_algebra.implies(
            "value > 100000 AND status = 'new'", "status = 'new'"
        )
        is True
    )


def test_implies_returns_none_outside_fragment():
    # IS NOT NULL is outside the symbolic fragment
    assert guard_algebra.implies("rfps.summary IS NOT NULL", "True") is None


# ---------- disjoint ----------


def test_disjoint_contradictory_numeric_ranges():
    assert guard_algebra.disjoint("value > 100000", "value < 50000") is True


def test_disjoint_overlapping_ranges_is_false():
    assert guard_algebra.disjoint("value > 50000", "value < 200000") is False


def test_disjoint_contradictory_string_equality():
    assert guard_algebra.disjoint("status = 'new'", "status = 'closed'") is True


# ---------- dispatcher routing-consistency check ----------


def _two_rule_graph(cond_a: str, cond_b: str) -> WorkGraph:
    return WorkGraph(
        name="Two Rules",
        case_schema={"rfps": {"id": "int", "value": "int", "status": "str"}},
        work_units=[
            WorkUnit(
                name="handle",
                params={},
                inputs=[],
                outputs=[],
                preconditions="True",
                done="SELECT 1 FROM rfps WHERE status = 'done'",
            )
        ],
        execution_bindings=[
            ExecutionBinding(
                target="handle",
                rules=[ExecutionRule(condition=cond_a, impl_kind="human")],
            ),
            ExecutionBinding(
                target="handle",
                rules=[ExecutionRule(condition=cond_b, impl_kind="agent")],
            ),
        ],
    )


def test_dispatcher_flags_overlapping_rules():
    wg = _two_rule_graph("value > 100000", "status = 'new'")
    issues = Dispatcher(wg).check_routing_consistency()
    assert len(issues) == 1
    issue = issues[0]
    assert isinstance(issue, RoutingIssue)
    assert issue.target == "handle"
    assert {issue.a_impl, issue.b_impl} == {"human", "agent"}


def test_dispatcher_no_issue_when_rules_are_disjoint():
    wg = _two_rule_graph("value > 100000", "value < 50000")
    issues = Dispatcher(wg).check_routing_consistency()
    assert issues == []


def test_dispatcher_no_issue_when_rules_share_executor():
    wg = WorkGraph(
        name="Same Impl",
        case_schema={"rfps": {"id": "int"}},
        work_units=[
            WorkUnit(
                name="handle",
                params={},
                inputs=[],
                outputs=[],
                preconditions="True",
                done="SELECT 1 FROM rfps WHERE status = 'done'",
            )
        ],
        execution_bindings=[
            ExecutionBinding(
                target="handle",
                rules=[ExecutionRule(condition="value > 100000", impl_kind="agent")],
            ),
            ExecutionBinding(
                target="handle",
                rules=[ExecutionRule(condition="status = 'new'", impl_kind="agent")],
            ),
        ],
    )
    assert Dispatcher(wg).check_routing_consistency() == []
