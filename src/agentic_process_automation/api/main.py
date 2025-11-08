from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, List
import uuid

from agentic_process_automation.core.unified_spec.models import WorkGraph, Case
from agentic_process_automation.core.unified_spec.interpreter import Interpreter

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
    case = Case(schema_=workgraph.case_schema, data={})
    cases[case_id] = case
    interpreters[case_id] = Interpreter(workgraph, case)
    human_tasks[case_id] = []

    return {"case_id": case_id}


@app.post("/case/{case_id}/tick")
async def tick_case(case_id: str):
    """Advances the state of a case by one interpreter cycle."""
    interpreter = interpreters.get(case_id)
    if not interpreter:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found.")

    # In a real implementation, we would dispatch and execute work items.
    # For now, we'll just advance the interpreter and log dummy tasks.
    work_items = interpreter.tick()

    # This is a simplified stand-in for the dispatcher and executor logic
    for item in work_items:
        if "human" in item.work_unit_name: # A simple heuristic for now
            human_tasks[case_id].append(item.model_dump())

    return {"message": f"Case '{case_id}' ticked. {len(work_items)} new work items.", "work_items": work_items}


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
