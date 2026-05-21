"""Tests for fold/filter expansion in the Interpreter and the combinator algebra."""

from agentic_process_automation.core.unified_spec.combinator_algebra import (
    compose,
    find_fusions,
    is_identity,
)
from agentic_process_automation.core.unified_spec.interpreter import Interpreter
from agentic_process_automation.core.unified_spec.models import (
    Case,
    Combinator,
    View,
    WorkGraph,
    WorkUnit,
)


# ---------- Filter expansion ----------


def _high_value_rfp_graph() -> WorkGraph:
    return WorkGraph(
        name="High-Value Escalation",
        case_schema={"rfps": {"id": "int", "value": "int", "status": "str"}},
        views=[
            View(name="all_rfps", reads=["SELECT * FROM rfps"]),
        ],
        work_units=[
            WorkUnit(
                name="escalate_rfp",
                params={"rfp_id": "RFP.id"},
                inputs=["all_rfps"],
                outputs=[],
                preconditions="True",
                done="SELECT 1 FROM rfps WHERE id = :rfp_id AND status = 'escalated'",
            )
        ],
        combinators=[
            Combinator(
                type="filter",
                work_unit="escalate_rfp",
                over="all_rfps",
                predicate="value > 100000",
            )
        ],
    )


def test_filter_emits_only_matching_items():
    wg = _high_value_rfp_graph()
    case = Case(
        schema_=wg.case_schema,
        data={
            "rfps": [
                {"id": "rfp-1", "value": 50_000, "status": "new"},
                {"id": "rfp-2", "value": 250_000, "status": "new"},
                {"id": "rfp-3", "value": 150_000, "status": "escalated"},
            ]
        },
    )
    items = Interpreter(work_graph=wg, case=case).tick()
    emitted_ids = sorted(wi.parameters["rfp_id"] for wi in items)
    assert emitted_ids == ["rfp-2"]


def test_filter_with_trivial_true_predicate_acts_like_map():
    wg = _high_value_rfp_graph()
    wg.combinators[0].predicate = "True"
    case = Case(
        schema_=wg.case_schema,
        data={
            "rfps": [
                {"id": "rfp-1", "value": 50_000, "status": "new"},
                {"id": "rfp-2", "value": 250_000, "status": "new"},
            ]
        },
    )
    items = Interpreter(work_graph=wg, case=case).tick()
    assert len(items) == 2


# ---------- Fold expansion ----------


def _score_aggregation_graph(into_view_query: str) -> WorkGraph:
    return WorkGraph(
        name="Score Aggregation",
        case_schema={
            "scores": {"id": "int", "value": "float"},
            "totals": {"total": "float"},
        },
        views=[
            View(name="all_scores", reads=["SELECT * FROM scores"]),
            View(name="aggregate_total", reads=[into_view_query]),
        ],
        work_units=[
            WorkUnit(
                name="sum_scores",
                params={},
                inputs=["all_scores"],
                outputs=["aggregate_total"],
                preconditions="True",
                done="SELECT 1 FROM totals",
            )
        ],
        combinators=[
            Combinator(
                type="fold",
                work_unit="sum_scores",
                over="all_scores",
                accumulator="0",
                into="aggregate_total",
            )
        ],
    )


def test_fold_emits_single_work_item_carrying_all_inputs():
    wg = _score_aggregation_graph(into_view_query="SELECT * FROM totals")
    case = Case(
        schema_=wg.case_schema,
        data={
            "scores": [
                {"id": "s1", "value": 0.4},
                {"id": "s2", "value": 0.7},
                {"id": "s3", "value": 0.9},
            ],
            "totals": [],
        },
    )
    items = Interpreter(work_graph=wg, case=case).tick()

    assert len(items) == 1
    assert items[0].work_unit_name == "sum_scores"
    assert items[0].parameters["accumulator"] == "0"
    assert items[0].parameters["into"] == "aggregate_total"
    assert [s["id"] for s in items[0].parameters["items"]] == ["s1", "s2", "s3"]


def test_fold_skipped_when_into_view_already_populated():
    wg = _score_aggregation_graph(into_view_query="SELECT * FROM totals")
    case = Case(
        schema_=wg.case_schema,
        data={
            "scores": [{"id": "s1", "value": 0.4}],
            "totals": [{"total": 0.4}],
        },
    )
    items = Interpreter(work_graph=wg, case=case).tick()
    assert items == []


def test_fold_with_empty_source_emits_nothing():
    wg = _score_aggregation_graph(into_view_query="SELECT * FROM totals")
    case = Case(
        schema_=wg.case_schema,
        data={"scores": [], "totals": []},
    )
    items = Interpreter(work_graph=wg, case=case).tick()
    assert items == []


# ---------- Combinator algebra ----------


def test_compose_map_map_fuses():
    c1 = Combinator(type="map", work_unit="summarize", over="rfps")
    c2 = Combinator(type="map", work_unit="score", over="rfps")
    fused = compose(c1, c2)
    assert fused is not None
    assert fused.type == "map"
    assert fused.over == "rfps"
    assert fused.work_unit == "summarize__then__score"


def test_compose_filter_filter_merges_predicates():
    c1 = Combinator(type="filter", work_unit="wu", over="rfps", predicate="value > 100000")
    c2 = Combinator(type="filter", work_unit="wu", over="rfps", predicate="status = 'new'")
    fused = compose(c1, c2)
    assert fused is not None
    assert fused.type == "filter"
    assert fused.predicate == "(value > 100000) AND (status = 'new')"


def test_compose_refuses_different_sources():
    c1 = Combinator(type="map", work_unit="a", over="rfps")
    c2 = Combinator(type="map", work_unit="b", over="clients")
    assert compose(c1, c2) is None


def test_find_fusions_picks_up_adjacent_maps():
    combinators = [
        Combinator(type="map", work_unit="summarize", over="rfps"),
        Combinator(type="map", work_unit="score", over="rfps"),
        Combinator(type="map", work_unit="route", over="clients"),
    ]
    opportunities = find_fusions(combinators)
    assert len(opportunities) == 1
    assert opportunities[0].kind == "map_map_fuse"


def test_find_fusions_recognises_map_then_fold_pipeline():
    combinators = [
        Combinator(type="map", work_unit="score", over="rfps"),
        Combinator(
            type="fold",
            work_unit="aggregate",
            over="rfps",
            accumulator="0",
            into="totals",
        ),
    ]
    opportunities = find_fusions(combinators)
    assert any(o.kind == "map_then_fold_pipeline" for o in opportunities)


def test_is_identity_detects_trivial_filter():
    assert is_identity(Combinator(type="filter", work_unit="wu", over="rfps", predicate="True"))
    assert not is_identity(
        Combinator(type="filter", work_unit="wu", over="rfps", predicate="value > 0")
    )
    assert not is_identity(Combinator(type="map", work_unit="wu", over="rfps"))
