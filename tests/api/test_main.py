import json
import os
from fastapi.testclient import TestClient
from agentic_process_automation.api.main import app

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

def create_case_and_get_id() -> str:
    """Helper function to create a case and return its ID."""
    # Ensure workgraph is loaded
    path = os.path.join(os.path.dirname(__file__), "../../examples/unified_spec/customer_support.json")
    with open(path) as f:
        workgraph_content = json.load(f)
    client.post("/workgraph", json={"name": "customer_support", "content": workgraph_content})

    # Create the case
    response = client.post("/case?workgraph_name=customer_support")
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


def test_tick_case():
    """Tests ticking a case."""
    case_id = create_case_and_get_id()

    response = client.post(f"/case/{case_id}/tick")
    assert response.status_code == 200
    assert "message" in response.json()

def test_get_human_tasks():
    """Tests getting human tasks."""
    case_id = create_case_and_get_id()

    # Tick the case to generate tasks
    client.post(f"/case/{case_id}/tick")

    response = client.get(f"/case/{case_id}/tasks")
    assert response.status_code == 200
    tasks = response.json()
    assert isinstance(tasks, list)
