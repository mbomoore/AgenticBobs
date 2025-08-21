from typing import List, Union
import io
import importlib

from lxml.etree import XMLSyntaxError

from SpiffWorkflow.dmn.parser import BpmnDmnParser

# Resolve ValidationException similarly to the BPMN validator; fall back to Exception
ValidationException = Exception
try:
    ve_mod = importlib.import_module('SpiffWorkflow.dmn.parser.ValidationException')
    ValidationException = getattr(ve_mod, 'ValidationException', ValidationException)
except Exception:
    try:
        parser_mod = importlib.import_module('SpiffWorkflow.dmn.parser')
        ValidationException = getattr(parser_mod, 'ValidationException', ValidationException)
    except Exception:
        ValidationException = Exception


def validate_dmn_string(dmn_xml: str) -> Union[str, List[str]]:
    """Validate a DMN XML string.

    Returns 'PASS' or a list of error messages.
    """
    errors: List[str] = []

    parser = BpmnDmnParser()

    try:
        bytes_io = io.BytesIO(dmn_xml.encode('utf-8'))
        parser.add_dmn_io(bytes_io)
    except XMLSyntaxError as e:
        errors.append(f"XMLSyntaxError: {e}")
        return errors
    except Exception as e:
        errors.append(f"Error adding DMN: {type(e).__name__}: {e}")
        return errors

    # Try to validate DMN artifacts. Use parser.get_dmn_dependencies or similar
    try:
        # If parser exposes a way to list DMN ids, prefer that; otherwise try find_all_specs
        ids = []
        if hasattr(parser, 'get_dmn_ids'):
            ids = parser.get_dmn_ids()
        elif hasattr(parser, 'find_all_specs'):
            ids = list(parser.find_all_specs().keys())

        for did in ids:
            try:
                # Attempt to get spec or engine to trigger validation
                if hasattr(parser, 'get_spec'):
                    parser.get_spec(did)
                elif hasattr(parser, 'get_engine'):
                    parser.get_engine(did)
            except ValidationException as exc:
                errors.append(f"ValidationException for {did}: {exc}")
            except Exception as exc:
                errors.append(f"Exception for {did}: {type(exc).__name__}: {exc}")
    except Exception as e:
        errors.append(f"Error during DMN validation discovery: {type(e).__name__}: {e}")

    if errors:
        return errors

    return 'PASS'
