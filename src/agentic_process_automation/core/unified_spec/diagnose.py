"""
Unified diagnostic surface for the process-design copilot.

`diagnose(work_graph)` is the single call the copilot makes to get a
complete read-out on a draft graph. It does not invent any new checks —
it composes the four sources already in this package:

  - lint.py:lint_static            (graph reachability, write discipline,
                                    cycles without measure)
  - preflight.py:bounded_reachability / deadlock_check / quality_implies_done
  - dispatcher.py:check_routing_consistency  (ambiguous bindings,
                                    via Phase 2 guard algebra)
  - simulation.bottlenecks         (Phase 3 Markov visitation × duration)
  - combinator_algebra.find_fusions (Phase 1 simplification opportunities)

The report is intentionally Pydantic-shaped so the copilot can serialise
it directly into a chat-friendly summary or pass it to an LLM as JSON.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from agentic_process_automation.core.unified_spec import preflight
from agentic_process_automation.core.unified_spec.combinator_algebra import (
    FusionOpportunity,
    find_fusions,
)
from agentic_process_automation.core.unified_spec.dispatcher import (
    Dispatcher,
    RoutingIssue,
)
from agentic_process_automation.core.unified_spec.lint import LintIssue, lint_static
from agentic_process_automation.core.unified_spec.models import Spec, WorkGraph
from agentic_process_automation.core.unified_spec.simulation import (
    WorkGraphProcessModel,
)


class ReachabilityReport(BaseModel):
    reachable: bool
    message: str
    horizon_k: int


class Bottleneck(BaseModel):
    work_unit: str
    expected_time_hours: float


class DiagnosticReport(BaseModel):
    work_graph_name: str
    lint_issues: List[LintIssue] = Field(default_factory=list)
    routing_issues: List[RoutingIssue] = Field(default_factory=list)
    reachability: Optional[ReachabilityReport] = None
    deadlock_possible: Optional[bool] = None
    bottlenecks: List[Bottleneck] = Field(default_factory=list)
    fusion_opportunities: List[FusionOpportunity] = Field(default_factory=list)

    def is_clean(self) -> bool:
        return not (
            self.lint_issues
            or self.routing_issues
            or (self.reachability is not None and not self.reachability.reachable)
            or self.deadlock_possible
        )

    def summary(self) -> str:
        parts = [f"WorkGraph {self.work_graph_name!r}:"]
        parts.append(f"  lint issues: {len(self.lint_issues)}")
        parts.append(f"  routing ambiguities: {len(self.routing_issues)}")
        if self.reachability:
            parts.append(
                f"  reachability (K={self.reachability.horizon_k}): "
                f"{'OK' if self.reachability.reachable else 'NOT REACHABLE'}"
            )
        if self.deadlock_possible is not None:
            parts.append(
                f"  deadlock possible: "
                f"{'YES' if self.deadlock_possible else 'no'}"
            )
        if self.bottlenecks:
            top = self.bottlenecks[0]
            parts.append(
                f"  top bottleneck: {top.work_unit} "
                f"(~{top.expected_time_hours:.2f}h)"
            )
        parts.append(f"  fusion opportunities: {len(self.fusion_opportunities)}")
        return "\n".join(parts)


def diagnose(
    work_graph: WorkGraph,
    *,
    spec: Optional[Spec] = None,
    starting_state: Optional[str] = None,
    transition_hints: Optional[Dict[Tuple[str, str], float]] = None,
    run_reachability: bool = True,
    horizon_k: int = 10,
    n_rfps: int = 3,
    top_bottlenecks: int = 3,
) -> DiagnosticReport:
    """Compose all five diagnostic sources into a single report.

    `spec` is required for lint checks; if omitted, `_spec_from_work_graph`
    builds one from the WorkGraph. `starting_state` defaults to the first
    WorkUnit with no inputs (the entry point); if none exists, bottleneck
    analysis is skipped because (I-P)^(-1) needs a designated starting row.
    """
    report = DiagnosticReport(work_graph_name=work_graph.name)

    effective_spec = spec or _spec_from_work_graph(work_graph)
    report.lint_issues = lint_static(effective_spec)
    report.routing_issues = Dispatcher(work_graph).check_routing_consistency()
    report.fusion_opportunities = find_fusions(list(work_graph.combinators))

    if run_reachability:
        try:
            reachable, msg = preflight.bounded_reachability(N=n_rfps, K=horizon_k)
            report.reachability = ReachabilityReport(
                reachable=reachable, message=msg, horizon_k=horizon_k
            )
            report.deadlock_possible = preflight.deadlock_check(N=n_rfps)
        except Exception as e:
            report.reachability = ReachabilityReport(
                reachable=False,
                message=f"Z3 preflight raised: {e}",
                horizon_k=horizon_k,
            )

    entry = starting_state or _infer_entry_state(work_graph)
    if entry is not None:
        try:
            model = WorkGraphProcessModel.from_work_graph(
                work_graph, transition_hints=transition_hints
            ).annotate_with_costs(work_graph)
            pairs = model.bottlenecks(starting_state=entry, top_k=top_bottlenecks)
            report.bottlenecks = [
                Bottleneck(work_unit=name, expected_time_hours=hours)
                for name, hours in pairs
            ]
        except Exception:
            pass

    return report


def _infer_entry_state(work_graph: WorkGraph) -> Optional[str]:
    """The first WorkUnit with no inputs — the natural simulation start."""
    for wu in work_graph.work_units:
        if not wu.inputs:
            return wu.name
    return work_graph.work_units[0].name if work_graph.work_units else None


def _spec_from_work_graph(work_graph: WorkGraph) -> Spec:
    """Project a WorkGraph onto the Spec shape lint_static expects."""
    return Spec(
        views={v.name: v for v in work_graph.views},
        work_units={wu.name: wu for wu in work_graph.work_units},
        bindings=list(work_graph.execution_bindings),
    )
