"""Notebook-3 runners: paired-variance OCBA added to all methods; resampling-window test."""
import numpy as np
from .config import PROTOCOL, costs_for_ratio
from .build import build_problem
from .allocation import reference, uniform, sequential_elimination, ocba, ocba_paired, regret
from .candidates import is_boundary
from .empirical import EmpiricalDemand, EmpiricalProblem
from . import experiment2 as X2

GRID = PROTOCOL.rollout_grid
METHODS = ("uniform", "seq_elim", "ocba", "ocba_paired")


def run_methods(pr, base):
    ref = reference(pr, grid=X2.REF_GRID_EXT)
    J = pr.costs(PROTOCOL.seed_operational, 0, max(GRID) * pr.K)
    Jb = ref["means"][ref["best"]]
    base = dict(base, K=pr.K, ref_R=ref["R"], ref_converged=ref["converged"], ref_J=Jb,
                boundary=is_boundary(pr.cand, ref["best"]),
                margin_rel=(float(np.sort(ref["means"])[1] - Jb) / (abs(Jb) + PROTOCOL.regret_eps)) if pr.K > 1 else np.inf)
    rows = []
    for N in GRID:
        res = dict(uniform=uniform(pr, N, J), seq_elim=sequential_elimination(pr, N * pr.K, J=J),
                   ocba=ocba(pr, N * pr.K, J=J), ocba_paired=ocba_paired(pr, N * pr.K, J=J))
        for m in METHODS:
            rows.append(dict(base, method=m, N=N, rollouts=res[m]["rollouts"], **regret(ref, res[m]["choice"], pr.H)))
    return rows


def original_worker(args):
    rec, H, ratio = args
    pr = build_problem(rec, H, costs_for_ratio(ratio))
    return run_methods(pr, dict(set="original", state_id=rec["state_id"], item=rec["item"], store=-1,
                                family=rec["family"], volume_tertile=rec["volume_tertile"], H=H, cost_ratio=ratio))


def replication_worker(args):
    rec, hist, H, ratio, window = args
    pr = X2.build_empirical_problem(rec, hist, H, costs_for_ratio(ratio), window=window)
    weeks = len(pr.emp.starts)
    return run_methods(pr, dict(set="replication", state_id=rec["state_id"], item=rec["item"], store=rec["store"],
                                family=rec["family"], volume_tertile=rec["volume_tertile"], H=H, cost_ratio=ratio,
                                window=window, weeks_available=weeks))
