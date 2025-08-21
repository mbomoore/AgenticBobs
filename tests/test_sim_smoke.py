from agentic_process_automation.core.pir import PIRBuilder
from agentic_process_automation.core.sim import run


def test_sim_smoke_runs_and_emits_ticks():
    b = PIRBuilder()
    b.add_node(id="n1", kind="task", name="Start")
    pir = b.build()

    logs = []
    scenario = {"horizon": 3, "seed": 1}

    run(pir, scenario, policies={}, resources={}, log_cb=lambda e: logs.append(e))

    # Expect at least one tick per simulated hour
    assert len([e for e in logs if e.get("event") == "tick"]) >= 1
