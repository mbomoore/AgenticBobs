from agentic_process_automation.core.ai import extract_bpmn_xml, system_prompt


def test_extract_bpmn_xml_none():
    assert extract_bpmn_xml("") is None
    assert extract_bpmn_xml("no xml here") is None


def test_extract_bpmn_xml_basic():
    txt = "xxx<definitions id='d'>\n  <process id='p'/>\n</definitions>yyy"
    out = extract_bpmn_xml(txt)
    assert out is not None
    assert out.lower().startswith("<definitions")
    assert out.strip().endswith("</definitions>")


def test_system_prompt_builds():
    msgs = system_prompt("add a task", "<definitions/>")
    assert isinstance(msgs, list)
    assert msgs[0]["role"] == "system"
    assert "BPMN" in msgs[0]["content"]
    assert "Current BPMN" in msgs[1]["content"]
