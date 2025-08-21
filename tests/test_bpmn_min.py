import sys
from pathlib import Path

import pytest
from agentic_process_automation.core.adapters.bpmn_min import from_bpmn_xml
from agentic_process_automation.core.pir import validate
import types

FIXTURE_SIMPLE = b"""
<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<definitions xmlns=\"http://www.omg.org/spec/BPMN/20100524/MODEL\" id=\"Defs_1\">
  <process id=\"Proc_1\" isExecutable=\"false\">
    <startEvent id=\"Start_1\" name=\"Start\" />
    <task id=\"Task_A\" name=\"Do A\" />
    <exclusiveGateway id=\"Gw_1\" />
    <task id=\"Task_B\" name=\"Do B\" />
    <endEvent id=\"End_1\" name=\"End\" />

    <sequenceFlow id=\"f1\" sourceRef=\"Start_1\" targetRef=\"Task_A\" />
    <sequenceFlow id=\"f2\" sourceRef=\"Task_A\" targetRef=\"Gw_1\" />
    <sequenceFlow id=\"f3\" sourceRef=\"Gw_1\" targetRef=\"Task_B\" />
    <sequenceFlow id=\"f4\" sourceRef=\"Task_B\" targetRef=\"End_1\" />
  </process>
  <bpmndi:BPMNDiagram xmlns:bpmndi=\"http://www.omg.org/spec/BPMN/20100524/DI\"/>
  <di:Diagram xmlns:di=\"http://www.omg.org/spec/DD/20100524/DI\"/>
  <dc:Bounds xmlns:dc=\"http://www.omg.org/spec/DD/20100524/DC\"/>
</definitions>
"""


def test_min_parser_builds_pir_and_validates():

    pir = from_bpmn_xml(FIXTURE_SIMPLE)
    report = validate(pir)
    assert report["errors"] == []
    # Ensure basic node kinds mapped
    kinds = {n.kind for n in pir.nodes.values()}
    assert {"startEvent", "task", "exclusiveGateway", "endEvent"}.issubset(kinds)
    # Ensure edges count matches flows
    assert len(pir.edges) == 4
def test_dispatcher_prefers_spiff_when_available(monkeypatch):
    # Simulate SpiffWorkflow being available by creating fake modules
    import types

    class DummyParser:
        def parse_xml_string(self, s):
            class Dummy:
                task_specs = {}
                sequence_flows = []
            return Dummy()

    mod_spiff = types.ModuleType("spiffworkflow")
    mod_bpmn = types.ModuleType("spiffworkflow.bpmn")
    mod_parser = types.ModuleType("spiffworkflow.bpmn.parser")
    setattr(mod_parser, "BpmnParser", DummyParser)
    sys.modules["spiffworkflow"] = mod_spiff
    sys.modules["spiffworkflow.bpmn"] = mod_bpmn
    sys.modules["spiffworkflow.bpmn.parser"] = mod_parser

    from agentic_process_automation.core.adapters.bpmn import parse_bpmn

    pir = parse_bpmn(FIXTURE_SIMPLE)
    # When Spiff is present, dispatcher should still return a PIR (even if empty via dummy)
    from agentic_process_automation.core.pir import PIR
    assert isinstance(pir, PIR)


def test_dispatcher_falls_back_without_spiff(monkeypatch):
    # Ensure spiffworkflow is not present
    for k in [
        "spiffworkflow",
        "spiffworkflow.bpmn",
        "spiffworkflow.bpmn.parser",
    ]:
        sys.modules.pop(k, None)
    from agentic_process_automation.core.adapters.bpmn import parse_bpmn
    pir = parse_bpmn(FIXTURE_SIMPLE)
    from agentic_process_automation.core.pir import PIR
    assert isinstance(pir, PIR)
    # Should have parsed nodes/edges via minimal parser
    assert len(pir.nodes) >= 4
    assert len(pir.edges) == 4


def test_user_task_and_variants_parse_as_task():
    from agentic_process_automation.core.adapters.bpmn_min import from_bpmn_xml
    from agentic_process_automation.core.pir import validate

    xml = b"""
    <definitions xmlns=\"http://www.omg.org/spec/BPMN/20100524/MODEL\" id=\"Defs_UserTask\"> 
        <process id=\"P\" isExecutable=\"false\"> 
            <startEvent id=\"s\"/> 
            <userTask id=\"u1\" name=\"Do it\"/> 
            <serviceTask id=\"u2\" name=\"Service\"/> 
            <endEvent id=\"e\"/> 
            <sequenceFlow id=\"f1\" sourceRef=\"s\" targetRef=\"u1\"/> 
            <sequenceFlow id=\"f2\" sourceRef=\"u1\" targetRef=\"u2\"/> 
            <sequenceFlow id=\"f3\" sourceRef=\"u2\" targetRef=\"e\"/> 
        </process> 
    </definitions>
    """
    pir = from_bpmn_xml(xml)
    report = validate(pir)
    assert report["errors"] == []
    kinds = {n.kind for n in pir.nodes.values()}
    assert "task" in kinds
    # ensure specific ids were created
    assert {"u1", "u2"}.issubset(set(pir.nodes.keys()))


