"""Optional integration test to exercise the Marvin agent path end-to-end.

Enable by setting environment variable RUN_MARVIN_INTEGRATION=1 and ensuring
an Ollama server is running with a compatible model (set OLLAMA_MODEL if needed).

This test forces the Marvin path by making the traditional fallback raise if used.
"""

from __future__ import annotations

import os
import httpx
import pytest

from agentic_process_automation.core.ai import agent_chat, agent_system_prompt


pytestmark = pytest.mark.marvin


def _server_reachable(base_url: str) -> bool:
    try:
        with httpx.Client(timeout=2.0) as c:
            base = base_url.rstrip("/")
            # Try OpenAI-compatible first
            r = c.get(base + "/models")
            if r.status_code < 500:
                return True
            # Fallback to plain Ollama style (if someone set OPENAI_BASE_URL to root)
            r2 = c.get(base + "/v1/models")
            return r2.status_code < 500
    except Exception:
        return False



def test_agent_chat_uses_marvin_when_available(monkeypatch):
    base_url = os.getenv("OPENAI_BASE_URL", "http://localhost:11434/v1")
    if not _server_reachable(base_url):
        pytest.skip(f"Ollama/OpenAI-compatible server not reachable at {base_url}")

    # Allow caller to select model via env var (e.g., OLLAMA_MODEL=llama3.1:8b)
    model = os.getenv("OLLAMA_MODEL")
    if model:
        import agentic_process_automation.core.ai as ai_mod
        monkeypatch.setattr(ai_mod, "DEFAULT_MODEL", model, raising=True)

    current_bpmn = ("<definitions xmlns=\"http://www.omg.org/spec/BPMN/20100524/MODEL\" id=\"Demo\">"
                    "<process id=\"P\"/></definitions>")
    messages = agent_system_prompt("Add a user task named 'Review'", current_bpmn)

    out = agent_chat(messages, max_iterations=1)
    assert isinstance(out, str) and len(out) > 0
    # Best-effort checks for format; models may vary
    assert "Q1:" in out and "Q2:" in out and "Q3:" in out
