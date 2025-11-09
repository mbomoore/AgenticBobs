import pytest
import json
from pathlib import Path
from src.agentic_process_automation.core.unified_spec.models import (
    Case,
    View,
    WorkUnit,
    Combinator,
    ExecutionBinding,
    WorkGraph,
    ExecutionRule,
    Spec,
)

def test_case_instantiation():
    """Tests that a Case can be instantiated with a valid schema."""
    case = Case(schema_={"clients": {"name": "str", "id": "int"}})
    assert case.schema_ == {"clients": {"name": "str", "id": "int"}}
    assert case.data == {}

def test_view_instantiation():
    """Tests that a View can be instantiated."""
    view = View(name="new_rfps", reads=["RFPs.*"], writes=[], invariants=[])
    assert view.name == "new_rfps"
    assert view.reads == ["RFPs.*"]

def test_work_unit_instantiation():
    """Tests that a WorkUnit can be instantiated."""
    work_unit = WorkUnit(
        name="evaluate_rfp",
        params={"rfp_id": "RFP.id"},
        inputs=["new_rfps"],
        outputs=[],
        preconditions="rfp.status == 'new'",
        done="rfp.status == 'evaluated'",
    )
    assert work_unit.name == "evaluate_rfp"
    assert work_unit.done == "rfp.status == 'evaluated'"

def test_combinator_instantiation():
    """Tests that a Combinator can be instantiated."""
    combinator = Combinator(
        type="map",
        work_unit="evaluate_rfp",
        over="SELECT id FROM RFPs WHERE status = 'new'",
    )
    assert combinator.type == "map"
    assert combinator.work_unit == "evaluate_rfp"
    assert combinator.over == "SELECT id FROM RFPs WHERE status = 'new'"

def test_execution_binding_instantiation():
    """Tests that an ExecutionBinding can be instantiated."""
    binding = ExecutionBinding(
        target="evaluate_rfp",
        rules=[
            ExecutionRule(
                condition="True",
                impl_kind="human",
            )
        ]
    )
    assert binding.target == "evaluate_rfp"

def test_work_graph_instantiation():
    """Tests that a WorkGraph can be instantiated with nested models."""
    work_graph = WorkGraph(
        name="rfp_triage",
        case_schema={"rfps": {"id": "int", "status": "str"}},
        views=[
            View(name="new_rfps", reads=["rfps.*"]),
        ],
        work_units=[
            WorkUnit(
                name="evaluate_rfp",
                params={"rfp_id": "RFP.id"},
                inputs=["new_rfps"],
                outputs=[],
                preconditions="rfp.status == 'new'",
                done="rfp.status == 'evaluated'",
            ),
        ],
        execution_bindings=[
            ExecutionBinding(
                target="evaluate_rfp",
                rules=[
                    ExecutionRule(
                        condition="True",
                        impl_kind="human",
                    )
                ]
            ),
        ],
    )
    assert work_graph.name == "rfp_triage"
    assert len(work_graph.views) == 1
    assert len(work_graph.work_units) == 1
    assert len(work_graph.execution_bindings) == 1

def test_work_graph_serialization_json():
    """Tests that a WorkGraph can be serialized to and from JSON."""
    work_graph = WorkGraph(
        name="rfp_triage",
        case_schema={"rfps": {"id": "int", "status": "str"}},
        views=[
            View(name="new_rfps", reads=["rfps.*"]),
        ],
    )
    json_data = work_graph.model_dump_json()
    reloaded_graph = WorkGraph.model_validate_json(json_data)
    assert reloaded_graph == work_graph

def test_work_graph_json_schema():
    """Tests that a JSON schema can be generated for the WorkGraph."""
    schema = WorkGraph.model_json_schema()
    assert schema["title"] == "WorkGraph"
    assert "case_schema" in schema["properties"]
    assert "views" in schema["properties"]
    assert "work_units" in schema["properties"]

def test_load_rfp_triage_example():
    """Tests that the rfp_triage.json example can be loaded."""
    example_path = Path(__file__).parent.parent.parent.parent / "examples" / "unified_spec" / "rfp_triage.json"
    assert example_path.exists(), "The example file rfp_triage.json does not exist."

    with open(example_path, "r") as f:
        spec_dict = json.load(f)

    # Adapt the example data to the new Spec model
    for wu in spec_dict.get("work_units", []):
        wu.setdefault("params", {})
        wu.setdefault("preconditions", "True")
        wu.setdefault("done", wu.get("done_condition", "True"))
        for output in wu.get("outputs", []):
            if output not in [v.get("name") for v in spec_dict.get("views", [])]:
                spec_dict.get("views", []).append({"name": output, "reads": [], "writes": []})


    for v in spec_dict.get("views", []):
        v.setdefault("reads", [v.get("query", "")])
        v.setdefault("writes", [])
        v.setdefault("invariants", [])

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

    spec = Spec(
        views={v['name']: View(**v) for v in spec_dict.get('views', [])},
        work_units={wu['name']: WorkUnit(**wu) for wu in spec_dict.get('work_units', [])},
        bindings=bindings,
        invariants=spec_dict.get('invariants', [])
    )

    assert isinstance(spec, Spec)
    assert len(spec.views) == 4
    assert len(spec.work_units) == 2
    assert len(spec.bindings) == 3
