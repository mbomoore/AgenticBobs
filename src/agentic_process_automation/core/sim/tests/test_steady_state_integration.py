import math

from agentic_process_automation.core.sim import ProcessModel, State, Resource, simulate
from agentic_process_automation.core.sim.simpy_adapter import SimulationParameters, SimulationSettings
from agentic_process_automation.core.sim.steady_state import steady_state_report_from_result


def build_plateau_model():
    # Simple two-state model: A then absorb in B
    p = ProcessModel("plateau")
    with p:
        # Attach a resource so occupancy time series exist
        a = State("A", time=0.01, resource=Resource(role="RoleA", capacity=5))
        b = State("B", time=0.0)
        p.add_transition(a >> 1.0 >> b)
    return p


def test_steady_state_report_integration_runs():
    model = build_plateau_model()
    # Spawn for a short time horizon; arrival rate to create multiple entities
    params = SimulationParameters(runs=30, arrival_rate_per_min=30.0, end_time_min=10.0)
    settings = SimulationSettings(simulations=1, seed=123)
    result = simulate(model, parameters=params, settings=settings)

    rep = steady_state_report_from_result(result, window=10, slope_rel_eps=0.05)
    assert isinstance(rep.warmup_index, int)
    assert rep.warmup_index >= 0
    assert isinstance(rep.times_hr, list) and len(rep.times_hr) > 0
    assert isinstance(rep.per_role, dict) and "RoleA" in rep.per_role
    role = rep.per_role["RoleA"]
    assert 0 <= role.get("utilization", 0.0) <= 1.0
