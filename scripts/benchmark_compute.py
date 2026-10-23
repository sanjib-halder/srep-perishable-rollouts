"""
Day-2 timing benchmark (protocol §6 / RQ1).

Measures end-to-end wall time, CPU time and peak memory for evaluating every
candidate of a state with N rollouts over horizon H -- scenario generation,
simulation, aggregation and action selection included -- then projects the
cost of one decision cycle using the frozen budget in budget.json.

This script only times computation; it never computes regret, so running it
does not inspect any decision-quality result.

  python scripts/benchmark_compute.py                # DEV mode if budget.json incomplete
  python scripts/benchmark_compute.py --states 200 --twin-check 3
"""
import argparse
import json
import os
import platform
import sys
import time
import tracemalloc

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from srep.config import PROTOCOL, protocol_hash
from srep.states import load_or_build
from srep.build import build_problem
from srep.allocation import uniform

GRID = (100, 500, 1000, 5000)


def load_budget():
    with open(os.path.join(ROOT, "budget.json")) as f:
        b = json.load(f)
    missing = [k for k, v in b.items() if not k.startswith("_") and v is None]
    missing += [f"hardware.{k}" for k, v in b["hardware"].items() if v is None and k != "gpu"]
    return b, missing


def time_twin_rollouts(rec, H, n=20):
    """Reference timing: the original GroceryTwin, one rollout at a time via clone()."""
    from twin.digital_twin import GroceryTwin
    from sgsg.generator import Batch, warehouse_capacity_for_sku
    pr = build_problem(rec, H)
    sp = pr.spec
    spec = dict(item_nbr=sp.item, family=sp.family, unit_price=sp.price,
                shelf_life_days=sp.shelf_life, avg_daily_demand=sp.base_rate)
    dm = pr.dm
    gen = lambda item, day, rng: int(rng.poisson(max(0.1, dm.base_lambda(item, day, 1)[0])))
    tw = GroceryTwin([spec], gen, warehouse_capacity_for_sku, seed=0)
    tw.day = pr.state.t0
    s = tw.skus[sp.item]
    s.batches = [Batch(int(q), tw.day, tw.day + r) for r, q in enumerate(pr.state.onhand) if q > 0]
    s.pending_orders = [(tw.day + i, int(q)) for i, q in enumerate(pr.state.pipe) if q > 0]
    t = time.perf_counter()
    for _ in range(n):
        for a in pr.cand:
            c = tw.clone()
            for h in range(H):
                c.step({sp.item: int(a) if h == 0 else 0})
    return (time.perf_counter() - t) / (n * pr.K)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--states", type=int, default=200)
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--twin-check", type=int, default=3, help="states on which to time the original twin")
    args = ap.parse_args()

    budget, missing = load_budget()
    mode = "OFFICIAL" if not missing else "DEV"
    print(f"Mode: {mode}" + ("" if not missing else f"  (budget.json incomplete: {missing})"))
    states = load_or_build("benchmark")
    rng = np.random.default_rng(0)
    sel = rng.choice(len(states), size=min(args.states, len(states)), replace=False)

    rows = []
    for H in PROTOCOL.horizons:
        for N in GRID:
            for i in sel:
                rec = states[int(i)]
                pr = build_problem(rec, H)
                best = []
                for _ in range(args.repeats):
                    w0, c0 = time.perf_counter(), time.process_time()
                    J = pr.costs(PROTOCOL.seed_operational, 0, N)
                    uniform(pr, N, J)
                    best.append((time.perf_counter() - w0, time.process_time() - c0))
                w, c = min(best)
                rows.append(dict(H=H, N=N, state_id=rec["state_id"], family=rec["family"], K=pr.K,
                                 wall_s=w, cpu_s=c, rollouts=N * pr.K, day_steps=N * pr.K * H))
            # peak memory on one representative state
            pr = build_problem(states[int(sel[0])], H)
            tracemalloc.start()
            pr.costs(PROTOCOL.seed_operational, 0, N)
            peak = tracemalloc.get_traced_memory()[1]
            tracemalloc.stop()
            for r in rows:
                if r["H"] == H and r["N"] == N:
                    r["peak_mem_mb_example"] = peak / 1e6
            print(f"H={H:2d} N={N:5d}: median wall/state {np.median([r['wall_s'] for r in rows if r['H']==H and r['N']==N])*1e3:8.1f} ms")

    df = pd.DataFrame(rows)
    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
    df.to_csv(os.path.join(ROOT, "results", f"timing_{mode.lower()}.csv"), index=False)

    summ = df.groupby(["H", "N"]).agg(K_mean=("K", "mean"), wall_med=("wall_s", "median"),
                                      wall_p95=("wall_s", lambda x: np.quantile(x, .95)),
                                      wall_mean=("wall_s", "mean"), cpu_mean=("cpu_s", "mean"),
                                      us_per_day_step=("day_steps", lambda x: 0)).reset_index()
    summ["us_per_day_step"] = [1e6 * df[(df.H == r.H) & (df.N == r.N)].wall_s.sum() /
                               df[(df.H == r.H) & (df.N == r.N)].day_steps.sum() for r in summ.itertuples()]

    pop = budget.get("decision_population_per_cycle")
    workers = budget.get("parallel_workers")
    limit = budget.get("permitted_cycle_duration_seconds")
    if pop and workers:
        summ["projected_cycle_s"] = summ.wall_mean * pop / workers
        if limit:
            summ["within_budget"] = summ.projected_cycle_s <= limit
    print("\n" + summ.to_string(index=False))

    twin = []
    for i in sel[:args.twin_check]:
        twin.append(time_twin_rollouts(states[int(i)], PROTOCOL.primary_horizon))
    if twin:
        eng = summ[(summ.H == PROTOCOL.primary_horizon) & (summ.N == 1000)].iloc[0]
        per_rollout_eng = eng.wall_mean / (1000 * eng.K_mean)
        print(f"\nOriginal GroceryTwin (clone+step): {np.mean(twin)*1e3:.2f} ms per rollout; "
              f"vectorised engine: {per_rollout_eng*1e6:.1f} us per rollout "
              f"(x{np.mean(twin)/per_rollout_eng:.0f}). Report engine timings, not twin timings.")

    meta = dict(mode=mode, protocol_hash=protocol_hash(), budget=budget, missing_budget_fields=missing,
                machine=dict(platform=platform.platform(), python=platform.python_version(),
                             cpu_count=os.cpu_count(), processor=platform.processor()),
                numpy=np.__version__, states_timed=len(sel), repeats=args.repeats,
                twin_ms_per_rollout=float(np.mean(twin) * 1e3) if twin else None,
                summary=summ.to_dict("records"))
    with open(os.path.join(ROOT, "results", f"timing_{mode.lower()}.json"), "w") as f:
        json.dump(meta, f, indent=2, default=str)
    if mode == "DEV":
        print("\nDEV mode: these timings are for development only and must not be reported.")


if __name__ == "__main__":
    main()
