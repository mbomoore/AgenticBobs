from typing import List
import re
from agentic_process_automation.core.unified_spec.models import Case, WorkGraph, WorkUnit, View, WorkItem
from agentic_process_automation.core.unified_spec.view_evaluation_engine import ViewEvaluationEngine

class Interpreter:
    """
    The runtime engine for executing a WorkGraph against a Case.
    """
    def __init__(self, work_graph: WorkGraph, case: Case):
        """
        Initializes the Interpreter with a WorkGraph and a Case.

        :param work_graph: The WorkGraph specification to execute.
        :param case: The Case instance to execute against.
        """
        self.work_graph = work_graph
        self.case = case
        self.view_engine = ViewEvaluationEngine(case=self.case)
        self.work_unit_map = {wu.name: wu for wu in self.work_graph.work_units}
        self.view_map = {v.name: v for v in self.work_graph.views}

    def _construct_query_from_predicate(self, predicate: str) -> str:
        """Constructs a valid SELECT query from a predicate."""
        # This is a simplified implementation. A more robust implementation
        # would use a proper SQL parser.
        if "SELECT " in predicate.upper():
            return predicate
        match = re.match(r"(\w+)\.", predicate)
        if not match:
            raise ValueError(f"Invalid predicate format: '{predicate}'")
        entity_name = match.group(1)
        return f"SELECT 1 FROM {entity_name} WHERE {predicate}"

    def tick(self) -> List[WorkItem]:
        """
        Executes one cycle of the interpreter loop.

        This method identifies which WorkUnits are "done" and which are "ready"
        to be worked on, and returns specific, parameterized WorkItems for them.

        :return: A list of WorkItems that are ready to be executed.
        """
        ready_work_items = []
        combinator_work_units = set()

        for combinator in self.work_graph.combinators:
            combinator_work_units.add(combinator.work_unit)
            if combinator.type == "map":
                work_unit_template = self.work_unit_map.get(combinator.work_unit)
                if not work_unit_template:
                    continue

                over_view = self.view_map.get(combinator.over)
                if not over_view:
                    continue
                items_to_process = self.view_engine.evaluate_view(over_view)

                for item in items_to_process:
                    params = {"rfp_id": item.get("id")}
                    query = self._construct_query_from_predicate(work_unit_template.done)
                    done_condition_view = View(name="done_condition_check", reads=[query])
                    done_results = self.view_engine.evaluate_view(done_condition_view, params=params)

                    if not done_results:
                        ready_work_items.append(
                            WorkItem(
                                work_unit_name=work_unit_template.name,
                                parameters=params,
                            )
                        )

        # Handle standalone work units
        for work_unit in self.work_graph.work_units:
            if work_unit.name in combinator_work_units:
                continue

            query = self._construct_query_from_predicate(work_unit.done)
            done_condition_view = View(name="done_condition_check", reads=[query])
            done_results = self.view_engine.evaluate_view(done_condition_view)

            if not done_results:
                ready_work_items.append(
                    WorkItem(
                        work_unit_name=work_unit.name,
                        parameters={}, # Standalone work units have no parameters for now
                    )
                )

        return ready_work_items
