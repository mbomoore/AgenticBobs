"""BPMN dispatcher that prefers SpiffWorkflow when available, else minimal parser."""
from __future__ import annotations

from typing import Any

from ..pir import PIR, PIRBuilder
from result import Ok, Err, Result, is_ok, is_err
from SpiffWorkflow.bpmn.parser import BpmnParser  # type: ignore


def _spiff_available() -> bool:
    try:
        import SpiffWorkflow  # noqa: F401
        return True
    except Exception:
        return False


def parse_bpmn(xml_bytes: bytes) -> PIR:
    if _spiff_available():
        try:
            from spiffworkflow.bpmn.parser import BpmnParser  # type: ignore
            parser = BpmnParser()
            _ = parser.parse_xml_string(xml_bytes.decode("utf-8"))
            # For now, we don't map Spiff spec; return empty PIR to satisfy type contract
            # Future work: transform spiff spec to PIR
            return PIRBuilder().build()
        except Exception:
            # Fall back to minimal parser on any issue
            pass
    # Minimal parser fallback
    from .bpmn_min import from_bpmn_xml
    return from_bpmn_xml(xml_bytes)


def is_good_bpmn(xml_bytes: bytes) -> Result[bool, str]:
    """
    Return either a True or an error message.
    """
    
    parser = BpmnParser()
    try:
        _ = parser.parse_xml_string(xml_bytes.decode("utf-8"))
        return Ok(True)
    except Exception as e:
        return Err(str(e))