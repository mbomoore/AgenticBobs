"""Semantics kernel for simple token flow on the PIR graph.

Provides:
- Token: a position in the graph (by node_id)
- SimState: time, active tokens, queues, resources
- next_enabled: enumerate enabled token moves based on outgoing edges
- step: apply a move and return a new SimState (functional style)

This is a minimal MVP: no guards/policies/resources enforced yet.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Dict, List, Tuple

from .pir import PIR

try:
    from icecream import ic  # type: ignore
except Exception:  # pragma: no cover
    def ic(*args, **kwargs):  # type: ignore
        return args if len(args) != 1 else args[0]


@dataclass(frozen=True)
class Token:
    """A token located at a specific node in the PIR graph."""

    node_id: str


@dataclass(frozen=True)
class SimState:
    """Simulation state snapshot."""

    time: float
    tokens: List[Token]  # active tokens in the process
    queues: Dict[str, List[str]]  # node_id -> list (reserved for future use)
    resources: Dict[str, int]  # pool_id -> available count


def _outgoing(pir: PIR) -> Dict[str, List[str]]:
    """Build adjacency list mapping from node_id to list of dst ids."""
    adj: Dict[str, List[str]] = {nid: [] for nid in pir.nodes.keys()}
    for e in pir.edges:
        if e.src in adj:
            adj[e.src].append(e.dst)
    return adj


Move = Tuple[Token, str]  # (which token, next node id)


def next_enabled(pir: PIR, state: SimState) -> List[Move]:
    """Return a list of enabled moves for the current tokens.

    A move is a (token, next_node_id) pair for each outgoing edge of token.node_id.
    """
    adj = _outgoing(pir)
    moves: List[Move] = []
    for t in state.tokens:
        for dst in adj.get(t.node_id, []):
            moves.append((t, dst))
    return moves


def step(pir: PIR, state: SimState, move: Move) -> SimState:
    """Apply a move, returning a new state with the token relocated.

    If the move references a token not in the current state, the state is returned unchanged.
    """
    token, dst = move
    new_tokens: List[Token] = []
    replaced_flag = False
    for t in state.tokens:
        if not replaced_flag and t == token:
            new_tokens.append(Token(node_id=dst))
            replaced_flag = True
        else:
            new_tokens.append(t)
    return replace(state, tokens=new_tokens)
