from typing import Dict, List
from .models import WorkGraph, WorkItem, ExecutionBinding, WorkUnit, Case, View
from .view_evaluation_engine import ViewEvaluationEngine

class Dispatcher:
    """
    Resolves a WorkItem to an executor based on the ExecutionBindings in a WorkGraph.
    """

    def __init__(self, work_graph: WorkGraph):
        self.work_graph = work_graph
        self._bindings_by_goal_tag: Dict[str, List[ExecutionBinding]] = {}
        self._work_units_by_name: Dict[str, WorkUnit] = {wu.name: wu for wu in work_graph.work_units}

        # Sort bindings to ensure 'True' conditions are evaluated last as fallbacks
        sorted_bindings = sorted(work_graph.execution_bindings, key=lambda b: b.condition == 'True')

        for binding in sorted_bindings:
            if binding.goal_tag not in self._bindings_by_goal_tag:
                self._bindings_by_goal_tag[binding.goal_tag] = []
            self._bindings_by_goal_tag[binding.goal_tag].append(binding)

    def resolve_executor(self, work_item: WorkItem, case: Case) -> str:
        """
        Resolves the executor for a given WorkItem by evaluating conditions
        on the provided Case.
        """
        work_unit = self._work_units_by_name.get(work_item.work_unit_name)
        if not work_unit:
            raise ValueError(f"WorkUnit '{work_item.work_unit_name}' not found in WorkGraph.")

        goal_tag = work_unit.goal_tag
        bindings = self._bindings_by_goal_tag.get(goal_tag, [])

        if not bindings:
            raise ValueError(f"No ExecutionBinding found for goal_tag '{goal_tag}'.")

        view_eval_engine = ViewEvaluationEngine(case)

        for binding in bindings:
            if binding.condition == "True":
                return binding.executor

            # Construct a temporary View to evaluate the condition query.
            temp_view = View(name="_condition_check", query=binding.condition)

            try:
                # evaluate_view returns a list of rows. If non-empty, the condition is met.
                result = view_eval_engine.evaluate_view(temp_view)
                if result:
                    return binding.executor
            except Exception:
                # If the query is invalid for the current case state (e.g., table not found),
                # treat it as a non-match and continue.
                continue

        raise ValueError(f"No matching ExecutionBinding found for goal_tag '{goal_tag}' with the current case state.")
