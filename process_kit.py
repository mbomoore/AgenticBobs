import math
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

# ========= IR NODES =========

@dataclass(frozen=True)
class Task:
    name: str  # station id

@dataclass(frozen=True)
class Seq:
    items: Tuple[Any, ...]  # tuple of IR nodes

@dataclass(frozen=True)
class Choice:
    p_pass: float           # probability to take "on_pass" (0..1)
    on_pass: Any            # IR node
    on_fail: Any            # IR node

@dataclass(frozen=True)
class Workcell:
    tasks: Tuple[Task, ...] # merged tasks done by same performer
    setup_mean: float       # mean setup inside the cell
    setup_scv: float = 0.0  # SCV of setup (0 = deterministic)
    name: str = ""          # station name for the cell (if blank, auto)

def seq(*nodes) -> Seq:
    flat = []
    for n in nodes:
        if isinstance(n, Seq):
            flat.extend(n.items)
        else:
            flat.append(n)
    return Seq(tuple(flat))

# ========= SCV / COMPOSITION HELPERS =========

def scv_of_sum(means: List[float], scvs: List[float]) -> float:
    """SCV of sum of independent RVs given means and SCVs."""
    var = sum((m*m*scv) for m, scv in zip(means, scvs))
    msum = sum(means)
    return 0.0 if msum <= 0 else var / (msum*msum)

def combine_workcell_params(tasks: List[Tuple[float, float]], setup_mean: float, setup_scv: float=0.0) -> Tuple[float, float]:
    """
    Combine underlying task (mean, scv) plus a setup to get (mean, scv) for a Workcell.
    tasks: list of (m, scv) for each component Task
    """
    means = [setup_mean] + [m for m,_ in tasks]
    scvs  = [setup_scv]  + [s for _,s in tasks]
    msum  = sum(means)
    scv   = scv_of_sum(means, scvs)
    return msum, scv

# ========= QUEUEING PRIMITIVES =========

def utilization(lam: float, m: float, c: int) -> float:
    return (lam * m) / max(c, 1)

def pk_mg1_wait(lam: float, m: float, scv_s: float) -> float:
    """Pollaczek–Khinchine (M/G/1) mean waiting time."""
    rho = lam * m
    if rho >= 1: return float('inf')
    return (rho / (1.0 - rho)) * 0.5 * (1.0 + scv_s) * m

def kingman_gg1_wait(lam: float, m: float, scv_a: float, scv_s: float) -> float:
    """Kingman approximation for G/G/1."""
    rho = lam * m
    if rho >= 1: return float('inf')
    return ((scv_a + scv_s) / 2.0) * (rho / (1.0 - rho)) * m

def erlang_c_mm_c_wait(lam: float, m: float, c: int) -> float:
    """Erlang-C exact for M/M/c: returns E[Wq]."""
    mu = 1.0 / m
    a = lam / mu             # offered load
    rho = a / c
    if rho >= 1: return float('inf')
    # P0
    s = sum((a**n) / math.factorial(n) for n in range(c))
    s += (a**c) / (math.factorial(c) * (1.0 - rho))
    P0 = 1.0 / s
    Pw = ((a**c) / (math.factorial(c) * (1.0 - rho))) * P0
    return Pw / (c*mu - lam)

def allencunneen_gg_c_wait(lam: float, m: float, scv_a: float, scv_s: float, c: int) -> float:
    """Allen–Cunneen approximation for G/G/c."""
    rho = utilization(lam, m, c)
    if rho >= 1: return float('inf')
    alpha = (scv_a + scv_s) / 2.0
    # delay probability approx (from AC), then Wq:
    return alpha * (rho ** (math.sqrt(2*(c+1)) - 1.0)) * (m / (c * (1.0 - rho)))

def choose_wait(lam: float, m: float, c: int, scv_s: float, scv_a: float=1.0) -> float:
    """
    Pick a sane waiting-time formula by regime:
      - c==1, scv_a==1: PK (M/G/1)
      - c==1, general:  Kingman (G/G/1)
      - c>1, scv's ~1:  Erlang-C (M/M/c)
      - c>1, general:   Allen–Cunneen (G/G/c)
    """
    if c <= 1:
        return pk_mg1_wait(lam, m, scv_s) if abs(scv_a - 1.0) < 1e-9 else kingman_gg1_wait(lam, m, scv_a, scv_s)
    else:
        if abs(scv_a - 1.0) < 1e-3 and abs(scv_s - 1.0) < 1e-3:
            return erlang_c_mm_c_wait(lam, m, c)
        return allencunneen_gg_c_wait(lam, m, scv_a, scv_s, c)

# ========= PATH ENUMERATION (expected visits & handovers) =========

def enumerate_paths(ir: Any) -> List[Tuple[List[Any], float]]:
    """
    Return all linearized station sequences with their probabilities.
    Stations = Task or Workcell. Seq concatenates; Choice splits by p.
    """
    def as_paths(node) -> List[Tuple[List[Any], float]]:
        if isinstance(node, Task) or isinstance(node, Workcell):
            return [([node], 1.0)]
        if isinstance(node, Seq):
            paths = [([], 1.0)]
            for child in node.items:
                child_paths = as_paths(child)
                new = []
                for p_nodes, p_prob in paths:
                    for c_nodes, c_prob in child_paths:
                        new.append((p_nodes + c_nodes, p_prob * c_prob))
                paths = new
            return paths
        if isinstance(node, Choice):
            p1 = as_paths(node.on_pass)
            p2 = as_paths(node.on_fail)
            return [(nodes, prob * node.p_pass) for nodes, prob in p1] + \
                   [(nodes, prob * (1.0 - node.p_pass)) for nodes, prob in p2]
        # Empty seq / no-op:
        return [([], 1.0)]
    # strip empties
    return [( [n for n in nodes if isinstance(n, (Task, Workcell))], prob)
            for nodes, prob in as_paths(ir)]

