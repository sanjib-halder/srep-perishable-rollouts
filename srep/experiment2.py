"""
Amendment A11 experiments (post-review): runner functions used by notebook 2.

  * run_methods       uniform / paired sequential elimination / OCBA on one Problem,
                      scored against a reference whose grid extends to 320,000 rollouts.
  * original_worker   the 500 pre-specified states with the twin's demand model.
  * replication_*     states rebuilt from raw Favorita by SGSG replay, demand resampled
                      from each store-item's own past sales (srep/empirical.py).
  * widegrid_worker   best candidate vs a dense grid of order quantities.
  * timing_worker     end-to-end decision (build + simulate + select) for the 50,000-run benchmark.
All workers are top-level functions so macOS 'spawn' multiprocessing can import them.
"""
import dataclasses
import numpy as np

from .config import PROTOCOL, costs_for_ratio
from .build import build_problem
from .engine import SkuSpec, AgeAwareSSPolicy
from .candidates import generate_candidates, is_boundary
from .allocation import reference, uniform, sequential_elimination, ocba, regret
from .empirical import EmpiricalDemand, EmpiricalProblem
from .favorita import SHELF_LIFE
from .sgsg_replay import replay_with_snapshots
from sgsg.generator import FAMILY_SUPPLIER, warehouse_capacity_for_sku

REF_GRID_EXT = (5000, 10000, 20000, 40000, 80000, 160000, 320000)
GRID = PROTOCOL.rollout_grid
METHODS = ("uniform", "seq_elim", "ocba")


def run_methods(pr, base):
    ref = reference(pr, grid=REF_GRID_EXT)
    Nmax = max(GRID)
    J = pr.costs(PROTOCOL.seed_operational, 0, Nmax * pr.K)
    Jb = ref["means"][ref["best"]]
    base = dict(base, K=pr.K, ref_R=ref["R"], ref_converged=ref["converged"], ref_J=Jb,
                ref_best_qty=int(pr.cand[ref["best"]]), boundary=is_boundary(pr.cand, ref["best"]),
                margin_rel=(float(np.sort(ref["means"])[1] - Jb) / (abs(Jb) + PROTOCOL.regret_eps)) if pr.K > 1 else np.inf)
    rows = []
    for N in GRID:
        u = uniform(pr, N, J)
        s = sequential_elimination(pr, N * pr.K, J=J)
        o = ocba(pr, N * pr.K, J=J)
        for m, res in zip(METHODS, (u, s, o)):
            rows.append(dict(base, method=m, N=N, rollouts=res["rollouts"], **regret(ref, res["choice"], pr.H)))
    return rows


# ------------------------------------------------------------------ original 500 states (twin demand)
def original_worker(args):
    rec, H, ratio = args
    pr = build_problem(rec, H, costs_for_ratio(ratio))
    base = dict(set="original", state_id=rec["state_id"], item=rec["item"], store=-1, family=rec["family"],
                volume_tertile=rec["volume_tertile"], H=H, cost_ratio=ratio)
    return run_methods(pr, base)


# ------------------------------------------------------------------ replication on raw Favorita
def build_replication_states(panel, n, seed, family_price, min_history=200, horizon_room=30, log=print):
    meta = panel["meta"].copy()
    elig = meta[(meta.active_days >= min_history + horizon_room + 60) & (meta.share_selling >= 0.5) & (meta.mean_sales >= 1.0)].copy()
    elig["volume_tertile"] = elig.groupby("family")["mean_sales"].transform(
        lambda x: np.digitize(x, np.quantile(x, [1 / 3, 2 / 3])))
    log(f"eligible store-items: {len(elig)} (of {len(meta)}); stores {elig.store_nbr.nunique()}; items {elig.item_nbr.nunique()}")
    cells = [(f, v) for f in SHELF_LIFE for v in range(3)]
    rng = np.random.default_rng(seed)
    picks = {}
    for k in range(n):
        f, v = cells[k % len(cells)]
        pool = elig[(elig.family == f) & (elig.volume_tertile == v)]
        row = pool.iloc[int(rng.integers(len(pool)))]
        t = int(rng.integers(row["first"] + min_history, row["last"] - horizon_room))
        picks.setdefault((int(row.store_nbr), int(row.item_nbr)), []).append((k, t, f, v, int(row["first"])))
    out = []
    for j, (key, lst) in enumerate(sorted(picks.items())):
        hist = panel["series"][key]
        first = lst[0][4]
        fam = lst[0][2]
        sl = SHELF_LIFE[fam]
        _, snaps, avg30 = replay_with_snapshots(hist[first:], sl, fam, max(t for _, t, _, _, _ in lst) - first + 1,
                                               seed=500_000 + j, snap_days=[t - first for _, t, _, _, _ in lst])
        for k, t, f, v, _ in lst:
            oh, pp = snaps[t - first]
            last = np.nonzero(pp)[0]
            pp = pp[: (last[-1] + 1 if len(last) else 1)]
            from .engine import State
            out.append(dict(state_id=200_000 + k, store=key[0], item=key[1], family=f, volume_tertile=int(v),
                            shelf_life=sl, t_idx=t, first=first, date=str(panel["days"][t].date()),
                            price=float(family_price[f]), sgsg_avg30=float(avg30),
                            state=State(t, oh.copy(), pp.copy())))
    out.sort(key=lambda r: r["state_id"])
    return out


