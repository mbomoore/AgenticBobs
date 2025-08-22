#!/usr/bin/env python3
"""
Focused test to debug Bob_2 XML vs text output issue.
"""

import sys
from pathlib import Path

# Add the project paths to sys.path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "marvin_scripts"))

from marvin_scripts.common import build_model
from marvin_scripts.generate_xml import ProcessGenerationConfig, generate_process_xml


def test_initial_generation():
    """Test initial XML generation."""
    print("🧪 TEST: Initial XML Generation")
    print("=" * 50)
    
    try:
        model = build_model(model_name="qwen3:4b")
        
        config = ProcessGenerationConfig(
            description_or_answers="Create a customer onboarding process",
            process_type="BPMN",
            model_instance=model
        )
        
        result = generate_process_xml(config)
        
        print(f"📊 Generated XML Length: {len(result.xml)}")
        print(f"🔍 Starts with XML?: {result.xml.startswith('<?xml')}")
        print(f"📋 First 200 chars:")
        print(repr(result.xml[:200]))
        print()
        
        return result.xml
        
    except Exception as e:
        print(f"❌ Initial generation failed: {e}")
        return None


def test_refinement_generation():
    """Test refinement XML generation."""
    print("🧪 TEST: Refinement XML Generation")
    print("=" * 50)
    
    # First get initial XML
    initial_xml = test_initial_generation()
    if not initial_xml:
        print("❌ Cannot test refinement without initial XML")
        return
    
    try:
        model = build_model(model_name="qwen3:4b")
        
        config = ProcessGenerationConfig(
            description_or_answers="Add a validation step to check customer documentation",
            process_type="BPMN",
            model_instance=model,
            current_xml=initial_xml  # This should trigger refinement mode
        )
        
        result = generate_process_xml(config)
        
        print(f"📊 Refined XML Length: {len(result.xml)}")
        print(f"🔍 Starts with XML?: {result.xml.startswith('<?xml')}")
        print(f"📋 First 200 chars:")
        print(repr(result.xml[:200]))
        print()
        
        # Check if it's descriptive text vs XML
        if not result.xml.startswith('<?xml') and not result.xml.startswith('<'):
            print("❌ PROBLEM: Bob_2 returned descriptive text instead of XML!")
            print(f"📝 Full response: {result.xml}")
        else:
            print("✅ Bob_2 returned proper XML format")
            
    except Exception as e:
        print(f"❌ Refinement generation failed: {e}")


def test_agent_instructions():
    """Check what instructions Bob_2 is receiving."""
    print("🧪 TEST: Agent Instructions Analysis")
    print("=" * 50)
    
    try:
        # Create a Bob_2 agent to examine its instructions
        model = build_model(model_name="qwen3:4b")
        process_type = "BPMN"
        
        # Simulate the same instructions as in generate_xml.py
        instructions = (
            f"You are an expert {process_type} diagram generator. "
            f"Your ONLY job is to output complete, valid {process_type} XML. "
            f"CRITICAL RULES:\n"
            f"1. Return ONLY XML starting with <?xml version=\n"
            f"2. NO explanations, NO descriptions, NO text before or after the XML\n"
            f"3. Modify the provided template to match the business process description\n"
            f"4. Ensure all element IDs are unique and properly referenced\n"
            f"5. Your response must be parseable by an XML parser\n"
            f"6. NEVER explain what you changed - just return the XML\n\n"
            f"Input: Template XML + Business process description\n"
            f"Output: Complete {process_type} XML (nothing else)"
        )
        
        print("🤖 Bob_2 Agent Instructions:")
        print(instructions)
        print()
        
        # Check if refinement vs initial generation makes a difference
        print("🔍 Checking instruction clarity:")
        if "ONLY XML" in instructions and "NO explanations" in instructions:
            print("✅ Instructions clearly specify XML-only output")
        else:
            print("⚠️  Instructions may be ambiguous")
            
        if "NEVER explain what you changed" in instructions:
            print("✅ Instructions explicitly forbid explanations")
        else:
            print("⚠️  Missing explicit explanation prohibition")
            
    except Exception as e:
        print(f"❌ Instructions analysis failed: {e}")


if __name__ == "__main__":
    print("🧪 BOB_2 XML GENERATION DEBUG")
    print("=" * 80)
    
    test_agent_instructions()
    print()
    test_initial_generation()
    print()
    test_refinement_generation()
    
    print("🎉 DEBUG TESTS COMPLETED!")
