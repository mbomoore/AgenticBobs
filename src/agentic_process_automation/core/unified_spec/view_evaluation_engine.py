from typing import Any, Dict, List
import re
from agentic_process_automation.core.unified_spec.models import Case, View


class ViewEvaluationEngine:
    """Evaluates a View definition against a Case to produce a data slice."""

    def __init__(self, case: Case):
        """Initializes the engine with a Case instance."""
        self.case = case

    def evaluate_view(self, view: View) -> List[Dict[str, Any]]:
        """
        Evaluates the query in the View against the Case data.

        :param view: The View to evaluate.
        :return: A list of dictionaries representing the result.
        :raises ValueError: If the query is malformed or the entity does not exist.
        """
        try:
            # Basic regex to parse "SELECT * FROM entity WHERE key = 'value'"
            match = re.match(r"SELECT\s+\*\s+FROM\s+(\w+)(?:\s+WHERE\s+(\w+)\s*=\s*'([^']*)')?", view.query)
            if not match:
                raise ValueError("Query parsing error: Only 'SELECT * FROM entity [WHERE key = 'value']' is supported.")

            entity_name = match.group(1)

            if entity_name not in self.case.data:
                raise ValueError(f"Entity '{entity_name}' not found in case data.")

            source_data = self.case.data[entity_name]

            # Handle WHERE clause if present
            if match.group(2) and match.group(3):
                key_to_filter = match.group(2)
                value_to_filter = match.group(3)

                return [
                    item for item in source_data
                    if item.get(key_to_filter) == value_to_filter
                ]
            else:
                return list(source_data)

        except Exception as e:
            # Re-raise internal errors as a consistent error type for the caller
            raise ValueError(f"Query parsing error: {e}")
