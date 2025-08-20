from sim_dsl.core import State, ProcessModel
from sim_dsl.simpy_adapter import simulate_markov_chain


def test_simulate_markov_chain():
    p = ProcessModel('mc')
    with p:
        s = State('Start')
        end = State('End')
        p.add_transition(s >> 1.0 >> end)
    res = simulate_markov_chain(p, steps=10)
    assert 'visits' in res and 'trace' in res
    assert sum(res['visits']) == 10
