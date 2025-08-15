"""Optional integration test to exercise the Marvin agent path end-to-end.

Enable by setting environment variable RUN_MARVIN_INTEGRATION=1 and ensuring
an Ollama server is running with a compatible model (set OLLAMA_MODEL if needed).

This test forces the Marvin path by making the traditional fallback raise if used.
"""

from __future__ import annotations

import os
import httpx
import pytest

from core.ai import agent_chat, agent_system_prompt


pytestmark = pytest.mark.marvin


def _server_reachable(base_url: str) -> bool:
    try:
        with httpx.Client(timeout=2.0) as c:
            # OpenAI-compatible models endpoint for Ollama proxy
            r = c.get(base_url.rstrip("/") + "/models")
            return r.status_code < 500
    except Exception:
        return False


@pytest.mark.skipif(os.getenv("RUN_MARVIN_INTEGRATION") != "1", reason="Set RUN_MARVIN_INTEGRATION=1 to run")
def test_agent_chat_uses_marvin_when_available(monkeypatch):
    base_url = os.getenv("OPENAI_BASE_URL", "http://localhost:11434/v1")
    if not _server_reachable(base_url):
        pytest.skip(f"Ollama/OpenAI-compatible server not reachable at {base_url}")

    # Allow caller to select model via env var (e.g., OLLAMA_MODEL=llama3.1:8b)
    model = os.getenv("OLLAMA_MODEL")
    if model:
        import core.ai as ai_mod
        monkeypatch.setattr(ai_mod, "DEFAULT_MODEL", model, raising=True)

    # Ensure fallback isn't used; if it is, the test should fail
    import core.ai as ai_mod
    def _fail_fallback(*a, **k):  # pragma: no cover - only used in this integration test
        raise AssertionError("Fallback path should not be used when Marvin is available")
    monkeypatch.setattr(ai_mod, "_traditional_agent_chat", _fail_fallback, raising=True)

    current_bpmn = ("<definitions xmlns=\"http://www.omg.org/spec/BPMN/20100524/MODEL\" id=\"Demo\">"
                    "<process id=\"P\"/></definitions>")
    messages = agent_system_prompt("Add a user task named 'Review'", current_bpmn)

    out = agent_chat(messages, max_iterations=1)
    assert isinstance(out, str) and len(out) > 0
    # Best-effort checks for format; models may vary
    assert "Q1:" in out and "Q2:" in out and "Q3:" in out
