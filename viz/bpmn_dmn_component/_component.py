from __future__ import annotations

import os
from typing import Optional

import streamlit as st
import streamlit.components.v1 as components

# If you prefer live dev with a local server, replace "path" with "url".
_component_func = components.declare_component(
    "bpmn_dmn_viewer",
    path=os.path.join(os.path.dirname(__file__), "frontend"),
)


def process_viewer(
    xml: str,
    mode: str = "bpmn",  # "bpmn" or "dmn"
    height: int = 520,
    width: str = "100%",
    key: Optional[str] = None,
    theme: str = "light",  # "light" or "dark" (simple CSS tweak)
    fit_on_load: bool = True,
) -> Optional[str]:
    """
    Render a BPMN/DMN diagram in Streamlit.

    Parameters
    ----------
    xml : str
        BPMN or DMN XML string.
    mode : {"bpmn","dmn"}
        Which viewer to use.
    height : int
        Pixel height of the viewer iframe.
    width : str
        CSS width (e.g. "100%", "900px").
    key : str | None
        Streamlit component key.
    theme : {"light","dark"}
        Basic theme for background.
    fit_on_load : bool
        Whether to auto-fit the diagram to the viewport on load.

    Returns
    -------
    clicked_id : str | None
        The element ID of the last clicked node/edge (if any).
    """
    if mode not in ("bpmn", "dmn"):
        raise ValueError("mode must be 'bpmn' or 'dmn'")

    # Note: width is applied via CSS inside the component
    clicked_id = _component_func(
        xml=xml,
        mode=mode,
        height=height,
        width=width,
        theme=theme,
        fit_on_load=fit_on_load,
        default=None,
        key=key,
    )
    return clicked_id
