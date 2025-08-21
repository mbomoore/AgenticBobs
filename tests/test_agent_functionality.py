"""Test the agent functionality specifically."""

import pytest
import sys
import os
from agentic_process_automation.core.ai import validate_bpmn_tool, get_available_tools, register_tool
from icecream import ic

def test_validate_bpmn_tool_registration():
    """Test that the validate_bpmn tool is properly registered."""
    tools = get_available_tools()
    assert "validate_bpmn" in tools
    assert callable(tools["validate_bpmn"])


def test_validate_bpmn_tool_valid_bpmn():
    """Test validation with valid BPMN."""
    valid_bpmn = """<?xml version="1.0" encoding="UTF-8"?>
<definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL" id="Defs_Sample">
    <process id="Proc_Sample" isExecutable="false">
        <startEvent id="Start_1" name="Start" />
        <task id="Task_A" name="Do A" />
        <endEvent id="End_1" name="End" />
        <sequenceFlow id="f1" sourceRef="Start_1" targetRef="Task_A" />
        <sequenceFlow id="f2" sourceRef="Task_A" targetRef="End_1" />
    </process>
</definitions>"""
    
    result = validate_bpmn_tool(valid_bpmn)
    
    
    ic(result)
    assert result["success"] is True
    assert result["errors"] == []


def test_validate_bpmn_tool_invalid_bpmn():
    """Test validation with invalid BPMN (missing node reference)."""
    invalid_bpmn = """<?xml version="1.0" encoding="UTF-8"?>
<definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL" id="Defs_Sample">
    <process id="Proc_Sample" isExecutable="false">
        <startEvent id="Start_1" name="Start" />
        <sequenceFlow id="f1" sourceRef="Start_1" targetRef="MISSING_NODE" />
    </process>
</definitions>"""
    
    result = validate_bpmn_tool(invalid_bpmn)
    assert result["success"] is True  # Parse succeeds but validation fails
    assert len(result["errors"]) > 0
    assert "MISSING_NODE" in str(result["errors"])


def test_validate_bpmn_tool_malformed_xml():
    """Test validation with malformed XML."""
    malformed_xml = "<invalid>xml without closing tag"
    
    result = validate_bpmn_tool(malformed_xml)
    assert result["success"] is False
    assert "error" in result
    assert len(result["errors"]) > 0


def test_tool_registration_decorator():
    """Test the tool registration decorator works."""
    
    @register_tool("test_tool")
    def test_function(input_str: str) -> dict:
        return {"result": f"processed: {input_str}"}
    
    tools = get_available_tools()
    assert "test_tool" in tools
    
    # Test the registered tool
    result = tools["test_tool"]("hello")
    assert result == {"result": "processed: hello"}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])