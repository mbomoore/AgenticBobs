import sys
from pathlib import Path

import pytest
from core.adapters.bpmn_min import from_bpmn_xml
from core.pir import validate
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


