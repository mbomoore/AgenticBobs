from agentic_process_automation.core.pir import PIRBuilder
from agentic_process_automation.core.semantics import Token, SimState, next_enabled, step


def build_linear_pir():
    b = PIRBuilder()
    b.add_node(id="A", kind="task", name="A")
    b.add_node(id="B", kind="task", name="B")
    b.add_node(id="C", kind="task", name="C")
    b.add_edge(src="A", dst="B")
    b.add_edge(src="B", dst="C")
    return b.build()


def test_next_enabled_linear():
    pir = build_linear_pir()
    s = SimState(time=0.0, tokens=[Token("A")], queues={}, resources={})
    moves = next_enabled(pir, s)
    assert len(moves) == 1
    tok, dst = moves[0]
    assert tok.node_id == "A"
    assert dst == "B"


def test_step_advances_token():
    pir = build_linear_pir()
    s = SimState(time=0.0, tokens=[Token("A")], queues={}, resources={})
    move = next_enabled(pir, s)[0]
    s2 = step(pir, s, move)
    assert s2.tokens[0].node_id == "B"
    # original state remains unchanged (functional style)
    assert s.tokens[0].node_id == "A"


def test_branching_enables_multiple_moves():
    b = PIRBuilder()
    b.add_node(id="A", kind="gateway", name="A")
    b.add_node(id="B1", kind="task", name="B1")
    b.add_node(id="B2", kind="task", name="B2")
    b.add_edge(src="A", dst="B1")
    b.add_edge(src="A", dst="B2")
    pir = b.build()

    s = SimState(time=0.0, tokens=[Token("A")], queues={}, resources={})
    moves = next_enabled(pir, s)
    dsts = {m[1] for m in moves}
    assert dsts == {"B1", "B2"}


def test_dead_end_has_no_moves():
    b = PIRBuilder()
    b.add_node(id="A", kind="task", name="A")
    pir = b.build()
    s = SimState(time=0.0, tokens=[Token("A")], queues={}, resources={})
    assert next_enabled(pir, s) == []
