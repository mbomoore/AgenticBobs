import pytest
from agentic_process_automation.core.sim.core import State, Transition, ProcessModel, ModelValidationError


def test_state_transition_dsl_basic():
    p = ProcessModel('tst')
    with p:
        a = State('A')
        b = State('B')
        t = a >> 1.0 >> b
        p.add_transition(t)
    # after context exit, validation should pass
    assert isinstance(p.transition_matrix(), type(__import__('numpy').zeros((1,1))))


def test_invalid_prob_sum_raises():
    p = ProcessModel('bad')
    with pytest.raises(ModelValidationError):
        with p:
            a = State('A')
            b = State('B')
            c = State('C')
            p.add_transition(a >> 0.6 >> b)
            p.add_transition(a >> 0.3 >> c)
