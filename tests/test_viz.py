import sys
import os

# Ensure the project root is on sys.path so `core` can be imported during tests
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from agentic_process_automation.core.pir import PIRBuilder
from agentic_process_automation.core.viz import pir_to_mermaid


def test_pir_to_mermaid_simple_flat_structure():
    """Test that the updated function works with simple non-swimlane structure."""
    b = PIRBuilder()
    b.add_node(id="start", kind="startEvent", name="Start")
    b.add_node(id="task1", kind="task", name="Do Work")
    b.add_node(id="end", kind="endEvent", name="End")
    b.add_edge(src="start", dst="task1")
    b.add_edge(src="task1", dst="end")
    pir = b.build()
    
    mermaid = pir_to_mermaid(pir)
    
    # Should start with flowchart LR
    assert mermaid.startswith("flowchart LR")
    # Should contain unorganized nodes section
    assert "Unorganized nodes" in mermaid
    # Should contain all nodes
    assert "start[\"Start\"]" in mermaid
    assert "task1[\"Do Work\"]" in mermaid
    assert "end[\"End\"]" in mermaid
    # Should contain flows
    assert "start --> task1" in mermaid
    assert "task1 --> end" in mermaid


def test_pir_to_mermaid_with_swimlanes():
    """Test the new swimlane functionality matching the problem statement example."""
    b = PIRBuilder()
    
    # Company pool nodes
    b.add_node(id="A1", kind="task", name="Triage", pool="Company", lane="Support Agent")
    b.add_node(id="A2", kind="task", name="Resolve", pool="Company", lane="Support Agent")
    b.add_node(id="A3", kind="task", name="Notify Customer", pool="Company", lane="Support Agent")
    b.add_node(id="S1", kind="task", name="Create Ticket", pool="Company", lane="Ticketing System")
    b.add_node(id="S2", kind="task", name="Update Status", pool="Company", lane="Ticketing System")
    
    # Customer pool nodes (direct pool membership, no specific lane)
    b.add_node(id="C1", kind="task", name="Submit Request", pool="Customer")
    b.add_node(id="C2", kind="task", name="Confirm Resolution", pool="Customer")
    
    # Internal lane flows
    b.add_edge(src="A1", dst="A2")
    b.add_edge(src="A2", dst="A3")
    b.add_edge(src="S1", dst="S2")
    b.add_edge(src="C1", dst="C2")
    
    # Cross-pool/lane flows
    b.add_edge(src="C1", dst="S1")  # Customer to Ticketing System
    b.add_edge(src="S1", dst="A1")  # Ticketing System to Support Agent
    b.add_edge(src="A2", dst="S2")  # Support Agent to Ticketing System
    b.add_edge(src="A3", dst="C2")  # Support Agent to Customer
    
    pir = b.build()
    mermaid = pir_to_mermaid(pir)
    
    # Should contain pool subgraphs
    assert "subgraph PoolCompany[\"Company\"]" in mermaid
    assert "subgraph PoolCustomer[\"Customer\"]" in mermaid
    
    # Should contain lane subgraphs within Company pool
    assert "subgraph LaneSupportAgent[\"Support Agent\"]" in mermaid
    assert "subgraph LaneTicketingSystem[\"Ticketing System\"]" in mermaid
    
    # Should contain nodes in correct lanes
    assert "A1[\"Triage\"]" in mermaid
    assert "A2[\"Resolve\"]" in mermaid
    assert "A3[\"Notify Customer\"]" in mermaid
    assert "S1[\"Create Ticket\"]" in mermaid
    assert "S2[\"Update Status\"]" in mermaid
    
    # Should contain direct pool nodes (Customer)
    assert "C1[\"Submit Request\"]" in mermaid
    assert "C2[\"Confirm Resolution\"]" in mermaid
    
    # Should have cross-pool flows with dotted lines
    assert "C1 -. message .-> S1" in mermaid
    assert "A3 -. message .-> C2" in mermaid
    
    # Should have cross-lane flows with dotted lines (same pool, different lanes)
    assert "S1 -. message .-> A1" in mermaid
    assert "A2 -. message .-> S2" in mermaid
    
    # Should have internal flows with solid lines (same lane)
    assert "A1 --> A2" in mermaid
    assert "A2 --> A3" in mermaid
    assert "S1 --> S2" in mermaid
    
    # Should contain styling
    assert "style PoolCompany fill:#f8f8f8,stroke:#bbb,stroke-width:1px" in mermaid
    assert "style PoolCustomer fill:#f8f8f8,stroke:#bbb,stroke-width:1px" in mermaid
    assert "style LaneSupportAgent fill:#ffffff,stroke:#ddd" in mermaid
    assert "style LaneTicketingSystem fill:#ffffff,stroke:#ddd" in mermaid


