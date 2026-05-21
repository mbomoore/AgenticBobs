"""
Binding-aware cost annotation.

The Markov visitation math gives expected *visit counts* per WorkUnit. To
turn that into the bottleneck signal the copilot cares about, each state
needs an expected duration and a per-invocation cost. Those numbers come
from the ExecutionBinding chosen for the WorkUnit — humans take longer and
cost differently than agents.

This module is the new piece in Phase 3 — the legacy `sim/` kernel has no
concept of binding. The defaults are intentionally crude (humans slower
and pricier than agents) so the example session has *something* to show;
the copilot is expected to override them with measured numbers.
"""

from __future__ import annotations

from typing import Dict, Optional

from pydantic import BaseModel, Field

from agentic_process_automation.core.unified_spec.models import (
    ExecutionRule,
    WorkGraph,
)


class ExecutorCost(BaseModel):
    impl_kind: str = Field(..., description="human | agent | hybrid")
    expected_duration_hours: float
    cost_per_invocation: float


DEFAULT_COSTS: Dict[str, ExecutorCost] = {
    "human": ExecutorCost(impl_kind="human", expected_duration_hours=2.0, cost_per_invocation=100.0),
    "agent": ExecutorCost(impl_kind="agent", expected_duration_hours=0.05, cost_per_invocation=0.50),
    "hybrid": ExecutorCost(impl_kind="hybrid", expected_duration_hours=0.5, cost_per_invocation=20.0),
}


def cost_for_work_unit(
    work_graph: WorkGraph,
    work_unit_name: str,
    *,
    overrides: Optional[Dict[str, ExecutorCost]] = None,
) -> ExecutorCost:
    """
    Pick the cost profile for a WorkUnit by inspecting its ExecutionBindings.

    Strategy: take the first binding whose target matches the WorkUnit name
    (or its goal_tag), then take its first rule's impl_kind. If no binding
    is found, fall back to the agent default — the copilot should warn about
    this elsewhere (a WorkUnit with no binding is itself a design problem).
    """
    table = {**DEFAULT_COSTS, **(overrides or {})}

    wu = next((w for w in work_graph.work_units if w.name == work_unit_name), None)
    candidate_targets = {work_unit_name}
    if wu and wu.goal_tag:
        candidate_targets.add(wu.goal_tag)

    rule = _first_matching_rule(work_graph, candidate_targets)
    impl_kind = rule.impl_kind if rule else "agent"
    return table.get(impl_kind, DEFAULT_COSTS["agent"])


def _first_matching_rule(
    work_graph: WorkGraph, targets: set[str]
) -> Optional[ExecutionRule]:
    for binding in work_graph.execution_bindings:
        if binding.target in targets and binding.rules:
            return binding.rules[0]
    return None
