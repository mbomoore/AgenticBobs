from agentic_process_automation.core.unified_spec.dispatcher import Dispatcher
from agentic_process_automation.core.unified_spec.models import WorkGraph, WorkItem, Case

def test_dispatcher_simple_resolution(rfp_triage_work_graph: WorkGraph):
    """Tests that the dispatcher can resolve a simple, unconditional binding."""
    dispatcher = Dispatcher(rfp_triage_work_graph)
    work_item = WorkItem(work_unit_name="summarize_rfp", parameters={"rfp_id": 1})
    case = Case(schema_=rfp_triage_work_graph.case_schema, data={})

    executor = dispatcher.resolve_executor(work_item, case)
    assert executor == "agent"

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
    assert dispatcher.resolve_executor(work_item, low_priority_case) == "agent"
