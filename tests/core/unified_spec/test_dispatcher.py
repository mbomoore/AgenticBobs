import json
import os
import pytest
from agentic_process_automation.core.unified_spec.models import WorkGraph, WorkItem, Case
from agentic_process_automation.core.unified_spec.dispatcher import Dispatcher

@pytest.fixture
def customer_support_work_graph() -> WorkGraph:
    """Loads the customer_support.json example."""
    path = os.path.join(os.path.dirname(__file__), "../../../examples/unified_spec/customer_support.json")
    with open(path) as f:
        data = json.load(f)
    return WorkGraph(**data)

def test_dispatcher_simple_resolution(customer_support_work_graph: WorkGraph):
    """Tests that the dispatcher correctly resolves executors without conditions."""
    dispatcher = Dispatcher(customer_support_work_graph)
    # This case is empty but conforms to the schema's top-level keys
    case_data = {"ticket": [], "audit_trail": []}
    case = Case(schema_=customer_support_work_graph.case_schema, data=case_data)

    work_items = [
        WorkItem(work_unit_name="Triage Ticket", parameters={}),
        WorkItem(work_unit_name="Route to Specialist", parameters={}),
        WorkItem(work_unit_name="Close Ticket", parameters={})
    ]
    expected_executors = ["ai_agent", "human", "system"]

    for item, expected in zip(work_items, expected_executors):
        assert dispatcher.resolve_executor(item, case) == expected

def test_dispatcher_conditional_resolution(conditional_work_graph: WorkGraph):
    """Tests that the dispatcher correctly resolves executors based on conditions."""
    dispatcher = Dispatcher(conditional_work_graph)
    work_item = WorkItem(work_unit_name="Handle Ticket", parameters={})

    # Test case 1: High priority ticket should go to a human
    high_priority_case = Case(
        schema_=conditional_work_graph.case_schema,
        data={"ticket": [{"priority": "high"}]}
    )
    assert dispatcher.resolve_executor(work_item, high_priority_case) == "human"

    # Test case 2: Low priority ticket should go to an AI agent
    low_priority_case = Case(
        schema_=conditional_work_graph.case_schema,
        data={"ticket": [{"priority": "low"}]}
    )
    assert dispatcher.resolve_executor(work_item, low_priority_case) == "ai_agent"

    # Test case 3: Medium priority should fall back to the system executor
    medium_priority_case = Case(
        schema_=conditional_work_graph.case_schema,
        data={"ticket": [{"priority": "medium"}]}
    )
    assert dispatcher.resolve_executor(work_item, medium_priority_case) == "system"
