from __future__ import annotations

import html
import json
import traceback

import streamlit as st
import streamlit.components.v1 as components

from core.adapters.bpmn import parse_bpmn
from core.pir import validate
from core.viz import pir_to_mermaid

# Optional: bpmn.io viewer component
try:
        from viz import st_process_viewer  # type: ignore
except Exception:
        st_process_viewer = None  # type: ignore


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


def _bpmn_html(xml: str, theme: str = "light", height: int = 600) -> str:
                                # Safely embed XML into JS using JSON string literal to avoid breaking on quotes/newlines
                                js_xml = json.dumps(xml)
                                bg_color = "#0f1116" if theme == "dark" else "#ffffff"
                                return f"""
<!doctype html>
<html>
        <head>
                <meta charset=\"utf-8\" />
                <style>
                        :root {{ --bg: #ffffff; }}
                        body {{ margin: 0; background: {bg_color}; }}
                        #canvas {{ width: 100%; height: {height}px; }}
                </style>
                <link rel=\"stylesheet\" href=\"https://unpkg.com/bpmn-js@10.5.0/dist/assets/bpmn-js.css\" />
                <script src=\"https://unpkg.com/bpmn-js@10.5.0/dist/bpmn-navigated-viewer.production.min.js\"></script>
        </head>
        <body>
                <div id=\"canvas\"></div>
                <script>
                        const xml = {js_xml};
                        const viewer = new BpmnJS({{ container: '#canvas' }});
                        viewer.importXML(xml).then(_ => {{
                                const canvas = viewer.get('canvas');
                                canvas.zoom('fit-viewport');
                        }}).catch(err => {{
                                document.getElementById('canvas').innerText = 'BPMN load error: ' + err.message;
                        }});
                </script>
        </body>
</html>
"""


st.set_page_config(page_title="BPMN Previewer", layout="wide")
st.title("BPMN XML → Diagram Preview")
st.caption("Paste BPMN 2.0 XML below; we parse to PIR and render a Mermaid diagram.")

if "bpmn_text" not in st.session_state:
        st.session_state.bpmn_text = ""

btns = st.columns([1, 1, 6])
with btns[0]:
        if st.button("Load sample BPMN"):
                st.session_state.bpmn_text = SAMPLE_BPMN
with btns[1]:
        if st.button("Clear"):
                st.session_state.bpmn_text = ""

text = st.text_area("BPMN XML", value=st.session_state.bpmn_text, height=300)
st.session_state.bpmn_text = text

if st.button("Render diagram"):
        if not text.strip():
                st.info("Paste BPMN XML above, or click 'Load sample BPMN'.")
        else:
                with st.spinner("Parsing BPMN…"):
                        try:
                                pir = parse_bpmn(text.encode("utf-8"))
                                report = validate(pir)
                                if report.get("errors"):
                                        st.error("Model has validation errors; fix and try again.")
                                        with st.expander("Validation report"):
                                                st.json(report)
                                else:
                                        mermaid = pir_to_mermaid(pir)
                                        st.subheader("Visualizations")
                                        tab_mermaid, tab_bpmn = st.tabs(["Mermaid", "bpmn.io Viewer"]) 

                                        with tab_mermaid:
                                                st.code(mermaid, language="mermaid")
                                                components.html(_mermaid_html(mermaid), height=600, scrolling=True)

                                        with tab_bpmn:
                                                xml = getattr(pir, "representations", {}).get("bpmn+xml")
                                                if not xml:
                                                        st.info("PIR does not carry original BPMN XML; cannot render with bpmn.io.")
                                                elif st_process_viewer is None:
                                                        st.error("Interactive bpmn.io component is unavailable. Ensure Streamlit is installed and the viz package is present.")
                                                else:
                                                        # Keep controls minimal to reduce reruns; the component keeps state with a stable key
                                                        theme = st.selectbox("Theme", ["light", "dark"], index=0, key="bpmn_theme")
                                                        height = st.slider("Height (px)", 360, 1000, 600, key="bpmn_height")
                                                        try:
                                                                clicked = st_process_viewer(xml=xml, mode="bpmn", height=height, theme=theme, key="bpmn_view")
                                                                st.caption(f"Last clicked BPMN element ID: {clicked}")
                                                        except Exception as e:
                                                                st.error(f"Failed to load interactive viewer: {e}")
                        except Exception as e:
                                st.error(f"Failed to parse or render BPMN: {e}")
                                with st.expander("Traceback"):
                                        st.code(traceback.format_exc())
