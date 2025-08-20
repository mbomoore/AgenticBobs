"""Generate a process XML diagram using Bob_2, given a description and a base empty template.

Usage:
  uv run python -m marvin_scripts.generate_xml --description "..." --type BPMN

Outputs the XML to stdout.
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from typing import Literal

import marvin
from core.bpmn_validator import validate_bpmn_string
from marvin.handlers import PrintHandler

from marvin_scripts.common import build_model, get_empty_process_model

ProcessType = Literal["BPMN", "DMN", "CMMN", "ArchiMate"]


@dataclass
class ProcessGenerationConfig:
    """Configuration for process XML generation."""
    description: str
    process_type: ProcessType
    model_name: str = "qwen3:8b"


def generate_process_xml(config: ProcessGenerationConfig) -> str:
    """Generate process XML from description using AI agent.
    
    Args:
        config: Configuration containing description, process type, and model settings
        
    Returns:
        Generated XML string representing the process
    """
    model = build_model(model_name=config.model_name)

    empty_template, example_inputs = get_empty_process_model(config.process_type)
    empty_xml = empty_template.format(**example_inputs)

    bob_2 = marvin.Agent(
        name="Bob_2",
        model=model,
        instructions=(
            "You are an expert business process modelling consultant. "
            "Your job is to look at a current XML diagram of a business process, "
            "along with an English language description of a business process, and output a new, "
            "valid XML diagram that reflects the business process described."
        ),
        tools=[validate_bpmn_string]
    )

    task = marvin.Task(
        "Make the necessary changes to the XML diagram to align it with the described business process",
        agents=[bob_2],
        context={"description": config.description, "xml_process": empty_xml},
    )

    return task.run(handlers=[PrintHandler()])


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate process XML from description")
    p.add_argument("--description", required=True, help="Natural language description")
    p.add_argument("--type", required=True, choices=["BPMN", "DMN", "CMMN", "ArchiMate"], help="Process model type")
    p.add_argument("--model", default="qwen3:8b", help="Model name to use")
    return p.parse_args()


def main() -> int:
    """Command-line interface for process XML generation."""
    args = parse_args()
    
    config = ProcessGenerationConfig(
        description=args.description,
        process_type=args.type,
        model_name=args.model
    )
    
    output = generate_process_xml(config)
    print(output)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
