from typing import Dict, List
from .models import WorkGraph, WorkItem, ExecutionBinding, WorkUnit

class Dispatcher:
    """
    Resolves a WorkItem to an executor based on the ExecutionBindings in a WorkGraph.
    """

    def __init__(self, work_graph: WorkGraph):
        self.work_graph = work_graph
        self._bindings_by_goal_tag: Dict[str, List[ExecutionBinding]] = {}
        self._work_units_by_name: Dict[str, WorkUnit] = {wu.name: wu for wu in work_graph.work_units}

        for binding in self.work_graph.execution_bindings:
            if binding.goal_tag not in self._bindings_by_goal_tag:
                self._bindings_by_goal_tag[binding.goal_tag] = []
            self._bindings_by_goal_tag[binding.goal_tag].append(binding)

    def resolve_executor(self, work_item: WorkItem) -> str:
        """
        Resolves the executor for a given WorkItem.
        """
        work_unit = self._work_units_by_name.get(work_item.work_unit_name)
        if not work_unit:
            raise ValueError(f"WorkUnit '{work_item.work_unit_name}' not found in WorkGraph.")

        goal_tag = work_unit.goal_tag
        bindings = self._bindings_by_goal_tag.get(goal_tag, [])

        # For now, we'll use the first matching binding without evaluating conditions.
        # In the future, this is where condition evaluation logic would go.
        if not bindings:
            raise ValueError(f"No ExecutionBinding found for goal_tag '{goal_tag}'.")

        return bindings[0].executor
