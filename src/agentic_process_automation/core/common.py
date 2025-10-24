"""
Common utilities for Marvin-based process modeling scripts.

Includes:
- XMLProcessObject model
- Provider/model factory for pydantic-ai OpenAI compat layer
- Minimal empty XML templates and helper for retrieving them
"""
from __future__ import annotations

from typing import Dict, Tuple, Optional, cast
from pydantic import BaseModel
import os

try:
    from pydantic_ai.providers.openai import OpenAIProvider
    from pydantic_ai.models.openai import OpenAIModel
    PYDANTIC_AI_AVAILABLE = True
except ImportError:
    PYDANTIC_AI_AVAILABLE = False

# Import centralized configuration
try:
    from ..config import get_ai_config
    CONFIG_AVAILABLE = True
except ImportError:
    # Fallback for when imported from tests or different contexts
    CONFIG_AVAILABLE = False

# Lazy imports to avoid import cost for scripts that don't need the LLM
def build_model(
    base_url: Optional[str] = None,
    model_name: Optional[str] = None,
    api_key: Optional[str] = None,
):
    """Construct an OpenAI-compatible model for pydantic-ai.

    Environment fallbacks:
    - LLM_BASE_URL (default from config)
    - LLM_MODEL_NAME (default from config)
    - LLM_API_KEY (default from config)
    """
    if not PYDANTIC_AI_AVAILABLE:
        raise ImportError("pydantic-ai library required for model building")

    # Use centralized config if available, otherwise fall back to environment/defaults
    if CONFIG_AVAILABLE:
        ai_config = get_ai_config()
        resolved_base_url = base_url or os.environ.get("LLM_BASE_URL", ai_config.ollama_api_url)
        resolved_model_name = model_name or os.environ.get("LLM_MODEL_NAME", ai_config.default_small_model)
        resolved_api_key = api_key or os.environ.get("LLM_API_KEY", ai_config.api_key)
    else:
        # Fallback for when config is not available
        resolved_base_url = base_url or os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1")
        resolved_model_name = model_name or os.environ.get("LLM_MODEL_NAME", "qwen3:8b")
        resolved_api_key = api_key or os.environ.get("LLM_API_KEY", "")

    provider = OpenAIProvider(base_url=resolved_base_url, api_key=resolved_api_key)  # type: ignore[attr-defined]
    # Cast to satisfy strict type hints in provider stubs
    model = OpenAIModel(model_name=cast(str, resolved_model_name), provider=provider)  # type: ignore[attr-defined]
    return model


class XMLProcessObject(BaseModel):
    """Container for an XML process artifact and metadata."""

    content: str
    type: str
    errors: list[str] = []
    warnings: list[str] = []


# Minimal templates copied from the notebook for independent reuse
EMPTY_XML_TEMPLATES_MINIMAL: Dict[str, str] = {
    "BPMN": """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<bpmn:definitions id=\"{definitions_id}\" targetNamespace=\"{target_namespace}\"
  xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\"
  xmlns:bpmn=\"http://www.omg.org/spec/BPMN/20100524/MODEL\"
  xmlns:bpmndi=\"http://www.omg.org/spec/BPMN/20100524/DI\"
  xmlns:dc=\"http://www.omg.org/spec/DD/20100524/DC\"
  xmlns:di=\"http://www.omg.org/spec/DD/20100524/DI\">
  <bpmn:process id=\"Process_1\" isExecutable=\"true\">
    <bpmn:startEvent id=\"StartEvent_1\" name=\"Start\">
      <bpmn:outgoing>Flow_1</bpmn:outgoing>
    </bpmn:startEvent>
    <bpmn:task id=\"Task_1\" name=\"Example Task\">
      <bpmn:incoming>Flow_1</bpmn:incoming>
      <bpmn:outgoing>Flow_2</bpmn:outgoing>
    </bpmn:task>
    <bpmn:endEvent id=\"EndEvent_1\" name=\"End\">
      <bpmn:incoming>Flow_2</bpmn:incoming>
    </bpmn:endEvent>
    <bpmn:sequenceFlow id=\"Flow_1\" sourceRef=\"StartEvent_1\" targetRef=\"Task_1\" />
    <bpmn:sequenceFlow id=\"Flow_2\" sourceRef=\"Task_1\" targetRef=\"EndEvent_1\" />
  </bpmn:process>
</bpmn:definitions>""",
    "DMN": """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<definitions id=\"{definitions_id}\" name=\"{definitions_name}\" namespace=\"{target_namespace}\"
  xmlns=\"https://www.omg.org/spec/DMN/20191111/MODEL/\"
  xmlns:dmndi=\"https://www.omg.org/spec/DMN/20191111/DMNDI/\"
  xmlns:di=\"http://www.omg.org/spec/DMN/20180521/DI/\"
  xmlns:dc=\"http://www.omg.org/spec/DMN/20180521/DC/\"
  xmlns:feel=\"https://www.omg.org/spec/DMN/20191111/FEEL/\">\n  <!-- Add <decision>, <inputData>, <businessKnowledgeModel>, etc. later -->\n</definitions>""",
    "CMMN": """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<cmmn:definitions id=\"{definitions_id}\" targetNamespace=\"{target_namespace}\"
  xmlns:cmmn=\"http://www.omg.org/spec/CMMN/20151109/MODEL\"
  xmlns:cmmndi=\"http://www.omg.org/spec/CMMN/20151109/CMMNDI\"
  xmlns:dc=\"http://www.omg.org/spec/DD/20100524/DC\"
  xmlns:di=\"http://www.omg.org/spec/DD/20100524/DI\">\n  <!-- Add <cmmn:case> later -->\n</cmmn:definitions>""",
    "ArchiMate": """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<model xmlns=\"http://www.opengroup.org/xsd/archimate/3.0/\"
  xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\"
  identifier=\"{model_id}\" name=\"{model_name}\">\n  <metadata>\n    <schema>{schema_version}</schema>\n  </metadata>\n  <!-- Add <elements>, <relationships>, <organizations>, <properties> later -->\n</model>""",
}

EXAMPLE_GLOBAL_INPUTS: Dict[str, Dict[str, str]] = {
    "BPMN": {
        "definitions_id": "def_bpmn_empty",
        "target_namespace": "urn:example:bpmn",
    },
    "DMN": {
        "definitions_id": "def_dmn_empty",
        "definitions_name": "EmptyDMN",
        "target_namespace": "urn:example:dmn",
    },
    "CMMN": {
        "definitions_id": "def_cmmn_empty",
        "target_namespace": "urn:example:cmmn",
    },
    "ArchiMate": {
        "model_id": "archi_model_empty",
        "model_name": "EmptyModel",
        "schema_version": "3.0",
    },
}


def get_empty_process_model(model_type: str) -> Tuple[str, Dict[str, str]]:
    """Return template and example inputs for a given process model type."""
    if model_type not in EMPTY_XML_TEMPLATES_MINIMAL:
        raise ValueError(f"Unknown model type: {model_type}")
    return EMPTY_XML_TEMPLATES_MINIMAL[model_type], EXAMPLE_GLOBAL_INPUTS[model_type]
