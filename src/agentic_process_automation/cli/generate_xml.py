"""Generate a process XML diagram using Bob_2, given a description and a base empty template.

Usage:
  uv run python -m marvin_scripts.generate_xml --description "..." --type BPMN

Outputs the XML to stdout.
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from typing import Literal, Optional, Union, List, Any

import marvin
from core.bpmn_validator import validate_bpmn_string
from marvin.handlers.print_handler import PrintHandler

from marvin_scripts.common import build_model, get_empty_process_model

ProcessType = Literal["BPMN", "DMN", "CMMN", "ArchiMate"]


@dataclass
class ProcessGenerationResult:
    """Result of process XML generation including optional refinement questions."""
    xml: str


@dataclass
class ProcessGenerationConfig:
    """Configuration for process XML generation.

    Either `model_instance` or `model_name` may be provided. If both are provided,
    `model_instance` takes precedence. `current_xml` may be provided to supply an
    existing process XML to be refined. `current_thread` may be any object representing
    the current conversation/thread and will be forwarded into the task context.
    """
    description_or_answers: str
    process_type: ProcessType
    model_name: Optional[str] = "qwen3:8b"
    model_instance: Optional[Any] = None
    current_xml: Optional[str] = None
    current_thread: Optional[Any] = None


def generate_process_xml(config: ProcessGenerationConfig) -> ProcessGenerationResult:
    """Generate process XML from description using AI agent.

    Args:
        config: Configuration containing description, process type, optional model (name or instance),
                optional current XML to refine, and optional current thread to continue.

    Returns:
        ProcessGenerationResult with generated XML and a (possibly empty) list of refinement questions.
    """
    # Resolve model: prefer an explicit model instance if provided
    if config.model_instance is not None:
        model = config.model_instance
    else:
        # build_model expects a model name
        model = build_model(model_name=config.model_name)

    empty_template, example_inputs = get_empty_process_model(config.process_type)
    # Use provided current XML if present; otherwise start from the empty template
    base_xml = config.current_xml if config.current_xml is not None else empty_template.format(**example_inputs)

    bob_2 = marvin.Agent(
        name="Bob_2",
        model=model,
        instructions=(
            "You are an expert business process modelling consultant. "
            "Your job is to look at a current XML diagram of a business process, "
            "along with an English language description of a business process, and output a new, "
            "valid XML diagram that reflects the business process described."
        ),
        tools=[validate_bpmn_string],
    )

    # Build the task context. Include the current thread if provided so the agent can continue a conversation.
    task_context = {
        "description": config.description_or_answers,
        "xml_process": base_xml,
    }


    xml_task = marvin.Task(
        "Make the necessary changes to the XML diagram to align it with the described business process",
        agents=[bob_2],
        context=task_context,
    )

    generated_xml = xml_task.run(thread=config.current_thread)

    # For now, no refinement question generator is invoked here; return an empty list to keep the contract stable.
    return ProcessGenerationResult(
        xml=generated_xml,
    )


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate process XML from description")
    p.add_argument("--description", required=True, help="Natural language description")
    p.add_argument("--type", required=True, choices=["BPMN", "DMN", "CMMN", "ArchiMate"], help="Process model type")
    p.add_argument("--model", default="qwen3:8b", help="Model name to use (ignored if supplying a model instance programmatically)")
    p.add_argument("--xml-file", help="Path to an existing XML file to refine", default=None)
    p.add_argument("--xml-data", help="Inline XML data to refine (takes precedence over --xml-file)", default=None)
    return p.parse_args()


def main() -> int:
    """Command-line interface for process XML generation."""
    args = parse_args()

    # Read XML from file if requested and not provided inline
    xml_data: Optional[str] = None
    if args.xml_data:
        xml_data = args.xml_data
    elif args.xml_file:
        with open(args.xml_file, "r", encoding="utf-8") as fh:
            xml_data = fh.read()

    config = ProcessGenerationConfig(
        description_or_answers=args.description,
        process_type=args.type,
        model_name=args.model,
        current_xml=xml_data,
        # current_thread cannot be provided via CLI; left as None for programmatic use
    )

    result = generate_process_xml(config)

    print("Generated XML:")
    print(result.xml)
    print("\nRefinement Questions:")
    for i, question in enumerate(result.refinement_questions, 1):
        print(f"{i}. {question}")

    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
