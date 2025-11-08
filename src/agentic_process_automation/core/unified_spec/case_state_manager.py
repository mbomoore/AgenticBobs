from typing import Any, Dict, List
from agentic_process_automation.core.unified_spec.models import Case


class CaseStateManager:
    """Manages the state of a Case instance."""

    def __init__(self, case: Case):
        """Initializes the CaseStateManager with a Case."""
        self.case = case

    def get_data(self, entity_name: str) -> List[Dict[str, Any]]:
        """
        Retrieves data for a given entity from the Case.

        :param entity_name: The name of the entity to retrieve.
        :return: A list of dictionaries representing the entity data.
        """
        return self.case.data.get(entity_name, [])

    def update_data(self, entity_name: str, new_data: Dict[str, Any]):
        """
        Updates an entity instance in the Case.

        Assumes that the `new_data` dictionary contains an 'id' field
        that can be used to identify the record to update.

        :param entity_name: The name of the entity to update.
        :param new_data: A dictionary containing the new data for the entity.
        :raises ValueError: If the entity name is not in the case schema.
        """
        if entity_name not in self.case.schema_:
            raise ValueError(f"Entity '{entity_name}' not found in case schema.")

        if entity_name not in self.case.data:
            self.case.data[entity_name] = []

        entity_list = self.case.data[entity_name]

        record_id = new_data.get("id")
        if record_id is None:
            # For now, if no ID, we can append. This might need refinement.
            entity_list.append(new_data)
            return

        for i, record in enumerate(entity_list):
            if record.get("id") == record_id:
                entity_list[i].update(new_data)
                return

        # If no record with the given ID is found, add it as a new record.
        entity_list.append(new_data)
