from core.pir import PIRBuilder
from core.viz import pir_to_mermaid, pir_to_cytoscape


def _build_sample_pir():
    b = PIRBuilder()
    b.add_node(id="Start_1", kind="startEvent", name="Start")
    b.add_node(id="Task_A", kind="task", name="Do A")
    b.add_node(id="Gw_1", kind="exclusiveGateway", name="GW")
    b.add_node(id="Task_B", kind="task", name="Do B")
    b.add_node(id="End_1", kind="endEvent", name="End")

    b.add_edge(src="Start_1", dst="Task_A")
    b.add_edge(src="Task_A", dst="Gw_1")
    b.add_edge(src="Gw_1", dst="Task_B", guard="x > 1")
    b.add_edge(src="Task_B", dst="End_1")
    return b.build()


def test_pir_to_mermaid_contains_nodes_edges_and_guards():
    pir = _build_sample_pir()
    m = pir_to_mermaid(pir)
    assert m.startswith("flowchart TD")
    # Nodes present
    assert 'Start_1["Start"]' in m
    assert 'Task_B["Do B"]' in m
    # Edges present with guard annotation
    assert "Start_1 --> Task_A" in m
    assert "Gw_1 -->|x > 1| Task_B" in m


def test_pir_to_cytoscape_structure_and_counts():
    pir = _build_sample_pir()
    cs = pir_to_cytoscape(pir)
    assert set(cs.keys()) == {"nodes", "edges"}
    assert len(cs["nodes"]) == len(pir.nodes)
    assert len(cs["edges"]) == len(pir.edges)
    # Check one node shape
    node_ids = {n["data"]["id"] for n in cs["nodes"]}
    assert {"Start_1", "Task_A", "Gw_1", "Task_B", "End_1"}.issubset(node_ids)
    # Edge carries guard when present
    edge = next(e for e in cs["edges"] if e["data"]["source"] == "Gw_1")
    assert edge["data"].get("guard") == "x > 1"
