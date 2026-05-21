"""
Tool palette for the process-design copilot.

Each function in this module is a self-contained "tool" call:
- typed in and out (Pydantic models or simple primitives)
- side-effect-free unless explicitly named otherwise
- a one-line docstring an LLM can use as a tool description

This module exists so wiring the copilot to the unified-spec runtime is
a matter of binding these functions to an agent framework (Agent SDK,
MCP, function calling) — not re-inventing the math.

Everything heavy lives in the Phase 1–4 modules; this file only
composes them and shapes the I/O.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from agentic_process_automation.core.unified_spec.combinator_algebra import (
    FusionOpportunity,
    find_fusions,
)
from agentic_process_automation.core.unified_spec.diagnose import (
    Bottleneck,
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
from agentic_process_automation.core.unified_spec.simulation import (
    ExecutorCost,
    WorkGraphProcessModel,
)


# ---------- Inspect ----------


class WorkUnitSummary(BaseModel):
    name: str
    goal_tag: Optional[str]
    impl_kind: Optional[str]
    inputs: List[str]
    outputs: List[str]


class WorkGraphSummary(BaseModel):
    name: str
    n_views: int
    n_work_units: int
    n_combinators: int
    n_bindings: int
    work_units: List[WorkUnitSummary]
    unbound_work_units: List[str] = Field(
        default_factory=list,
        description="WorkUnits with no ExecutionBinding — themselves a design problem.",
    )


def inspect_workgraph(work_graph: WorkGraph) -> WorkGraphSummary:
    """Return a structural summary of a WorkGraph for the copilot to reason over."""
    bound_targets = {b.target for b in work_graph.execution_bindings}
    summaries: List[WorkUnitSummary] = []
    unbound: List[str] = []
    for wu in work_graph.work_units:
        rule = _first_rule_for(work_graph, wu)
        impl = rule.impl_kind if rule else None
        if impl is None and wu.name not in bound_targets and (
            wu.goal_tag is None or wu.goal_tag not in bound_targets
        ):
            unbound.append(wu.name)
        summaries.append(
            WorkUnitSummary(
                name=wu.name,
                goal_tag=wu.goal_tag,
                impl_kind=impl,
                inputs=list(wu.inputs),
                outputs=list(wu.outputs),
            )
        )
    return WorkGraphSummary(
        name=work_graph.name,
        n_views=len(work_graph.views),
        n_work_units=len(work_graph.work_units),
        n_combinators=len(work_graph.combinators),
        n_bindings=len(work_graph.execution_bindings),
        work_units=summaries,
        unbound_work_units=unbound,
    )


# ---------- Diagnose (thin wrapper) ----------


def diagnose_workgraph(
    work_graph: WorkGraph, *, run_reachability: bool = False
) -> DiagnosticReport:
    """Run the full diagnostic pass over a WorkGraph (see diagnose.py)."""
    return diagnose(work_graph, run_reachability=run_reachability)


# ---------- Simulate ----------


class SimulationResult(BaseModel):
    work_graph_name: str
    starting_state: str
    expected_total_cost: float
    expected_total_duration_hours: float
    bottlenecks: List[Bottleneck]
    per_state_visits: Dict[str, float]


def simulate_under_binding(
    work_graph: WorkGraph,
    *,
    cost_overrides: Optional[Dict[str, ExecutorCost]] = None,
    transition_hints: Optional[Dict[Tuple[str, str], float]] = None,
    starting_state: Optional[str] = None,
    top_bottlenecks: int = 3,
) -> SimulationResult:
    """Run the Markov simulator with the current bindings (or overrides)."""
    from agentic_process_automation.core.unified_spec.simulation.markov import (
        state_visits,
    )

    entry = starting_state or _infer_entry(work_graph)
    if entry is None:
        raise ValueError("Cannot simulate: WorkGraph has no work_units")

    model = WorkGraphProcessModel.from_work_graph(
        work_graph, transition_hints=transition_hints
    ).annotate_with_costs(work_graph, overrides=cost_overrides)

    visits = state_visits(model.states, model.transitions, model.index_of(entry))
    bottleneck_pairs = model.bottlenecks(starting_state=entry, top_k=top_bottlenecks)

    return SimulationResult(
        work_graph_name=work_graph.name,
        starting_state=entry,
        expected_total_cost=model.expected_total_cost(starting_state=entry),
        expected_total_duration_hours=sum(
            s.expected_duration_hours * v for s, v in visits if s.name != "Done"
        ),
        bottlenecks=[
            Bottleneck(work_unit=name, expected_time_hours=h)
            for name, h in bottleneck_pairs
        ],
        per_state_visits={s.name: v for s, v in visits},
    )


def find_bottleneck(sim_result: SimulationResult) -> List[str]:
    """Extract just the work-unit names from a simulation result, slowest first."""
    return [b.work_unit for b in sim_result.bottlenecks]


# ---------- Propose ----------


def propose_binding_change(
    work_graph: WorkGraph,
    work_unit_name: str,
    new_impl_kind: str,
) -> WorkGraph:
    """
    Return a deep-copied WorkGraph with `work_unit_name`'s first binding rule
    switched to `new_impl_kind`. Does NOT mutate the input — the copilot
    should diff the candidate against the original and present both.
    """
    if new_impl_kind not in {"human", "agent", "hybrid"}:
        raise ValueError(f"new_impl_kind must be human|agent|hybrid, got {new_impl_kind!r}")

    candidate = deepcopy(work_graph)
    wu = next((w for w in candidate.work_units if w.name == work_unit_name), None)
    if wu is None:
        raise ValueError(f"WorkUnit {work_unit_name!r} not in WorkGraph")

    targets = {work_unit_name}
    if wu.goal_tag:
        targets.add(wu.goal_tag)

    changed = False
    for binding in candidate.execution_bindings:
        if binding.target in targets and binding.rules:
            binding.rules[0].impl_kind = new_impl_kind
            changed = True
            break

    if not changed:
        candidate.execution_bindings.append(
            ExecutionBinding(
                target=work_unit_name,
                rules=[ExecutionRule(condition="True", impl_kind=new_impl_kind)],
            )
        )

    return candidate


def suggest_combinator(
    work_graph: WorkGraph, view_name: str
) -> Optional[FusionOpportunity]:
    """If the WorkGraph already has combinators over `view_name` that could be
    fused, return the first fusion opportunity. Used by the copilot to spot
    pipelines the user has open-coded as parallel maps."""
    related = [c for c in work_graph.combinators if c.over == view_name]
    if len(related) < 2:
        return None
    fusions = find_fusions(related)
    return fusions[0] if fusions else None


# ---------- helpers ----------


def _first_rule_for(work_graph: WorkGraph, wu: WorkUnit) -> Optional[ExecutionRule]:
    targets = {wu.name}
    if wu.goal_tag:
        targets.add(wu.goal_tag)
    for binding in work_graph.execution_bindings:
        if binding.target in targets and binding.rules:
            return binding.rules[0]
    return None


def _infer_entry(work_graph: WorkGraph) -> Optional[str]:
    for wu in work_graph.work_units:
        if not wu.inputs:
            return wu.name
    return work_graph.work_units[0].name if work_graph.work_units else None
