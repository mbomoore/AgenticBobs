#!/usr/bin/env python3
"""
Simple test of the BPMN layout engine to verify the Sugiyama algorithm works.
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from bpmn_layout import add_layout_to_bpmn
import xml.etree.ElementTree as ET

def extract_positions(bpmn_xml):
    """Extract element positions from BPMN XML."""
    root = ET.fromstring(bpmn_xml)
    
    # Find all bounds elements
    positions = {}
    
    # Register namespaces
    namespaces = {
        'bpmndi': 'http://www.omg.org/spec/BPMN/20100524/DI',
        'dc': 'http://www.omg.org/spec/DD/20100524/DC'
    }
    
    # Find all BPMNShape elements
    for shape in root.findall('.//bpmndi:BPMNShape', namespaces):
        elem_id = shape.get('bpmnElement')
        bounds = shape.find('./dc:Bounds', namespaces)
        if bounds is not None and elem_id:
            x = float(bounds.get('x', 0))
            y = float(bounds.get('y', 0))
            positions[elem_id] = (x, y)
    
    return positions

def test_layout_quality():
    """Test the layout quality with a branching workflow."""
    print("Testing BPMN Layout Quality")
    print("=" * 40)
    
    # Test with a workflow that has decision branching
    bpmn_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL" id="Definitions_Test">
  <process id="Process_Test" isExecutable="false">
    <startEvent id="Start_1" name="Start"/>
    <task id="Task_A" name="Analyze"/>
    <exclusiveGateway id="Gateway_1" name="Decision"/>
    <task id="Task_B" name="Path B"/>
    <task id="Task_C" name="Path C"/>
    <task id="Task_D" name="Merge"/>
    <endEvent id="End_1" name="End"/>
    
    <sequenceFlow id="f1" sourceRef="Start_1" targetRef="Task_A"/>
    <sequenceFlow id="f2" sourceRef="Task_A" targetRef="Gateway_1"/>
    <sequenceFlow id="f3" sourceRef="Gateway_1" targetRef="Task_B"/>
    <sequenceFlow id="f4" sourceRef="Gateway_1" targetRef="Task_C"/>
    <sequenceFlow id="f5" sourceRef="Task_B" targetRef="Task_D"/>
    <sequenceFlow id="f6" sourceRef="Task_C" targetRef="Task_D"/>
    <sequenceFlow id="f7" sourceRef="Task_D" targetRef="End_1"/>
  </process>
</definitions>'''
    
    # Apply layout
    result = add_layout_to_bpmn(bpmn_xml, layout_algorithm='dot')
    
    # Extract positions
    positions = extract_positions(result)
    
    print(f"Positioned {len(positions)} elements:")
    
    # Group by layers (x-coordinate)
    layers = {}
    for elem_id, (x, y) in positions.items():
        if x not in layers:
            layers[x] = []
        layers[x].append((elem_id, y))
    
    # Sort layers and display
    sorted_layers = sorted(layers.items())
    print("\nLayout Analysis:")
    print("Layer | Elements")
    print("------|----------")
    
    for i, (x, elements) in enumerate(sorted_layers):
        # Sort elements in layer by y-coordinate
        elements.sort(key=lambda item: item[1])
        element_names = [elem[0] for elem in elements]
        print(f"{i+1:5} | {', '.join(element_names)}")
    
    # Analyze layout quality
    print("\nLayout Quality Assessment:")
    
    # Check if workflow flows left-to-right
    if len(sorted_layers) >= 3:
        start_x = sorted_layers[0][0]
        end_x = sorted_layers[-1][0]
        if end_x > start_x:
            print("✅ Proper left-to-right flow")
        else:
            print("❌ Incorrect flow direction")
    
    # Check if branching is handled properly
    gateway_layer = None
    for x, elements in sorted_layers:
        if any('Gateway' in elem[0] for elem in elements):
            gateway_layer = x
            break
    
    if gateway_layer:
        # Find tasks in next layer after gateway
        next_layers = [x for x in sorted(layers.keys()) if x > gateway_layer]
        if next_layers:
            next_layer_tasks = [elem[0] for elem in layers[next_layers[0]]]
            branch_tasks = [task for task in next_layer_tasks if task.startswith('Task_')]
            if len(branch_tasks) >= 2:
                print(f"✅ Branching properly handled: {len(branch_tasks)} parallel branches")
            else:
                print("⚠️ Branching may not be optimal")
    
    # Check for reasonable spacing
    x_coords = [x for x, _ in positions.values()]
    y_coords = [y for x, y in positions.values()]
    
    if len(set(x_coords)) >= 3:  # At least 3 layers
        avg_x_spacing = (max(x_coords) - min(x_coords)) / (len(set(x_coords)) - 1)
        if 150 <= avg_x_spacing <= 400:
            print(f"✅ Good horizontal spacing: {avg_x_spacing:.1f}px")
        else:
            print(f"⚠️ Horizontal spacing may be suboptimal: {avg_x_spacing:.1f}px")
    
    if len(set(y_coords)) >= 2:  # At least 2 different y positions
        y_range = max(y_coords) - min(y_coords)
        if 50 <= y_range <= 300:
            print(f"✅ Good vertical spacing: {y_range:.1f}px range")
        else:
            print(f"⚠️ Vertical spacing may be suboptimal: {y_range:.1f}px range")
    
    print(f"\nResult: {'✅ GOOD LAYOUT' if len(sorted_layers) >= 4 else '⚠️ LAYOUT NEEDS IMPROVEMENT'}")

if __name__ == "__main__":
    test_layout_quality()