def expected_visits(ir: Any) -> Dict[str, float]:
    """Expected number of visits to each station per case."""
    visits: Dict[str, float] = {}
    for nodes, prob in enumerate_paths(ir):
        for n in nodes:
            key = n.name if isinstance(n, Workcell) and n.name else getattr(n, "name")
            visits[key] = visits.get(key, 0.0) + prob
    return visits

def expected_handover_count(ir: Any, performer_of: Dict[str, str]) -> float:
    """
    Expected number of cross-performer transitions per case (to multiply by a handover penalty).
    """
    total = 0.0
    for nodes, prob in enumerate_paths(ir):
        for a, b in zip(nodes, nodes[1:]):
            pa = performer_of[getattr(a, "name")]
            pb = performer_of[getattr(b, "name")]
            if pa != pb:
                total += prob
    return total

# ========= END-TO-END METRICS OVER THE IR =========

def compute_station_params_for_node(node: Any, stations: Dict[str, Dict[str, float]]) -> Tuple[str, float, float, int, str]:
    """
    Return (name, mean, scv, capacity, performer) for Task or Workcell node.
    For Workcell, combine its component tasks (from 'stations') and setup_* on the node itself.
    """
    if isinstance(node, Task):
        s = stations[node.name]
        return node.name, s["m"], s["scv"], int(s["c"]), s["performer"]
    if isinstance(node, Workcell):
        name = node.name or "Cell(" + "+".join(t.name for t in node.tasks) + ")"
        comps = [ (stations[t.name]["m"], stations[t.name]["scv"]) for t in node.tasks ]
        m, scv = combine_workcell_params(comps, node.setup_mean, node.setup_scv)
        # policy: take performer from first task; capacity default 1 unless provided
        perf = stations[node.tasks[0].name]["performer"]
        cap  = int(stations.get(name, {}).get("c", 1))
        return name, m, scv, cap, perf
    raise ValueError("Unsupported node type")

def analytic_metrics(
    ir: Any,
    lam: float,
    stations: Dict[str, Dict[str, float]],
    arrival_scv: float = 1.0,
    handover_penalty: float = 0.0
) -> Dict[str, Any]:
    """
    Compute mean cycle time and per-station metrics using approximations.
    'stations' maps station-name -> {m, scv, c, performer}.
    """
    # 1) Expected visits & performers
    visits = expected_visits(ir)

    # Build a performer map including workcells
    performer_of: Dict[str, str] = {}
    for nodes, _ in enumerate_paths(ir):
        for n in nodes:
            name, m, scv, c, perf = compute_station_params_for_node(n, stations)
            performer_of[name] = perf

    # 2) Per-station arrival rates
    lam_j = {name: lam * V for name, V in visits.items()}

    # 3) Per-station waits and response times
    station_rows = []
    for nodes, _ in enumerate_paths(ir):
        for n in nodes:
            name, m, scv_s, c, perf = compute_station_params_for_node(n, stations)
            if name in [row["station"] for row in station_rows]:  # already processed
                continue
            lam_eff = lam_j[name]
            rho = utilization(lam_eff, m, c)
            Wq = choose_wait(lam_eff, m, c, scv_s=scv_s, scv_a=arrival_scv)
            Tj = Wq + m
            station_rows.append({
                "station": name, "performer": perf, "c": c,
                "lambda": lam_eff, "rho": rho, "m": m, "scv_s": scv_s,
                "E_Wq": Wq, "E_T": Tj, "visits": visits[name]
            })

    # 4) Expected handover overhead
    Hcount = expected_handover_count(ir, performer_of)
    Hmean  = Hcount * handover_penalty

    # 5) End-to-end mean cycle
    E_T = sum(row["visits"] * row["E_T"] for row in station_rows) + Hmean

    return {"E_cycle": E_T, "handover_mean": Hmean, "per_station": station_rows, "visits": visits}



if __name__=='__main__':
    # Define a 3-step baseline and an "AI -> verify" variant
    ir_baseline = seq(Task("Step1"), Task("Step2"), Task("Step3"))
    ir_ai_verify = seq(Task("Step1"), seq(Task("Step2_AI"), Choice(0.6, seq(), Task("Step2_Verify"))), Task("Step3"))

    # Station params: mean m (minutes), SCV of service, capacity c, performer label
    stations = {
        "Step1":         {"m": 4.0,  "scv": 0.25, "c": 1, "performer": "Intake"},
        "Step2":         {"m":12.0,  "scv": 0.36, "c": 2, "performer": "Analyst"},
        "Step3":         {"m": 5.5,  "scv": 0.20, "c": 1, "performer": "Delivery"},
        "Step2_AI":      {"m": 3.0,  "scv": 0.16, "c": 2, "performer": "Agent"},
        "Step2_Verify":  {"m": 8.0,  "scv": 0.25, "c": 1, "performer": "Verifier"},
    }

    lam = 6/60.0  # 6 cases/hour
    print(analytic_metrics(ir_baseline,   lam, stations, arrival_scv=1.0, handover_penalty=0.5)["E_cycle"])
    print(analytic_metrics(ir_ai_verify, lam, stations, arrival_scv=1.0, handover_penalty=0.5)["E_cycle"])
