#!/usr/bin/env python3
"""
Test to capture exactly what Bob_2 outputs in different scenarios.
"""

import sys
from pathlib import Path

# Add the project paths to sys.path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "marvin_scripts"))

from marvin_scripts.common import build_model
from marvin_scripts.generate_xml import ProcessGenerationConfig, generate_process_xml


def test_multiple_refinements():
    """Test multiple refinement scenarios to catch inconsistent behavior."""
    print("🧪 TEST: Multiple Refinement Scenarios")
    print("=" * 60)
    
    model = build_model(model_name="qwen3:4b")
    
    # Generate initial XML
    print("📝 Step 1: Initial Generation")
    config = ProcessGenerationConfig(
        description_or_answers="Create a customer onboarding process",
        process_type="BPMN",
        model_instance=model
    )
    
    initial_result = generate_process_xml(config)
    print(f"✅ Initial XML: {len(initial_result.xml)} chars, valid: {initial_result.xml.startswith('<?xml')}")
    
    # Save initial XML for refinements
    base_xml = initial_result.xml
    
    # Test different refinement requests
    refinements = [
        "Add a validation step to check customer documentation",
        "Include a decision point for different customer types",
        "Add error handling for failed verification",
        "Include approval workflow for high-risk customers"
    ]
    
    for i, refinement in enumerate(refinements, 2):
        print(f"\n📝 Step {i}: Refinement - {refinement}")
        
        config = ProcessGenerationConfig(
            description_or_answers=refinement,
            process_type="BPMN",
            model_instance=model,
            current_xml=base_xml
        )
        
        result = generate_process_xml(config)
        
        print(f"📊 Result: {len(result.xml)} chars")
        print(f"🔍 Valid XML: {result.xml.startswith('<?xml') or result.xml.startswith('<')}")
        
        if result.xml.startswith('<?xml') or result.xml.startswith('<'):
            print("✅ Proper XML returned")
            print(f"📋 Preview: {repr(result.xml[:100])}...")
        else:
            print("❌ NON-XML CONTENT RETURNED!")
            print(f"📝 Full response: {repr(result.xml)}")
            print("🔍 This is the problem we need to fix!")
            
        print("-" * 40)


def test_with_different_models():
    """Test with different model sizes to see if it affects behavior."""
    print("\n🧪 TEST: Different Model Behavior")
    print("=" * 60)
    
    models_to_test = ["qwen3:4b", "qwen3:8b"]
    
    for model_name in models_to_test:
        print(f"\n🤖 Testing with {model_name}")
        try:
            model = build_model(model_name=model_name)
            
            # Test refinement scenario
            config = ProcessGenerationConfig(
                description_or_answers="Add validation step",
                process_type="BPMN",  
                model_instance=model,
                current_xml="""<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions id="test" targetNamespace="urn:example:bpmn"
  xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL">
  <bpmn:process id="Process_1" isExecutable="true">
    <bpmn:startEvent id="StartEvent_1" name="Start"/>
    <bpmn:endEvent id="EndEvent_1" name="End"/>
  </bpmn:process>
</bpmn:definitions>"""
            )
            
            result = generate_process_xml(config)
            
            if result.xml.startswith('<?xml') or result.xml.startswith('<'):
                print(f"✅ {model_name}: Returned proper XML ({len(result.xml)} chars)")
            else:
                print(f"❌ {model_name}: Returned text description!")
                print(f"📝 Content: {repr(result.xml[:200])}...")
                
        except Exception as e:
            print(f"❌ {model_name}: Error - {e}")


if __name__ == "__main__":
    print("🧪 BOB_2 CONSISTENCY TESTING")
    print("=" * 80)
    
    test_multiple_refinements()
    test_with_different_models()
    
    print("\n🎉 CONSISTENCY TESTS COMPLETED!")
