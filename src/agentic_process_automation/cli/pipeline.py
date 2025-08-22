"""End-to-end pipeline: detect type, generate XML, validate (BPMN only).

Usage:
  uv run python -m marvin_scripts.pipeline --description "..."

Notes:
- Validation is performed for BPMN only (others: placeholder pass-through).
"""
from __future__ import annotations

import argparse
import io
import sys

import marvin

from .common import build_model

from .detect_type import bob_1

from .generate_xml import generate_process_xml, ProcessGenerationConfig

from .generate_refinement_questions import generate_refinement_questions, RefinementQuestionsConfig

# use the marvin.thread system make a conversation.



if __name__ == "__main__":
    
    small = build_model(model_name="qwen3:8b")
    large = build_model(model_name="gpt-oss:20b")
    
    thread = marvin.Thread()

    
    while True:
        
            
        # if we are at the beginning, then start by asking for a description of the process and typifying it
        if not hasattr(thread, '_process_type'):
            input_text = input("What would you say that you do here? ")
            
            thread._process_type = bob_1(small, input_text)
        else:
            input_text = input(f"You can write your answers here: ")
            
            if input_text.lower() in ['exit', 'quit', 'q', 'stop']:
                print("Exiting the pipeline.")
                print("XML so far: ")
                print(thread._current_xml)
                sys.exit(0)
            
        pgen_conf = ProcessGenerationConfig(
            description_or_answers=input_text,
            process_type=thread._process_type,
            model_instance=large,
            current_thread=thread,
            current_xml=getattr(thread, '_current_xml', None)
        )
        
        xml = generate_process_xml(pgen_conf)
        
        thread._current_xml = xml.xml
        
        
        rfc = RefinementQuestionsConfig(
            original_description_or_answer=input_text,
            generated_xml=thread._current_xml,
            process_type=thread._process_type,
            model_instance=large,
            current_thread=thread
        )
        
        questions = generate_refinement_questions(rfc)
        
        print("Here are some questions to refine the process model:")
        for q in questions:
            print(f"- {q}")
            
        
        
        
            
        