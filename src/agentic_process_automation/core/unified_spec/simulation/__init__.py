"""Simulation kernel for WorkGraph — ported from `core/sim/` onto unified-spec types."""

from agentic_process_automation.core.unified_spec.simulation.binding_aware import (
    ExecutorCost,
    cost_for_work_unit,
)
from agentic_process_automation.core.unified_spec.simulation.markov import (
    state_visits,
    transition_matrix,
)
from agentic_process_automation.core.unified_spec.simulation.process_model import (
    WGState,
    WGTransition,
    WorkGraphProcessModel,
)
from agentic_process_automation.core.unified_spec.simulation.steady_state import (
    SteadyStateReport,
    detect_warmup_index,
    is_stationary,
    moving_avg,
    sliding_slope,
)

__all__ = [
    "ExecutorCost",
    "cost_for_work_unit",
    "state_visits",
    "transition_matrix",
    "WGState",
    "WGTransition",
    "WorkGraphProcessModel",
    "SteadyStateReport",
    "detect_warmup_index",
    "is_stationary",
    "moving_avg",
    "sliding_slope",
]
