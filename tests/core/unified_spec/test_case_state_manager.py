import pytest

from agentic_process_automation.core.unified_spec.models import Case, WorkGraph
from agentic_process_automation.core.unified_spec.case_state_manager import CaseStateManager


@pytest.fixture
def initial_case(rfp_triage_work_graph: WorkGraph) -> Case:
    """Creates an initial Case instance for testing."""
    return Case(
        schema_=rfp_triage_work_graph.case_schema,
        data={
            "rfps": [
                {"id": 1, "title": "New RFP 1", "status": "new", "summary": None, "score": None},
                {"id": 2, "title": "New RFP 2", "status": "new", "summary": None, "score": None},
            ]
        },
    )


def test_case_state_manager_init(initial_case: Case):
    """Tests that the CaseStateManager can be initialized with a Case."""
    manager = CaseStateManager(initial_case)
    assert manager.case is initial_case


def test_case_state_manager_get_data(initial_case: Case):
    """Tests that the CaseStateManager can retrieve data from the Case."""
    manager = CaseStateManager(initial_case)
    rfps = manager.get_data("rfps")
    assert len(rfps) == 2
    assert rfps[0]["id"] == 1


def test_case_state_manager_update_data(initial_case: Case):
    """Tests that the CaseStateManager can update data in the Case."""
    manager = CaseStateManager(initial_case)
    manager.update_data("rfps", {"id": 1, "summary": "This is a summary."})
    rfps = manager.get_data("rfps")
    assert rfps[0]["summary"] == "This is a summary."
    assert rfps[1]["summary"] is None # ensure only the correct record was updated


def test_case_state_manager_update_nonexistent_entity(initial_case: Case):
    """Tests that updating a non-existent entity raises an error."""
    manager = CaseStateManager(initial_case)
    with pytest.raises(ValueError):
        manager.update_data("clients", {"id": 1, "name": "New Client"})
