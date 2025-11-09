from typing import Dict, List
from .models import WorkGraph, WorkItem, ExecutionBinding, WorkUnit, Case, View
from .view_evaluation_engine import ViewEvaluationEngine

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
