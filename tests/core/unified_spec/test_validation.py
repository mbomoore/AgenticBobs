import pytest
from pydantic import ValidationError

from src.agentic_process_automation.core.unified_spec.models import (
    View,
    WorkUnit,
    ExecutionBinding,
    Spec,
)


def test_view_model_enhancements():
    """Tests that the View model can be instantiated with new fields."""
    view_data = {
        "name": "test_view",
        "reads": ["RFP.*"],
        "writes": ["Decision.outcome"],
        "invariants": ["RFP.id > 0"],
    }
    view = View(**view_data)
    assert view.name == "test_view"
    assert view.reads == ["RFP.*"]
    assert view.writes == ["Decision.outcome"]
    assert view.invariants == ["RFP.id > 0"]


def test_work_unit_model_enhancements():
    """Tests that the WorkUnit model can be instantiated with new fields."""
    work_unit_data = {
        "name": "test_wu",
        "params": {"rfp_id": "RFP.id"},
        "inputs": ["view1"],
        "outputs": ["view2"],
        "preconditions": "RFP.status == 'new'",
        "done": "Decision.outcome is not None",
        "quality": "Decision.confidence > 0.9",
        "write_set": ["Decision.outcome"],
        "side_effects": "none",
        "idempotent": True,
        "conflict_policy": "merge",
        "termination_measure": "retries < 3",
    }
    work_unit = WorkUnit(**work_unit_data)
    assert work_unit.name == "test_wu"


def test_spec_model_and_validation():
    """Tests the new Spec model and its validation logic."""
    spec_data = {
        "views": {
            "view1": {"name": "view1", "reads": [], "writes": []},
        },
        "work_units": {
            "wu1": {
                "name": "wu1",
                "params": {},
                "inputs": ["view1", "non_existent_view"],
                "outputs": [],
                "preconditions": "True",
                "done": "False",
            }
        },
    }
    with pytest.raises(ValidationError, match="references missing View 'non_existent_view'"):
        Spec(**spec_data)


def test_execution_binding_and_rule_models():
    """Tests the new ExecutionRule and ExecutionBinding models."""
    binding_data = {
        "target": "assess_rfp",
        "rules": [
            {
                "condition": "RFP.value < 50000",
                "impl_kind": "agent",
                "token_limit": 8192,
                "tool_schemas": ["search"],
                "privacy_level": "internal",
                "approval_policy": "auto",
            }
        ],
    }
    binding = ExecutionBinding(**binding_data)
    assert binding.target == "assess_rfp"
    assert len(binding.rules) == 1
    assert binding.rules[0].impl_kind == "agent"
