from pydantic import BaseModel
from agentic_process_automation.core.unified_spec.models import WorkGraph
import json

def get_workgraph_schema() -> str:
    """
    Generates a JSON schema for the WorkGraph model.
    """
    schema = WorkGraph.model_json_schema()
    return json.dumps(schema, indent=2)

if __name__ == "__main__":
    schema_json = get_workgraph_schema()
    with open("workgraph.schema.json", "w") as f:
        f.write(schema_json)
    print("WorkGraph JSON schema generated and saved to workgraph.schema.json")
