import pytest
import json
from pathlib import Path
from src.agentic_process_automation.core.unified_spec.models import (
    Case,
    View,
    WorkUnit,
    Combinator,
    ExecutionBinding,
    WorkGraph,
)

def test_case_instantiation():
    """Tests that a Case can be instantiated with a valid schema."""
    case = Case(schema_={"clients": {"name": "str", "id": "int"}})
    assert case.schema_ == {"clients": {"name": "str", "id": "int"}}
    assert case.data == {}

def test_view_instantiation():
    """Tests that a View can be instantiated."""
    view = View(name="new_rfps", query="SELECT * FROM RFPs WHERE status = 'new'")
    assert view.name == "new_rfps"
    assert view.query == "SELECT * FROM RFPs WHERE status = 'new'"

def test_work_unit_instantiation():
    """Tests that a WorkUnit can be instantiated."""
    work_unit = WorkUnit(
        name="evaluate_rfp",
        goal_tag="evaluate_rfp",
        done_condition="rfp.status == 'evaluated'",
    )
    assert work_unit.name == "evaluate_rfp"
    assert work_unit.goal_tag == "evaluate_rfp"
    assert work_unit.done_condition == "rfp.status == 'evaluated'"

def test_combinator_instantiation():
    """Tests that a Combinator can be instantiated."""
    combinator = Combinator(
        type="map",
        work_unit="evaluate_rfp",
        over="SELECT id FROM RFPs WHERE status = 'new'",
    )
    assert combinator.type == "map"
    assert combinator.work_unit == "evaluate_rfp"
    assert combinator.over == "SELECT id FROM RFPs WHERE status = 'new'"

def test_execution_binding_instantiation():
    """Tests that an ExecutionBinding can be instantiated."""
    binding = ExecutionBinding(goal_tag="evaluate_rfp", executor="human")
    assert binding.goal_tag == "evaluate_rfp"
    assert binding.executor == "human"

def test_work_graph_instantiation():
    """Tests that a WorkGraph can be instantiated with nested models."""
    work_graph = WorkGraph(
        name="rfp_triage",
        case_schema={"rfps": {"id": "int", "status": "str"}},
        views=[
            View(name="new_rfps", query="SELECT * FROM rfps WHERE status = 'new'"),
        ],
        work_units=[
            WorkUnit(
                name="evaluate_rfp",
                goal_tag="evaluate_rfp",
                inputs=["new_rfps"],
                done_condition="rfp.status == 'evaluated'",
            ),
        ],
        execution_bindings=[
            ExecutionBinding(goal_tag="evaluate_rfp", executor="human"),
        ],
    )
    assert work_graph.name == "rfp_triage"
    assert len(work_graph.views) == 1
    assert len(work_graph.work_units) == 1
    assert len(work_graph.execution_bindings) == 1

def test_work_graph_serialization_json():
    """Tests that a WorkGraph can be serialized to and from JSON."""
    work_graph = WorkGraph(
        name="rfp_triage",
        case_schema={"rfps": {"id": "int", "status": "str"}},
        views=[
            View(name="new_rfps", query="SELECT * FROM rfps WHERE status = 'new'"),
        ],
    )
    json_data = work_graph.model_dump_json()
    reloaded_graph = WorkGraph.model_validate_json(json_data)
    assert reloaded_graph == work_graph

def test_work_graph_json_schema():
    """Tests that a JSON schema can be generated for the WorkGraph."""
    schema = WorkGraph.model_json_schema()
    assert schema["title"] == "WorkGraph"
    assert "case_schema" in schema["properties"]
    assert "views" in schema["properties"]
    assert "work_units" in schema["properties"]

def test_load_rfp_triage_example():
    """Tests that the rfp_triage.json example can be loaded."""
    example_path = Path(__file__).parent.parent.parent.parent / "examples" / "unified_spec" / "rfp_triage.json"
    assert example_path.exists(), "The example file rfp_triage.json does not exist."

    with open(example_path, "r") as f:
        json_data = f.read()

    work_graph = WorkGraph.model_validate_json(json_data)
    assert isinstance(work_graph, WorkGraph)
    assert work_graph.name == "RFP Triage"
    assert len(work_graph.views) == 2
    assert len(work_graph.work_units) == 2
    assert len(work_graph.combinators) == 2
    assert len(work_graph.execution_bindings) == 3
