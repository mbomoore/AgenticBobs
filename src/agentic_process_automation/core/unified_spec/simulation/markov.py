"""
Markov visitation math, ported from `core/sim/core.py:162-186`.

Pure functions over plain state/transition objects: no global context, no
class hierarchy. The legacy `ProcessModel.transition_matrix()` and
`state_visits()` are reproduced here against unified-spec types so the
algorithms stay identical while the inputs change.
"""

from __future__ import annotations

from typing import List, Sequence, Tuple

import numpy as np

from agentic_process_automation.core.unified_spec.simulation.process_model import (
    WGState,
    WGTransition,
)


def transition_matrix(states: Sequence[WGState], transitions: Sequence[WGTransition]) -> np.ndarray:
    """Build the n×n transition probability matrix P where P[i, j] = prob(i → j)."""
    n = len(states)
    mat = np.zeros((n, n))
    index = {s.name: i for i, s in enumerate(states)}
    for t in transitions:
        i = index[t.from_state]
        j = index[t.to_state]
        mat[i, j] += t.prob
    return mat


def state_visits(
    states: Sequence[WGState],
    transitions: Sequence[WGTransition],
    starting_index: int = 0,
    *,
    success_state_name: str = "Done",
) -> List[Tuple[WGState, float]]:
    """
    Expected visitation counts using the fundamental-matrix identity (I − P)⁻¹.

    Mirrors `ProcessModel.state_visits`: if a state named `success_state_name`
    exists, visit counts are normalised so the success state has value 1
    (interpretation: "expected visits per successful completion"). Otherwise
    raw counts from the fundamental matrix row are returned.
    """
    n = len(states)
    if n == 0:
        return []
    P = transition_matrix(states, transitions)
    I = np.eye(n)
    inv = np.linalg.inv(I - P)

    success_idx = next(
        (i for i, s in enumerate(states) if s.name == success_state_name), None
    )
    if success_idx is not None and inv[starting_index, success_idx] != 0:
        row = inv[starting_index, :] / inv[starting_index, success_idx]
    else:
        row = inv[starting_index, :]
    return [(states[i], float(row[i])) for i in range(n)]
