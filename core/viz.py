"""Visualization transforms for PIR.

Provides:
- pir_to_mermaid: Mermaid flowchart TD string
- pir_to_cytoscape: dict with nodes and edges for Cytoscape.js
"""
from __future__ import annotations

from typing import Dict, List, Optional

from core.pir import PIR

try:  # optional dependency; only used in apps, not in unit tests
    from viz.bpmn_dmn_component import st_process_viewer  # type: ignore
except Exception:  # pragma: no cover
    st_process_viewer = None  # type: ignore


def pir_to_mermaid(pir: PIR) -> str:
    lines: List[str] = ["flowchart LR"]
    # Nodes: label with name; fall back to id
    for nid, node in pir.nodes.items():
        label = node.name or nid
        # Use square brackets for standard nodes; gateways can use diamond style with { }
        if node.kind.endswith("Gateway") or node.kind in {"exclusiveGateway", "parallelGateway"}:
            # Mermaid diamond: {label}. Escape brace in f-string by doubling '}'
            lines.append(f"    {nid}{{\"{label}\"}}")
        else:
            lines.append(f"    {nid}[\"{label}\"]")

    # Edges: include guard annotations if present
    for e in pir.edges:
        if e.guard:
            lines.append(f"    {e.src} -->|{e.guard}| {e.dst}")
        else:
            lines.append(f"    {e.src} --> {e.dst}")
    return "\n".join(lines)


def pir_to_cytoscape(pir: PIR) -> Dict[str, List[dict]]:
    nodes = [
        {
            "data": {
                "id": nid,
                "label": node.name or nid,
                "kind": node.kind,
                "lane": node.lane,
            }
        }
        for nid, node in pir.nodes.items()
    ]
    edges = [
        {
            "data": {
                "id": f"{e.src}__{e.dst}",
                "source": e.src,
                "target": e.dst,
                "guard": e.guard,
            }
        }
        for e in pir.edges
    ]
    return {"nodes": nodes, "edges": edges}


def get_representation(pir: PIR, fmt: str) -> Optional[str]:
    """Fetch a textual representation from the PIR if present.

    Examples of fmt: "bpmn+xml", "dmn+xml", "mermaid".
    Returns None if not attached.
    """
    return pir.representations.get(fmt)


def streamlit_show(pir: PIR, fmt: str = "bpmn+xml", height: int = 520, theme: str = "light") -> Optional[str]:
    """Render the PIR using the Streamlit BPMN/DMN viewer if available.

    Returns the last clicked element id, or None. Requires Streamlit in environment.
    """
    if st_process_viewer is None:
        raise RuntimeError("Streamlit component not available. Install Streamlit to use this.")
    xml = get_representation(pir, fmt)
    if not xml:
        raise ValueError(f"PIR does not carry representation '{fmt}'")
    mode = "bpmn" if fmt.startswith("bpmn") else ("dmn" if fmt.startswith("dmn") else "bpmn")
    return st_process_viewer(xml=xml, mode=mode, height=height, theme=theme, key=f"viz_{mode}")
