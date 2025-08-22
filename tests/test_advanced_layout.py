#!/usr/bin/env python3
"""
Test the advanced BPMN layout algorithms with various workflow patterns.
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from bpmn_layout import add_layout_to_bpmn
import logging

# Enable detailed logging
logging.basicConfig(level=logging.INFO)

def test_simple_linear_workflow():
    """Test with a simple linear workflow."""
    print("\n=== Testing Simple Linear Workflow ===")
    bpmn_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL" id="Definitions_1">
  <process id="Process_1" isExecutable="false">
    <startEvent id="StartEvent_1" name="Start"/>
    <task id="Task_1" name="Task 1"/>
    <task id="Task_2" name="Task 2"/>
    <endEvent id="EndEvent_1" name="End"/>
    <sequenceFlow id="Flow_1" sourceRef="StartEvent_1" targetRef="Task_1"/>
    <sequenceFlow id="Flow_2" sourceRef="Task_1" targetRef="Task_2"/>
    <sequenceFlow id="Flow_3" sourceRef="Task_2" targetRef="EndEvent_1"/>
  </process>
</definitions>'''
    
    result = add_layout_to_bpmn(bpmn_xml, layout_algorithm='dot')
    
    # Check that positions were added
    if 'bpmndi:BPMNShape' in result and 'dc:Bounds' in result:
        print("✅ Layout successfully added to simple linear workflow")
        
        # Extract some position info for verification
        import xml.etree.ElementTree as ET
        root = ET.fromstring(result)
        bounds_elements = root.findall('.//*[@x]')
        print(f"   Found {len(bounds_elements)} positioned elements")
        
        # Print some sample positions
        for i, elem in enumerate(bounds_elements[:3]):
            x, y = elem.get('x'), elem.get('y')
            print(f"   Element {i+1}: x={x}, y={y}")
    else:
        print("❌ Failed to add layout")


def test_branching_workflow():
    """Test with a workflow that has branching (gateway)."""
    print("\n=== Testing Branching Workflow ===")
    bpmn_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL" id="Definitions_2">
  <process id="Process_2" isExecutable="false">
    <startEvent id="Start_1" name="Start"/>
    <task id="Task_A" name="Analyze Requirements"/>
    <exclusiveGateway id="Gateway_1" name="Clear?"/>
    <task id="Task_B" name="Clarify"/>
    <task id="Task_C" name="Design"/>
    <endEvent id="End_1" name="End"/>
    
    <sequenceFlow id="f1" sourceRef="Start_1" targetRef="Task_A"/>
    <sequenceFlow id="f2" sourceRef="Task_A" targetRef="Gateway_1"/>
    <sequenceFlow id="f3" name="No" sourceRef="Gateway_1" targetRef="Task_B"/>
    <sequenceFlow id="f4" name="Yes" sourceRef="Gateway_1" targetRef="Task_C"/>
    <sequenceFlow id="f5" sourceRef="Task_B" targetRef="Task_C"/>
    <sequenceFlow id="f6" sourceRef="Task_C" targetRef="End_1"/>
  </process>
</definitions>'''
    
    result = add_layout_to_bpmn(bpmn_xml, layout_algorithm='dot')
    
    if 'bpmndi:BPMNShape' in result:
        print("✅ Layout successfully added to branching workflow")
        
        # Extract layer information
        import xml.etree.ElementTree as ET
        root = ET.fromstring(result)
        bounds_elements = root.findall('.//*[@x]')
        
        # Group by x-coordinate (layers)
        x_positions = {}
        for elem in bounds_elements:
            x = float(elem.get('x', 0))
            if x not in x_positions:
                x_positions[x] = []
            # Get the element ID from the shape's bpmnElement attribute
            shape = elem.getparent()
            elem_id = shape.get('bpmnElement', 'unknown') if shape is not None else 'unknown'
            x_positions[x].append(elem_id)
        
        # Print layer information
        sorted_layers = sorted(x_positions.items())
        print(f"   Organized into {len(sorted_layers)} layers:")
        for i, (x, elements) in enumerate(sorted_layers):
            print(f"   Layer {i+1} (x={x}): {elements}")
    else:
        print("❌ Failed to add layout")


def test_parallel_workflow():
    """Test with parallel branches."""
    print("\n=== Testing Parallel Workflow ===")
    bpmn_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL" id="Definitions_3">
  <process id="Process_3" isExecutable="false">
    <startEvent id="Start_1" name="Start"/>
    <parallelGateway id="Fork_1" name="Fork"/>
    <task id="Task_A" name="Task A"/>
    <task id="Task_B" name="Task B"/>
    <task id="Task_C" name="Task C"/>
    <parallelGateway id="Join_1" name="Join"/>
    <endEvent id="End_1" name="End"/>
    
    <sequenceFlow id="f1" sourceRef="Start_1" targetRef="Fork_1"/>
    <sequenceFlow id="f2" sourceRef="Fork_1" targetRef="Task_A"/>
    <sequenceFlow id="f3" sourceRef="Fork_1" targetRef="Task_B"/>
    <sequenceFlow id="f4" sourceRef="Fork_1" targetRef="Task_C"/>
    <sequenceFlow id="f5" sourceRef="Task_A" targetRef="Join_1"/>
    <sequenceFlow id="f6" sourceRef="Task_B" targetRef="Join_1"/>
    <sequenceFlow id="f7" sourceRef="Task_C" targetRef="Join_1"/>
    <sequenceFlow id="f8" sourceRef="Join_1" targetRef="End_1"/>
  </process>
</definitions>'''
    
    result = add_layout_to_bpmn(bpmn_xml, layout_algorithm='dot')
    
    if 'bpmndi:BPMNShape' in result:
        print("✅ Layout successfully added to parallel workflow")
        
        # Check for proper parallel arrangement
        import xml.etree.ElementTree as ET
        root = ET.fromstring(result)
        
        # Find the parallel tasks (should be in same layer)
        task_positions = {}
        for shape in root.findall('.//bpmndi:BPMNShape[@bpmnElement]', 
                                  {'bpmndi': 'http://www.omg.org/spec/BPMN/20100524/DI'}):
            elem_id = shape.get('bpmnElement')
            if elem_id and elem_id.startswith('Task_'):
                bounds = shape.find('.//dc:Bounds', {'dc': 'http://www.omg.org/spec/DD/20100524/DC'})
                if bounds is not None:
                    x = float(bounds.get('x', 0))
                    y = float(bounds.get('y', 0))
                    task_positions[elem_id] = (x, y)
        
        print(f"   Task positions: {task_positions}")
        
        # Check if tasks are roughly in the same vertical layer (same x, different y)
        if len(task_positions) >= 3:
            x_coords = [pos[0] for pos in task_positions.values()]
            if len(set(x_coords)) <= 2:  # Should be in 1-2 layers
                print("   ✅ Parallel tasks properly arranged in layers")
            else:
                print("   ⚠️ Parallel tasks may not be optimally arranged")
    else:
        print("❌ Failed to add layout")


if __name__ == "__main__":
    print("Testing Advanced BPMN Layout Algorithms")
    print("=" * 50)
    
    test_simple_linear_workflow()
    test_branching_workflow()
    test_parallel_workflow()
    
    print("\n" + "=" * 50)
    print("Testing completed!")
