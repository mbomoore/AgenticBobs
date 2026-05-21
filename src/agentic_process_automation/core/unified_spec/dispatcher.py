from typing import Dict, List, Tuple

from pydantic import BaseModel

from . import guard_algebra
from .models import Case, ExecutionBinding, View, WorkGraph, WorkItem, WorkUnit
from .view_evaluation_engine import ViewEvaluationEngine


class RoutingIssue(BaseModel):
    """A potential ambiguity surfaced by `Dispatcher.check_routing_consistency`."""

    target: str
    rule_a_condition: str
    rule_b_condition: str
    a_impl: str
    b_impl: str
    message: str


class Dispatcher:
    """
    Resolves a WorkItem to an executor based on the ExecutionBindings in a WorkGraph.
    """

    def __init__(self, work_graph: WorkGraph):
        self.work_graph = work_graph
        self._bindings_by_target: Dict[str, List[ExecutionBinding]] = {}
        self._work_units_by_name: Dict[str, WorkUnit] = {wu.name: wu for wu in work_graph.work_units}

        # Sort bindings to ensure 'True' conditions are evaluated last as fallbacks
        sorted_bindings = sorted(work_graph.execution_bindings, key=lambda b: b.rules[0].condition == 'True')

        for binding in sorted_bindings:
            if binding.target not in self._bindings_by_target:
                self._bindings_by_target[binding.target] = []
            self._bindings_by_target[binding.target].append(binding)

    def resolve_executor(self, work_item: WorkItem, case: Case) -> str:
        """
        Resolves the executor for a given WorkItem by evaluating conditions
        on the provided Case.
        """
        work_unit = self._work_units_by_name.get(work_item.work_unit_name)
        if not work_unit:
            raise ValueError(f"WorkUnit '{work_item.work_unit_name}' not found in WorkGraph.")

        target = work_unit.name
        bindings = self._bindings_by_target.get(target, [])

        if not bindings:
            # Fallback to goal_tag if no specific binding found for work_unit name
            target = work_unit.goal_tag
            bindings = self._bindings_by_target.get(target, [])

        if not bindings:
            raise ValueError(f"No ExecutionBinding found for target '{target}'.")

        view_eval_engine = ViewEvaluationEngine(case)

        for binding in bindings:
            for rule in binding.rules:
                if rule.condition == "True":
                    return rule.impl_kind

                # Construct a temporary View to evaluate the condition query.
                temp_view = View(name="_condition_check", reads=[rule.condition])

                try:
                    # evaluate_view returns a list of rows. If non-empty, the condition is met.
                    result = view_eval_engine.evaluate_view(temp_view)
                    if result:
                        return rule.impl_kind
                except Exception:
                    # If the query is invalid for the current case state (e.g., table not found),
                    # treat it as a non-match and continue.
                    continue

        raise ValueError(f"No matching ExecutionBinding found for target '{target}' with the current case state.")

    def check_routing_consistency(self) -> List[RoutingIssue]:
        """
        Statically inspect bindings for routing ambiguity.

        For each target, collect every (condition, impl_kind) pair from its
        bindings and ask `guard_algebra.disjoint` whether two non-fallback
        conditions could ever match the same Case while assigning different
        executors. Conditions outside the symbolic fragment (e.g. raw SQL)
        are skipped — the copilot sees only the ambiguities it can prove.
        """
        issues: List[RoutingIssue] = []
        for target, bindings in self._bindings_by_target.items():
            flat: List[Tuple[str, str]] = []
            for binding in bindings:
                for rule in binding.rules:
                    if rule.condition.strip().lower() == "true":
                        continue
                    flat.append((rule.condition, rule.impl_kind))

            for i, (cond_a, impl_a) in enumerate(flat):
                for cond_b, impl_b in flat[i + 1 :]:
                    if impl_a == impl_b:
                        continue
                    is_disjoint = guard_algebra.disjoint(cond_a, cond_b)
                    if is_disjoint is False:
                        issues.append(
                            RoutingIssue(
                                target=target,
                                rule_a_condition=cond_a,
                                rule_b_condition=cond_b,
                                a_impl=impl_a,
                                b_impl=impl_b,
                                message=(
                                    f"Target {target!r}: rules "
                                    f"{cond_a!r} → {impl_a} and "
                                    f"{cond_b!r} → {impl_b} can both match "
                                    f"the same Case; routing is ambiguous."
                                ),
                            )
                        )
        return issues
