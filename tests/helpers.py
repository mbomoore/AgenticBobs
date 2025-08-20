"""Shared test helpers to reduce duplication across test modules."""
from __future__ import annotations

import re


def valid_bpmn(name: str = "Sample") -> str:
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


def invalid_bpmn_missing_node() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL" id="Defs_Bad">
    <process id="Proc_Bad" isExecutable="false">
        <startEvent id="Start_1" name="Start" />
        <sequenceFlow id="f1" sourceRef="Start_1" targetRef="MISSING_NODE" />
    </process>
</definitions>"""


def with_questions(bpmn: str) -> str:
    return f"{bpmn}\nQ1: First question?\nQ2: Second question?\nQ3: Third question?"


def count_questions(text: str) -> int:
    return len(re.findall(r"^Q[1-3]:", text, flags=re.M))
