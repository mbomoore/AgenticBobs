import pytest
from agentic_process_automation.core.unified_spec.models import (
    Case,
    View,
    WorkUnit,
    Combinator,
    ExecutionBinding,
    WorkGraph,
)

# Define the canonical "RFP Triage" WorkGraph as a test fixture
@pytest.fixture
def rfp_triage_work_graph() -> WorkGraph:
    """Provides a complete WorkGraph spec for the RFP Triage example."""
    return WorkGraph(
        name="RFP Triage Process",
        case_schema={
            "RFPs": {
                "id": str,
                "status": str,
                "value_estimate": int,
                "client_id": str,
            },
            "Clients": {"id": str, "name": str, "priority": str},
            "Decisions": {
                "id": str,
                "rfp_id": str,
                "outcome": str,
                "confidence": float,
            },
        },
        views=[
            View(
                name="new_rfps",
                query="SELECT * FROM RFPs WHERE status = 'new'",
            ),
            View(
                name="rfp_decision",
                query="SELECT * FROM Decisions WHERE rfp_id = :rfp_id",
            ),
        ],
        work_units=[
            WorkUnit(
                name="assess_rfp",
                goal_tag="assess_rfp",
                inputs=["new_rfps"],
                outputs=["rfp_decision"],
                done_condition="SELECT * FROM Decisions WHERE rfp_id = :rfp_id AND outcome IN ['go', 'no_go']",
                quality_condition="SELECT * FROM Decisions WHERE rfp_id = :rfp_id AND confidence >= 0.8",
            )
        ],
        combinators=[
            Combinator(
                type="map",
                work_unit="assess_rfp",
                over="SELECT id AS rfp_id FROM RFPs WHERE status = 'new'",
            )
        ],
        execution_bindings=[
            ExecutionBinding(
                goal_tag="assess_rfp",
                executor="ai_agent",
                condition="SELECT * FROM RFPs WHERE id = :rfp_id AND value_estimate < 50000",
            ),
            ExecutionBinding(
                goal_tag="assess_rfp",
                executor="human",
                condition="SELECT * FROM RFPs WHERE id = :rfp_id AND value_estimate >= 50000",
            ),
        ],
    )


from agentic_process_automation.core.unified_spec.interpreter import Interpreter


def test_work_graph_loads_successfully(rfp_triage_work_graph: WorkGraph):
    """
    Tests that the rfp_triage_work_graph fixture is a valid WorkGraph model.
    """
    assert rfp_triage_work_graph is not None
    assert rfp_triage_work_graph.name == "RFP Triage Process"
    assert len(rfp_triage_work_graph.work_units) == 1
    assert rfp_triage_work_graph.work_units[0].name == "assess_rfp"


def test_interpreter_identifies_initial_ready_work_unit(rfp_triage_work_graph: WorkGraph):
    """
    Tests that the interpreter correctly identifies the first ready WorkUnit.
    """
    # This case has one RFP that is 'new' and has no decision yet.
    case = Case(
        schema_=rfp_triage_work_graph.case_schema,
        data={
            "RFPs": [
                {"id": "rfp-001", "status": "new", "value_estimate": 60000, "client_id": "client-abc"},
            ],
            "Clients": [{"id": "client-abc", "name": "Big Corp", "priority": "high"}],
            "Decisions": [],
        },
    )

    interpreter = Interpreter(work_graph=rfp_triage_work_graph, case=case)
    ready_work_items = interpreter.tick()

    assert len(ready_work_items) == 1
    assert ready_work_items[0].work_unit_name == "assess_rfp"
    assert ready_work_items[0].parameters == {"rfp_id": "rfp-001"}
