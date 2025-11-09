import re
from typing import List, Optional
import networkx as nx
from pydantic import BaseModel
from .models import Spec

class LintIssue(BaseModel):
    kind: str
    where: str
    msg: str
    hint: Optional[str] = None

def lint_static(spec: Spec) -> List[LintIssue]:
    issues: List[LintIssue] = []

    # (a) views: read/write discipline & lens-ish sanity
    for v in spec.views.values():
        if not v.writes and any("update" in inv.lower() for inv in v.invariants):
            issues.append(LintIssue(kind="VIEW_INVARIANT_MUTATION",
                                    where=v.name,
                                    msg="Read-only view declares mutation-like invariant.",
                                    hint="Move mutation to WorkUnit or declare writes."))

    # (b) work units: read/write sets consistent with views
    for wu in spec.work_units.values():
        allowed = set()
        for ov in wu.outputs:
            if ov in spec.views:
                allowed.update(spec.views[ov].writes)
        for f in wu.write_set:
            if f not in allowed:
                issues.append(LintIssue(kind="WRITE_OUTSIDE_VIEW",
                                        where=wu.name,
                                        msg=f"'{f}' not in any output view's writes.",
                                        hint=f"Add to View.writes or remove from write_set."))

        if wu.side_effects != "none" and wu.conflict_policy == "merge":
            issues.append(LintIssue(kind="SIDE_EFFECT_POLICY_WEAK",
                                    where=wu.name,
                                    msg="Nontrivial side-effects with 'merge' policy.",
                                    hint="Use 'fail' or design compensations."))

    # (c) whole graph: reachability of views & orphans
    G = nx.DiGraph()
    for v in spec.views:
        G.add_node(("view", v))
    for w in spec.work_units:
        G.add_node(("wu", w))

    for wu in spec.work_units.values():
        for vin in wu.inputs:
            G.add_edge(("view", vin), ("wu", wu.name))
        for vout in wu.outputs:
            G.add_edge(("wu", wu.name), ("view", vout))

    for n in list(G.nodes()):
        if G.in_degree(n) == 0 and n[0] == "wu":
            issues.append(LintIssue(kind="UNREACHABLE_WU",
                                    where=n[1], msg="No incoming views lead here."))
        if G.out_degree(n) == 0 and n[0] == "wu":
            issues.append(LintIssue(kind="SINK_WU",
                                    where=n[1], msg="Produces no views consumed downstream."))

    # cycles without measure
    sccs = [c for c in nx.strongly_connected_components(G) if len(c) > 1]
    for comp in sccs:
        wus_in_cycle = [n for n in comp if n[0] == "wu"]
        if not any(spec.work_units[n[1]].termination_measure for n in wus_in_cycle):
            issues.append(LintIssue(kind="CYCLE_NO_MEASURE",
                                    where=",".join(n[1] for n in wus_in_cycle),
                                    msg="Cyclic work units without termination measure.",
                                    hint="Add termination_measure or make one edge acyclic."))

    return issues