def build_empirical_problem(rec, hist, H, costs, window=None):
    fam = rec["family"]
    emp = EmpiricalDemand(hist, rec["t_idx"], first=rec["first"]) if window is None else \
        EmpiricalDemand(hist, rec["t_idx"], window=window, first=rec["first"])
    spec = SkuSpec(item=rec["item"], family=fam, price=rec["price"], shelf_life=rec["shelf_life"],
                   base_rate=float(emp.weekday_mean.mean()), supplier_idx=FAMILY_SUPPLIER[fam],
                   capacity=warehouse_capacity_for_sku(rec["sgsg_avg30"], rec["shelf_life"]))
    policy = AgeAwareSSPolicy(spec, emp.mean_demand(H + spec.shelf_life + 60))
    cand = generate_candidates(None, spec, rec["state"], policy, samples=emp.protection_samples(policy.L + 1))
    return EmpiricalProblem(spec=spec, state=rec["state"], cand=cand, policy=policy, H=H,
                            state_id=rec["state_id"], dm=None, costs_params=costs, emp=emp)


def replication_worker(args):
    rec, hist, H, ratio = args
    pr = build_empirical_problem(rec, hist, H, costs_for_ratio(ratio))
    base = dict(set="replication", state_id=rec["state_id"], item=rec["item"], store=rec["store"],
                family=rec["family"], volume_tertile=rec["volume_tertile"], H=H, cost_ratio=ratio,
                demand_cv=float(hist[max(rec["first"], rec["t_idx"] - 182):rec["t_idx"]].std() /
                                max(hist[max(rec["first"], rec["t_idx"] - 182):rec["t_idx"]].mean(), 1e-9)))
    return run_methods(pr, base)


# ------------------------------------------------------------------ wider candidate grid
def widegrid_worker(args):
    kind, rec, hist, H = args
    pr = build_problem(rec, H) if kind == "original" else build_empirical_problem(rec, hist, H, costs_for_ratio("base"))
    mx = int(pr.cand.max())
    grid = np.unique(np.concatenate([np.linspace(0, 2.5 * mx + 5, 24).round().astype(np.int64), pr.cand]))
    pr2 = dataclasses.replace(pr, cand=grid)
    J = pr2.costs(PROTOCOL.seed_reference, 0, 20000)
    m = J.mean(0)
    in_set = np.isin(grid, pr.cand)
    best_set, best_all = m[in_set].min(), m.min()
    return dict(set=kind, state_id=rec["state_id"], family=rec["family"], H=H, K=pr.K,
                gap_rel=float((best_set - best_all) / (abs(best_all) + 1e-9)),
                grid_best_qty=int(grid[np.argmin(m)]), set_best_qty=int(grid[in_set][np.argmin(m[in_set])]),
                grid_best_outside_set_range=bool(grid[np.argmin(m)] > mx or grid[np.argmin(m)] < pr.cand.min()))


# ------------------------------------------------------------------ end-to-end timing
def timing_worker(args):
    rec, H, N = args
    pr = build_problem(rec, H)
    return int(pr.cand[uniform(pr, N)["choice"]])
