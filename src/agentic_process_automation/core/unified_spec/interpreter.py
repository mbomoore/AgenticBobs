from typing import List
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

                over_view = View(name="combinator_over", query=combinator.over)
                items_to_process = self.view_engine.evaluate_view(over_view)

                for params in items_to_process:
                    done_condition_view = View(name="done_condition_check", query=work_unit_template.done_condition)
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

            done_condition_view = View(name="done_condition_check", query=work_unit.done_condition)
            done_results = self.view_engine.evaluate_view(done_condition_view)

            if not done_results:
                ready_work_items.append(
                    WorkItem(
                        work_unit_name=work_unit.name,
                        parameters={}, # Standalone work units have no parameters for now
                    )
                )

        return ready_work_items
