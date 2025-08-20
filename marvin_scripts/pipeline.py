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
from SpiffWorkflow.bpmn.parser import BpmnParser, BpmnValidator

from marvin_scripts.common import build_model, get_empty_process_model
from core.bpmn_validator import validate_bpmn_string


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Detect type, generate XML, validate")
    p.add_argument("--description", required=True, help="Natural language description")
    return p.parse_args()


def detect_type(description: str, model) -> str:
    bob_1 = marvin.Agent(
        name="Bob_1",
        model=model,
        instructions=(
            "You are an expert business process modelling consultant. "
            "Decide if the process is best modelled as BPMN, DMN or CMMN. "
            "Respond with only the model type."
        ),
    )
    return bob_1.run(description, handlers=[])


def generate_xml(description: str, model_type: str, model) -> str:
    empty_template, example_inputs = get_empty_process_model(model_type)
    empty_xml = empty_template.format(**example_inputs)

    bob_2 = marvin.Agent(
        name="Bob_2",
        model=model,
        instructions=(
            "You are an expert business process modelling consultant. "
            "Update the XML diagram to reflect the described business process."
        ),
        tools=[validate_bpmn_string],
    )

    task = marvin.Task(
        "Make the necessary changes to the XML diagram to align it with the described business process",
        agents=[bob_2],
        context={"description": description, "xml_process": empty_xml},
    )

    return task.run(handlers=[])


def validate_if_bpmn(model_type: str, xml_text: str) -> None:
    if model_type != "BPMN":
        print("Validation skipped (only BPMN supported)")
        return

    validator = BpmnValidator()
    parser = BpmnParser(validator=validator)

    bytes_xml = xml_text.encode("utf-8")
    bytes_io = io.BytesIO(bytes_xml)
    parser.add_bpmn_io(bytes_io)
    print("Validation OK")


def main() -> int:
    args = parse_args()
    model = build_model()

    model_type = detect_type(args.description, model)
    print(f"Detected type: {model_type}")

    xml_out = generate_xml(args.description, model_type, model)
    print("\n--- Generated XML ---\n")
    print(xml_out)

    try:
        validate_if_bpmn(model_type, xml_out)
    except Exception as exc:
        print(f"Validation error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
