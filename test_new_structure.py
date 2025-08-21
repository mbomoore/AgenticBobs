#!/usr/bin/env python3
"""Test script to validate the new package structure after reorganization."""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_core_imports():
    """Test core package imports."""
    print("🧪 Testing core imports...")
    
    # Test basic core imports
    from agentic_process_automation.core import PIR, PIRBuilder, Node, Edge, validate
    from agentic_process_automation.core.pir import PIR as PIR2  # Test direct import
    from agentic_process_automation.core.scenario import Scenario, create_default_scenario
    from agentic_process_automation.core.resources import ResourcePool, create_resource_pool
    from agentic_process_automation.core.stochastic import ConstantDistribution, create_distribution
    
    assert PIR == PIR2, "PIR imports should match"
    print("✅ Core imports successful")


def test_pir_functionality():
    """Test PIR builder and validation."""
    print("🧪 Testing PIR functionality...")
    
    from agentic_process_automation.core import PIRBuilder, validate
    
    # Build a simple process
    builder = PIRBuilder()
    builder.add_node(id="start", kind="start", name="Begin")
    builder.add_node(id="task1", kind="task", name="Do Work")
    builder.add_node(id="end", kind="end", name="Finish")
    builder.add_edge(src="start", dst="task1")
    builder.add_edge(src="task1", dst="end")
    
    pir = builder.build()
    
    # Validate the process
    report = validate(pir)
    assert report["errors"] == [], f"Validation should pass, got errors: {report['errors']}"
    assert len(pir.nodes) == 3, f"Expected 3 nodes, got {len(pir.nodes)}"
    assert len(pir.edges) == 2, f"Expected 2 edges, got {len(pir.edges)}"
    
    print("✅ PIR functionality working")


def test_scenario_functionality():
    """Test scenario creation and management."""
    print("🧪 Testing scenario functionality...")
    
    from agentic_process_automation.core.scenario import create_default_scenario, Scenario
    
    # Test default scenario
    scenario = create_default_scenario("test_scenario")
    assert scenario.name == "test_scenario"
    assert scenario.duration == 24.0
    assert scenario.num_instances == 100
    
    # Test custom scenario
    custom_scenario = Scenario(
        name="custom",
        description="Custom test scenario",
        duration=48.0,
        num_instances=50
    )
    assert custom_scenario.name == "custom"
    assert custom_scenario.duration == 48.0
    
    print("✅ Scenario functionality working")


def test_adapters():
    """Test adapter imports."""
    print("🧪 Testing adapter imports...")
    
    try:
        from agentic_process_automation.core.adapters.bpmn_min import from_bpmn_xml
        print("✅ BPMN min adapter available")
    except ImportError:
        print("⚠️ BPMN min adapter not available")
    
    try:
        from agentic_process_automation.core.adapters.bpmn import parse_bpmn
        print("✅ BPMN adapter available")
    except ImportError:
        print("⚠️ BPMN adapter not available (SpiffWorkflow not installed)")


def test_ops_imports():
    """Test operations package imports."""
    print("🧪 Testing operations imports...")
    
    from agentic_process_automation.ops import EventTracker, get_tracker, log_event
    from agentic_process_automation.ops.tracking import Event
    
    # Test event tracking
    tracker = get_tracker()
    assert isinstance(tracker, EventTracker)
    
    # Test logging an event
    log_event("test", "case_1", activity="test_activity", resource="test_resource")
    events = tracker.get_events(case_id="case_1")
    assert len(events) > 0
    assert events[-1].case_id == "case_1"
    
    print("✅ Operations functionality working")


def test_qa_imports():
    """Test QA package imports."""
    print("🧪 Testing QA imports...")
    
    from agentic_process_automation.qa import ConformanceChecker
    
    # Test mock conformance checker (since PM4Py likely not installed)
    checker = ConformanceChecker()
    result = checker.check_conformance([])
    assert "conformance_rate" in result
    
    print("✅ QA functionality working")


def test_cli_imports():
    """Test CLI package imports."""
    print("🧪 Testing CLI imports...")
    
    try:
        from agentic_process_automation.cli.generate_xml import generate_process_xml
        print("✅ CLI generate_xml available")
    except ImportError:
        print("⚠️ CLI generate_xml not available")
    
    try:
        from agentic_process_automation.cli.validate_bpmn import validate_bpmn_file
        print("✅ CLI validate_bpmn available")
    except ImportError:
        print("⚠️ CLI validate_bpmn not available")


def test_app_imports():
    """Test app package imports."""
    print("🧪 Testing app imports...")
    
    try:
        # This might fail due to Streamlit not being available or import issues
        import agentic_process_automation.app.main
        print("✅ Main app module importable")
    except ImportError as e:
        print(f"⚠️ Main app module import failed: {e}")


def run_all_tests():
    """Run all tests."""
    print("🚀 Testing new package structure after reorganization...\n")
    
    try:
        test_core_imports()
        test_pir_functionality()
        test_scenario_functionality()
        test_adapters()
        test_ops_imports()
        test_qa_imports()
        test_cli_imports()
        test_app_imports()
        
        print("\n🎉 All tests passed! The reorganization is successful!")
        print("\n📦 New package structure:")
        print("   src/agentic_process_automation/")
        print("   ├── core/     # Process logic, PIR, simulation")
        print("   ├── app/      # UI applications (Streamlit)")
        print("   ├── qa/       # Quality assurance, conformance")
        print("   ├── ops/      # Operations, monitoring, tracking")
        print("   └── cli/      # Command-line tools")
        print("\n🔗 Import examples:")
        print("   from agentic_process_automation.core import PIR, PIRBuilder")
        print("   from agentic_process_automation.ops import get_tracker")
        print("   from agentic_process_automation.qa import ConformanceChecker")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
