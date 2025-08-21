import pytest
from typing import Any, cast

from agentic_process_automation.core.pir import PIR, PIRBuilder, validate


def test_archimate_nodes_and_relations_basic():
    """Archimate-like elements should be attachable without breaking validation.

    This test verifies that:
    - Nodes can carry notation/type/parent/props without affecting core validation.
    - Undirected edges (e.g., ArchiMate structural relations) do not trigger reachability warnings.
    """
    pir = PIR()
    b = PIRBuilder(pir)

    # Create two ArchiMate elements via builder using extended kwargs
    b.add_node(
        id="bp1",
        kind="BusinessProcess",
        name="Fulfill Order",
        notation="archimate",
        type="archimate:BusinessProcess",
        parent=None,
        props={"layer": "business"},
    )
    b.add_node(
        id="as1",
        kind="ApplicationService",
        name="Order API",
        notation="archimate",
        type="archimate:ApplicationService",
        parent=None,
        props={"interfaceType": "REST"},
    )

    # An undirected relation (e.g., Access/Association) should not contribute to reachability
    b.add_edge(
        src="bp1",
        dst="as1",
        relation="archimate:Association",
        directed=False,
    )

    report = validate(pir)
    # Should not error; and should not warn about reachability/isolated due to undirected-only relations
    assert report["errors"] == []
    assert not any("Unreachable nodes" in w or "Isolated nodes" in w for w in report["warnings"])


def test_views_and_mappings_storage():
    """Views and mappings can be stored on the PIR for diagram-specific selections and cross-notation traceability."""
    pir = PIR()
    b = PIRBuilder(pir)
    # Create simple BPMN nodes to keep validation trivial
    b.add_node(id="n1", kind="task", name="Do X")
    b.add_node(id="n2", kind="task", name="Do Y")
    b.add_edge(src="n1", dst="n2")

    # Attach a view-like structure via PIR.views
    cast(Any, pir).views["business_view"] = {
        "id": "business_view",
        "name": "Business Layer",
        "viewpoint": "Layered",
        "nodes": ["n1"],
        "edges": [],
        "props": {"layout": "grid"},
    }

    # Cross-notation mapping: BPMN task realizes an ArchiMate service
    cast(Any, pir).mappings["n1"] = ["as1"]

    report = validate(pir)
    assert report["errors"] == []

    # Views/mappings preserved
    assert "business_view" in cast(Any, pir).views
    assert cast(Any, pir).mappings["n1"] == ["as1"]
