"""Visualization transforms for PIR.

Provides:
- pir_to_mermaid: Mermaid flowchart TD string
- pir_to_cytoscape: dict with nodes and edges for Cytoscape.js
"""
from __future__ import annotations

from typing import Dict, List, Optional

from core.pir import PIR



def pir_to_mermaid(pir: PIR) -> str:
    lines: List[str] = ["flowchart LR"]
    
    # Group nodes by pools and lanes
    pools: Dict[str, Dict[str, List[str]]] = {}  # pool -> lane -> [node_ids]
    unorganized_nodes: List[str] = []  # nodes without pool/lane organization
    
    for nid, node in pir.nodes.items():
        if node.pool:
            if node.pool not in pools:
                pools[node.pool] = {}
            
            lane_key = node.lane or "_direct_pool_"  # Special key for direct pool membership
            if lane_key not in pools[node.pool]:
                pools[node.pool][lane_key] = []
            pools[node.pool][lane_key].append(nid)
        else:
            unorganized_nodes.append(nid)
    
    # Generate pool subgraphs
    for pool_name, lanes in pools.items():
        lines.append(f"  %% Pool: {pool_name}")
        pool_id = f"Pool{pool_name.replace(' ', '')}"
        lines.append(f"  subgraph {pool_id}[\"{pool_name}\"]")
        lines.append("    direction TB")
        lines.append("")
        
        # Generate lane subgraphs within the pool
        for lane_key, node_ids in lanes.items():
            if lane_key == "_direct_pool_":
                # Nodes directly in pool (no specific lane)
                lines.append("    direction LR")
                for nid in node_ids:
                    node = pir.nodes[nid]
                    label = node.name or nid
                    if node.kind.endswith("Gateway") or node.kind in {"exclusiveGateway", "parallelGateway"}:
                        lines.append(f"    {nid}{{\"{label}\"}}")
                    else:
                        lines.append(f"    {nid}[\"{label}\"]")
            else:
                # Nodes in a specific lane
                lane_id = f"Lane{lane_key.replace(' ', '')}"
                lines.append(f"    subgraph {lane_id}[\"{lane_key}\"]")
                lines.append("      direction LR")
                for nid in node_ids:
                    node = pir.nodes[nid]
                    label = node.name or nid
                    if node.kind.endswith("Gateway") or node.kind in {"exclusiveGateway", "parallelGateway"}:
                        lines.append(f"      {nid}{{\"{label}\"}}")
                    else:
                        lines.append(f"      {nid}[\"{label}\"]")
                lines.append("    end")
        
        lines.append("  end")
        lines.append("")
    
    # Generate unorganized nodes (no pool/lane)
    if unorganized_nodes:
        lines.append("  %% Unorganized nodes")
        for nid in unorganized_nodes:
            node = pir.nodes[nid]
            label = node.name or nid
            if node.kind.endswith("Gateway") or node.kind in {"exclusiveGateway", "parallelGateway"}:
                lines.append(f"  {nid}{{\"{label}\"}}")
            else:
                lines.append(f"  {nid}[\"{label}\"]")
        lines.append("")
    
    # Generate edges (including cross-pool/lane flows)
    if pir.edges:
        lines.append("  %% Flows")
        for e in pir.edges:
            src_node = pir.nodes.get(e.src)
            dst_node = pir.nodes.get(e.dst)
            
            # Determine if this is a cross-pool or cross-lane flow
            is_cross_flow = False
            if src_node and dst_node:
                # Cross-pool flow: different pools, or one has pool and other doesn't
                if src_node.pool != dst_node.pool:
                    is_cross_flow = True
                # Cross-lane flow within same pool
                elif src_node.pool == dst_node.pool and src_node.lane != dst_node.lane:
                    is_cross_flow = True
            
            # Use dotted line for cross-pool/lane messages, solid for internal flows
            if is_cross_flow:
                if e.guard:
                    lines.append(f"  {e.src} -.{e.guard}.-> {e.dst}")
                else:
                    lines.append(f"  {e.src} -. message .-> {e.dst}")
            else:
                if e.guard:
                    lines.append(f"  {e.src} -->|{e.guard}| {e.dst}")
                else:
                    lines.append(f"  {e.src} --> {e.dst}")
    
    # Add optional styling for pools and lanes
    if pools:
        lines.append("")
        lines.append("  %% Styling")
        for pool_name in pools.keys():
            pool_id = f"Pool{pool_name.replace(' ', '')}"
            lines.append(f"  style {pool_id} fill:#f8f8f8,stroke:#bbb,stroke-width:1px")
            
            for lane_key in pools[pool_name].keys():
                if lane_key != "_direct_pool_":
                    lane_id = f"Lane{lane_key.replace(' ', '')}"
                    lines.append(f"  style {lane_id} fill:#ffffff,stroke:#ddd")
    
    return "\n".join(lines)


def pir_to_cytoscape(pir: PIR) -> Dict[str, List[dict]]:
    nodes = [
        {
            "data": {
                "id": nid,
                "label": node.name or nid,
                "kind": node.kind,
                "lane": node.lane,
                "pool": node.pool,
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

