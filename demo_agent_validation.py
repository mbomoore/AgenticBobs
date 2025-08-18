#!/usr/bin/env python3
"""Example demonstrating the BPMN validation agent capabilities."""

from core.ai import validate_bpmn_tool

# Example of BPMN with validation errors that the agent can detect and help fix
BROKEN_BPMN_EXAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL" id="Defs_Optimized" targetNamespace="http://bpmn.io/schema/bpmn">
   <process id="Process_1" isExecutable="false">
       <startEvent id="Start_Request" name="Application Request"/>
       <task id="Task_Review" name="Review Application"/>
       <intermediateThrowEvent id="Event_FollowUp" name="Follow-up (Check for Response)"/>
       <endEvent id="End_Approved" name="Approved"/>
       <endEvent id="End_Closed" name="Closed"/>
       
       <!-- This flow has errors: references non-existent nodes -->
       <sequenceFlow id="f1" sourceRef="Start_Request" targetRef="Task_Review"/>
       <sequenceFlow id="f2" sourceRef="Task_Review" targetRef="Event_FollowUp"/>
       <sequenceFlow id="f3" sourceRef="Event_FollowUp" targetRef="NONEXISTENT_NODE"/>
       <!-- End_Closed is isolated (no flows in or out) -->
   </process>
</definitions>"""

# Example of fixed BPMN 
FIXED_BPMN_EXAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL" id="Defs_Optimized" targetNamespace="http://bpmn.io/schema/bpmn">
   <process id="Process_1" isExecutable="false">
       <startEvent id="Start_Request" name="Application Request"/>
       <task id="Task_Review" name="Review Application"/>
       <intermediateThrowEvent id="Event_FollowUp" name="Follow-up (Check for Response)"/>
       <endEvent id="End_Approved" name="Approved"/>
       
       <!-- Fixed flows: proper connections -->
       <sequenceFlow id="f1" sourceRef="Start_Request" targetRef="Task_Review"/>
       <sequenceFlow id="f2" sourceRef="Task_Review" targetRef="Event_FollowUp"/>
       <sequenceFlow id="f3" sourceRef="Event_FollowUp" targetRef="End_Approved"/>
   </process>
</definitions>"""

def demonstrate_agent_validation():
    """Demonstrate how the agent can detect and help fix BPMN validation issues."""
    
    print("🤖 BPMN Validation Agent Demo")
    print("=" * 50)
    
    print("\n1. Testing BROKEN BPMN (with validation errors):")
    print("-" * 50)
    broken_result = validate_bpmn_tool(BROKEN_BPMN_EXAMPLE)
    print(f"✅ Parsing success: {broken_result['success']}")
    print(f"❌ Errors found: {len(broken_result['errors'])}")
    for i, error in enumerate(broken_result['errors'], 1):
        print(f"   {i}. {error}")
    print(f"⚠️  Warnings: {len(broken_result['warnings'])}")
    for i, warning in enumerate(broken_result['warnings'], 1):
        print(f"   {i}. {warning}")
    
    print("\n2. Testing FIXED BPMN (after agent correction):")
    print("-" * 50)
    fixed_result = validate_bpmn_tool(FIXED_BPMN_EXAMPLE)
    print(f"✅ Parsing success: {fixed_result['success']}")
    print(f"✅ Errors found: {len(fixed_result['errors'])}")
    print(f"⚠️  Warnings: {len(fixed_result['warnings'])}")
    for i, warning in enumerate(fixed_result['warnings'], 1):
        print(f"   {i}. {warning}")
    
    print("\n3. Agent Capabilities Summary:")
    print("-" * 50)
    print("✅ Detects invalid node references in sequence flows")
    print("✅ Identifies isolated nodes (no incoming/outgoing flows)")  
    print("✅ Finds unreachable nodes in process flow")
    print("✅ Supports intermediate events (intermediateThrowEvent, intermediateCatchEvent)")
    print("✅ Validates BPMN structure and connectivity")
    print("✅ Provides detailed error messages for fixing")
    
    print("\n🎯 In Agent Mode, the AI will:")
    print("- Automatically validate BPMN after each modification")
    print("- Receive feedback on validation errors and warnings")
    print("- Iteratively fix issues until BPMN validates successfully")
    print("- Support up to 5 iterations of automatic correction")

if __name__ == "__main__":
    demonstrate_agent_validation()