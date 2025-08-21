import sys
import os
import pytest

# Ensure the project root is on sys.path so `core` can be imported during tests
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from agentic_process_automation.core.pir import PIRBuilder, validate, PIR, Node, Edge


def test_pir_validate_happy():
    b = PIRBuilder()
    b.add_node(id="n1", kind="task", name="Start")
    b.add_node(id="n2", kind="task", name="End")
    b.add_edge(src="n1", dst="n2")
    pir = b.build()
    r = validate(pir)
    assert r["errors"] == []


def test_pir_validate_broken_edge():
    b = PIRBuilder()
    b.add_node(id="n1", kind="task", name="Start")
    b.add_edge(src="n1", dst="missing")
    pir = b.build()
    r = validate(pir)
    assert r["errors"]


def test_pir_validate_duplicate_id_mismatch_rejection():
    # create a PIR where the dict key doesn't match node.id
    pir = PIR()
    pir.nodes["k1"] = Node(id="different", kind="task", name="M")
    r = validate(pir)
    assert any("Node id mismatch" in e for e in r["errors"]), r


def test_pir_validate_duplicate_id_acceptance():
    b = PIRBuilder()
    b.add_node(id="n1", kind="task", name="A")
    pir = b.build()
    r = validate(pir)
    assert not r["errors"]


def test_pir_validate_unreachable_nodes_rejection():
    # component A: a1 -> a2 (source exists)
    # component B: c1 <-> c2 (cycle, no source) -> should be unreachable
    pir = PIR()
    pir.nodes["a1"] = Node(id="a1", kind="task", name="a1")
    pir.nodes["a2"] = Node(id="a2", kind="task", name="a2")
    pir.nodes["c1"] = Node(id="c1", kind="task", name="c1")
    pir.nodes["c2"] = Node(id="c2", kind="task", name="c2")
    pir.edges.append(Edge(src="a1", dst="a2"))
    pir.edges.append(Edge(src="c1", dst="c2"))
    pir.edges.append(Edge(src="c2", dst="c1"))

    r = validate(pir)
    assert any("Unreachable nodes" in w for w in r["warnings"]), r


def test_pir_validate_unreachable_nodes_acceptance():
    b = PIRBuilder()
    b.add_node(id="n1", kind="task", name="n1")
    b.add_node(id="n2", kind="task", name="n2")
    b.add_node(id="n3", kind="task", name="n3")
    b.add_edge(src="n1", dst="n2")
    b.add_edge(src="n2", dst="n3")
    pir = b.build()
    r = validate(pir)
    assert not any("Unreachable nodes" in w for w in r["warnings"]) , r


def test_pir_validate_isolated_node_rejection():
    b = PIRBuilder()
    b.add_node(id="n1", kind="task", name="n1")
    b.add_node(id="iso", kind="task", name="iso")
    b.add_edge(src="n1", dst="n1")
    pir = b.build()
    r = validate(pir)
    assert any("Isolated nodes" in w for w in r["warnings"]), r


def test_pir_validate_isolated_node_acceptance():
    b = PIRBuilder()
    b.add_node(id="n1", kind="task", name="n1")
    b.add_node(id="n2", kind="task", name="n2")
    b.add_edge(src="n1", dst="n2")
    pir = b.build()
    r = validate(pir)
    assert not any("Isolated nodes" in w for w in r["warnings"]) , r
