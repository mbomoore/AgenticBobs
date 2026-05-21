"""
Combinator algebra: identify simplifications and fusions across a list of
Combinators in a WorkGraph.

The interpreter (`interpreter.py`) executes combinators directly. This module
exists for the **process-design copilot**: it lets the copilot recognise that
a draft graph could be expressed more compactly (e.g. two adjacent maps fuse
into one), or that a sequence is malformed (e.g. fold over an empty source).

Each rule returns a `FusionOpportunity` rather than mutating the graph, so the
copilot can present the suggestion to the user before applying it.
"""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from agentic_process_automation.core.unified_spec.models import Combinator


FusionKind = Literal[
    "map_map_fuse",
    "filter_filter_merge",
    "map_then_fold_pipeline",
]


class FusionOpportunity(BaseModel):
    """A simplification the copilot could propose to the user."""

    kind: FusionKind = Field(..., description="The algebraic rule that applies.")
    c1: Combinator
    c2: Combinator
    suggested: Combinator = Field(
        ...,
        description=(
            "Resulting combinator. Its `work_unit` field is the name of a "
            "fused WorkUnit the user must define (composition produces a "
            "candidate, not a runnable WorkUnit on its own)."
        ),
    )
    rationale: str


def compose(
    c1: Combinator,
    c2: Combinator,
    fused_work_unit_name: Optional[str] = None,
) -> Optional[Combinator]:
    """
    Attempt to fuse two combinators that share a source.

    Returns the fused combinator on success, or None if no rule applies.

    Identity laws:
      map(f)   . map(g)   = map(f.g)        when c1.over == c2.over
      filter(p). filter(q)= filter(p AND q) when c1.over == c2.over

    Sequencing (map → fold) is recognised by `find_fusions` but not fused by
    `compose`, because the fold consumes the map's output downstream rather
    than alongside it.
    """
    if c1.over != c2.over:
        return None

    name = fused_work_unit_name or f"{c1.work_unit}__then__{c2.work_unit}"

    if c1.type == "map" and c2.type == "map":
        return Combinator(type="map", work_unit=name, over=c1.over)

    if c1.type == "filter" and c2.type == "filter":
        merged_predicate = _and(c1.predicate, c2.predicate)
        return Combinator(
            type="filter",
            work_unit=name,
            over=c1.over,
            predicate=merged_predicate,
        )

    return None


def find_fusions(combinators: List[Combinator]) -> List[FusionOpportunity]:
    """Scan a combinator list for simplification opportunities."""
    opportunities: List[FusionOpportunity] = []

    for i, c1 in enumerate(combinators):
        for c2 in combinators[i + 1 :]:
            fused = compose(c1, c2)
            if fused is None:
                if c1.type == "map" and c2.type == "fold" and c2.over == c1.over:
                    opportunities.append(
                        FusionOpportunity(
                            kind="map_then_fold_pipeline",
                            c1=c1,
                            c2=c2,
                            suggested=c2,
                            rationale=(
                                f"map '{c1.work_unit}' and fold '{c2.work_unit}' "
                                f"both consume '{c1.over}'. Consider chaining the "
                                f"map's output into the fold's source to avoid "
                                f"re-reading the same View twice."
                            ),
                        )
                    )
                continue

            kind: FusionKind = (
                "map_map_fuse" if c1.type == "map" else "filter_filter_merge"
            )
            opportunities.append(
                FusionOpportunity(
                    kind=kind,
                    c1=c1,
                    c2=c2,
                    suggested=fused,
                    rationale=(
                        f"{c1.type} '{c1.work_unit}' and {c2.type} '{c2.work_unit}' "
                        f"both operate on '{c1.over}' and can be fused into a "
                        f"single combinator."
                    ),
                )
            )

    return opportunities


def is_identity(c: Combinator) -> bool:
    """A combinator is an identity when it cannot affect what its source View yields."""
    if c.type == "filter" and (c.predicate is None or c.predicate.strip().lower() in {"true", "1"}):
        return True
    return False


def _and(p: Optional[str], q: Optional[str]) -> Optional[str]:
    if p is None:
        return q
    if q is None:
        return p
    return f"({p}) AND ({q})"
