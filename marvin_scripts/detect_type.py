"""Detect the best process model type (BPMN, DMN, CMMN) from a description.

Usage:
  uv run python -m marvin_scripts.detect_type --description "..."
"""
from __future__ import annotations

import argparse
import json
import sys

import marvin

from marvin_scripts.common import build_model



def bob_1(model, description: str) -> str:
    """Detect the best process model type from a description using Bob_1."""
    bob_1 = marvin.Agent(
        name="Bob_1",
        model=model,
        instructions=(
            "You are an expert business process modelling consultant. "
            "Your job is to look at a business process and decide if it is best "
            "modelled as BPMN, DMN or CMMN. Please just respond with the appropriate "
            "model type, no explanation is needed."
        ),
        model_settings={"think": False},
    )
    return bob_1.run(description)
    


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Detect process model type from description")
    p.add_argument("--description", required=True, help="Natural language process description")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    model = build_model()

    bob_1 = marvin.Agent(
        name="Bob_1",
        model=model,
        instructions=(
            "You are an expert business process modelling consultant. "
            "Your job is to look at a business process and decide if it is best "
            "modelled as BPMN, DMN or CMMN. Please just respond with the appropriate "
            "model type, no explanation is needed."
        ),
    )

    answer: str = bob_1.run(args.description, handlers=[])

    print(answer)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
