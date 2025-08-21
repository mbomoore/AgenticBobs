"""Example: build a small model and run it with the simpy adapter."""
from sim_dsl import ProcessModel, State, Resource
from sim_dsl.simpy_adapter import simulate_with_simpy


def main():
    p = ProcessModel('survey')
    with p:
        analyst = Resource('Analyst', cost=100)
        find = State('Find', time=0.05, resource=analyst)
        refine = State('Refine', time=4, resource=analyst)
        success = State('Success')
        failure = State('Failure')
        p.add_transition(find >> 0.1 >> refine)
        p.add_transition(find >> 0.9 >> failure)
        p.add_transition(refine >> 0.5 >> success)
        p.add_transition(refine >> 0.5 >> failure)

    res = simulate_with_simpy(p, runs=10, seed=42)
    print('counts:', res['counts'])


if __name__ == '__main__':
    main()
