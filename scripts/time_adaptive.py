"""Wall-clock time per decision: uniform (N=500) vs sequential elimination (nominal 250), 150 twin states, H=14, base costs.
Single process, so per-decision times are comparable.  Run from the srep folder:
    python3 scripts/time_adaptive.py
Prints a small JSON block -- please send it back."""
import os, sys, time, json
import numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from srep.states import load_or_build
from srep.build import build_problem
from srep.config import costs_for_ratio
from srep.allocation import uniform, sequential_elimination

recs = load_or_build("benchmark")
pick = np.random.default_rng(1).choice(len(recs), 150, replace=False)
T = {"build": [], "uniform_500": [], "seq_elim_250": []}
for i in pick:
    t = time.perf_counter(); pr = build_problem(recs[int(i)], 14, costs_for_ratio("base")); T["build"].append(time.perf_counter() - t)
    t = time.perf_counter(); uniform(pr, 500); T["uniform_500"].append(time.perf_counter() - t)
    t = time.perf_counter(); sequential_elimination(pr, 250 * pr.K); T["seq_elim_250"].append(time.perf_counter() - t)
out = {k: dict(mean_ms=round(1000 * np.mean(v), 1), median_ms=round(1000 * np.median(v), 1)) for k, v in T.items()}
out["slowdown_seq_elim_vs_uniform"] = round(np.mean(T["seq_elim_250"]) / np.mean(T["uniform_500"]), 2)
print(json.dumps(out, indent=1))
