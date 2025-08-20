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

from marvin_scripts.common import build_model

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
                        "Your job is to analyze a generated XML process diagram and the original description, "
                        "then generate exactly 3 thoughtful questions that would help refine and improve the process model. "
                        "Focus on areas like missing steps, unclear decision points, exception handling, "
                        "role responsibilities, timing constraints, or integration points. "
                        "Make your questions specific and actionable."
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

        # Parse questions from the response. Accept numbered or bulleted lists; fall back to splitting into lines.
        candidate_lines = [line.strip() for line in response_text.splitlines() if line.strip()]
        questions_list = [
                line.lstrip("1234567890. ").strip(" -•")
                for line in candidate_lines
                if line.startswith(("1.", "2.", "3.", "-", "•")) or len(candidate_lines) <= 3
        ]

        # If parsing produced no items but there are lines, return up to the first 3 non-empty lines.
        if not questions_list and candidate_lines:
                questions_list = candidate_lines[:3]

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
