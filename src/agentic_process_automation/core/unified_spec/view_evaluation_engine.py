import re
import ast
from typing import Any, Dict, List, Optional, Tuple
from agentic_process_automation.core.unified_spec.models import Case, View

class ViewEvaluationEngine:
    """Evaluates a View definition against a Case to produce a data slice."""

    def __init__(self, case: Case):
        """Initializes the engine with a Case instance."""
        self.case = case

    def evaluate_view(self, view: View, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Evaluates the query in the View against the Case data.
        Handles parameter substitution and simple WHERE clauses.
        """
        query = view.query
        if params:
            for key, value in params.items():
                if isinstance(value, str):
                    query = query.replace(f":{key}", f"'{value}'")
                else:
                    query = query.replace(f":{key}", str(value))

        try:
            select_part, where_part = self._parse_select_where(query)
            entity_name, columns = self._parse_select_part(select_part)

            if entity_name not in self.case.data:
                return []

            source_data = self.case.data[entity_name]
            filtered_data = self._apply_where_clause(source_data, where_part)
            return self._project_columns(filtered_data, columns)

        except Exception as e:
            raise ValueError(f"Query parsing error: {e}")

    def _parse_select_where(self, query: str) -> Tuple[str, Optional[str]]:
        """Splits a query into its SELECT...FROM and WHERE parts."""
        if " WHERE " in query.upper():
            parts = re.split(r'\s+WHERE\s+', query, flags=re.IGNORECASE, maxsplit=1)
            return parts[0], parts[1]
        return query, None

    def _parse_select_part(self, select_part: str) -> Tuple[str, Optional[List[Tuple[str, str]]]]:
        """Parses the 'SELECT columns FROM entity' part of a query, handling aliases."""
        match = re.match(r"SELECT\s+(.+)\s+FROM\s+(\w+)", select_part.strip(), re.IGNORECASE)
        if not match:
            raise ValueError(f"Invalid SELECT...FROM format: '{select_part}'")

        columns_str = match.group(1).strip()
        entity_name = match.group(2).strip()

        if columns_str == "*":
            return entity_name, None

        columns = []
        for col_str in columns_str.split(','):
            col_str = col_str.strip()
            alias_parts = re.split(r'\s+AS\s+', col_str, flags=re.IGNORECASE, maxsplit=1)
            if len(alias_parts) == 2:
                columns.append((alias_parts[0].strip(), alias_parts[1].strip()))
            else:
                columns.append((col_str, col_str))
        return entity_name, columns

    def _apply_where_clause(self, data: List[Dict[str, Any]], where_part: Optional[str]) -> List[Dict[str, Any]]:
        """Filters data based on the WHERE clause."""
        if not where_part:
            return data

        clauses = re.split(r'\s+AND\s+', where_part, flags=re.IGNORECASE)

        filtered_data = list(data)
        for clause in clauses:
            filtered_data = self._apply_single_clause(filtered_data, clause.strip())

        return filtered_data

    def _apply_single_clause(self, data: List[Dict[str, Any]], clause: str) -> List[Dict[str, Any]]:
        """Applies a single filter condition from a WHERE clause."""
        equal_match = re.match(r"(\w+)\s*=\s*'([^']*)'", clause)
        if equal_match:
            key, value = equal_match.groups()
            return [item for item in data if str(item.get(key)) == value]

        in_match = re.match(r"(\w+)\s+IN\s+(\[.*\])", clause, re.IGNORECASE)
        if in_match:
            key, values_str = in_match.groups()
            try:
                values = ast.literal_eval(values_str)
                if not isinstance(values, list):
                    raise ValueError("IN clause requires a list.")
                return [item for item in data if item.get(key) in values]
            except (ValueError, SyntaxError) as e:
                raise ValueError(f"Malformed IN clause values: {values_str}. Error: {e}")

        raise ValueError(f"Unsupported WHERE clause format: {clause}")

    def _project_columns(self, data: List[Dict[str, Any]], columns: Optional[List[Tuple[str, str]]]) -> List[Dict[str, Any]]:
        """Selects specific columns from the data, handling aliases."""
        if not columns:
            return data

        projected_data = []
        for item in data:
            new_item = {}
            for original_name, alias in columns:
                if original_name in item:
                    new_item[alias] = item.get(original_name)
            projected_data.append(new_item)

        return projected_data
