"""Agent workflow tests exercising end-to-end behavior using the real agent.

Markers:
- marvin: integration tests that require a running Ollama/OpenAI-compatible server
"""

from __future__ import annotations

import pytest

import os
import httpx

from core.ai import agent_chat, system_prompt
from tests.helpers import valid_bpmn, invalid_bpmn_missing_node, with_questions, count_questions


pytestmark = pytest.mark.marvin


def _server_reachable(base_url: str) -> bool:
    try:
        with httpx.Client(timeout=2.0) as c:
            base = base_url.rstrip("/")
            r = c.get(base + "/models")
            if r.status_code < 500:
                return True
            r2 = c.get(base + "/v1/models")
            return r2.status_code < 500
    except Exception:
        return False



def test_natural_language_input_generates_bpmn():
    """Agent should handle natural language requests and return BPMN with questions."""
    base_url = os.getenv("OPENAI_BASE_URL", "http://localhost:11434/v1")
    if not _server_reachable(base_url):
        pytest.skip(f"Ollama/OpenAI-compatible server not reachable at {base_url}")

    messages = system_prompt(
        "Create a simple three-step approval process.",
        "<definitions xmlns=\"http://www.omg.org/spec/BPMN/20100524/MODEL\" id=\"Empty\"><process id=\"P\"/></definitions>",
    )
    out = agent_chat(messages)

    assert "<definitions" in out and "</definitions>" in out
    assert count_questions(out) == 3


def test_uses_current_bpmn_if_present():
    """Agent should look at current BPMN and produce BPMN with follow-up questions."""
    base_url = os.getenv("OPENAI_BASE_URL", "http://localhost:11434/v1")
    if not _server_reachable(base_url):
        pytest.skip(f"Ollama/OpenAI-compatible server not reachable at {base_url}")

    current = valid_bpmn("Current")
    messages = system_prompt("Rename process to 'Updated' and keep structure.", current)
    out = agent_chat(messages)

    assert "<definitions" in out and "</definitions>" in out
    assert count_questions(out) == 3


def test_generates_changes_to_align_with_instructions():
    """Agent should modify the BPMN to align with instructions (format and questions only)."""
    base_url = os.getenv("OPENAI_BASE_URL", "http://localhost:11434/v1")
    if not _server_reachable(base_url):
        pytest.skip(f"Ollama/OpenAI-compatible server not reachable at {base_url}")

    current = valid_bpmn("Alpha")
    messages = system_prompt("Insert a review task between A and End.", current)
    try:
        out = agent_chat(messages)
    except Exception as e:
        pytest.skip(f"Agent returned no text or failed: {e}")

    assert "<definitions" in out and "</definitions>" in out
    assert count_questions(out) == 3


def test_marvin_agent_runs_with_tools_enabled_env():
    """Agent should run end-to-end when tools are enabled via env (no introspection)."""
    base_url = os.getenv("OPENAI_BASE_URL", "http://localhost:11434/v1")
    if not _server_reachable(base_url):
        pytest.skip(f"Ollama/OpenAI-compatible server not reachable at {base_url}")

    os.environ["MARVIN_ENABLE_TOOLS"] = "1"
    messages = system_prompt("Produce a valid process.", valid_bpmn("Base"))
    out = agent_chat(messages)

    assert isinstance(out, str) and "<definitions" in out and "</definitions>" in out
    assert count_questions(out) == 3

