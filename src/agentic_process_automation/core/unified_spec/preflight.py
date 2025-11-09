from dataclasses import dataclass
from typing import Tuple
from z3 import (Solver, IntSort, BoolSort, ArraySort, IntVal, BoolVal, Const, Array,
                Select, Store, And, Or, Not, Implies, ForAll, Exists, sat, unsat, Optimize, K)

@dataclass
class Z3State:
    # Minimal example: we only model Decision.outcome and Decision.confidence by rfp_id
    outcome: "z3.ArrayRef"      # Int -> Int  (-1 none, 0 no_go, 1 go)
    confidence: "z3.ArrayRef" # Int -> Int  (0..100)

def mk_init_state(N:int) -> Z3State:
    IntS = IntSort()
    return Z3State(outcome=K(IntS, -1),
                   confidence=K(IntS, 0))

def clone_state(st:Z3State, t:int) -> Z3State:
    # re-name arrays per step
    return Z3State(
        outcome=Array(f"outcome_{t}", IntSort(), IntSort()),
        confidence=Array(f"conf_{t}", IntSort(), IntSort()),
    )

# Parse tiny expressions (toy: in real code, compile your DSL to Z3 terms)
def decision_done(rfp_id, st:Z3State):
    return Or(Select(st.outcome, rfp_id) == 0, Select(st.outcome, rfp_id) == 1)

def decision_quality_ok(rfp_id, st:Z3State):
    return Select(st.confidence, rfp_id) >= 80

def assess_rfp_guard(rfp_id, st:Z3State):
    # Example pre: outcome is unset
    return Select(st.outcome, rfp_id) == -1

def assess_rfp_step(rfp_id, st:Z3State, stp1:Z3State):
    # Example transition: set outcome and confidence (nondeterministic but constrained)
    o = Const("o_choice", IntSort())
    c = Const("c_choice", IntSort())
    return And(
        Or(o == 0, o == 1),
        c >= 50, c <= 100,
        stp1.outcome == Store(st.outcome, rfp_id, o),
        stp1.confidence == Store(st.confidence, rfp_id, c),
    )

def bounded_reachability(N:int=3, K:int=2) -> Tuple[bool, str]:
    s = Solver()
    r0 = IntVal(0)
    s0 = mk_init_state(N)

    states = [s0]
    for t in range(0, K):
        s_next = clone_state(states[-1], t+1)
        fired = Const(f"fired_{t}", BoolSort())

        s.add(Implies(fired,
                      And(assess_rfp_guard(r0, states[-1]),
                          assess_rfp_step(r0, states[-1], s_next))))
        s.add(Implies(Not(fired),
                      And(s_next.outcome == states[-1].outcome,
                          s_next.confidence == states[-1].confidence)))
        states.append(s_next)

    goal = Or(*[And(decision_done(r0, st), decision_quality_ok(r0, st)) for st in states])
    s.add(goal)

    result = s.check()
    if result == sat:
        return True, "REACHABLE: done & quality achievable within K steps."
    return False, "UNREACHABLE: within bound. Increase K or inspect preconditions."

def deadlock_check(N:int=3):
    s = Solver()
    st = Z3State(outcome=Array("outcome_sym", IntSort(), IntSort()),
                 confidence=Array("conf_sym", IntSort(), IntSort()))

    i = Const("i", IntSort())
    s.add(ForAll([i], Or(Select(st.outcome, i) == -1, Select(st.outcome, i) == 0, Select(st.outcome, i) == 1)))

    r0 = IntVal(0)
    not_done = Not(decision_done(r0, st))
    no_enabled = Not(assess_rfp_guard(r0, st))
    s.add(And(not_done, no_enabled))
    return s.check() == sat

def quality_implies_done_check(N:int=3):
    s = Solver()
    st = Z3State(outcome=Array("outcome_sym", IntSort(), IntSort()),
                 confidence=Array("conf_sym", IntSort(), IntSort()))

    i = Const("i", IntSort())
    s.add(ForAll([i], Or(Select(st.outcome, i) == -1, Select(st.outcome, i) == 0, Select(st.outcome, i) == 1)))

    r0 = IntVal(0)
    s.add(And(decision_quality_ok(r0, st), Not(decision_done(r0, st))))
    return s.check() != sat
