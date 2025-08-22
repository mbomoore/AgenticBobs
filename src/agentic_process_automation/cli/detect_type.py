"""Detect the best process model type (BPMN, DMN, CMMN) from a description.

Usage:
  uv run python -m marvin_scripts.detect_type --description "..."
"""
from __future__ import annotations

import argparse
import json
import sys

try:
    import marvin
    MARVIN_AVAILABLE = True
except ImportError:
    MARVIN_AVAILABLE = False

from .common import build_model



def bob_1(model, description: str) -> str:
    """Detect the best process model type from a description using Bob_1."""
    if not MARVIN_AVAILABLE:
        raise ImportError("marvin library required for AI-based type detection")
    
    bob_1 = marvin.Agent(  # type: ignore[attr-defined]
        name="Bob_1",
        model=model,
        instructions=(
            "You are an expert business process modelling consultant. "
            "Your job is to look at a business process and decide if it is best "
            "modelled as BPMN, DMN or CMMN. Please just respond with the appropriate "
            "model type, no explanation is needed."
        ),
    )
    return bob_1.run(description)
    


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Detect process model type from description")
    p.add_argument("--description", required=True, help="Natural language process description")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    
    if not MARVIN_AVAILABLE:
        print("Error: marvin library required for AI-based type detection")
        print("Install with: pip install marvin")
        return 1
    
    model = build_model()

    bob_1 = marvin.Agent(  # type: ignore[attr-defined]
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
