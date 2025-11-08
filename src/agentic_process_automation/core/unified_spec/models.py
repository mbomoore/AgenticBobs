from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

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

class View(BaseModel):
    """
    A functionally-inspired 'slice' or 'lens' of the world from the Case.
    It defines what context a WorkUnit can read and what parts it is allowed to write.
    """
    name: str = Field(..., description="A unique name for the view.")
    query: str = Field(
        ...,
        description="The query to select a slice of data from the Case. (e.g., 'SELECT * FROM RFPs WHERE status = \"new\"')."
    )

class WorkUnit(BaseModel):
    """
    Describes one logical, executor-agnostic step of knowledge work.
    """
    name: str = Field(..., description="A unique name for the work unit.")
    goal_tag: str = Field(..., description="A semantic label for the work, e.g., 'evaluate_rfp'.")

    inputs: List[str] = Field(
        default_factory=list,
        description="A list of View names that this work unit reads from."
    )
    outputs: List[str] = Field(
        default_factory=list,
        description="A list of View names that this work unit writes to."
    )

    done_condition: str = Field(
        ...,
        description="A predicate over the Case that must be true for this work unit to be considered complete."
    )
    quality_condition: Optional[str] = Field(
        None,
        description="An optional predicate over the Case that defines a quality bar for the work."
    )

class Combinator(BaseModel):
    """
    Uses functional patterns over sets of Work Units.
    """
    type: str = Field(..., description="The type of combinator (e.g., 'map', 'fold', 'filter').")
    work_unit: str = Field(..., description="The name of the WorkUnit to apply.")
    over: str = Field(..., description="The query or View name defining the set of items to operate on.")

class ExecutionBinding(BaseModel):
    """
    Attaches an implementation policy to a Work Unit or goal tag.
    """
    goal_tag: str = Field(..., description="The goal_tag this binding applies to.")
    executor: str = Field(..., description="The name of the executor to use (e.g., 'human', 'ai_agent', 'swarm').")
    condition: Optional[str] = Field(
        None,
        description="An optional condition on the Case for this binding to be active."
    )

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
