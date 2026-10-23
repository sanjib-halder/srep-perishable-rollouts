"""
Day-2 rollout-stability benchmark and branch decision (protocol §4, §6).

For every benchmark state and horizon:
  1. large-rollout reference with convergence check (§5.4);
  2. uniform allocation for every N in the rollout grid;
  3. paired sequential elimination at each matched budget N x K;
  4. relative regret against the reference.
Then applies the preregistered branch rule and prints Plan A / Plan B / Stop.

Refuses to run on the benchmark set without --signed-off (protocol §17).
Use --dev for smoke tests on the DEV states (never reported).

  python scripts/day2_branch.py --dev --workers 2
  python scripts/day2_branch.py --signed-off --workers 8
"""
import argparse
import json
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from srep.config import PROTOCOL, protocol_hash, costs_for_ratio, COST_RATIOS
from srep.states import load_or_build
from srep.build import build_problem
from srep.allocation import reference, uniform, sequential_elimination, regret
from srep.candidates import is_boundary


def run_state(args):
    rec, H, ratio = args
    t = time.perf_counter()
    pr = build_problem(rec, H, costs_for_ratio(ratio))
    ref = reference(pr)
    Nmax = max(PROTOCOL.rollout_grid)
    rows_needed = max(Nmax, Nmax * pr.K // 2 + PROTOCOL.se_n0 + PROTOCOL.se_batch)
    J = pr.costs(PROTOCOL.seed_operational, 0, rows_needed)
    J_best = ref["means"][ref["best"]]
    out = []
    base = dict(state_id=rec["state_id"], item=rec["item"], H=H, cost_ratio=ratio, family=rec["family"], shelf_life=rec["shelf_life"],
                volume_tertile=rec["volume_tertile"], disrupted=rec["disrupted"], K=pr.K,
                ref_R=ref["R"], ref_converged=ref["converged"], ref_best_qty=int(pr.cand[ref["best"]]),
                ref_J=J_best, boundary=is_boundary(pr.cand, ref["best"]),
                ref_max_paired_se_rel=float(np.max(ref["paired_se"]) / (abs(J_best) + PROTOCOL.regret_eps)),
                margin_rel=float(np.sort(ref["means"])[1] - J_best) / (abs(J_best) + PROTOCOL.regret_eps) if pr.K > 1 else np.inf)
    for N in PROTOCOL.rollout_grid:
        u = uniform(pr, N, J)
        out.append({**base, "method": "uniform", "N": N, "rollouts": u["rollouts"], **regret(ref, u["choice"], H)})
        s = sequential_elimination(pr, N * pr.K, J=J)
        out.append({**base, "method": "seq_elim", "N": N, "rollouts": s["rollouts"],
                    "survivors": s["survivors"], **regret(ref, s["choice"], H)})
    for r in out:
        r["state_seconds"] = time.perf_counter() - t
    return out


def branch_decision(df, timing):
    P = PROTOCOL
    u = df[(df.method == "uniform") & (df.H == P.primary_horizon)]
    frac = lambda d: float((d.r_rel <= P.branch_regret_threshold).mean())
    f100 = frac(u[u.N == P.branch_rollouts])
    crit100 = f100 >= P.branch_state_fraction
    small = {N: frac(u[u.N == N]) for N in P.stop_small_budgets}
    small_by_family = {N: {f: frac(g[g.N == N]) for f, g in u.groupby("family")} for N in P.stop_small_budgets}
    small_ok = any(all(v >= P.branch_state_fraction for v in small_by_family[N].values()) for N in P.stop_small_budgets)

    affordable = None
    if timing and timing.get("mode") == "OFFICIAL":
        recs = [r for r in timing["summary"] if r["H"] == P.primary_horizon and r["N"] == P.operational_full_rollouts]
        if recs and "within_budget" in recs[0]:
            affordable = bool(recs[0]["within_budget"])

    if small_ok:
        decision = "STOP candidate: very small uniform budgets already meet the criterion in every family -- check for regime heterogeneity before stopping (protocol §4 row 3)."
    elif crit100 or affordable:
        decision = "PLAN B: do not build the surrogate; compare uniform budgets with paired sequential elimination."
    elif affordable is None:
        decision = "UNDECIDED: 100-rollout criterion fails, but no OFFICIAL timing result exists to test affordability. Run benchmark_compute.py with a completed budget.json."
    else:
        decision = "PLAN A: 100-rollout criterion fails and full rollout violates the frozen budget -- build the surrogate and gate."
    return dict(frac_states_ok_at_100=f100, criterion_100_passes=crit100, frac_ok_small=small,
                frac_ok_small_by_family=small_by_family, full_rollout_affordable=affordable, decision=decision)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dev", action="store_true")
    ap.add_argument("--signed-off", action="store_true")
    ap.add_argument("--workers", type=int, default=os.cpu_count())
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--cost-ratio", choices=list(COST_RATIOS), default="base")
    args = ap.parse_args()
    if not args.dev and not args.signed_off:
        sys.exit("Refusing to touch benchmark states: complete the §17 sign-off and pass --signed-off (or use --dev).")
    kind = "dev" if args.dev else "benchmark"
    states = load_or_build(kind)[: args.limit]
    jobs = [(rec, H, args.cost_ratio) for H in PROTOCOL.horizons for rec in states]
    t = time.perf_counter()
    with Pool(args.workers) as pool:
        res = []
        for i, r in enumerate(pool.imap_unordered(run_state, jobs, chunksize=1)):
            res.extend(r)
            if (i + 1) % 25 == 0:
                print(f"  {i+1}/{len(jobs)} state-horizons done ({time.perf_counter()-t:.0f}s)")
    df = pd.DataFrame(res)
    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
    df.to_csv(os.path.join(ROOT, "results", f"day2_{kind}_{args.cost_ratio}.csv"), index=False)

    tpath = os.path.join(ROOT, "results", "timing_official.json")
    timing = json.load(open(tpath)) if os.path.exists(tpath) else None
    dec = branch_decision(df, timing)
    dec.update(protocol_hash=protocol_hash(), kind=kind, cost_ratio=args.cost_ratio, n_states=len(states), elapsed_s=time.perf_counter() - t,
               ref_converged_frac=float(df.drop_duplicates(["state_id", "H"]).ref_converged.mean()),
               boundary_frac=float(df.drop_duplicates(["state_id", "H"]).boundary.mean()))
    with open(os.path.join(ROOT, "results", f"day2_{kind}_{args.cost_ratio}_decision.json"), "w") as f:
        json.dump(dec, f, indent=2, default=str)

    tab = (df.groupby(["H", "method", "N"])
             .agg(mean_rollouts=("rollouts", "mean"), p_correct=("correct", "mean"),
                  frac_ok=("r_rel", lambda x: (x <= PROTOCOL.branch_regret_threshold).mean()),
                  r_rel_median=("r_rel", "median"), r_rel_p95=("r_rel", lambda x: np.quantile(x, .95)),
                  r_rel_max=("r_rel", "max")).reset_index())
    print(tab.to_string(index=False))
    print(json.dumps({k: v for k, v in dec.items()}, indent=2, default=str))
    if args.dev:
        print("\nDEV run: smoke test only. Do not report or use these numbers to tune the protocol.")


if __name__ == "__main__":
    main()
