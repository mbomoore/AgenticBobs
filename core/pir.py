from dataclasses import dataclass, field
from typing import Dict, List, Optional

from pydantic import BaseModel, ValidationError, Field
from pydantic import model_validator


@dataclass(frozen=True)
class Node:
    id: str
    kind: str
    name: str
    lane: Optional[str] = None
    policy_ref: Optional[str] = None


@dataclass(frozen=True)
class Edge:
    src: str
    dst: str
    guard: Optional[str] = None


@dataclass
class PIR:
    nodes: Dict[str, Node] = field(default_factory=dict)
    edges: List[Edge] = field(default_factory=list)
    resources: Dict[str, dict] = field(default_factory=dict)  # pools, skills
    metadata: Dict[str, str] = field(default_factory=dict)
    representations: Dict[str, str] = field(default_factory=dict)
    """Format-specific original representations attached to this PIR.

    Keys should be MIME-like format identifiers such as:
    - "bpmn+xml": original BPMN 2.0 XML (utf-8 text)
    - "dmn+xml": original DMN XML
    - "mermaid": Mermaid definition text
    - "json": arbitrary JSON serialization

    Values are textual payloads (str). Binary data should be encoded to text (e.g., utf-8 or base64).
    """


class PIRBuilder:
    def __init__(self, pir: Optional[PIR] = None):
        self.pir = pir or PIR()

    def add_node(self, **kw):
        self.pir.nodes[kw["id"]] = Node(**kw)
        return self

    def add_edge(self, **kw):
        self.pir.edges.append(Edge(**kw))
        return self

    def set_resource_pool(self, rid: str, cfg: dict):
        self.pir.resources[rid] = cfg
        return self

    def attach_representation(self, fmt: str, data: str):
        """Attach a format-specific original representation to the PIR.

        Parameters
        ----------
        fmt: str
            A short MIME-like identifier (e.g., "bpmn+xml", "dmn+xml", "mermaid").
        data: str
            The textual content for this representation.
        """
        self.pir.representations[fmt] = data
        return self

    def build(self) -> PIR:
        return self.pir


# Pydantic models used for validation and nicer error messages
class NodeModel(BaseModel):
    id: str
    kind: str
    name: str
    lane: Optional[str] = None
    policy_ref: Optional[str] = None


class EdgeModel(BaseModel):
    src: str
    dst: str
    guard: Optional[str] = None


class PIRModel(BaseModel):
    nodes: Dict[str, NodeModel]
    edges: List[EdgeModel]
    resources: Dict[str, dict] = Field(default_factory=dict)
    metadata: Dict[str, str] = Field(default_factory=dict)
    representations: Dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def edges_refer_to_nodes(cls, values):
        nodes = values.nodes or {}
        edges = values.edges or []
        errors = []
        node_ids = set(nodes.keys())
        for e in edges:
            if e.src not in node_ids:
                errors.append(f"Edge src '{e.src}' is not a known node")
            if e.dst not in node_ids:
                errors.append(f"Edge dst '{e.dst}' is not a known node")
        if errors:
            raise ValueError("; ".join(errors))
        return values


def validate(pir: PIR) -> dict:
    """Validate a PIR using pydantic models and return a dict with errors/warnings.

    This function intentionally returns a simple dict so callers don't need
    to depend on Pydantic exceptions.
    """
    errors: List[str] = []
    warnings: List[str] = []
    try:
        # convert nodes/edges to serializable forms for Pydantic
        nodes = {
            nid: NodeModel(
                id=n.id,
                kind=n.kind,
                name=n.name,
                lane=n.lane,
                policy_ref=n.policy_ref,
            )
            for nid, n in pir.nodes.items()
        }

        edges = [
            EdgeModel(src=e.src, dst=e.dst, guard=e.guard)
            for e in pir.edges
        ]

        PIRModel(
            nodes=nodes,
            edges=edges,
            resources=pir.resources,
            metadata=pir.metadata,
            representations=pir.representations,
        )
    except ValidationError as ve:
        for err in ve.errors():
            errors.append(str(err))
    except ValueError as ve:
        errors.append(str(ve))

    # Additional light-weight checks beyond pydantic
    # 1) Duplicate id sanity: ensure stored key matches node.id
    for key, node in pir.nodes.items():
        if node.id != key:
            errors.append(f"Node id mismatch: dict key '{key}' != node.id '{node.id}'")

    # 2) Reachability: find nodes reachable from source nodes (in-degree == 0)
    node_ids = set(pir.nodes.keys())
    adj: Dict[str, List[str]] = {nid: [] for nid in node_ids}
    indeg: Dict[str, int] = {nid: 0 for nid in node_ids}
    for e in pir.edges:
        if e.src in adj:
            adj[e.src].append(e.dst)
        if e.dst in indeg:
            indeg[e.dst] += 1

    sources = [n for n, d in indeg.items() if d == 0]
    # if no explicit sources, pick an arbitrary node as start
    if not sources and node_ids:
        sources = [next(iter(node_ids))]

    # BFS
    reachable = set()
    stack = list(sources)
    while stack:
        cur = stack.pop()
        if cur in reachable:
            continue
        reachable.add(cur)
        for nb in adj.get(cur, []):
            if nb not in reachable:
                stack.append(nb)

    unreachable = sorted(list(node_ids - reachable))
    if unreachable:
        warnings.append(f"Unreachable nodes: {unreachable}")

    # 3) Isolated nodes (no in, no out)
    isolated = [n for n in node_ids if indeg.get(n, 0) == 0 and not adj.get(n)]
    if isolated:
        warnings.append(f"Isolated nodes (no in/out edges): {isolated}")

    return {"errors": errors, "warnings": warnings}
