import pytest
import json
from pathlib import Path

from agentic_process_automation.core.unified_spec.models import (
    Case,
    WorkGraph,
    View,
    WorkUnit,
    ExecutionBinding,
    ExecutionRule,
)
from agentic_process_automation.core.unified_spec.view_evaluation_engine import ViewEvaluationEngine


@pytest.fixture
def rfp_triage_work_graph() -> WorkGraph:
    """Loads the RFP triage example WorkGraph."""
    filepath = Path(__file__).parent.parent.parent.parent / "examples" / "unified_spec" / "rfp_triage.json"
    with open(filepath, "r") as f:
        spec_dict = json.load(f)

    for wu in spec_dict.get("work_units", []):
        wu.setdefault("params", {})
        wu.setdefault("preconditions", "True")
        wu.setdefault("done", wu.get("done_condition", "True"))

    for v_dict in spec_dict.get("views", []):
        v_dict.setdefault("reads", [v_dict.get("query", "")])
        v_dict.setdefault("writes", [])
        v_dict.setdefault("invariants", [])

    bindings = []
    for b in spec_dict.get("execution_bindings", []):
        impl_kind = b.get("executor")
        if impl_kind == "ai_agent":
            impl_kind = "agent"
        bindings.append(ExecutionBinding(
            target=b.get("goal_tag"),
            rules=[
                ExecutionRule(
                    condition=b.get("condition") or "True",
                    impl_kind=impl_kind,
                )
            ]
        ))

    return WorkGraph(
        name=spec_dict.get("name"),
        case_schema=spec_dict.get("case_schema"),
        views=[View(**v) for v in spec_dict.get('views', [])],
        work_units=[WorkUnit(**wu) for wu in spec_dict.get('work_units', [])],
        execution_bindings=bindings,
    )


@pytest.fixture
def initial_case(rfp_triage_work_graph: WorkGraph) -> Case:
    """Creates an initial Case instance for testing."""
    return Case(
        schema_=rfp_triage_work_graph.case_schema,
        data={
            "rfps": [
                {"id": 1, "title": "New RFP 1", "status": "new", "summary": None, "score": None},
                {"id": 2, "title": "Scored RFP 1", "status": "scored", "summary": "A summary", "score": 0.8},
                {"id": 3, "title": "New RFP 2", "status": "new", "summary": None, "score": None},
            ]
        },
    )


def test_evaluate_view_simple_select(initial_case: Case):
    """Tests that a simple 'SELECT *' query returns all items."""
    view = View(name="all_rfps", reads=["SELECT * FROM rfps"])
    engine = ViewEvaluationEngine(initial_case)

    result = engine.evaluate_view(view)

    assert len(result) == 3
    assert result[0]["id"] == 1
    assert result[1]["id"] == 2
    assert result[2]["id"] == 3


def test_evaluate_view_with_where_clause(initial_case: Case):
    """Tests a 'SELECT' query with a 'WHERE' clause."""
    view = View(name="new_rfps", reads=["SELECT * FROM rfps WHERE status = 'new'"])
    engine = ViewEvaluationEngine(initial_case)

    result = engine.evaluate_view(view)

    assert len(result) == 2
    assert result[0]["id"] == 1
    assert result[1]["id"] == 3
    assert all(item["status"] == "new" for item in result)


def test_evaluate_view_no_results(initial_case: Case):
    """Tests a query that should return no results."""
    view = View(name="archived_rfps", reads=["SELECT * FROM rfps WHERE status = 'archived'"])
    engine = ViewEvaluationEngine(initial_case)

    result = engine.evaluate_view(view)

    assert len(result) == 0


def test_evaluate_view_nonexistent_entity_returns_empty(initial_case: Case):
    """Tests that querying a non-existent entity returns an empty list."""
    view = View(name="clients_view", reads=["SELECT * FROM clients"])
    engine = ViewEvaluationEngine(initial_case)
    result = engine.evaluate_view(view)
    assert result == []


def test_evaluate_view_with_in_clause(initial_case: Case):
    """Tests a 'SELECT' query with a 'WHERE ... IN' clause."""
    view = View(name="specific_rfps", reads=["SELECT * FROM rfps WHERE id IN [1, 3]"])
    engine = ViewEvaluationEngine(initial_case)

    result = engine.evaluate_view(view)

    assert len(result) == 2
    assert result[0]["id"] == 1
    assert result[1]["id"] == 3


def test_evaluate_view_malformed_query(initial_case: Case):
    """Tests that a malformed query raises an error."""
    view = View(name="malformed_query", reads=["SELECT FROM rfps"])
    engine = ViewEvaluationEngine(initial_case)

    with pytest.raises(ValueError, match="Query parsing error"):
        engine.evaluate_view(view)
