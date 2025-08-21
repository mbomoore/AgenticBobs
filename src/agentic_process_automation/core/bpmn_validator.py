from typing import List, Union
import io

from SpiffWorkflow.bpmn.parser import BpmnParser, BpmnValidator
import importlib
from lxml.etree import XMLSyntaxError

# ValidationException in the SpiffWorkflow package may be exported as a module
# or as a class; resolve the actual exception class at runtime so we can catch it.
# Try to resolve the ValidationException class; if resolution fails, fall back to Exception
ValidationException = Exception
try:
    ve_mod = importlib.import_module('SpiffWorkflow.bpmn.parser.ValidationException')
    ValidationException = getattr(ve_mod, 'ValidationException', ValidationException)
except Exception:
    # Some installs export ValidationException directly from the parser package
    try:
        parser_mod = importlib.import_module('SpiffWorkflow.bpmn.parser')
        ValidationException = getattr(parser_mod, 'ValidationException', ValidationException)
    except Exception:
        ValidationException = Exception


def validate_bpmn_string(bpmn_xml: str) -> Union[str, List[str]]:
    """Validate a BPMN XML string.

    Returns:
      - "PASS" if the BPMN parses and validates without errors.
      - a list of error/warning messages otherwise.

    The function uses a BytesIO for the XML input to preserve any XML
    encoding declaration (<?xml ... encoding="UTF-8"?>) which lxml
    requires when parsing bytes.
    """
    errors: List[str] = []

    parser = BpmnParser(validator=BpmnValidator())

    # Add the BPMN content via a BytesIO so XML declarations are handled.
    try:
        bytes_io = io.BytesIO(bpmn_xml.encode("utf-8"))
        parser.add_bpmn_io(bytes_io)
    except XMLSyntaxError as e:
        errors.append(f"XMLSyntaxError: {e}")
        return errors
    except Exception as e:
        errors.append(f"Error adding BPMN: {type(e).__name__}: {e}")
        return errors

    # For each discovered process, request its spec which triggers validation.
    for pid in parser.get_process_ids():
        try:
            parser.get_spec(pid)
        except ValidationException as exc:
            errors.append(f"ValidationException for {pid}: {exc}")
        except Exception as exc:
            errors.append(f"Exception for {pid}: {type(exc).__name__}: {exc}")

    if errors:
        return errors

    return "PASS"
