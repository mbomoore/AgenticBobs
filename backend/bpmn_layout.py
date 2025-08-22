"""
BPMN Layout Engine - Python backend for computing optimal BPMN diagram layouts.

This module provides intelligent layout algorithms for BPMN diagrams using graph theory
and NetworkX with fallback layout algorithms.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Dict, List, Tuple, Optional, Set, Any
import networkx as nx
import logging

logger = logging.getLogger(__name__)

# Try to import graphviz layout, but don't fail if not available
try:
    from networkx.drawing.nx_agraph import graphviz_layout
    HAS_GRAPHVIZ = True
except ImportError:
    logger.info("Graphviz not available, using NetworkX-only layouts")
    HAS_GRAPHVIZ = False
    graphviz_layout = None  # Define for type checking

# BPMN element dimensions (standard BPMN sizes)
ELEMENT_DIMENSIONS = {
    'startEvent': {'width': 36, 'height': 36},
    'endEvent': {'width': 36, 'height': 36},
    'intermediateThrowEvent': {'width': 36, 'height': 36},
    'intermediateCatchEvent': {'width': 36, 'height': 36},
    'task': {'width': 100, 'height': 80},
    'userTask': {'width': 100, 'height': 80},
    'serviceTask': {'width': 100, 'height': 80},
    'manualTask': {'width': 100, 'height': 80},
    'scriptTask': {'width': 100, 'height': 80},
    'businessRuleTask': {'width': 100, 'height': 80},
    'sendTask': {'width': 100, 'height': 80},
    'receiveTask': {'width': 100, 'height': 80},
    'exclusiveGateway': {'width': 50, 'height': 50},
    'inclusiveGateway': {'width': 50, 'height': 50},
    'parallelGateway': {'width': 50, 'height': 50},
    'eventBasedGateway': {'width': 50, 'height': 50},
    'complexGateway': {'width': 50, 'height': 50},
    'subProcess': {'width': 150, 'height': 120},
    'callActivity': {'width': 100, 'height': 80},
}

# BPMN namespaces
BPMN_NS = {
    'bpmn': 'http://www.omg.org/spec/BPMN/20100524/MODEL',
    'bpmndi': 'http://www.omg.org/spec/BPMN/20100524/DI',
    'dc': 'http://www.omg.org/spec/DD/20100524/DC',
    'di': 'http://www.omg.org/spec/DD/20100524/DI'
}


class BPMNLayoutEngine:
    """
    Intelligent BPMN layout engine using NetworkX and Graphviz.
    
    Features:
    - Automatic detection of BPMN element types
    - Hierarchical layout optimized for process flows
    - Proper edge routing with minimal crossings
    - Standard BPMN element sizing
    - Clean separation of elements
    """
    
    def __init__(self, layout_algorithm: str = 'dot'):
        """
        Initialize the layout engine.
        
        Args:
            layout_algorithm: Graphviz layout algorithm ('dot', 'neato', 'fdp', 'sfdp', 'circo', 'twopi')
                             'dot' is best for hierarchical/flow diagrams
        """
        self.layout_algorithm = layout_algorithm
        self.graph = nx.DiGraph()
        self.elements: Dict[str, Dict[str, Any]] = {}
        self.flows: Dict[str, Dict[str, Any]] = {}
        
    def parse_bpmn_structure(self, bpmn_xml: str) -> None:
        """Parse BPMN XML to extract elements and sequence flows."""
        try:
            # Parse XML
            root = ET.fromstring(bpmn_xml)
            
            # Register namespaces for searching
            for prefix, uri in BPMN_NS.items():
                ET.register_namespace(prefix, uri)
            
            # Find process elements
            process = root.find('.//bpmn:process', BPMN_NS)
            if process is None:
                logger.warning("No BPMN process found in XML")
                return
            
            # Extract all BPMN elements
            for elem_type in ELEMENT_DIMENSIONS.keys():
                elements = process.findall(f'.//bpmn:{elem_type}', BPMN_NS)
                for elem in elements:
                    elem_id = elem.get('id')
                    if elem_id:
                        self.elements[elem_id] = {
                            'type': elem_type,
                            'name': elem.get('name', ''),
                            'element': elem
                        }
                        # Add node to graph
                        self.graph.add_node(elem_id, 
                                          element_type=elem_type,
                                          **ELEMENT_DIMENSIONS[elem_type])
            
            # Extract sequence flows
            flows = process.findall('.//bpmn:sequenceFlow', BPMN_NS)
            for flow in flows:
                flow_id = flow.get('id')
                source_ref = flow.get('sourceRef')
                target_ref = flow.get('targetRef')
                
                if flow_id and source_ref and target_ref:
                    self.flows[flow_id] = {
                        'source': source_ref,
                        'target': target_ref,
                        'name': flow.get('name', ''),
                        'element': flow
                    }
                    # Add edge to graph
                    if source_ref in self.elements and target_ref in self.elements:
                        self.graph.add_edge(source_ref, target_ref, flow_id=flow_id)
            
            logger.info(f"Parsed BPMN: {len(self.elements)} elements, {len(self.flows)} flows")
            
        except ET.ParseError as e:
            logger.error(f"Failed to parse BPMN XML: {e}")
            raise
        except Exception as e:
            logger.error(f"Error parsing BPMN structure: {e}")
            raise
    
    def compute_layout(self, spacing_factor: float = 1.5) -> Dict[str, Tuple[float, float]]:
        """
        Compute optimal layout positions for BPMN elements.
        
        Args:
            spacing_factor: Multiplier for spacing between elements (1.0 = tight, 2.0 = loose)
            
        Returns:
            Dict mapping element IDs to (x, y) positions
        """
        if not self.graph.nodes():
            logger.warning("No elements to layout")
            return {}
        
        try:
            # First try: Use Graphviz for hierarchical layout if available
            if HAS_GRAPHVIZ and self.layout_algorithm == 'dot':
                try:
                    from networkx.drawing.nx_agraph import graphviz_layout as gviz_layout
                    positions = gviz_layout(self.graph, prog=self.layout_algorithm)
                    # Scale positions to account for BPMN element sizes
                    return self._scale_positions(positions, spacing_factor)
                except Exception as e:
                    logger.warning(f"Graphviz layout failed: {e}, falling back to Sugiyama algorithm")
            
            # Second try: Use our Sugiyama-style hierarchical layout (best for workflows)
            logger.info("Using Sugiyama hierarchical layout algorithm")
            return self._sugiyama_hierarchical_layout(spacing_factor)
            
        except Exception as e:
            logger.error(f"All layout algorithms failed: {e}, using grid fallback")
            return self._fallback_grid_layout()
    
    def _scale_positions(self, positions: Dict[str, Tuple[float, float]], spacing_factor: float) -> Dict[str, Tuple[float, float]]:
        """Scale positions from Graphviz to reasonable pixel coordinates."""
        scaled_positions = {}
        
        # Find bounding box of initial layout
        if positions:
            x_coords = [pos[0] for pos in positions.values()]
            y_coords = [pos[1] for pos in positions.values()]
            x_min, x_max = min(x_coords), max(x_coords)
            y_min, y_max = min(y_coords), max(y_coords)
            
            # Calculate scaling factors
            x_range = x_max - x_min if x_max != x_min else 100
            y_range = y_max - y_min if y_max != y_min else 100
            
            # Scale to provide good spacing
            x_scale = spacing_factor * 200  # Base spacing of 200px
            y_scale = spacing_factor * 150  # Base spacing of 150px
            
            # Apply scaling and offset
            for elem_id, (x, y) in positions.items():
                # Normalize to 0-1 range, then scale
                norm_x = (x - x_min) / x_range if x_range > 0 else 0
                norm_y = (y - y_min) / y_range if y_range > 0 else 0
                
                # Apply scaling and add offset for margins
                scaled_x = 100 + norm_x * x_scale  # 100px left margin
                scaled_y = 100 + norm_y * y_scale  # 100px top margin
                
                scaled_positions[elem_id] = (scaled_x, scaled_y)
                
        logger.info(f"Scaled layout for {len(scaled_positions)} elements")
        return scaled_positions
    
    def _fallback_spring_layout(self, spacing_factor: float) -> Dict[str, Tuple[float, float]]:
        """Fallback to NetworkX spring layout if Graphviz fails."""
        try:
            positions = nx.spring_layout(self.graph, 
                                       k=spacing_factor*2, 
                                       iterations=50)
            
            # Scale to reasonable pixel coordinates
            scaled_positions = {}
            for elem_id, (x, y) in positions.items():
                scaled_x = 100 + x * 800  # Scale to ~800px width
                scaled_y = 100 + y * 600  # Scale to ~600px height
                scaled_positions[elem_id] = (scaled_x, scaled_y)
                
            return scaled_positions
        except Exception as e:
            logger.error(f"Spring layout failed: {e}")
            return self._fallback_hierarchical_layout(spacing_factor)
    
    def _sugiyama_hierarchical_layout(self, spacing_factor: float) -> Dict[str, Tuple[float, float]]:
        """
        Implement Sugiyama-style hierarchical layout for workflow diagrams.
        This is specifically designed for BPMN/workflow diagrams with proper layering.
        """
        positions = {}
        
        try:
            # Step 1: Handle cycles intelligently for workflow diagrams
            if not nx.is_directed_acyclic_graph(self.graph):
                self._handle_workflow_cycles()
            
            # Step 2: Assign nodes to layers using longest path
            layers = self._assign_to_layers()
            
            # Step 3: Minimize crossings within each layer
            ordered_layers = self._minimize_crossings(layers)
            
            # Step 4: Assign coordinates
            positions = self._assign_coordinates(ordered_layers, spacing_factor)
            
            return positions
            
        except Exception as e:
            logger.error(f"Sugiyama layout failed: {e}")
            return self._fallback_grid_layout()
    
    def _handle_workflow_cycles(self) -> None:
        """
        Intelligently handle cycles in workflow diagrams.
        
        This method identifies cycles and breaks them by removing edges that represent
        exception flows or backward loops, preserving the main workflow direction.
        """
        cycles = list(nx.simple_cycles(self.graph))
        logger.info(f"Found {len(cycles)} cycles in the workflow")
        
        for cycle in cycles:
            if len(cycle) <= 1:
                continue
                
            # Try to identify the best edge to remove based on BPMN semantics
            best_edge_to_remove = None
            
            # Look for exception flows or events that typically go backwards
            for i in range(len(cycle)):
                u = cycle[i]
                v = cycle[(i + 1) % len(cycle)]
                
                # Prefer removing edges from catch events (exceptions)
                if u.startswith('CatchEvent') or 'Exception' in u:
                    best_edge_to_remove = (u, v)
                    break
                    
                # Or edges going to earlier elements (assuming IDs have some ordering)
                if v < u:  # Simple heuristic based on ID ordering
                    best_edge_to_remove = (u, v)
            
            # If no obvious choice, remove the last edge in the cycle
            if best_edge_to_remove is None:
                best_edge_to_remove = (cycle[-1], cycle[0])
            
            # Remove the chosen edge
            u, v = best_edge_to_remove
            if self.graph.has_edge(u, v):
                logger.info(f"Removing cycle edge: {u} -> {v}")
                self.graph.remove_edge(u, v)
                
                # Mark this as a back edge for potential special rendering
                if not hasattr(self, 'back_edges'):
                    self.back_edges = []
                self.back_edges.append((u, v))

    def _assign_to_layers(self) -> Dict[int, List[str]]:
        """Assign nodes to layers based on longest path from start nodes."""
        layers: Dict[int, List[str]] = {}
        node_layer: Dict[str, int] = {}
        
        # Find start nodes (no incoming edges)
        start_nodes = [n for n in self.graph.nodes() if self.graph.in_degree(n) == 0]
        if not start_nodes:
            # If no clear start, pick nodes with minimum in-degree
            min_degree = min(self.graph.in_degree(n) for n in self.graph.nodes())
            start_nodes = [n for n in self.graph.nodes() if self.graph.in_degree(n) == min_degree]
        
        # Assign layer 0 to start nodes
        for node in start_nodes:
            node_layer[node] = 0
            if 0 not in layers:
                layers[0] = []
            layers[0].append(node)
        
        # Topological sort to process nodes in dependency order
        try:
            topo_order = list(nx.topological_sort(self.graph))
        except nx.NetworkXError:
            # If still not acyclic, use DFS order
            topo_order = list(nx.dfs_preorder_nodes(self.graph, source=start_nodes[0] if start_nodes else None))
        
        # Assign layers based on maximum predecessor layer + 1
        for node in topo_order:
            if node not in node_layer:
                # Find maximum layer of all predecessors
                max_pred_layer = -1
                for pred in self.graph.predecessors(node):
                    if pred in node_layer:
                        max_pred_layer = max(max_pred_layer, node_layer[pred])
                
                layer = max_pred_layer + 1
                node_layer[node] = layer
                
                if layer not in layers:
                    layers[layer] = []
                layers[layer].append(node)
        
        return layers
    
    def _minimize_crossings(self, layers: Dict[int, List[str]]) -> Dict[int, List[str]]:
        """Minimize edge crossings between adjacent layers using barycenter heuristic."""
        ordered_layers = dict(layers)
        max_layer = max(layers.keys()) if layers else 0
        
        # Iteratively improve layer ordering
        for iteration in range(3):  # Limited iterations for performance
            # Forward pass: order layers based on predecessors
            for layer_num in range(1, max_layer + 1):
                if layer_num in ordered_layers and layer_num - 1 in ordered_layers:
                    current_layer = ordered_layers[layer_num]
                    prev_layer = ordered_layers[layer_num - 1]
                    
                    # Calculate barycenter for each node in current layer
                    node_barycenters = []
                    for node in current_layer:
                        predecessors = [p for p in self.graph.predecessors(node) if p in prev_layer]
                        if predecessors:
                            # Average position of predecessors
                            barycenter = sum(prev_layer.index(p) for p in predecessors) / len(predecessors)
                        else:
                            barycenter = len(prev_layer)  # Place at end if no predecessors
                        node_barycenters.append((barycenter, node))
                    
                    # Sort by barycenter
                    node_barycenters.sort()
                    ordered_layers[layer_num] = [node for _, node in node_barycenters]
            
            # Backward pass: order layers based on successors
            for layer_num in range(max_layer - 1, -1, -1):
                if layer_num in ordered_layers and layer_num + 1 in ordered_layers:
                    current_layer = ordered_layers[layer_num]
                    next_layer = ordered_layers[layer_num + 1]
                    
                    # Calculate barycenter for each node in current layer
                    node_barycenters = []
                    for node in current_layer:
                        successors = [s for s in self.graph.successors(node) if s in next_layer]
                        if successors:
                            # Average position of successors
                            barycenter = sum(next_layer.index(s) for s in successors) / len(successors)
                        else:
                            barycenter = len(next_layer)  # Place at end if no successors
                        node_barycenters.append((barycenter, node))
                    
                    # Sort by barycenter
                    node_barycenters.sort()
                    ordered_layers[layer_num] = [node for _, node in node_barycenters]
        
        return ordered_layers
    
    def _assign_coordinates(self, layers: Dict[int, List[str]], spacing_factor: float) -> Dict[str, Tuple[float, float]]:
        """Assign final coordinates to nodes with proper spacing."""
        positions = {}
        
        # Calculate spacing
        layer_width = 200.0 * spacing_factor  # Horizontal spacing between layers
        node_height = 100.0 * spacing_factor  # Vertical spacing between nodes
        start_x = 100.0
        start_y = 100.0
        
        max_layer = max(layers.keys()) if layers else 0
        
        for layer_num in range(max_layer + 1):
            if layer_num not in layers:
                continue
                
            layer_nodes = layers[layer_num]
            layer_x = start_x + layer_num * layer_width
            
            # Center the layer vertically
            total_height = (len(layer_nodes) - 1) * node_height
            layer_start_y = start_y - total_height / 2
            
            # Special handling for single nodes to center them nicely
            if len(layer_nodes) == 1:
                layer_start_y = start_y
            
            for i, node in enumerate(layer_nodes):
                node_y = layer_start_y + i * node_height
                positions[node] = (layer_x, node_y)
        
        return positions
    
    def _fallback_grid_layout(self) -> Dict[str, Tuple[float, float]]:
        """Absolute fallback: arrange nodes in a simple grid."""
        positions = {}
        nodes = list(self.graph.nodes())
        
        # Arrange in a grid pattern
        grid_width = max(3, int(len(nodes) ** 0.5) + 1)
        
        for i, node in enumerate(nodes):
            row = i // grid_width
            col = i % grid_width
            x = 100.0 + col * 200.0
            y = 100.0 + row * 150.0
            positions[node] = (x, y)
        
        return positions

    def _fallback_hierarchical_layout(self, spacing_factor: float) -> Dict[str, Tuple[float, float]]:
        """Fallback hierarchical layout - now uses improved Sugiyama algorithm."""
        return self._sugiyama_hierarchical_layout(spacing_factor)


def add_layout_to_bpmn(bpmn_xml: str, layout_algorithm: str = 'dot') -> str:
    """
    Add layout information to BPMN XML that lacks diagram interchange (DI) data.
    
    Args:
        bpmn_xml: BPMN XML string (possibly without layout)
        layout_algorithm: Layout algorithm to use ('dot', 'neato', 'fdp', etc.)
        
    Returns:
        BPMN XML with complete layout information
    """
    try:
        # Check if layout already exists
        if 'bpmndi:BPMNShape' in bpmn_xml and 'bpmndi:BPMNEdge' in bpmn_xml:
            logger.info("BPMN already has layout information, skipping layout computation")
            return bpmn_xml
        
        # Initialize layout engine
        layout_engine = BPMNLayoutEngine(layout_algorithm=layout_algorithm)
        
        # Parse BPMN structure
        layout_engine.parse_bpmn_structure(bpmn_xml)
        
        # Compute layout
        positions = layout_engine.compute_layout()
        
        if not positions:
            logger.warning("No layout computed, returning original XML")
            return bpmn_xml
        
        # Parse XML for modification
        root = ET.fromstring(bpmn_xml)
        
        # Register namespaces
        for prefix, uri in BPMN_NS.items():
            ET.register_namespace(prefix, uri)
        
        # Find or create BPMNDiagram
        bpmn_diagram = root.find('.//bpmndi:BPMNDiagram', BPMN_NS)
        if bpmn_diagram is None:
            bpmn_diagram = ET.SubElement(root, f"{{{BPMN_NS['bpmndi']}}}BPMNDiagram")
            bpmn_diagram.set('id', 'BPMNDiagram_1')
        
        # Find or create BPMNPlane
        bpmn_plane = bpmn_diagram.find('.//bpmndi:BPMNPlane', BPMN_NS)
        if bpmn_plane is None:
            bpmn_plane = ET.SubElement(bpmn_diagram, f"{{{BPMN_NS['bpmndi']}}}BPMNPlane")
            bpmn_plane.set('id', 'BPMNPlane_1')
            # Find process to link to
            process = root.find('.//bpmn:process', BPMN_NS)
            if process is not None:
                bpmn_plane.set('bpmnElement', process.get('id', 'Process_1'))
        else:
            # Clear existing shapes and edges
            bpmn_plane.clear()
        
        # Add BPMNShape elements
        for elem_id, (x, y) in positions.items():
            if elem_id in layout_engine.elements:
                elem_type = layout_engine.elements[elem_id]['type']
                dimensions = ELEMENT_DIMENSIONS.get(elem_type, {'width': 100, 'height': 80})
                
                # Create BPMNShape
                shape = ET.SubElement(bpmn_plane, f"{{{BPMN_NS['bpmndi']}}}BPMNShape")
                shape.set('id', f"{elem_id}_di")
                shape.set('bpmnElement', elem_id)
                
                # Create Bounds
                bounds = ET.SubElement(shape, f"{{{BPMN_NS['dc']}}}Bounds")
                bounds.set('x', str(int(x)))
                bounds.set('y', str(int(y)))
                bounds.set('width', str(dimensions['width']))
                bounds.set('height', str(dimensions['height']))
        
        # Add BPMNEdge elements
        for flow_id, flow_info in layout_engine.flows.items():
            source_id = flow_info['source']
            target_id = flow_info['target']
            
            if source_id in positions and target_id in positions:
                # Calculate connection points
                source_pos = positions[source_id]
                target_pos = positions[target_id]
                source_dims = ELEMENT_DIMENSIONS.get(
                    layout_engine.elements[source_id]['type'], 
                    {'width': 100, 'height': 80}
                )
                target_dims = ELEMENT_DIMENSIONS.get(
                    layout_engine.elements[target_id]['type'], 
                    {'width': 100, 'height': 80}
                )
                
                # Calculate exit and entry points
                source_x = source_pos[0] + source_dims['width']
                source_y = source_pos[1] + source_dims['height'] / 2
                target_x = target_pos[0]
                target_y = target_pos[1] + target_dims['height'] / 2
                
                # Create BPMNEdge
                edge = ET.SubElement(bpmn_plane, f"{{{BPMN_NS['bpmndi']}}}BPMNEdge")
                edge.set('id', f"{flow_id}_di")
                edge.set('bpmnElement', flow_id)
                
                # Create waypoints
                waypoint1 = ET.SubElement(edge, f"{{{BPMN_NS['di']}}}waypoint")
                waypoint1.set('x', str(int(source_x)))
                waypoint1.set('y', str(int(source_y)))
                
                waypoint2 = ET.SubElement(edge, f"{{{BPMN_NS['di']}}}waypoint")
                waypoint2.set('x', str(int(target_x)))
                waypoint2.set('y', str(int(target_y)))
        
        # Convert back to string
        ET.indent(root, space="  ")
        result = ET.tostring(root, encoding='unicode', xml_declaration=True)
        
        logger.info(f"Successfully added layout to BPMN with {len(positions)} elements")
        return result
        
    except Exception as e:
        logger.error(f"Failed to add layout to BPMN: {e}")
        # Return original XML if layout fails
        return bpmn_xml


# Quick test function
def test_layout_engine():
    """Test the layout engine with a simple BPMN."""
    test_bpmn = '''<?xml version="1.0" encoding="UTF-8"?>
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
    
    result = add_layout_to_bpmn(test_bpmn)
    print("Layout test completed")
    return result


if __name__ == "__main__":
    # Enable logging for testing
    logging.basicConfig(level=logging.INFO)
    test_layout_engine()
