"""Small utility helpers extracted from the repository."""
from typing import Any, Dict


def serialize_model(meta: Dict[str, Any]) -> Dict[str, Any]:
    """Return a JSON-serializable dict for a model metadata object (placeholder)."""
    return {k: str(v) for k, v in meta.items()}
