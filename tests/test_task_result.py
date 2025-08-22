#!/usr/bin/env python3
"""
Test to see exactly what task.run() returns.
"""

import sys
from pathlib import Path

# Add the project paths to sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.agentic_process_automation.cli.common import build_model
from src.agentic_process_automation.cli.generate_xml import ProcessGenerationConfig, generate_process_xml


def test_task_result():
    """Test what the task actually returns."""
    print("🧪 TEST: Task Result Investigation")
    print("=" * 50)
    
    try:
        model = build_model(model_name="qwen3:4b")
        
        config = ProcessGenerationConfig(
            description_or_answers="Create a simple process",
            process_type="BPMN",
            model_instance=model
        )
        
        print("📤 Running generation...")
        result = generate_process_xml(config)
        
        print(f"📊 Final result type: {type(result)}")
        print(f"📊 Final result XML length: {len(result.xml)}")
        print(f"📊 Final result valid: {result.xml.startswith('<?xml')}")
        print(f"📋 Final result preview: {repr(result.xml[:200])}")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_task_result()