def test_pir_to_mermaid_mixed_organized_unorganized():
    """Test that nodes with and without pools/lanes work together."""
    b = PIRBuilder()
    
    # Organized nodes
    b.add_node(id="A1", kind="task", name="Task A", pool="Pool1", lane="Lane1")
    b.add_node(id="B1", kind="task", name="Task B", pool="Pool1")  # Direct pool, no lane
    
    # Unorganized nodes
    b.add_node(id="U1", kind="task", name="Unorganized Task")
    
    # Edges between different organizational levels
    b.add_edge(src="U1", dst="A1")  # Unorganized to organized
    b.add_edge(src="A1", dst="B1")  # Lane to direct pool
    b.add_edge(src="B1", dst="U1")  # Direct pool to unorganized
    
    pir = b.build()
    mermaid = pir_to_mermaid(pir)
    
    # Should have pool structure
    assert "subgraph PoolPool1[\"Pool1\"]" in mermaid
    assert "subgraph LaneLane1[\"Lane1\"]" in mermaid
    
    # Should have unorganized section
    assert "Unorganized nodes" in mermaid
    assert "U1[\"Unorganized Task\"]" in mermaid
    
    # Should have cross-organizational flows
    assert "U1 -. message .-> A1" in mermaid
    assert "B1 -. message .-> U1" in mermaid
    # Cross-lane flow within same pool (lane to direct pool) should be dotted
    assert "A1 -. message .-> B1" in mermaid


def test_pir_to_mermaid_with_guards():
    """Test that guards work correctly with swimlanes."""
    b = PIRBuilder()
    
    b.add_node(id="A1", kind="task", name="Task A", pool="Pool1", lane="Lane1")
    b.add_node(id="B1", kind="task", name="Task B", pool="Pool2")
    
    # Edge with guard between pools
    b.add_edge(src="A1", dst="B1", guard="condition")
    
    pir = b.build()
    mermaid = pir_to_mermaid(pir)
    
    # Should use guard text instead of "message" for cross-pool flow
    assert "A1 -.condition.-> B1" in mermaid


def test_pir_to_mermaid_with_gateways():
    """Test that gateways are rendered correctly in swimlanes."""
    b = PIRBuilder()
    
    b.add_node(id="G1", kind="exclusiveGateway", name="Decision", pool="Pool1", lane="Lane1")
    b.add_node(id="T1", kind="task", name="Task", pool="Pool1", lane="Lane1")
    
    b.add_edge(src="G1", dst="T1")
    
    pir = b.build()
    mermaid = pir_to_mermaid(pir)
    
    # Gateway should use diamond syntax
    assert "G1{\"Decision\"}" in mermaid
    # Task should use rectangle syntax
    assert "T1[\"Task\"]" in mermaid


def test_pir_builder_add_pooled_node_convenience_method():
    """Test the convenience method for adding pooled nodes."""
    b = PIRBuilder()
    
    # Use convenience method
    b.add_pooled_node("N1", "task", "Task 1", "Pool1", "Lane1")
    b.add_pooled_node("N2", "task", "Task 2", "Pool1")  # No lane
    
    pir = b.build()
    
    # Verify nodes were created correctly
    assert "N1" in pir.nodes
    assert "N2" in pir.nodes
    
    n1 = pir.nodes["N1"]
    assert n1.pool == "Pool1"
    assert n1.lane == "Lane1"
    assert n1.name == "Task 1"
    assert n1.kind == "task"
    
    n2 = pir.nodes["N2"]
    assert n2.pool == "Pool1"
    assert n2.lane is None
    assert n2.name == "Task 2"
    assert n2.kind == "task"