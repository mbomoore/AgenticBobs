from agentic_process_automation.core.adapters.bpmn_min import from_bpmn_xml


def test_bpmn_adapter_attaches_original_xml_representation():
    xml = b"""<?xml version='1.0' encoding='UTF-8'?>
<definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL">
  <process id="P1">
    <startEvent id="s" />
  </process>
</definitions>
"""
    pir = from_bpmn_xml(xml)
    assert "bpmn+xml" in pir.representations
    assert "<definitions" in pir.representations["bpmn+xml"]
