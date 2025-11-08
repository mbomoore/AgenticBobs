#!/usr/bin/env python3
"""
Standalone test script for the Bob agent flow.
Tests Bob_1 (process detection), Bob_2 (XML generation), and Bob_3 (refinement questions).
"""

import sys
from pathlib import Path

# Add the project paths to sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from agentic_process_automation.cli.detect_type import bob_1
from agentic_process_automation.cli.generate_xml import generate_process_xml, ProcessGenerationConfig
import pytest
from agentic_process_automation.cli.generate_refinement_questions import generate_refinement_questions, RefinementQuestionsConfig
from agentic_process_automation.core.common import build_model


@pytest.mark.skip(reason="Skipping test that requires a running Ollama server.")
def test_full_flow(user_message: str):
    """Test the complete Bob agent flow."""
    print("=" * 80)
    print(f"🚀 TESTING BOBS FLOW")
    print(f"📝 User Message: {user_message}")
    print("=" * 80)
    
    # Build models
    small_model = build_model(model_name="qwen3:4b")
    large_model = build_model(model_name="qwen3:8b")
    
    # Step 1: Bob_1 - Process Type Detection
    print("\n🔍 STEP 1: Bob_1 - Process Type Detection")
    print("-" * 50)
    detected_type = bob_1(small_model, user_message)
    print(f"✅ Detected Process Type: {detected_type}")
    
    # Step 2: Bob_2 - XML Generation
    print(f"\n🏗️  STEP 2: Bob_2 - {detected_type} XML Generation")
    print("-" * 50)
    
    pgen_config = ProcessGenerationConfig(
        description_or_answers=user_message,
        process_type=detected_type,  # type: ignore
        model_instance=large_model
    )
    
    bpmn_result = generate_process_xml(pgen_config)
    
    print(f"📊 Generated XML Length: {len(bpmn_result.xml) if bpmn_result.xml else 0}")
    
    if bpmn_result.xml:
        print(f"📋 XML Preview (first 300 chars):")
        print(f"```xml")
        print(bpmn_result.xml[:300] + "..." if len(bpmn_result.xml) > 300 else bpmn_result.xml)
        print(f"```")
        
        # Check if it's valid XML
        if bpmn_result.xml.strip().startswith('<?xml'):
            print("✅ XML Format: Valid (starts with XML declaration)")
        elif bpmn_result.xml.strip().startswith('<'):
            print("⚠️  XML Format: Partial (starts with tag but no declaration)")
        else:
            print("❌ XML Format: Invalid (does not start with XML content)")
    else:
        print("❌ No XML generated!")
        return
    
    # Step 3: Bob_3 - Refinement Questions
    print(f"\n❓ STEP 3: Bob_3 - Refinement Questions Generation")
    print("-" * 50)
    
    questions_config = RefinementQuestionsConfig(
        original_description_or_answer=user_message,
        generated_xml=bpmn_result.xml,
        process_type=detected_type,  # type: ignore
        model_instance=small_model
    )
    
    raw_questions = generate_refinement_questions(questions_config)
    
    # Clean up questions (same logic as backend)
    questions = []
    for q in raw_questions:
        if isinstance(q, str):
            clean_q = q.strip().lstrip("123456789. -•").strip()
            if clean_q and not clean_q.startswith("{") and not clean_q.startswith("["):
                questions.append(clean_q)
        else:
            clean_q = str(q).strip().lstrip("123456789. -•").strip()
            if clean_q and not clean_q.startswith("{") and not clean_q.startswith("["):
                questions.append(clean_q)
    
    print(f"📝 Generated Questions Count: {len(questions)}")
    if questions:
        print("📋 Questions:")
        for i, question in enumerate(questions, 1):
            print(f"   {i}. {question}")
    else:
        print("❌ No refinement questions generated!")
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 FLOW SUMMARY")
    print("=" * 80)
    print(f"✅ Process Type Detection: {detected_type}")
    print(f"✅ XML Generation: {'SUCCESS' if bpmn_result.xml and bpmn_result.xml.strip().startswith(('<', '<?xml')) else 'FAILED'}")
    print(f"✅ Questions Generation: {'SUCCESS' if questions else 'FAILED'}")
    print(f"📏 Final XML Length: {len(bpmn_result.xml) if bpmn_result.xml else 0} characters")
    print(f"🔢 Questions Count: {len(questions)}")
    
    return {
        'process_type': detected_type,
        'xml': bpmn_result.xml,
        'questions': questions
    }


