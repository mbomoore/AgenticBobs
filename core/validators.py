from typing import List, Union

from .bpmn_validator import validate_bpmn_string
from .dmn_validator import validate_dmn_string


def validate_model_string(model_xml: str, model_type: str) -> Union[str, List[str]]:
    """Validate a model string of the given type.

    Args:
        model_xml: the XML text of the model (BPMN or DMN)
        model_type: 'bpmn' or 'dmn' (case-insensitive)

    Returns:
        'PASS' or a list of error strings.
    """
    mt = model_type.lower()
    if mt == 'bpmn':
        return validate_bpmn_string(model_xml)
    if mt == 'dmn':
        return validate_dmn_string(model_xml)
    raise ValueError(f"Unknown model_type: {model_type}. Use 'bpmn' or 'dmn'.")


# Convenience aliases
def validate_bpmn(model_xml: str) -> Union[str, List[str]]:
    return validate_bpmn_string(model_xml)


def validate_dmn(model_xml: str) -> Union[str, List[str]]:
    return validate_dmn_string(model_xml)
