from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Any
import uuid

from agentic_process_automation.core.unified_spec.models import WorkGraph, Case
from agentic_process_automation.core.unified_spec.interpreter import Interpreter
from agentic_process_automation.core.unified_spec.dispatcher import Dispatcher
from agentic_process_automation.core.unified_spec.executors import get_executor

app = FastAPI()

# In-memory storage for simplicity
workgraphs: Dict[str, WorkGraph] = {}
cases: Dict[str, Case] = {}
interpreters: Dict[str, Interpreter] = {}
human_tasks: Dict[str, List[Dict]] = {}


class WorkGraphInput(BaseModel):
    name: str
    content: Dict


@app.post("/workgraph")
async def load_workgraph(workgraph_input: WorkGraphInput):
    """Loads and validates a new WorkGraph specification."""
    try:
        workgraph = WorkGraph(**workgraph_input.content)
        workgraphs[workgraph_input.name] = workgraph
        return {"message": f"WorkGraph '{workgraph_input.name}' loaded successfully."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/case")
async def create_case(workgraph_name: str):
    """Creates a new Case instance from a WorkGraph."""
    workgraph = workgraphs.get(workgraph_name)
    if not workgraph:
        raise HTTPException(status_code=404, detail=f"WorkGraph '{workgraph_name}' not found.")

    case_id = str(uuid.uuid4())
    # Initialize with empty data structure based on schema
    initial_data = {entity: [] for entity in workgraph.case_schema.get("properties", {}).keys()}
    case = Case(schema_=workgraph.case_schema, data=initial_data)
    cases[case_id] = case
    interpreters[case_id] = Interpreter(workgraph, case)
    human_tasks[case_id] = []

    return {"case_id": case_id}


@app.post("/case/{case_id}/data")
async def set_case_data(case_id: str, data: Dict[str, List[Dict[str, Any]]]):
    """Sets the data for a specific case."""
    case = cases.get(case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found.")

    case.data = data
    return {"message": f"Data for case '{case_id}' updated successfully."}


@app.post("/case/{case_id}/tick")
async def tick_case(case_id: str):
    """Advances the state of a case by one interpreter cycle."""
    interpreter = interpreters.get(case_id)
    if not interpreter:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found.")

    work_items = interpreter.tick()

    if not work_items:
        return {"message": f"Case '{case_id}' ticked. No new work items."}

    dispatcher = Dispatcher(interpreter.work_graph)

    for item in work_items:
        try:
            executor_name = dispatcher.resolve_executor(item, interpreter.case)

            # Inject dependencies for executors
            executor_kwargs = {}
            if executor_name == "human":
                executor_kwargs["task_list"] = human_tasks[case_id]

            executor = get_executor(executor_name, **executor_kwargs)
            executor.execute(item)

        except Exception as e:
            # In a real system, you'd have more robust error handling
            # and possibly a dead-letter queue for failed work items.
            print(f"Error executing work item {item.work_unit_name}: {e}")


    return {"message": f"Case '{case_id}' ticked. {len(work_items)} new work items processed.", "work_items": [i.model_dump() for i in work_items]}


@app.get("/case/{case_id}")
async def get_case(case_id: str):
    """Gets the current state of a case."""
    case = cases.get(case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found.")
    return case.model_dump()


@app.get("/case/{case_id}/tasks")
async def get_human_tasks(case_id: str):
    """Gets the list of pending human tasks."""
    if case_id not in cases:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found.")
    return human_tasks.get(case_id, [])