@pytest.mark.skip(reason="Skipping test that requires a running Ollama server.")
def test_refinement_flow(original_message: str, refinement_message: str, previous_xml: str, process_type: str):
    """Test a refinement/follow-up interaction."""
    print("\n" + "=" * 80)
    print(f"🔄 TESTING REFINEMENT FLOW")
    print(f"📝 Original: {original_message}")
    print(f"🔧 Refinement: {refinement_message}")
    print("=" * 80)
    
    large_model = build_model(model_name="qwen3:8b")
    small_model = build_model(model_name="qwen3:4b")
    
    # Create conversation context
    conversation_context = f"user: {original_message}\nassistant: I've created a {process_type} process.\nuser: {refinement_message}"
    
    # Step 1: Bob_2 - XML Refinement
    print(f"\n🔧 STEP 1: Bob_2 - {process_type} XML Refinement")
    print("-" * 50)
    
    pgen_config = ProcessGenerationConfig(
        description_or_answers=conversation_context,
        process_type=process_type,  # type: ignore
        model_instance=large_model,
        current_xml=previous_xml
    )
    
    refined_result = generate_process_xml(pgen_config)
    
    print(f"📊 Refined XML Length: {len(refined_result.xml) if refined_result.xml else 0}")
    print(f"📏 Original vs Refined: {len(previous_xml)} → {len(refined_result.xml) if refined_result.xml else 0}")
    
    if refined_result.xml:
        print(f"📋 Refined XML Preview (first 300 chars):")
        print(f"```xml")
        print(refined_result.xml[:300] + "..." if len(refined_result.xml) > 300 else refined_result.xml)
        print(f"```")
    
    # Step 2: Bob_3 - New Refinement Questions
    print(f"\n❓ STEP 2: Bob_3 - New Refinement Questions")
    print("-" * 50)
    
    questions_config = RefinementQuestionsConfig(
        original_description_or_answer=refinement_message,
        generated_xml=refined_result.xml,
        process_type=process_type,  # type: ignore
        model_instance=small_model
    )
    
    raw_questions = generate_refinement_questions(questions_config)
    
    # Clean up questions
    questions = []
    for q in raw_questions:
        if isinstance(q, str):
            clean_q = q.strip().lstrip("123456789. -•").strip()
            if clean_q and not clean_q.startswith("{") and not clean_q.startswith("["):
                questions.append(clean_q)
        else:
            clean_q = str(q).strip().lstrip("123456789. -•").strip()
            if clean_q and not clean_q.startswith("{") and not clean_q.startswith("["):
                questions.append(clean_q)
    
    print(f"📝 New Questions Count: {len(questions)}")
    if questions:
        print("📋 New Questions:")
        for i, question in enumerate(questions, 1):
            print(f"   {i}. {question}")
    else:
        print("❌ No new refinement questions generated!")
    
    return {
        'refined_xml': refined_result.xml,
        'new_questions': questions
    }


if __name__ == "__main__":
    # Test 1: Initial flow
    print("🧪 TEST 1: Initial Process Creation")
    initial_result = test_full_flow("Create a customer onboarding process")
    
    # Test 2: Refinement flow
    if initial_result and initial_result.get('xml'):
        print("\n🧪 TEST 2: Process Refinement")
        refinement_result = test_refinement_flow(
            original_message="Create a customer onboarding process",
            refinement_message="Add a validation step to check customer documentation",
            previous_xml=initial_result['xml'],
            process_type=initial_result['process_type']
        )
    
    print("\n🎉 ALL TESTS COMPLETED!")
