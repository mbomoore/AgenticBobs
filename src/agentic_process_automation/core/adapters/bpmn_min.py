"""Minimal BPMN 2.0 XML to PIR parser.

Supports a subset sufficient for tests:
- startEvent, endEvent, task, exclusiveGateway as nodes
- sequenceFlow as edges
- Ignores lanes/pools, forms guards from conditionExpression if present
"""
from __future__ import annotations

from xml.etree import ElementTree as ET
from typing import Dict

from ..pir import PIRBuilder


BPMN_NS = {
    "bpmn": "http://www.omg.org/spec/BPMN/20100524/MODEL",
}


def _tag(local: str) -> str:
    return f"{{{BPMN_NS['bpmn']}}}{local}"


def from_bpmn_xml(xml_bytes: bytes):
    # Be tolerant of leading whitespace/newlines before the XML declaration
    root = ET.fromstring(xml_bytes.lstrip())

    # Attempt to find <process> elements in BPMN namespace
    processes = list(root.findall(".//bpmn:process", namespaces=BPMN_NS))
    b = PIRBuilder()
    # Attach original BPMN XML representation (as text)
    try:
        b.attach_representation("bpmn+xml", xml_bytes.decode("utf-8"))
    except Exception:
        # Fallback: best-effort decode ignoring errors
        b.attach_representation("bpmn+xml", xml_bytes.decode("utf-8", errors="ignore"))

    # Map supported elements to PIR nodes
    node_elems = [
        ("startEvent", _tag("startEvent")),
        ("endEvent", _tag("endEvent")),
        # Treat common BPMN task subtypes as generic 'task' for our PIR
        ("task", _tag("task")),
        ("task", _tag("userTask")),
        ("task", _tag("serviceTask")),
        ("task", _tag("manualTask")),
        ("task", _tag("scriptTask")),
        ("task", _tag("businessRuleTask")),
        ("task", _tag("sendTask")),
        ("task", _tag("receiveTask")),
        ("exclusiveGateway", _tag("exclusiveGateway")),
        # Support intermediate events used in simple flows
        ("intermediateThrowEvent", _tag("intermediateThrowEvent")),
        ("intermediateCatchEvent", _tag("intermediateCatchEvent")),
    ]

    # Build node index for quick lookup
    for proc in processes:
        for kind, qname in node_elems:
            for el in proc.findall(f".//{qname}"):
                el_id = el.get("id")
                name = el.get("name", el_id)
                if el_id:
                    b.add_node(id=el_id, kind=kind, name=name)

        # sequence flows as edges
        for sf in proc.findall(f".//{_tag('sequenceFlow')}"):
            src = sf.get("sourceRef")
            dst = sf.get("targetRef")
            guard = None
            # Optional conditionExpression
            for cond in sf.findall(f".//{_tag('conditionExpression')}"):
                text = (cond.text or "").strip()
                if text:
                    guard = text
                    break
            if src and dst:
                b.add_edge(src=src, dst=dst, guard=guard)

    return b.build()
