def test_timed_resource_basic():
    import pytest
    simpy = pytest.importorskip("simpy")
    from sim_dsl.resources import TimedResource

    env = simpy.Environment()
    tr = TimedResource(env, capacity=1)

    def user(env):
        yield from tr.hold(env, 2)

    env.process(user(env))
    env.run()

    assert tr.total_acquired == 1
    assert tr.total_time_held == 2
