"""Generate refinement questions for process models using Bob_3.

Usage:
    uv run python -m marvin_scripts.generate_refinement_questions --description "..." --xml "..." --type BPMN

This version accepts a model instance and a current thread (both optional) via the config,
so callers can pass concrete marvin objects instead of a model name.
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from typing import Any, Optional, Literal

import marvin
from marvin.handlers.print_handler import PrintHandler

from .common import build_model

ProcessType = Literal["BPMN", "DMN", "CMMN", "ArchiMate"]


@dataclass
class RefinementQuestionsConfig:
        """Configuration for generating refinement questions.

        Either provide a concrete model_instance or a model_name (model_name is used
        to build a model via build_model if model_instance is None). Optionally pass
        a current_thread to provide task context from an existing conversation/thread.
        """
        original_description_or_answer: str
        generated_xml: str
        process_type: ProcessType
        model_instance: Optional[Any] = None
        current_thread: Optional[Any] = None
        model_name: str = "qwen3:8b"


def generate_refinement_questions(config: RefinementQuestionsConfig) -> list[str]:
        """Generate refinement questions for a process model using Bob_3.

        Args:
                config: Configuration containing description, XML, process type, and model/thread settings

        Returns:
                List of refinement questions
        """
        # Use provided model instance if present, otherwise build from model_name
        model = config.model_instance if config.model_instance is not None else build_model(model_name=config.model_name)

        bob_3 = marvin.Agent(
                name="Bob_3",
                model=model,
                instructions=(
                        "You are an expert business process analyst. "
                        "Your ONLY job is to generate exactly 3 refinement questions. "
                        "CRITICAL RULES:\n"
                        "1. Generate EXACTLY 3 questions, no more, no less\n"
                        "2. Number each question (1., 2., 3.)\n"
                        "3. Focus on practical process improvements\n"
                        "4. Questions should address: missing steps, decision points, exception handling, roles, timing, or integrations\n"
                        "5. Make questions specific and actionable\n"
                        "6. ALWAYS provide 3 questions even if the process seems complete\n\n"
                        "Format your response as:\n"
                        "1. [First question about the process]\n"
                        "2. [Second question about the process]\n"
                        "3. [Third question about the process]"
                ),
        )

        # Provide the original description, the generated XML and the process type, and pass through thread if provided.
        task_context = {
                "original_description_or_answer": config.original_description_or_answer,
                "generated_xml": config.generated_xml,
                "process_type": config.process_type,
        }

        questions_task = marvin.Task(
                "Generate 3 refinement questions for the process model",
                agents=[bob_3],
                context=task_context,
        )

        # Run the task. Avoid forcing PrintHandler so the caller (or tests) can receive the response object.
        try:
                raw_response = questions_task.run(thread=config.current_thread)
        except Exception:
                # As a fallback, attempt to run with a PrintHandler so CLI usage still prints something.
                raw_response = questions_task.run(handlers=[PrintHandler()])

        response_text = str(raw_response or "")
        print(f"🔍 Bob_3 raw response length: {len(response_text)}")
        print(f"🔍 Bob_3 response preview: {repr(response_text[:200])}")

        # Enhanced question parsing with multiple fallback strategies
        questions_list = []
        
        # Strategy 1: Look for numbered questions (1., 2., 3.)
        import re
        numbered_pattern = r'(\d+)\.\s*(.+?)(?=\d+\.|$)'
        numbered_matches = re.findall(numbered_pattern, response_text, re.DOTALL | re.MULTILINE)
        
        if numbered_matches:
                questions_list = [match[1].strip() for match in numbered_matches if match[1].strip()]
                print(f"✅ Found {len(questions_list)} numbered questions")
        
        # Strategy 2: Split by lines and look for question-like content
        if not questions_list:
                candidate_lines = [line.strip() for line in response_text.splitlines() if line.strip()]
                for line in candidate_lines:
                        # Remove common prefixes and check if it looks like a question
                        clean_line = line.lstrip("1234567890. -•").strip()
                        if clean_line and (clean_line.endswith('?') or len(clean_line) > 20):
                                questions_list.append(clean_line)
                                if len(questions_list) >= 3:
                                        break
                print(f"✅ Found {len(questions_list)} questions from line parsing")
        
        # Strategy 3: Generate fallback questions if none found
        if not questions_list:
                print("⚠️  No questions found, generating fallback questions")
                fallback_questions = [
                        f"What specific roles or stakeholders should be responsible for each step in this {config.process_type} process?",
                        f"How should exception scenarios or error conditions be handled within this process?",
                        f"What approval workflows or decision points might be missing from the current {config.process_type} model?"
                ]
                questions_list = fallback_questions
        
        # Ensure we have exactly 3 questions
        if len(questions_list) < 3:
                # Pad with generic questions
                while len(questions_list) < 3:
                        questions_list.append(f"What additional considerations should be included for this {config.process_type} process?")
        elif len(questions_list) > 3:
                # Trim to first 3
                questions_list = questions_list[:3]
        
        print(f"✅ Final question count: {len(questions_list)}")
        return questions_list


def parse_args() -> argparse.Namespace:
        """Parse command line arguments."""
        p = argparse.ArgumentParser(description="Generate refinement questions for process models")
        p.add_argument("--description", required=True, help="Original natural language description")
        p.add_argument("--xml", required=True, help="Generated XML process model")
        p.add_argument("--type", required=True, choices=["BPMN", "DMN", "CMMN", "ArchiMate"], help="Process model type")
        p.add_argument("--model", default="qwen3:8b", help="Model name to use when a model instance is not provided")
        return p.parse_args()


def main() -> int:
        """Command-line interface for refinement question generation."""
        args = parse_args()

        # Build a model instance for CLI usage (callers who already have a model instance should construct the config directly).
        model_instance = build_model(model_name=args.model)

        config = RefinementQuestionsConfig(
                original_description_or_answer=args.description,
                generated_xml=args.xml,
                process_type=args.type,
                model_instance=model_instance,
                # current_thread cannot be provided via CLI; left as None for programmatic use
        )

        questions = generate_refinement_questions(config)

        print("Refinement Questions:")
        for i, question in enumerate(questions, 1):
                print(f"{i}. {question}")

        return 0


if __name__ == "__main__":  # pragma: no cover
        sys.exit(main())
