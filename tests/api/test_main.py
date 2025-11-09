import json
import os
from fastapi.testclient import TestClient
from agentic_process_automation.api.main import app
from agentic_process_automation.core.unified_spec.models import (
    WorkGraph,
    View,
    WorkUnit,
    ExecutionBinding,
    ExecutionRule,
)

client = TestClient(app)

def adapt_customer_support_spec(spec_dict: dict) -> WorkGraph:
    """Adapts the customer_support.json data to the new WorkGraph model."""
    for wu in spec_dict.get("work_units", []):
        wu.setdefault("params", {})
        wu.setdefault("preconditions", "True")
        wu.setdefault("done", wu.get("done_condition", "True"))
        wu.setdefault("inputs", [v["name"] for v in wu.get("input_views", [])])
        wu.setdefault("outputs", [])

    for v_dict in spec_dict.get("views", []):
        v_dict.setdefault("reads", [v_dict.get("query", "")])
        v_dict.setdefault("writes", [])
        v_dict.setdefault("invariants", [])

    bindings = []
    for b in spec_dict.get("execution_bindings", []):
        impl_kind = b.get("executor")
        if impl_kind == "ai_agent":
            impl_kind = "agent"
        elif impl_kind == "system":
            impl_kind = "agent"  # Or some other default
        bindings.append(ExecutionBinding(
            target=b.get("goal_tag"),
            rules=[
                ExecutionRule(
                    condition=b.get("condition") or "True",
                    impl_kind=impl_kind,
                )
            ]
        ))

    return WorkGraph(
        name=spec_dict.get("name"),
        case_schema=spec_dict.get("case_schema"),
        views=[View(**v) for v in spec_dict.get('views', [])],
        work_units=[WorkUnit(**wu) for wu in spec_dict.get('work_units', [])],
        execution_bindings=bindings,
    )

def test_load_workgraph():
    """Tests loading a WorkGraph."""
    path = os.path.join(os.path.dirname(__file__), "../../examples/unified_spec/customer_support.json")
    with open(path) as f:
        workgraph_content = json.load(f)

    adapted_workgraph = adapt_customer_support_spec(workgraph_content)

    response = client.post("/workgraph", json={"name": "customer_support", "content": adapted_workgraph.model_dump()})
    assert response.status_code == 200
    assert response.json() == {"message": "WorkGraph 'customer_support' loaded successfully."}

def test_create_case():
    """Tests creating a case."""
    # First, load a workgraph
    test_load_workgraph()

    response = client.post("/case?workgraph_name=customer_support")
    assert response.status_code == 200
    assert "case_id" in response.json()

def create_case_and_get_id(workgraph_name: str = "customer_support") -> str:
    """Helper function to create a case and return its ID."""
    # Ensure workgraph is loaded
    if workgraph_name == "customer_support":
        path = os.path.join(os.path.dirname(__file__), "../../examples/unified_spec/customer_support.json")
        with open(path) as f:
            workgraph_content = json.load(f)
        adapted_workgraph = adapt_customer_support_spec(workgraph_content)
        client.post("/workgraph", json={"name": "customer_support", "content": adapted_workgraph.model_dump()})
    # This is a bit of a hack for testing, but it works
    elif "content" in globals() and workgraph_name == "conditional_test":
        client.post("/workgraph", json={"name": "conditional_test", "content": globals()["content"]})

    # Create the case
    response = client.post(f"/case?workgraph_name={workgraph_name}")
    assert response.status_code == 200
    return response.json()["case_id"]

def test_get_case():
    """Tests getting a case."""
    case_id = create_case_and_get_id()

    response = client.get(f"/case/{case_id}")
    assert response.status_code == 200
    case_data = response.json()
    assert case_data["schema_"] is not None
    assert case_data["data"] is not None

def test_set_case_data():
    """Tests setting data for a case."""
    case_id = create_case_and_get_id()
    case_data = {"ticket": [{"priority": "high"}]}
    response = client.post(f"/case/{case_id}/data", json=case_data)
    assert response.status_code == 200

    # Verify the data was set
    response = client.get(f"/case/{case_id}")
    assert response.status_code == 200
    assert response.json()["data"] == case_data

def test_tick_case_dispatches_correctly(mocker, conditional_work_graph: WorkGraph):
    """Integration test to verify the /tick endpoint dispatches to the correct executor."""
    # Load the conditional workgraph
    globals()["content"] = conditional_work_graph.model_dump()
    client.post("/workgraph", json={"name": "conditional_test", "content": globals()["content"]})

    # Create a case for this workgraph
    case_id = create_case_and_get_id("conditional_test")

    # Set case data to trigger the 'human' executor
    case_data = {"ticket": [{"priority": "high"}]}
    client.post(f"/case/{case_id}/data", json=case_data)

    # Mock the HumanExecutor's execute method
    mock_execute = mocker.patch(
        "agentic_process_automation.core.unified_spec.executors.HumanExecutor.execute",
        return_value=None
    )

    # Tick the case
    response = client.post(f"/case/{case_id}/tick")
    assert response.status_code == 200

    # Assert that the HumanExecutor was called with the correct WorkItem
    mock_execute.assert_called_once()
    args, _ = mock_execute.call_args
    work_item = args[0]
    assert work_item.work_unit_name == "Handle Ticket"
