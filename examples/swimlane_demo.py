#!/usr/bin/env python3
"""
Demonstration of BPMN swimlane support in PIR class and pir_to_mermaid function.

This script shows how to create the exact example from the problem statement.
"""

import sys
import os

# Ensure the project root is on sys.path so `core` can be imported
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.pir import PIRBuilder
from core.viz import pir_to_mermaid


def main():
    """Demonstrate the new BPMN swimlane functionality."""
    
    print("BPMN Swimlane Support Demonstration")
    print("=" * 50)
    
    # Create PIR using the new pooled node functionality
    b = PIRBuilder()
    
    # Company pool nodes using new convenience method
    b.add_pooled_node("A1", "task", "Triage", "Company", "Support Agent")
    b.add_pooled_node("A2", "task", "Resolve", "Company", "Support Agent")
    b.add_pooled_node("A3", "task", "Notify Customer", "Company", "Support Agent")
    b.add_pooled_node("S1", "task", "Create Ticket", "Company", "Ticketing System")
    b.add_pooled_node("S2", "task", "Update Status", "Company", "Ticketing System")
    
    # Customer pool nodes (direct pool membership, no specific lane)
    b.add_pooled_node("C1", "task", "Submit Request", "Customer")
    b.add_pooled_node("C2", "task", "Confirm Resolution", "Customer")
    
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
    
    print("Generated Mermaid with BPMN Swimlanes:")
    print("-" * 40)
    print(pir_to_mermaid(pir))
    print("-" * 40)
    
    print("\nKey Features Demonstrated:")
    print("• Pools as top-level subgraphs (Company, Customer)")
    print("• Lanes as nested subgraphs within pools (Support Agent, Ticketing System)")
    print("• Direct pool membership (Customer nodes)")
    print("• Cross-pool flows with dotted lines (C1 -> S1, A3 -> C2)")
    print("• Cross-lane flows with dotted lines (S1 -> A1, A2 -> S2)")
    print("• Internal lane flows with solid lines (A1 -> A2, etc.)")
    print("• Automatic styling for pools and lanes")
    print("• Backward compatibility for non-swimlane structures")


if __name__ == "__main__":
    main()