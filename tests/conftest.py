import pytest
from agentic_process_automation.core.unified_spec.models import WorkGraph

@pytest.fixture
def conditional_work_graph() -> WorkGraph:
    """Creates a WorkGraph with conditional execution bindings."""
    return WorkGraph(
        name="Conditional Test",
        case_schema={
            "type": "object",
            "properties": {
                "ticket": {
                    "type": "object",
                    "properties": {"priority": {"type": "string"}, "status": {"type": "string"}}
                }
            }
        },
        work_units=[
            {
                "name": "Handle Ticket",
                "goal_tag": "ticket_handling",
                "done_condition": "SELECT 1 FROM ticket WHERE status = 'done'"
            }
        ],
        execution_bindings=[
            {
                "goal_tag": "ticket_handling",
                "executor": "human",
                "condition": "SELECT 1 FROM ticket WHERE priority = 'high'"
            },
            {
                "goal_tag": "ticket_handling",
                "executor": "ai_agent",
                "condition": "SELECT 1 FROM ticket WHERE priority = 'low'"
            },
            {
                "goal_tag": "ticket_handling",
                "executor": "system",
                "condition": "True" # Default fallback
            }
        ]
    )
