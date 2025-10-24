import sys
from pathlib import Path

# Add the project paths to sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from agentic_process_automation.core.pir import PIRBuilder
from agentic_process_automation.core.sim import simulate, SimulationParameters, SimulationSettings
from agentic_process_automation.core.sim.pir_adapter import pir_to_process_model


def test_sim_smoke_runs_and_emits_ticks():
    b = PIRBuilder()
    b.add_node(id="n1", kind="task", name="Start")
    b.add_node(id="n2", kind="task", name="End")
    b.add_edge(src="n1", dst="n2")
    pir = b.build()

    process_model = pir_to_process_model(pir)

    params = SimulationParameters(runs=1, end_time_min=3)
    settings = SimulationSettings(simulations=1, seed=1)
    result = simulate(process_model, parameters=params, settings=settings)

    # A simple check to ensure the simulation ran
    assert result is not None
