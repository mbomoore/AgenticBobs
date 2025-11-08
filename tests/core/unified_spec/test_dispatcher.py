import json
import os
import pytest
from agentic_process_automation.core.unified_spec.models import WorkGraph, WorkItem
from agentic_process_automation.core.unified_spec.dispatcher import Dispatcher
from agentic_process_automation.core.unified_spec.executors import HumanExecutor, get_executor

@pytest.fixture
def customer_support_work_graph() -> WorkGraph:
    """Loads the customer_support.json example."""
    path = os.path.join(os.path.dirname(__file__), "../../../examples/unified_spec/customer_support.json")
    with open(path) as f:
        data = json.load(f)
    return WorkGraph(**data)

def test_dispatcher_resolution(customer_support_work_graph: WorkGraph):
    """Tests that the dispatcher correctly resolves executors."""
    dispatcher = Dispatcher(customer_support_work_graph)

    # Test resolution for each goal tag
    work_items = [
        WorkItem(work_unit_name="categorize_ticket", parameters={}),
        WorkItem(work_unit_name="assign_billing_ticket", parameters={}),
        WorkItem(work_unit_name="resolve_ticket_by_human", parameters={}),
        WorkItem(work_unit_name="send_resolution_email", parameters={})
    ]

    expected_executors = ["ai_agent", "ai_agent", "human", "system"]

    for item, expected in zip(work_items, expected_executors):
        assert dispatcher.resolve_executor(item) == expected

def test_human_executor(tmp_path):
    """Tests that the HumanExecutor logs tasks to a file."""
    task_file = tmp_path / "human_tasks.log"
    executor = HumanExecutor(task_file=str(task_file))
    work_item = WorkItem(work_unit_name="resolve_ticket_by_human", parameters={"ticket_id": 123})

    executor.execute(work_item)

    assert task_file.exists()
    with open(task_file) as f:
        log_content = f.read()
        log_data = json.loads(log_content)
        assert log_data["work_unit_name"] == "resolve_ticket_by_human"
        assert log_data["parameters"]["ticket_id"] == 123

def test_get_executor_factory():
    """Tests the get_executor factory function."""
    assert isinstance(get_executor("human"), HumanExecutor)
    with pytest.raises(ValueError):
        get_executor("non_existent_executor")
