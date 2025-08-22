#!/usr/bin/env python3
"""
Simple test to verify each component works individually.
"""

import sys
from pathlib import Path

# Add the project paths to sys.path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "marvin_scripts"))

from marvin_scripts.common import get_empty_process_model, build_model


def test_templates():
    """Test that templates are working."""
    print("🧪 TEST: Template Generation")
    print("=" * 50)
    
    for process_type in ["BPMN", "DMN", "CMMN", "ArchiMate"]:
        try:
            template, inputs = get_empty_process_model(process_type)
            filled_template = template.format(**inputs)
            print(f"✅ {process_type}: {len(filled_template)} characters")
            print(f"   Preview: {filled_template[:100]}...")
        except Exception as e:
            print(f"❌ {process_type}: Error - {e}")
    
    print()


def test_bob_1_simple():
    """Test Bob_1 with a simple direct approach."""
    print("🧪 TEST: Bob_1 Process Detection (Simple)")
    print("=" * 50)
    
    try:
        from marvin_scripts.detect_type import bob_1
        model = build_model(model_name="qwen3:4b")
        
        test_messages = [
            "Create a customer onboarding process",
            "Build a decision table for loan approval",
            "Design a case management workflow for customer service",
            "Create an enterprise architecture view"
        ]
        
        for msg in test_messages:
            try:
                result = bob_1(model, msg)
                print(f"✅ '{msg[:30]}...' → {result}")
            except Exception as e:
                print(f"❌ '{msg[:30]}...' → Error: {e}")
                
    except Exception as e:
        print(f"❌ Bob_1 setup failed: {e}")
    
    print()


def test_xml_generation_manual():
    """Test XML generation with manual template filling."""
    print("🧪 TEST: Manual XML Generation")
    print("=" * 50)
    
    try:
        template, inputs = get_empty_process_model("BPMN")
        base_xml = template.format(**inputs)
        
        print(f"📋 Base BPMN Template ({len(base_xml)} chars):")
        print(base_xml)
        print()
        
        # Try simple modification
        modified_xml = base_xml.replace("Example Task", "Customer Onboarding Task")
        print(f"🔧 Modified XML ({len(modified_xml)} chars):")
        print(modified_xml[:500] + "..." if len(modified_xml) > 500 else modified_xml)
        
    except Exception as e:
        print(f"❌ Manual XML generation failed: {e}")
    
    print()


def test_bob_2_direct():
    """Test Bob_2 with direct model call."""
    print("🧪 TEST: Bob_2 Direct Model Test")  
    print("=" * 50)
    
    try:
        model = build_model(model_name="qwen3:8b")
        template, inputs = get_empty_process_model("BPMN")
        base_xml = template.format(**inputs)
        
        # Create a simple prompt instead of using the complex agent
        prompt = f"""You are an expert BPMN diagram generator. 
Your job is to modify the provided XML template to create a complete BPMN diagram.

CRITICAL RULES:
1. Return ONLY XML starting with <?xml version=
2. NO explanations, NO descriptions, NO text before or after the XML
3. Modify the provided template to match the business process description
4. Ensure all element IDs are unique and properly referenced

Template XML:
{base_xml}

Business Process Description:
Create a customer onboarding process

Output (XML only):"""

        print("📤 Sending prompt to model...")
        print("🤖 Waiting for response...")
        
        # This is a simplified approach - we'd need to implement direct model calling
        print("⚠️  Direct model testing requires implementing OpenAI client call")
        print("    This would bypass the complex Marvin agent system")
        
    except Exception as e:
        print(f"❌ Direct model test failed: {e}")
    
    print()


if __name__ == "__main__":
    print("🧪 SIMPLE COMPONENT TESTS")
    print("=" * 80)
    
    test_templates()
    test_bob_1_simple() 
    test_xml_generation_manual()
    test_bob_2_direct()
    
    print("🎉 SIMPLE TESTS COMPLETED!")
