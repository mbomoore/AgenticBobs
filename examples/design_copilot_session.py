"""
End-to-end demonstration of the process-design copilot's tool palette.

Loads an RFP-triage WorkGraph, runs the full diagnostic surface, identifies
the bottleneck, proposes flipping that step's binding from human to agent,
and prints a before/after table.

Run with:
    uv run python examples/design_copilot_session.py
"""

from __future__ import annotations

from agentic_process_automation.core.unified_spec.design_tools import (
    diagnose_workgraph,
    find_bottleneck,
    inspect_workgraph,
    propose_binding_change,
    simulate_under_binding,
    suggest_combinator,
)
from agentic_process_automation.core.unified_spec.models import (
    ExecutionBinding,
    ExecutionRule,
    View,
    WorkGraph,
    WorkUnit,
)


def build_demo_workgraph() -> WorkGraph:
    """A small, self-contained RFP triage graph with a human bottleneck."""
    return WorkGraph(
        name="RFP Triage Demo",
        case_schema={
            "rfps": {"id": "int", "value": "int", "status": "str"},
            "scores": {"rfp_id": "int", "v": "float"},
            "decisions": {"rfp_id": "int", "outcome": "str"},
        },
        views=[
            View(name="new_rfps", reads=["SELECT * FROM rfps"], writes=[]),
            View(
                name="score_results",
                reads=["SELECT * FROM scores"],
                writes=["scores.v"],
            ),
            View(
                name="decision_results",
                reads=["SELECT * FROM decisions"],
                writes=["decisions.outcome"],
            ),
        ],
        work_units=[
            WorkUnit(
                name="triage",
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
                write_set=["decisions.outcome"],
            ),
        ],
        execution_bindings=[
            ExecutionBinding(
                target="triage",
                rules=[ExecutionRule(condition="True", impl_kind="agent")],
            ),
            ExecutionBinding(
                target="approve",
                rules=[ExecutionRule(condition="True", impl_kind="human")],
            ),
        ],
    )


def _print_summary(wg: WorkGraph) -> None:
    summary = inspect_workgraph(wg)
    print(f"  name         : {summary.name}")
    print(f"  work units   : {summary.n_work_units}")
    print(f"  bindings     : {summary.n_bindings}")
    if summary.unbound_work_units:
        print(f"  unbound WUs  : {summary.unbound_work_units}")
    for wu in summary.work_units:
        print(f"    - {wu.name:12} impl={wu.impl_kind:>6}  inputs={wu.inputs}")


def _print_diagnostics(wg: WorkGraph) -> None:
    report = diagnose_workgraph(wg)
    print(report.summary())
    if report.routing_issues:
        for ri in report.routing_issues:
            print(f"    ! routing: {ri.message}")
    if report.fusion_opportunities:
        for op in report.fusion_opportunities:
            print(f"    > fusion ({op.kind}): {op.rationale}")


def _print_sim_comparison(before, after) -> None:
    print(
        f"  {'state':<14} {'visits':>8} {'before(h)':>10} {'after(h)':>10}"
    )
    all_states = sorted(set(before.per_state_visits) | set(after.per_state_visits))
    for name in all_states:
        v = before.per_state_visits.get(name, 0.0)
        b_t = next(
            (b.expected_time_hours for b in before.bottlenecks if b.work_unit == name),
            0.0,
        )
        a_t = next(
            (b.expected_time_hours for b in after.bottlenecks if b.work_unit == name),
            0.0,
        )
        print(f"  {name:<14} {v:>8.3f} {b_t:>10.3f} {a_t:>10.3f}")
    print(
        f"  TOTAL          {' ':>8} {before.expected_total_duration_hours:>10.3f} "
        f"{after.expected_total_duration_hours:>10.3f}"
    )
    print(
        f"  COST $         {' ':>8} {before.expected_total_cost:>10.2f} "
        f"{after.expected_total_cost:>10.2f}"
    )


def main() -> None:
    wg = build_demo_workgraph()

    print("\n=== 1. Inspect the draft graph ===")
    _print_summary(wg)

    print("\n=== 2. Diagnose ===")
    _print_diagnostics(wg)

    print("\n=== 3. Simulate under current bindings ===")
    before = simulate_under_binding(wg)
    print(f"  bottlenecks (worst first): {find_bottleneck(before)}")
    print(f"  expected total cost      : ${before.expected_total_cost:.2f}")
    print(
        f"  expected total duration  : {before.expected_total_duration_hours:.2f}h"
    )

    print("\n=== 4. Propose: flip the slow human step to agent ===")
    worst = before.bottlenecks[0].work_unit
    print(f"  bottleneck = {worst!r} — proposing impl_kind='agent'")
    candidate = propose_binding_change(wg, worst, "agent")

    print("\n=== 5. Simulate candidate ===")
    after = simulate_under_binding(candidate)

    print("\n=== 6. Comparison ===")
    _print_sim_comparison(before, after)

    print("\n=== 7. suggest_combinator demo ===")
    suggestion = suggest_combinator(wg, "new_rfps")
    if suggestion:
        print(f"  found {suggestion.kind}: {suggestion.rationale}")
    else:
        print("  no fusion opportunity for 'new_rfps' in this graph")

    print("\nSession complete.")


if __name__ == "__main__":
    main()
