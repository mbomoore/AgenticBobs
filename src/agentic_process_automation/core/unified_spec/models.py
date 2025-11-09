from __future__ import annotations
from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field, field_validator

# ---- Core primitives ----

class View(BaseModel):
    name: str
    reads: List[str] = Field(default_factory=list)  # e.g., ["RFP.*", "Doc.{rfp_id,kind,body}"]
    writes: List[str] = Field(default_factory=list)  # empty => read-only
    invariants: List[str] = Field(default_factory=list)  # simple predicates over schema

class WorkUnit(BaseModel):
    name: str
    goal_tag: Optional[str] = None
    params: Dict[str, str]  # param -> type or foreign key, e.g., {"rfp_id": "RFP.id"}
    inputs: List[str]       # view names it reads
    outputs: List[str]      # view names it writes
    preconditions: str      # boolean expr over Case
    done: str               # boolean expr over Case
    quality: Optional[str] = None
    write_set: List[str] = Field(default_factory=list)  # exact fields this WU mutates
    side_effects: Literal["none","external_io","mutation"] = "none"
    idempotent: bool = True
    conflict_policy: Literal["merge","last_write_wins","fail"] = "merge"
    termination_measure: Optional[str] = None

class ExecutionRule(BaseModel):
    condition: str      # e.g., "RFP[rfp_id].value < 50000"
    impl_kind: Literal["human","agent","hybrid"]
    token_limit: Optional[int] = None
    tool_schemas: List[str] = Field(default_factory=list)
    privacy_level: Literal["public","internal","restricted"] = "internal"
    approval_policy: Literal["auto","human_approve"] = "auto"

class ExecutionBinding(BaseModel):
    target: str               # work unit name or goal tag
    rules: List[ExecutionRule]

class Spec(BaseModel):
    views: Dict[str, View]
    work_units: Dict[str, WorkUnit]
    bindings: List[ExecutionBinding] = Field(default_factory=list)
    invariants: List[str] = Field(default_factory=list)  # global invariants

    @field_validator("work_units")
    def _rw_views_exist(cls, wus, values):
        if 'views' not in values.data:
            return wus
        views = values.data["views"]
        for wu in wus.values():
            for v in wu.inputs + wu.outputs:
                if v not in views:
                    raise ValueError(f"WorkUnit {wu.name} references missing View '{v}'")
        return wus

class Case(BaseModel):
    """
    The shared container for all state relevant to a unit of work.
    It is explicitly relational, containing entities, attributes, and relations.
    """
    schema_: Dict[str, Any] = Field(
        ...,
        description="Defines the relational schema of the case (e.g., {'clients': {'name': str, 'id': int}})."
    )
    data: Dict[str, List[Dict[str, Any]]] = Field(
        default_factory=dict,
        description="The actual instance data for the case, organized by entity type."
    )

class Combinator(BaseModel):
    """
    Uses functional patterns over sets of Work Units.
    """
    type: str = Field(..., description="The type of combinator (e.g., 'map', 'fold', 'filter').")
    work_unit: str = Field(..., description="The name of the WorkUnit to apply.")
    over: str = Field(..., description="The query or View name defining the set of items to operate on.")

class WorkGraph(BaseModel):
    """
    The complete, self-contained specification for a unit of knowledge work.
    """
    name: str = Field(..., description="The name of the work graph.")
    case_schema: Dict[str, Any] = Field(..., description="The schema for the Case.")
    views: List[View] = Field(default_factory=list)
    work_units: List[WorkUnit] = Field(default_factory=list)
    combinators: List[Combinator] = Field(default_factory=list)
    execution_bindings: List[ExecutionBinding] = Field(default_factory=list)


class WorkItem(BaseModel):
    """
    Represents a specific, parameterized instance of a WorkUnit that is ready for execution.
    """
    work_unit_name: str = Field(..., description="The name of the WorkUnit template.")
    parameters: Dict[str, Any] = Field(..., description="The specific parameters for this instance of the work.")
