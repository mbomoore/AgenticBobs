import pytest
from agentic_process_automation.core.unified_spec.models import Case

def test_case_instantiation():
    """
    Tests that a Case can be instantiated with a valid schema and data.
    This test also serves as basic documentation for how to create a Case.
    """
    case_schema = {
        "clients": {"name": "str", "id": "int"},
        "rfps": {"status": "str", "value": "float"}
    }
    case_data = {
        "clients": [{"name": "Acme Corp", "id": 1}],
        "rfps": [{"status": "new", "value": 10000.0}]
    }

    case = Case(schema_=case_schema, data=case_data)

    assert case.schema_ == case_schema
    assert case.data == case_data

def test_case_default_data():
    """
    Tests that a Case can be instantiated with just a schema, and the data
    field defaults to an empty dictionary.
    """
    case_schema = {
        "clients": {"name": "str", "id": "int"}
    }

    case = Case(schema_=case_schema)

    assert case.schema_ == case_schema
    assert case.data == {}

def test_case_instantiation_with_invalid_data():
    """
    Tests that pydantic raises a validation error when data does not match
    the schema (in a real implementation, this would be enforced by a
    validation layer, but for now we just test pydantic's behavior).
    """
    # NOTE: This is a placeholder for a more robust validation mechanism.
    # Pydantic itself does not enforce the schema on the data dictionary.
    # A proper implementation would require a custom validator.
    # For now, we just test that we can instantiate with mismatched data.
    case_schema = {
        "clients": {"name": "str", "id": "int"}
    }
    case_data = {
        "clients": [{"name": "Acme Corp", "id": "not_an_int"}]
    }

    case = Case(schema_=case_schema, data=case_data)
    assert case.data["clients"][0]["id"] == "not_an_int"

from agentic_process_automation.core.unified_spec.models import View

def test_view_instantiation():
    """
    Tests that a View can be instantiated with valid data.
    This test also serves as basic documentation for how to create a View.
    """
    view = View(
        name="new_rfps",
        query="SELECT * FROM rfps WHERE status = 'new'"
    )

    assert view.name == "new_rfps"
    assert view.query == "SELECT * FROM rfps WHERE status = 'new'"

from agentic_process_automation.core.unified_spec.models import WorkUnit

def test_workunit_instantiation():
    """
    Tests that a WorkUnit can be instantiated with valid data.
    This test also serves as basic documentation for how to create a WorkUnit.
    """
    work_unit = WorkUnit(
        name="evaluate_rfp",
        goal_tag="evaluate_rfp",
        inputs=["new_rfps"],
        outputs=["evaluated_rfps"],
        done_condition="rfps.status == 'evaluated'",
        quality_condition="rfps.value > 0"
    )

    assert work_unit.name == "evaluate_rfp"
    assert work_unit.goal_tag == "evaluate_rfp"
    assert work_unit.inputs == ["new_rfps"]
    assert work_unit.outputs == ["evaluated_rfps"]
    assert work_unit.done_condition == "rfps.status == 'evaluated'"
    assert work_unit.quality_condition == "rfps.value > 0"

def test_workunit_optional_fields():
    """
    Tests that a WorkUnit can be instantiated without optional fields.
    """
    work_unit = WorkUnit(
        name="evaluate_rfp",
        goal_tag="evaluate_rfp",
        done_condition="rfps.status == 'evaluated'"
    )

    assert work_unit.name == "evaluate_rfp"
    assert work_unit.goal_tag == "evaluate_rfp"
    assert work_unit.inputs == []
    assert work_unit.outputs == []
    assert work_unit.done_condition == "rfps.status == 'evaluated'"
    assert work_unit.quality_condition is None

from agentic_process_automation.core.unified_spec.models import Combinator

def test_combinator_instantiation():
    """
    Tests that a Combinator can be instantiated with valid data.
    This test also serves as basic documentation for how to create a Combinator.
    """
    combinator = Combinator(
        type="map",
        work_unit="evaluate_rfp",
        over="new_rfps"
    )

    assert combinator.type == "map"
    assert combinator.work_unit == "evaluate_rfp"
    assert combinator.over == "new_rfps"

from agentic_process_automation.core.unified_spec.models import ExecutionBinding

def test_execution_binding_instantiation():
    """
    Tests that an ExecutionBinding can be instantiated with valid data.
    This test also serves as basic documentation for how to create an ExecutionBinding.
    """
    binding = ExecutionBinding(
        goal_tag="evaluate_rfp",
        executor="human",
        condition="rfps.value > 10000"
    )

    assert binding.goal_tag == "evaluate_rfp"
    assert binding.executor == "human"
    assert binding.condition == "rfps.value > 10000"

