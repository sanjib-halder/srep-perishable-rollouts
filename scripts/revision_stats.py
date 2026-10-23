"""Numbers for the revised manuscript (twin states, extended reference, three methods)."""
import os, sys, json
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "results")
THR, TARGET, B = 0.005, 0.95, 2000
GRID = (10, 25, 50, 100, 250, 500, 1000)
FAMS = ("BREAD/BAKERY", "PRODUCE", "DAIRY")
rng = np.random.default_rng(2026)

df = pd.concat([pd.read_csv(os.path.join(RES, f"nb02_original_{r}.csv")) for r in ("base", "low", "high")])
df["ok"] = (df.r_rel <= THR).astype(float)
df["near"] = df.margin_rel <= THR


def boot_mean(values, items):
    """Item-clustered percentile bootstrap CI of a mean."""
    g = pd.DataFrame({"v": values, "i": items}).groupby("i")["v"].agg(["sum", "count"])
    s, n = g["sum"].values, g["count"].values
    w = rng.multinomial(len(g), np.full(len(g), 1 / len(g)), size=B)
    stats = (w @ s) / (w @ n)
    return float(np.mean(values)), [float(x) for x in np.percentile(stats, [2.5, 97.5])]


def req(d):
    for N in GRID:
        if d[d.N == N].ok.mean() >= TARGET:
            return N
    return None


out = {}
for (ratio, H), d in df.groupby(["cost_ratio", "H"]):
    key = f"{ratio}_H{H}"
    st = d.drop_duplicates("state_id")
    r = dict(adequate=float(st.ref_converged.mean()), edge=float(st.boundary.mean()), near=float(st.near.mean()),
             K=float(st.K.mean()), req={}, req_fam={}, rows={}, diff={})
    Ksum = st.K.sum()
    for m in ("uniform", "seq_elim", "ocba"):
        dm = d[d.method == m]
        r["req"][m] = req(dm)
        r["req_fam"][m] = {f: req(dm[dm.family == f]) for f in FAMS}
        for N in GRID:
            x = dm[dm.N == N]
            share, ci = boot_mean(x.ok.values, x.item.values)
            r["rows"][f"{m}_{N}"] = dict(share=share, ci=ci, rpc=float(x.rollouts.sum() / Ksum),
                                         p_best=float(x.correct.mean()), p95=float(x.r_rel.quantile(.95)),
                                         used_over_budget=float((x.rollouts / (x.K * N)).mean()))
    # paired differences vs uniform
    u = d[d.method == "uniform"].set_index(["state_id", "N"])
    for m in ("seq_elim", "ocba"):
        o = d[d.method == m].set_index(["state_id", "N"])
        j = u[["item", "ok", "near"]].join(o[["ok"]], rsuffix="_m").reset_index()
        j["diff"] = j.ok_m - j.ok
        for stratum, jj in (("all", j), ("near", j[j.near]), ("clear", j[~j.near])):
            for N in GRID:
                x = jj[jj.N == N]
                mean, ci = boot_mean(x["diff"].values, x["item"].values)
                r["diff"][f"{m}_{stratum}_{N}"] = dict(mean=mean, ci=ci, n=int(len(x)))
    adq = d[d.ref_converged]
    r["adequate_only"] = {f"{m}_{N}": float(adq[(adq.method == m) & (adq.N == N)].ok.mean())
                          for m in ("uniform", "seq_elim", "ocba") for N in (100, 250, 500)}
    out[key] = r

fam_near = df[(df.cost_ratio == "base") & (df.H == 14)].drop_duplicates("state_id").groupby("family").near.mean().to_dict()
out["near_by_family_base_H14"] = {k: float(v) for k, v in fam_near.items()}
json.dump(out, open(os.path.join(RES, "revision_stats.json"), "w"), indent=1)
b = out["base_H14"]
print("base H14 req", b["req"], b["req_fam"])
for N in (25, 100, 250, 500, 1000):
    print(N, {m: (round(100 * b["rows"][f"{m}_{N}"]["share"], 1), [round(100 * c, 1) for c in b["rows"][f"{m}_{N}"]["ci"]], round(b["rows"][f"{m}_{N}"]["rpc"])) for m in ("uniform", "seq_elim", "ocba")})
for k in ("low_H14", "high_H14", "base_H7", "high_H7", "low_H7"):
    print(k, out[k]["req"], out[k]["req_fam"], "adequate", round(out[k]["adequate"], 3), "near", round(out[k]["near"], 3))
for m in ("seq_elim", "ocba"):
    print(m, {s: {N: (round(100 * b["diff"][f"{m}_{s}_{N}"]["mean"], 1), [round(100 * c, 1) for c in b["diff"][f"{m}_{s}_{N}"]["ci"]]) for N in (50, 100, 250, 500, 1000)} for s in ("all", "near", "clear")})
print("used/budget SE", {N: round(b["rows"][f"seq_elim_{N}"]["used_over_budget"], 2) for N in GRID})
print("H7 base SE-U at 1000", out["base_H7"]["diff"]["seq_elim_all_1000"])
print("near by family", out["near_by_family_base_H14"])
