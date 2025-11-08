import json
import os
from fastapi.testclient import TestClient
from agentic_process_automation.api.main import app
from agentic_process_automation.core.unified_spec.models import WorkGraph

client = TestClient(app)

def test_load_workgraph():
    """Tests loading a WorkGraph."""
    path = os.path.join(os.path.dirname(__file__), "../../examples/unified_spec/customer_support.json")
    with open(path) as f:
        workgraph_content = json.load(f)

    response = client.post("/workgraph", json={"name": "customer_support", "content": workgraph_content})
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
        client.post("/workgraph", json={"name": "customer_support", "content": workgraph_content})
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