def test_execution_binding_optional_fields():
    """
    Tests that an ExecutionBinding can be instantiated without optional fields.
    """
    binding = ExecutionBinding(
        goal_tag="evaluate_rfp",
        executor="ai_agent"
    )

    assert binding.goal_tag == "evaluate_rfp"
    assert binding.executor == "ai_agent"
    assert binding.condition is None

from agentic_process_automation.core.unified_spec.models import WorkGraph

def test_workgraph_instantiation():
    """
    Tests that a WorkGraph can be instantiated with valid data, including nested models.
    This also serves as a basic integration test of the core models.
    """
    case_schema = {
        "rfps": {"status": "str", "value": "float"}
    }

    views = [
        View(name="new_rfps", query="SELECT * FROM rfps WHERE status = 'new'")
    ]

    work_units = [
        WorkUnit(
            name="evaluate_rfp",
            goal_tag="evaluate_rfp",
            inputs=["new_rfps"],
            outputs=[],
            done_condition="rfps.status == 'evaluated'"
        )
    ]

    combinators = [
        Combinator(type="map", work_unit="evaluate_rfp", over="new_rfps")
    ]

    execution_bindings = [
        ExecutionBinding(goal_tag="evaluate_rfp", executor="human")
    ]

    work_graph = WorkGraph(
        name="rfp_triage",
        case_schema=case_schema,
        views=views,
        work_units=work_units,
        combinators=combinators,
        execution_bindings=execution_bindings
    )

    assert work_graph.name == "rfp_triage"
    assert work_graph.case_schema == case_schema
    assert len(work_graph.views) == 1
    assert work_graph.views[0].name == "new_rfps"
    assert len(work_graph.work_units) == 1
    assert work_graph.work_units[0].name == "evaluate_rfp"
    assert len(work_graph.combinators) == 1
    assert work_graph.combinators[0].type == "map"
    assert len(work_graph.execution_bindings) == 1
    assert work_graph.execution_bindings[0].executor == "human"

def test_unified_spec_integration():
    """
    Tests the integration of the unified spec models in a more complex scenario.
    """
    # 1. Define the Case Schema
    case_schema = {
        "rfps": {"id": "int", "status": "str", "value": "float", "summary": "str"},
        "evaluations": {"rfp_id": "int", "score": "float", "is_approved": "bool"}
    }

    # 2. Define Views
    views = [
        View(name="new_rfps", query="SELECT * FROM rfps WHERE status = 'new'"),
        View(name="summarized_rfps", query="SELECT * FROM rfps WHERE status = 'summarized'"),
        View(name="evaluated_rfps", query="SELECT * FROM evaluations")
    ]

    # 3. Define WorkUnits
    work_units = [
        WorkUnit(
            name="summarize_rfp",
            goal_tag="summarize",
            inputs=["new_rfps"],
            outputs=["summarized_rfps"],
            done_condition="rfps.status == 'summarized'"
        ),
        WorkUnit(
            name="evaluate_rfp",
            goal_tag="evaluate",
            inputs=["summarized_rfps"],
            outputs=["evaluated_rfps"],
            done_condition="evaluations.rfp_id == rfps.id"
        )
    ]

    # 4. Define Combinators
    combinators = [
        Combinator(type="map", work_unit="summarize_rfp", over="new_rfps"),
        Combinator(type="map", work_unit="evaluate_rfp", over="summarized_rfps")
    ]

    # 5. Define Execution Bindings
    execution_bindings = [
        ExecutionBinding(goal_tag="summarize", executor="ai_agent"),
        ExecutionBinding(goal_tag="evaluate", executor="human", condition="rfps.value > 50000"),
        ExecutionBinding(goal_tag="evaluate", executor="ai_agent", condition="rfps.value <= 50000")
    ]

    # 6. Create the WorkGraph
    work_graph = WorkGraph(
        name="rfp_processing_pipeline",
        case_schema=case_schema,
        views=views,
        work_units=work_units,
        combinators=combinators,
        execution_bindings=execution_bindings
    )

    # 7. Assertions
    assert work_graph.name == "rfp_processing_pipeline"
    assert len(work_graph.views) == 3
    assert len(work_graph.work_units) == 2
    assert len(work_graph.combinators) == 2
    assert len(work_graph.execution_bindings) == 3

    # Check some relationships
    summarize_wu = work_graph.work_units[0]
    evaluate_wu = work_graph.work_units[1]

    assert summarize_wu.inputs[0] == "new_rfps"
    assert evaluate_wu.inputs[0] == "summarized_rfps"

    summarize_binding = work_graph.execution_bindings[0]
    assert summarize_binding.goal_tag == "summarize"

    evaluate_binding_human = work_graph.execution_bindings[1]
    assert evaluate_binding_human.goal_tag == "evaluate"
    assert evaluate_binding_human.executor == "human"
