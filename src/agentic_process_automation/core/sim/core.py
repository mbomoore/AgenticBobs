"""Core DSL types: State, Transition, ProcessModel

This file ports the minimal DSL found in the notebook into typed dataclasses and
removes global state. Operator overloads reproduce the `state >> prob >> next` style.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Union, Dict, Any, overload
import numpy as np


class ModelValidationError(ValueError):
    pass


@dataclass
class ResourceRef:
    role: str
    cost: float = 0.0


@dataclass
class State:
    name: str
    time: float = 0.0
    # accept any resource-like object (from resources.Resource or legacy ResourceRef)
    resource: Optional[Any] = None

    # internal index will be assigned by ProcessModel when added
    index: Optional[int] = field(default=None, init=False, repr=False)

    def __post_init__(self):
        # Auto-register with the active ProcessModel context
        if ProcessModel._active_context:
            ProcessModel._active_context.add_state(self)

    @overload
    def __rshift__(self, other: float) -> "_ProbHolder":
        ...

    @overload
    def __rshift__(self, other: Tuple[Tuple[float, "State"], ...]) -> List["Transition"]:
        ...

    @overload
    def __rshift__(self, other: "State") -> "Transition":
        ...

    def __rshift__(self, other):
        # Support: state >> prob >> state  OR state >> ( (prob, state), ... )
        if isinstance(other, float):
            # return an intermediary carrying probability
            return _ProbHolder(self, other)
        elif isinstance(other, tuple):
            # tuple of transitions provided
            transitions: List[Transition] = []
            for t in other:
                if not (isinstance(t, tuple) and isinstance(t[0], float) and isinstance(t[1], State)):
                    raise ValueError("Invalid transition tuple")
                transitions.append(Transition(from_var=self, to_var=t[1], prob=t[0]))
            return transitions
        elif isinstance(other, State):
            # allow chaining without explicit prob (rare) -> default prob 1
            return Transition(from_var=self, to_var=other, prob=1.0)
        else:
            raise ValueError("Unsupported operand for >> in State")


@dataclass
class Transition:
    from_var: State
    to_var: State
    prob: float
    name: Optional[str] = None

    def __rshift__(self, other: "State") -> "State":
        # allow Transition >> State to set to_var if missing
        if isinstance(other, State):
            self.to_var = other
            return other
        raise ValueError("Can only shift a Transition to a State")


class _ProbHolder:
    def __init__(self, state: State, prob: float):
        self.state = state
        self.prob = prob

    def __rshift__(self, other_state: State) -> Transition:
        if not isinstance(other_state, State):
            raise ValueError("Right operand must be a State")
        return Transition(from_var=self.state, to_var=other_state, prob=self.prob)


class ProcessModel:
    """Container for states and transitions. Use as a context manager to build models.

    Example:
        p = ProcessModel('proc')
        with p:
            s1 = State('A')
            s2 = State('B')
            s1 >> 1.0 >> s2
    """
    _active_context: Optional["ProcessModel"] = None

    def __init__(self, name: str):
        self.name = name
        self.states: List[State] = []
        self.transitions: List[Transition] = []
        self.states_by_name: Dict[str, State] = {}

    def __enter__(self):
        ProcessModel._active_context = self
        return self

    def __exit__(self, exc_type, exc, tb):
        # validate transitions
        self._assign_state_indices()
        self._validate_transition_probabilities()
        ProcessModel._active_context = None

    def add_state(self, state: State):
        if state in self.states:
            return
        state.index = len(self.states)
        self.states.append(state)
        self.states_by_name[state.name] = state

    def add_transition(self, transition: Transition):
        # ensure states are registered
        self.add_state(transition.from_var)
        self.add_state(transition.to_var)
        self.transitions.append(transition)

    def add_transitions(self, transitions: List[Transition]):
        for t in transitions:
            self.add_transition(t)

    def _assign_state_indices(self):
        for i, s in enumerate(self.states):
            s.index = i

    def _validate_transition_probabilities(self):
        n = len(self.states)
        if n == 0:
            return
        mat = np.zeros((n, n))
        for t in self.transitions:
            i = self.states.index(t.from_var)
            j = self.states.index(t.to_var)
            mat[i, j] += t.prob
        row_sums = mat.sum(axis=1)
        # allow absorbing states
        for i, s in enumerate(self.states):
            # ignore states with no outgoing (absorbing): sum can be 0
            if row_sums[i] == 0:
                continue
            if not np.isclose(row_sums[i], 1.0):
                raise ModelValidationError(f"Transition probabilities for state {s.name} sum to {row_sums[i]:.4f} != 1")

    def transition_matrix(self) -> np.ndarray:
        n = len(self.states)
        mat = np.zeros((n, n))
        for t in self.transitions:
            i = self.states.index(t.from_var)
            j = self.states.index(t.to_var)
            mat[i, j] += t.prob
        return mat

    def state_visits(self, starting_state=0):
        I = np.eye(len(self.states))
        P = self.transition_matrix()
        # (I - P)^{-1}
        inv = np.linalg.inv(I - P)
        # find index of Success if present
        success_indices = [i for i, s in enumerate(self.states) if s.name == 'Success']
        if success_indices:
            success_idx = success_indices[0]
        else:
            success_idx = None
        if success_idx is not None:
            result = inv[starting_state, :] / inv[starting_state, success_idx]
        else:
            result = inv[starting_state, :]
        return list((state, result[i]) for i, state in enumerate(self.states))

    def states_cost(self):
        visits = self.state_visits()
        return list((state, state.resource.cost * state.time * visit if state.resource else 0.0) for state, visit in visits)

    # helper builder utilities
    def build_from_dsl(self):
        # scan transitions created via operator DSL in current globals is not used here; instead,
        # we expect the user to call add_transition explicitly when creating transitions using >>
        pass
