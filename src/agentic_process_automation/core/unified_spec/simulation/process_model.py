"""
WorkGraph-as-Markov-chain.

The legacy `ProcessModel` consumed PIR nodes and edges. WorkGraph has no
explicit edges — work units are linked implicitly through View dependencies
(WU A writes a View; WU B reads it). `WorkGraphProcessModel.from_work_graph`
infers a transition graph from those dependencies and adds a synthetic
absorbing `Done` state.

The graph it produces is what the Markov layer reasons over. Probabilities
are uniform across outgoing edges by default; the caller can pass
`transition_hints` to override specific edges when measured data exists.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from agentic_process_automation.core.unified_spec.models import WorkGraph


@dataclass(frozen=True)
class WGState:
    name: str
    impl_kind: Optional[str] = None
    expected_duration_hours: float = 0.0
    cost_per_invocation: float = 0.0


@dataclass(frozen=True)
class WGTransition:
    from_state: str
    to_state: str
    prob: float


DONE_STATE = "Done"


@dataclass
class WorkGraphProcessModel:
    states: List[WGState]
    transitions: List[WGTransition]
    name: str = "workgraph"

    _state_index: Dict[str, int] = field(init=False, repr=False, default_factory=dict)

    def __post_init__(self) -> None:
        self._state_index = {s.name: i for i, s in enumerate(self.states)}
        self._validate_row_sums()

    @classmethod
    def from_work_graph(
        cls,
        work_graph: WorkGraph,
        *,
        transition_hints: Optional[Dict[Tuple[str, str], float]] = None,
    ) -> "WorkGraphProcessModel":
        """Infer transitions from View read/write dependencies between WorkUnits."""
        successors: Dict[str, List[str]] = defaultdict(list)
        wu_names = [wu.name for wu in work_graph.work_units]
        writer_to_views: Dict[str, List[str]] = {wu.name: list(wu.outputs) for wu in work_graph.work_units}
        view_to_readers: Dict[str, List[str]] = defaultdict(list)
        for wu in work_graph.work_units:
            for view in wu.inputs:
                view_to_readers[view].append(wu.name)

        for writer, views in writer_to_views.items():
            seen: set[str] = set()
            for view in views:
                for reader in view_to_readers.get(view, []):
                    if reader == writer or reader in seen:
                        continue
                    successors[writer].append(reader)
                    seen.add(reader)

        for wu in wu_names:
            if not successors[wu]:
                successors[wu] = [DONE_STATE]

        states = [WGState(name=wu) for wu in wu_names] + [WGState(name=DONE_STATE)]

        hints = transition_hints or {}
        transitions: List[WGTransition] = []
        for src, dsts in successors.items():
            override = {
                dst: hints[(src, dst)] for dst in dsts if (src, dst) in hints
            }
            unset = [d for d in dsts if d not in override]
            remaining = max(0.0, 1.0 - sum(override.values()))
            for dst, p in override.items():
                transitions.append(WGTransition(from_state=src, to_state=dst, prob=p))
            if unset:
                share = remaining / len(unset)
                for dst in unset:
                    transitions.append(WGTransition(from_state=src, to_state=dst, prob=share))

        return cls(states=states, transitions=transitions, name=work_graph.name)

    def annotate_with_costs(
        self,
        work_graph: WorkGraph,
        *,
        overrides=None,
    ) -> "WorkGraphProcessModel":
        """Return a new model with each non-terminal state's cost/duration filled in."""
        from agentic_process_automation.core.unified_spec.simulation.binding_aware import (
            cost_for_work_unit,
        )

        annotated: List[WGState] = []
        for state in self.states:
            if state.name == DONE_STATE:
                annotated.append(state)
                continue
            cost = cost_for_work_unit(work_graph, state.name, overrides=overrides)
            annotated.append(
                WGState(
                    name=state.name,
                    impl_kind=cost.impl_kind,
                    expected_duration_hours=cost.expected_duration_hours,
                    cost_per_invocation=cost.cost_per_invocation,
                )
            )
        return WorkGraphProcessModel(
            states=annotated, transitions=list(self.transitions), name=self.name
        )

    def index_of(self, state_name: str) -> int:
        return self._state_index[state_name]

    def bottlenecks(self, *, starting_state: str, top_k: int = 3) -> List[Tuple[str, float]]:
        """Return the top-k states by expected total time (visits × duration)."""
        from agentic_process_automation.core.unified_spec.simulation.markov import (
            state_visits,
        )

        visits = state_visits(self.states, self.transitions, self.index_of(starting_state))
        weighted = [
            (s.name, v * s.expected_duration_hours)
            for s, v in visits
            if s.name != DONE_STATE
        ]
        weighted.sort(key=lambda pair: pair[1], reverse=True)
        return weighted[:top_k]

    def expected_total_cost(self, *, starting_state: str) -> float:
        from agentic_process_automation.core.unified_spec.simulation.markov import (
            state_visits,
        )

        visits = state_visits(self.states, self.transitions, self.index_of(starting_state))
        return sum(v * s.cost_per_invocation for s, v in visits if s.name != DONE_STATE)

    def _validate_row_sums(self) -> None:
        rows: Dict[str, float] = defaultdict(float)
        for t in self.transitions:
            rows[t.from_state] += t.prob
        for src, total in rows.items():
            if abs(total - 1.0) > 1e-6:
                raise ValueError(
                    f"Transition probabilities for state {src!r} sum to {total:.6f} != 1"
                )
