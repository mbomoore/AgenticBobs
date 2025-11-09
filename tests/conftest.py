import pytest
import json
from pathlib import Path
from agentic_process_automation.core.unified_spec.models import (
    WorkGraph,
    WorkUnit,
    ExecutionBinding,
    ExecutionRule,
    View,
    Combinator,
)

@pytest.fixture
def conditional_work_graph() -> WorkGraph:
    """Creates a WorkGraph with conditional execution bindings."""
    return WorkGraph(
        name="Conditional Test",
        case_schema={
            "type": "object",
            "properties": {
                "ticket": {
                    "type": "object",
                    "properties": {"priority": {"type": "string"}, "status": {"type": "string"}}
                }
            }
        },
        work_units=[
            WorkUnit(
                name="Handle Ticket",
                params={},
                inputs=[],
                outputs=[],
                preconditions="True",
                done="SELECT 1 FROM ticket WHERE status = 'done'"
            )
        ],
        execution_bindings=[
            ExecutionBinding(
                target="Handle Ticket",
                rules=[
                    ExecutionRule(
                        condition="SELECT 1 FROM ticket WHERE priority = 'high'",
                        impl_kind="human",
                    )
                ]
            ),
            ExecutionBinding(
                target="Handle Ticket",
                rules=[
                    ExecutionRule(
                        condition="SELECT 1 FROM ticket WHERE priority = 'low'",
                        impl_kind="agent",
                    )
                ]
            ),
            ExecutionBinding(
                target="Handle Ticket",
                rules=[
                    ExecutionRule(
                        condition="True",
                        impl_kind="agent", # Default fallback
                    )
                ]
            )
        ]
    )

@pytest.fixture
def rfp_triage_work_graph() -> WorkGraph:
    """Loads and adapts the RFP triage example WorkGraph."""
    filepath = Path(__file__).parent.parent / "examples" / "unified_spec" / "rfp_triage.json"
    with open(filepath, "r") as f:
        spec_dict = json.load(f)

    for wu in spec_dict.get("work_units", []):
        wu.setdefault("goal_tag", wu.get("name"))
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

    spec_dict["combinators"][0]["over"] = "new_rfps"
    spec_dict["combinators"][1]["over"] = "scored_rfps"
    return WorkGraph(
        name=spec_dict.get("name"),
        case_schema=spec_dict.get("case_schema"),
        views=[View(**v) for v in spec_dict.get('views', [])],
        work_units=[WorkUnit(**wu) for wu in spec_dict.get('work_units', [])],
        combinators=[Combinator(**c) for c in spec_dict.get('combinators', [])],
        execution_bindings=bindings,
    )
