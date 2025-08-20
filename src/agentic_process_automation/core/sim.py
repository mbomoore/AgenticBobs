from typing import Callable
from .pir import PIR


try:
    import simpy  # type: ignore
except Exception:
    simpy = None  # type: ignore


def compile_model(pir: PIR, policies: dict, resources: dict) -> Callable:
    """Return a runner(env, scenario, log_cb) callable that performs a trivial simulation.

    If SimPy is available, the runner will be a SimPy process. Otherwise, a
    simple fallback runner (pure Python) is returned that advances integer
    time steps and calls back with tick events.
    """

    if simpy is not None:
        def runner(env: simpy.Environment, scenario: dict, log_cb: Callable):
            horizon = float(scenario.get("horizon", 1))
            # simplistic state
            while env.now < horizon:
                yield env.timeout(1.0)
                log_cb({"t": env.now, "event": "tick"})

        return runner

    # Fallback pure-Python runner
    def runner_py(env_unused, scenario: dict, log_cb: Callable):
        horizon = int(float(scenario.get("horizon", 1)))
        for t in range(1, horizon + 1):
            # synchronous sleep avoided; just emit ticks
            log_cb({"t": float(t), "event": "tick"})

    return runner_py


def run(pir: PIR, scenario: dict, policies: dict, resources: dict, log_cb: Callable):
    """Run the compiled model either with SimPy or the fallback loop."""
    runner = compile_model(pir, policies, resources)
    if simpy is not None:
        env = simpy.Environment()
        env.process(runner(env, scenario, log_cb))
        env.run(until=scenario.get("horizon", 1))
    else:
        # runner is a pure-Python callable that ignores env
        runner(None, scenario, log_cb)

