# Minimal resources module: Resource descriptor and TimedResource wrapper
from dataclasses import dataclass


@dataclass
class Resource:
    role: str
    cost: float = 0.0
    capacity: int = 1

    def __repr__(self) -> str:
        return f"{self.role} (cost:{self.cost}/hr, cap:{self.capacity})"


class TimedResource:
    def __init__(self, env, capacity: int = 1):
        try:
            import simpy
        except Exception as e:
            raise ImportError("simpy is required for TimedResource") from e
        self._env = env
        self._res = simpy.Resource(env, capacity=capacity)
        self.capacity = capacity
        # counters for metrics
        self.total_acquired = 0
        self.total_time_held = 0.0
        # timeline events: list of (timestamp, delta) where delta is +1 on acquire, -1 on release
        self.timeline = []

    def request(self):
        return self._res.request()

    def release(self, req):
        return self._res.release(req)

    def hold(self, env, duration: float):
        req = self._res.request()
        yield req
        self.total_acquired += 1
        start = env.now
        # record acquisition event
        try:
            self.timeline.append((float(start), 1))
        except Exception:
            pass
        try:
            if duration > 0:
                yield env.timeout(duration)
        finally:
            self._res.release(req)
            end = env.now
            self.total_time_held += (end - start)
            # record release event
            try:
                self.timeline.append((float(end), -1))
            except Exception:
                pass

    @property
    def utilization(self) -> float:
        """Return utilization as fraction of total available resource time.

        Computed as total_time_held / (simulation_time * capacity). Simulation time is
        taken from the environment's current time (`env.now`). Returns 0.0 if env.now
        is zero or unavailable.
        """
        try:
            sim_time = float(self._env.now)
        except Exception:
            return 0.0
        if sim_time <= 0 or self.capacity <= 0:
            return 0.0
        util = self.total_time_held / (sim_time * self.capacity)
        # clamp to [0, 1]
        if util < 0:
            return 0.0
        if util > 1:
            return 1.0
        return util
