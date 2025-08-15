"""Agent workflow tests exercising end-to-end behavior (with model mocked).

Markers:
- agent: end-to-end agent behavior
"""

from __future__ import annotations

import re
import pytest

from core.ai import agent_chat, system_prompt


pytestmark = pytest.mark.agent


def _valid_bpmn(name: str = "Sample") -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL" id="Defs_{name}">
    <process id="Proc_{name}" isExecutable="false">
        <startEvent id="Start_1" name="Start" />
        <task id="Task_A" name="Do A" />
        <endEvent id="End_1" name="End" />
        <sequenceFlow id="f1" sourceRef="Start_1" targetRef="Task_A" />
        <sequenceFlow id="f2" sourceRef="Task_A" targetRef="End_1" />
    </process>
</definitions>"""


def _invalid_bpmn_missing_node() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL" id="Defs_Bad">
    <process id="Proc_Bad" isExecutable="false">
        <startEvent id="Start_1" name="Start" />
        <sequenceFlow id="f1" sourceRef="Start_1" targetRef="MISSING_NODE" />
    </process>
</definitions>"""


def _with_questions(bpmn: str) -> str:
    return f"{bpmn}\nQ1: First question?\nQ2: Second question?\nQ3: Third question?"


def _count_questions(text: str) -> int:
    return len(re.findall(r"^Q[1-3]:", text, flags=re.M))


@pytest.fixture(autouse=True)
def force_traditional_path(monkeypatch):
    """Force agent_chat to use the traditional validation loop by making
    marvin.run raise. This isolates tests from network/LLM dependencies.
    """
    import core.ai as ai

    def _raise(*_a, **_k):
        raise RuntimeError("disable marvin for tests")

    monkeypatch.setattr(ai.marvin, "run", _raise)
    yield


def test_natural_language_input_generates_bpmn(monkeypatch):
    """Agent should handle natural language requests and return BPMN with questions."""
    from core import ai as ai_mod

    # Model returns a valid BPMN and questions on first try
    monkeypatch.setattr(ai_mod, "chat", lambda *a, **k: _with_questions(_valid_bpmn("NaturalLang")))

    messages = system_prompt(
        "Create a simple three-step approval process.",
        "<definitions xmlns=\"http://www.omg.org/spec/BPMN/20100524/MODEL\" id=\"Empty\"><process id=\"P\"/></definitions>",
    )
    out = agent_chat(messages)

    assert "<definitions" in out and "</definitions>" in out
    assert _count_questions(out) == 3


def test_uses_current_bpmn_if_present(monkeypatch):
    """Agent should look at current BPMN and produce an updated version if needed."""
    from core import ai as ai_mod

    current = _valid_bpmn("Current")
    updated = _valid_bpmn("Updated")

    # Return an updated BPMN referencing a different id/name to indicate change
    monkeypatch.setattr(ai_mod, "chat", lambda *a, **k: _with_questions(updated))

    messages = system_prompt("Rename process to 'Updated' and keep structure.", current)
    out = agent_chat(messages)

    assert "Defs_Updated" in out and "Proc_Updated" in out
    assert _count_questions(out) == 3


def test_generates_changes_to_align_with_instructions(monkeypatch):
    """Agent should modify the BPMN to align with instructions (detectable delta)."""
    from core import ai as ai_mod

    current = _valid_bpmn("Alpha")
    # Simulate adding a new task and flow as alignment change
    changed = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<definitions xmlns=\"http://www.omg.org/spec/BPMN/20100524/MODEL\" id=\"Defs_Alpha\">
    <process id=\"Proc_Alpha\" isExecutable=\"false\">
        <startEvent id=\"Start_1\" name=\"Start\" />
        <task id=\"Task_A\" name=\"Do A\" />
        <task id=\"Task_B\" name=\"Review\" />
        <endEvent id=\"End_1\" name=\"End\" />
        <sequenceFlow id=\"f1\" sourceRef=\"Start_1\" targetRef=\"Task_A\" />
        <sequenceFlow id=\"f2\" sourceRef=\"Task_A\" targetRef=\"Task_B\" />
        <sequenceFlow id=\"f3\" sourceRef=\"Task_B\" targetRef=\"End_1\" />
    </process>
</definitions>"""

    monkeypatch.setattr(ai_mod, "chat", lambda *a, **k: _with_questions(changed))

    messages = system_prompt("Insert a review task between A and End.", current)
    out = agent_chat(messages)

    assert "Task_B" in out and "Review" in out
    assert "sequenceFlow id=\"f2\"" in out
    assert _count_questions(out) == 3


def test_validator_is_used_on_generated_bpmn(monkeypatch):
    """Agent should validate generated BPMN using the validator tool."""
    import core.ai as ai_mod

    calls = {"count": 0}
    real_validate = ai_mod.validate_bpmn

    def spy_validate(xml: str):
        calls["count"] += 1
        return real_validate(xml)

    monkeypatch.setattr(ai_mod, "validate_bpmn", spy_validate)
    monkeypatch.setattr(ai_mod, "chat", lambda *a, **k: _with_questions(_valid_bpmn("Val")))

    messages = system_prompt("Produce a valid process.", _valid_bpmn("Base"))
    _ = agent_chat(messages)

    assert calls["count"] >= 1


def test_iterates_until_fixed_or_max_iterations(monkeypatch):
    """Agent should fix invalid BPMN and revalidate until success or max tries."""
    import core.ai as ai_mod

    responses = [
        _with_questions(_invalid_bpmn_missing_node()),  # invalid first
        _with_questions(_valid_bpmn("Fixed")),         # then fixed
    ]

    def chat_sequence(*a, **k):
        return responses.pop(0)

    monkeypatch.setattr(ai_mod, "chat", chat_sequence)

    messages = system_prompt("Fix any validation errors.", _valid_bpmn("Initial"))
    out = agent_chat(messages, max_iterations=3)

    # Should converge to the valid, fixed BPMN
    assert "Defs_Fixed" in out and "Proc_Fixed" in out
    assert _count_questions(out) == 3


def test_stops_after_max_iterations(monkeypatch):
    """If the model keeps producing invalid BPMN, agent should stop after N tries."""
    import core.ai as ai_mod

    # Always return invalid BPMN
    monkeypatch.setattr(ai_mod, "chat", lambda *a, **k: _with_questions(_invalid_bpmn_missing_node()))

    messages = system_prompt("This will remain invalid.", _valid_bpmn("Start"))
    out = agent_chat(messages, max_iterations=2)

    assert "<definitions" in out  # Still returns what model produced
    assert "Maximum validation iterations reached" in out
    assert _count_questions(out) == 3
