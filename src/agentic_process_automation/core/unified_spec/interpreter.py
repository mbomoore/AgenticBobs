from typing import Any, Dict, List, Optional
import re
from agentic_process_automation.core.unified_spec.models import (
    Case,
    Combinator,
    View,
    WorkGraph,
    WorkItem,
    WorkUnit,
)
from agentic_process_automation.core.unified_spec.view_evaluation_engine import (
    ViewEvaluationEngine,
)


class Interpreter:
    """
    The runtime engine for executing a WorkGraph against a Case.
    """

    def __init__(self, work_graph: WorkGraph, case: Case):
        self.work_graph = work_graph
        self.case = case
        self.view_engine = ViewEvaluationEngine(case=self.case)
        self.work_unit_map = {wu.name: wu for wu in self.work_graph.work_units}
        self.view_map = {v.name: v for v in self.work_graph.views}

    def _construct_query_from_predicate(self, predicate: str) -> str:
        """Constructs a valid SELECT query from a predicate."""
        if "SELECT " in predicate.upper():
            return predicate
        match = re.match(r"(\w+)\.", predicate)
        if not match:
            raise ValueError(f"Invalid predicate format: '{predicate}'")
        entity_name = match.group(1)
        return f"SELECT 1 FROM {entity_name} WHERE {predicate}"

    def _items_for_combinator(self, combinator: Combinator) -> List[Dict[str, Any]]:
        """Resolve the source items the combinator operates over."""
        over_view = self.view_map.get(combinator.over)
        if not over_view:
            return []
        return self.view_engine.evaluate_view(over_view)

    def _is_item_done(self, work_unit: WorkUnit, params: Optional[Dict[str, Any]] = None) -> bool:
        """Check the WorkUnit's done predicate against the Case for a single parameter binding."""
        query = self._construct_query_from_predicate(work_unit.done)
        done_view = View(name="done_condition_check", reads=[query])
        return bool(self.view_engine.evaluate_view(done_view, params=params))

    def _expand_map(
        self, combinator: Combinator, work_unit: WorkUnit
    ) -> List[WorkItem]:
        """Map: emit one WorkItem per source item whose done predicate is false."""
        emitted: List[WorkItem] = []
        for item in self._items_for_combinator(combinator):
            params = {"rfp_id": item.get("id")}
            if not self._is_item_done(work_unit, params):
                emitted.append(
                    WorkItem(work_unit_name=work_unit.name, parameters=params)
                )
        return emitted

    def _expand_filter(
        self, combinator: Combinator, work_unit: WorkUnit
    ) -> List[WorkItem]:
        """Filter: like map, but skip items that fail the combinator's predicate."""
        predicate = combinator.predicate
        emitted: List[WorkItem] = []
        for item in self._items_for_combinator(combinator):
            if predicate is not None and not _evaluate_python_predicate(predicate, item):
                continue
            params = {"rfp_id": item.get("id")}
            if not self._is_item_done(work_unit, params):
                emitted.append(
                    WorkItem(work_unit_name=work_unit.name, parameters=params)
                )
        return emitted

    def _expand_fold(
        self, combinator: Combinator, work_unit: WorkUnit
    ) -> List[WorkItem]:
        """
        Fold: collapse all source items into a single WorkItem.

        Emits one WorkItem if the fold has not yet produced a row in the `into`
        view. The emitted WorkItem carries the full input list plus the seed
        accumulator so the executor can perform the reduction.
        """
        if combinator.into:
            target_view = self.view_map.get(combinator.into)
            if target_view and self.view_engine.evaluate_view(target_view):
                return []

        items = self._items_for_combinator(combinator)
        if not items:
            return []

        return [
            WorkItem(
                work_unit_name=work_unit.name,
                parameters={
                    "items": items,
                    "accumulator": combinator.accumulator,
                    "into": combinator.into,
                },
            )
        ]

    def tick(self) -> List[WorkItem]:
        """
        Executes one cycle of the interpreter loop.

        Identifies which WorkUnits are "ready" and returns parameterized
        WorkItems for them.
        """
        ready_work_items: List[WorkItem] = []
        combinator_work_units = set()

        expanders = {
            "map": self._expand_map,
            "filter": self._expand_filter,
            "fold": self._expand_fold,
        }

        for combinator in self.work_graph.combinators:
            combinator_work_units.add(combinator.work_unit)
            work_unit = self.work_unit_map.get(combinator.work_unit)
            if not work_unit:
                continue
            expander = expanders.get(combinator.type)
            if expander is None:
                continue
            ready_work_items.extend(expander(combinator, work_unit))

        for work_unit in self.work_graph.work_units:
            if work_unit.name in combinator_work_units:
                continue
            if not self._is_item_done(work_unit, params=None):
                ready_work_items.append(
                    WorkItem(work_unit_name=work_unit.name, parameters={})
                )

        return ready_work_items


_SAFE_PREDICATE_PATTERN = re.compile(r"^[\w\s\.<>=!\(\)\+\-\*\/'\",%]+$")


def _evaluate_python_predicate(predicate: str, item: Dict[str, Any]) -> bool:
    """
    Evaluate a simple Python-style boolean predicate against a single item dict.

    Used by `_expand_filter` for in-memory selection. Restricted to a small
    alphabet to keep the evaluation safe; richer guard logic lives in
    `guard_algebra.py` (Phase 2).
    """
    if predicate is None:
        return True
    expr = predicate.strip()
    if not _SAFE_PREDICATE_PATTERN.match(expr):
        raise ValueError(f"Unsupported predicate syntax: {predicate!r}")
    try:
        return bool(eval(expr, {"__builtins__": {}}, dict(item)))
    except NameError:
        return False
