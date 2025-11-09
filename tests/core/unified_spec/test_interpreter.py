import pytest
from agentic_process_automation.core.unified_spec.models import (
    Case,
    WorkGraph,
)
from agentic_process_automation.core.unified_spec.interpreter import Interpreter


def test_work_graph_loads_successfully(rfp_triage_work_graph: WorkGraph):
    """
    Tests that the rfp_triage_work_graph fixture is a valid WorkGraph model.
    """
    assert rfp_triage_work_graph is not None
    assert rfp_triage_work_graph.name == "RFP Triage"
    assert len(rfp_triage_work_graph.work_units) == 2
    assert rfp_triage_work_graph.work_units[0].name == "summarize_rfp"


def test_interpreter_identifies_initial_ready_work_unit(rfp_triage_work_graph: WorkGraph):
    """
    Tests that the interpreter correctly identifies the first ready WorkUnit.
    """
    # This case has one RFP that is 'new' and has no decision yet.
    case = Case(
        schema_=rfp_triage_work_graph.case_schema,
        data={
            "rfps": [
                {"id": "rfp-001", "status": "scored", "value_estimate": 60000, "client_id": "client-abc", "summary": "A summary"},
            ],
            "Clients": [{"id": "client-abc", "name": "Big Corp", "priority": "high"}],
            "Decisions": [],
        },
    )

    interpreter = Interpreter(work_graph=rfp_triage_work_graph, case=case)
    ready_work_items = interpreter.tick()

    assert len(ready_work_items) == 1
    assert ready_work_items[0].work_unit_name == "score_rfp"
    assert ready_work_items[0].parameters == {"rfp_id": "rfp-001"}
