"""Validate a BPMN XML string via SpiffWorkflow parser/validator.

Usage:
  uv run python -m marvin_scripts.validate_bpmn <<<'<bpmn:definitions ...>...'
  or pipe a file: cat model.bpmn | uv run python -m marvin_scripts.validate_bpmn
"""
from __future__ import annotations

import sys
import io

from SpiffWorkflow.bpmn.parser import BpmnParser, BpmnValidator


def main() -> int:
    xml_text = sys.stdin.read()
    if not xml_text.strip():
        print("No XML provided on stdin", file=sys.stderr)
        return 2

    validator = BpmnValidator()
    parser = BpmnParser(validator=validator)

    bytes_xml = xml_text.encode("utf-8")
    bytes_io = io.BytesIO(bytes_xml)

    # This will raise if invalid; we can capture and format errors
    try:
        parser.add_bpmn_io(bytes_io)
        print("OK: BPMN parsed without fatal errors")
        return 0
    except Exception as exc:  # Spiff can raise different exceptions
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
