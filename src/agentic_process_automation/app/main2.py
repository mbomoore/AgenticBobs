from __future__ import annotations

import html
import json
import re
import traceback

import streamlit as st
import streamlit.components.v1 as components

from ..core.adapters.bpmn import parse_bpmn
from ..core.pir import validate
from ..core.viz import pir_to_mermaid
from ..cli.generate_xml import generate_process_xml, ProcessGenerationConfig

SAMPLE_BPMN = """<?xml version="1.0" encoding="UTF-8"?>
<definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL" id="Defs_Sample">
        <process id="Proc_Sample" isExecutable="false">
                <startEvent id="Start_1" name="Start" />
                <task id="Task_A" name="Do A" />
                <exclusiveGateway id="Gw_1" name="Route" />
                <task id="Task_B" name="Do B" />
                <endEvent id="End_1" name="End" />

                <sequenceFlow id="f1" sourceRef="Start_1" targetRef="Task_A" />
                <sequenceFlow id="f2" sourceRef="Task_A" targetRef="Gw_1" />
                <sequenceFlow id="f3" sourceRef="Gw_1" targetRef="Task_B" />
                <sequenceFlow id="f4" sourceRef="Task_B" targetRef="End_1" />
        </process>
        <bpmndi:BPMNDiagram xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"/>
        <di:Diagram xmlns:di="http://www.omg.org/spec/DD/20100524/DI"/>
        <dc:Bounds xmlns:dc="http://www.omg.org/spec/DD/20100524/DC"/>
</definitions>
"""


def _mermaid_html(mermaid_code: str) -> str:
        safe = html.escape(mermaid_code)
        return f"""
<!doctype html>
<html>
    <head>
        <meta charset=\"utf-8\" />
        <style> body {{ margin: 0; }} </style>
        <script type=\"module\">
            import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
            mermaid.initialize({{ startOnLoad: true, theme: 'default' }});
            window.mermaid = mermaid;
        </script>
    </head>
    <body>
        <div class=\"mermaid\">{safe}</div>
    </body>
</html>
"""


st.set_page_config(page_title="The Bobs 2.0", layout="wide")
st.title("The Bobs 2.0")
st.caption("(Make a real AI agent that can work for you!)")

if "bpmn_text" not in st.session_state:
        st.session_state.bpmn_text = ""

# Layout: chat on the left (wide), visualization on the right (narrow)
col_left, col_right = st.columns([1, 2])

with col_left:

        if "chat_messages" not in st.session_state:
                # Seed with an opening assistant message
                st.session_state.chat_messages = [
                        {"role": "assistant", "content": "What would you say... you do here?"}
                ]

        # Show chat history
        for m in st.session_state.chat_messages:
                with st.chat_message(m["role"]):
                        st.markdown(m["content"])  # safe; may include XML fenced code

        user_msg = st.chat_input("Well, Bobs...")
        if user_msg:
                st.session_state.chat_messages.append({"role": "user", "content": user_msg})
                with st.chat_message("user"):
                        st.markdown(user_msg)

                with st.chat_message("assistant"):
                        with st.spinner("Thinking with Ollama…"):
                                try:
                                        config = ProcessGenerationConfig(
                                                description=user_msg,
                                                process_type="BPMN",
                                                model_name="gpt-oss:20b"
                                        )
                                        maybe_xml = generate_process_xml(config)
                                        
                                        if maybe_xml and maybe_xml.strip():
                                                st.session_state.bpmn_text = maybe_xml
                                                st.success("BPMN updated.")
                                                # Generate follow-up questions
                                                qs = [
                                                        "Q1: What are the exact start and end conditions for this process?",
                                                        "Q2: Who performs each task, and are there approvals, SLAs, or handoffs?",
                                                        "Q3: What branching rules/exceptions should we include at decision points?",
                                                ]
                                                st.markdown("\n".join(qs))
                                                st.session_state.chat_messages.append({"role": "assistant", "content": "\n".join(qs)})
                                        else:
                                                st.error("Failed to generate BPMN XML")
                                                qs = [
                                                        "Q1: What is the precise goal and success criteria for this process?",
                                                        "Q2: Which roles/systems own each step and what inputs/outputs are required?",
                                                        "Q3: Are there exceptions, loops, or SLAs that must be modeled?",
                                                ]
                                                st.markdown("\n".join(qs))
                                                st.session_state.chat_messages.append({"role": "assistant", "content": "\n".join(qs)})
                                except Exception as e:
                                        st.error(f"Process generation failed: {e}")
                                        st.session_state.chat_messages.append({"role": "assistant", "content": f"Error: {e}"})
                               

with col_right:
        # Auto-parse and render Mermaid from current BPMN first
        current_text = st.session_state.bpmn_text
        mermaid = None
        if not current_text.strip():
                st.info("talk to bob")
        else:
                with st.spinner("Rendering diagram…"):
                        try:
                                pir = parse_bpmn(current_text.encode("utf-8"))
                                report = validate(pir)
                                if report.get("errors"):
                                        st.error("Model has validation errors; fix and try again.")
                                        with st.expander("Validation report"):
                                                st.json(report)
                                else:
                                        mermaid = pir_to_mermaid(pir)
                                        st.subheader("Your process")
                                        components.html(_mermaid_html(mermaid), height=600, scrolling=True)
                        except Exception as e:
                                st.error(f"Failed to parse or render BPMN: {e}")
                                with st.expander("Traceback"):
                                        st.code(traceback.format_exc())

        # Controls and XML editor (below the diagram)
        ctrl = st.columns([3, 3])
        with ctrl[0]:
                if st.button("Load sample BPMN", use_container_width=True):
                        st.session_state.bpmn_text = SAMPLE_BPMN
        with ctrl[1]:
                if st.button("Clear", use_container_width=True):
                        st.session_state.bpmn_text = ""

        exp = st.expander("BPMN XML (hidden by default)", expanded=False)
        with exp:
                text = st.text_area("BPMN XML", value=st.session_state.bpmn_text, height=300)
                st.session_state.bpmn_text = text
                if mermaid:
                        st.markdown("Mermaid (read-only):")
                        st.code(mermaid, language="mermaid")
