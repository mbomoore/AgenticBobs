#!/usr/bin/env python3
"""
Test script for the cycle handling in BPMN layout engine.
Tests the problematic cyclic workflow provided by the user.
"""

import sys
from pathlib import Path

# Add the project paths to sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root / "backend"))

from bpmn_layout import add_layout_to_bpmn

# The problematic BPMN XML with cycles provided by the user
cyclic_bpmn_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI" xmlns:dc="http://www.omg.org/spec/DD/20100524/DC" xmlns:di="http://www.omg.org/spec/DD/20100524/DI" id="Definitions_1" targetNamespace="http://bpmn.io/schema/bpmn" exporter="Camunda Modeler" exporterVersion="5.15.0">
  <bpmn:process id="Process_1" isExecutable="true">
    <bpmn:startEvent id="StartEvent_1">
      <bpmn:outgoing>Flow_1</bpmn:outgoing>
    </bpmn:startEvent>
    <bpmn:task id="Task_Engineer" name="Engineer reviews requirements">
      <bpmn:incoming>Flow_1</bpmn:incoming>
      <bpmn:incoming>Flow_3</bpmn:incoming>
      <bpmn:outgoing>Flow_2</bpmn:outgoing>
    </bpmn:task>
    <bpmn:intermediateCatchEvent id="CatchEvent_Exception" name="Exception caught">
      <bpmn:incoming>Flow_2</bpmn:incoming>
      <bpmn:outgoing>Flow_4</bpmn:outgoing>
      <bpmn:errorEventDefinition />
    </bpmn:intermediateCatchEvent>
    <bpmn:task id="Task_ContactCustomer" name="Contact customer for clarification">
      <bpmn:incoming>Flow_4</bpmn:incoming>
      <bpmn:outgoing>Flow_3</bpmn:outgoing>
    </bpmn:task>
    <bpmn:endEvent id="EndEvent_1">
      <bpmn:incoming>Flow_5</bpmn:incoming>
    </bpmn:endEvent>
    <bpmn:sequenceFlow id="Flow_1" sourceRef="StartEvent_1" targetRef="Task_Engineer" />
    <bpmn:sequenceFlow id="Flow_2" sourceRef="Task_Engineer" targetRef="CatchEvent_Exception" />
    <bpmn:sequenceFlow id="Flow_3" sourceRef="Task_ContactCustomer" targetRef="Task_Engineer" />
    <bpmn:sequenceFlow id="Flow_4" sourceRef="CatchEvent_Exception" targetRef="Task_ContactCustomer" />
    <bpmn:sequenceFlow id="Flow_5" sourceRef="Task_Engineer" targetRef="EndEvent_1" />
  </bpmn:process>
</bpmn:definitions>'''

def test_cycle_handling():
    print("Testing cycle handling in BPMN layout engine...")
    
    try:
        # Test with the improved cycle handling
        result_xml = add_layout_to_bpmn(cyclic_bpmn_xml, layout_algorithm='dot')
        
        print("✅ SUCCESS: Cycle handling completed without errors")
        print("✅ Layout applied to cyclic workflow")
        
        # Check if the result contains proper coordinates
        if 'x=' in result_xml and 'y=' in result_xml:
            print("✅ Coordinates found in the result")
        else:
            print("❌ No coordinates found in the result")
            
        # Save the result for inspection
        with open('/Users/marshallomoore/Desktop/ProjectsLocal/AgenticBobs/test_cycle_result.bpmn', 'w') as f:
            f.write(result_xml)
        print("✅ Result saved to test_cycle_result.bpmn")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

if __name__ == "__main__":
    success = test_cycle_handling()
    if success:
        print("\n🎉 Cycle handling test PASSED!")
    else:
        print("\n💥 Cycle handling test FAILED!")
