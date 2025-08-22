#!/usr/bin/env python3
"""
Test just the XML generation part directly with the model.
"""

import sys
from pathlib import Path
import requests
import json

# Add the project paths to sys.path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "marvin_scripts"))

from marvin_scripts.common import get_empty_process_model


def test_direct_ollama_call():
    """Test direct call to Ollama without Marvin framework."""
    print("🧪 TEST: Direct Ollama XML Generation")
    print("=" * 50)
    
    try:
        # Get BPMN template
        template, inputs = get_empty_process_model("BPMN")
        base_xml = template.format(**inputs)
        
        # Create prompt for XML generation
        prompt = f"""You are an expert BPMN diagram generator. Your job is to modify XML templates to create complete BPMN diagrams.

CRITICAL RULES:
1. Return ONLY valid XML starting with <?xml version=
2. NO explanations, NO descriptions, NO text before or after
3. Modify the template to match the business process
4. Keep all XML structure and namespaces intact
5. Ensure element IDs are unique and properly referenced

Template to modify:
{base_xml}

Business Process: Create a customer onboarding process with steps for document collection, verification, and account setup.

Return XML only:"""

        # Direct Ollama API call
        ollama_url = "http://localhost:11434/api/generate"
        payload = {
            "model": "qwen3:4b",
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "top_p": 0.9
            }
        }
        
        print("📤 Sending request to Ollama...")
        response = requests.post(ollama_url, json=payload, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            generated_xml = result.get('response', '').strip()
            
            print(f"✅ Generated XML ({len(generated_xml)} chars):")
            print("🔍 First 500 characters:")
            print(generated_xml[:500])
            print()
            
            # Check if it looks like valid XML
            if generated_xml.startswith('<?xml'):
                print("✅ Output starts with XML declaration")
            else:
                print("❌ Output doesn't start with XML declaration")
                print(f"📋 Raw response: {generated_xml[:200]}...")
                
            return generated_xml
            
        else:
            print(f"❌ Ollama request failed: {response.status_code}")
            print(f"📋 Response: {response.text}")
            return None
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to Ollama server")
        print("💡 Make sure Ollama is running: ollama serve")
        return None
    except Exception as e:
        print(f"❌ Direct Ollama test failed: {e}")
        return None


def test_xml_extraction():
    """Test XML extraction from text containing explanations."""
    print("🧪 TEST: XML Extraction from Mixed Content")
    print("=" * 50)
    
    # Simulate a response with explanations
    mixed_response = """Here's the BPMN diagram for customer onboarding:

<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions id="def_customer_onboarding" targetNamespace="urn:example:bpmn"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL">
  <bpmn:process id="Process_1" isExecutable="true">
    <bpmn:startEvent id="StartEvent_1" name="Start Onboarding"/>
    <bpmn:task id="Task_1" name="Collect Documents"/>
    <bpmn:endEvent id="EndEvent_1" name="Complete Onboarding"/>
  </bpmn:process>
</bpmn:definitions>

This process includes the essential steps for customer onboarding."""
    
    try:
        import re
        
        # Test the same patterns used in generate_xml.py
        xml_patterns = [
            r'(<\?xml.*?</.*?>)',  # Complete XML document
            r'(<.*?xmlns.*?</.*?>)',  # XML with namespace
            r'(<definitions.*?</definitions>)',  # BPMN definitions block
            r'(<process.*?</process>)',  # Process block
        ]
        
        found_xml = None
        for pattern in xml_patterns:
            xml_match = re.search(pattern, mixed_response, re.DOTALL)
            if xml_match:
                found_xml = xml_match.group(1)
                print(f"✅ Extracted XML using pattern: {pattern[:20]}...")
                break
        
        if found_xml:
            print(f"✅ Successfully extracted XML ({len(found_xml)} chars):")
            print(found_xml[:300] + "..." if len(found_xml) > 300 else found_xml)
        else:
            print("❌ No XML patterns matched")
            
    except Exception as e:
        print(f"❌ XML extraction test failed: {e}")


if __name__ == "__main__":
    print("🧪 XML GENERATION TESTS")
    print("=" * 80)
    
    xml_result = test_direct_ollama_call()
    print()
    test_xml_extraction()
    
    print("\n🎉 XML TESTS COMPLETED!")
