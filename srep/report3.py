"""Summary tables for notebook 3, with item-clustered bootstrap intervals."""
import json
import numpy as np
import pandas as pd

THR, TARGET, B = 0.005, 0.95, 2000
GRID = (10, 25, 50, 100, 250, 500, 1000)
FAMS = ("BREAD/BAKERY", "PRODUCE", "DAIRY")
METHODS = ("uniform", "seq_elim", "ocba", "ocba_paired")


def boot(values, items, rng):
    g = pd.DataFrame({"v": values, "i": items}).groupby("i")["v"].agg(["sum", "count"])
    w = rng.multinomial(len(g), np.full(len(g), 1 / len(g)), size=B)
    st = (w @ g["sum"].values) / (w @ g["count"].values)
    return float(np.mean(values)), [float(v) for v in np.percentile(st, [2.5, 97.5])]


def req(d):
    for N in GRID:
        if (d[d.N == N].r_rel <= THR).mean() >= TARGET:
            return N
    return None


def summarise(df, label, cluster="item", seed=2026):
    rng = np.random.default_rng(seed)
    df = df.copy()
    df["ok"] = (df.r_rel <= THR).astype(float)
    df["near"] = df.margin_rel <= THR
    out = {}
    for (ratio, H), d in df.groupby(["cost_ratio", "H"]):
        st = d.drop_duplicates("state_id")
        Ks = st.K.sum()
        r = dict(n=int(len(st)), items=int(st[cluster].nunique()), adequate=float(st.ref_converged.mean()),
                 edge=float(st.boundary.mean()), near=float(st.near.mean()), K_mean=float(st.K.mean()),
                 K_min=int(st.K.min()), K_max=int(st.K.max()), req={}, req_fam={}, rows={}, diff={})
        for m in METHODS:
            dm = d[d.method == m]
            r["req"][m] = req(dm)
            r["req_fam"][m] = {f: req(dm[dm.family == f]) for f in FAMS}
            for N in GRID:
                x = dm[dm.N == N]
                s, ci = boot(x.ok.values, x[cluster].values, rng)
                r["rows"][f"{m}_{N}"] = dict(share=s, ci=ci, rpc=float(x.rollouts.sum() / Ks))
        u = d[d.method == "uniform"].set_index(["state_id", "N"])
        for m in METHODS[1:]:
            o = d[d.method == m].set_index(["state_id", "N"])
            j = u[[cluster, "ok", "near"]].join(o[["ok"]], rsuffix="_m").reset_index()
            j["diff"] = j.ok_m - j.ok
            for stratum, jj in (("all", j), ("near", j[j.near]), ("clear", j[~j.near])):
                for N in GRID:
                    x = jj[jj.N == N]
                    mval, ci = boot(x["diff"].values, x[cluster].values, rng)
                    r["diff"][f"{m}_{stratum}_{N}"] = dict(mean=mval, ci=ci, n=int(len(x)))
        out[f"{label}|{ratio}|H{H}"] = r
    return out


def to_markdown(stats):
    L = []
    rq = lambda v: ">1000" if v is None else str(v)
    for key, r in stats.items():
        L.append(f"\n### {key}  (states {r['n']}, clusters {r['items']}, K {r['K_min']}-{r['K_max']} mean {r['K_mean']:.1f}, "
                 f"adequate {r['adequate']:.3f}, edge {r['edge']:.3f}, near-tied {r['near']:.3f})")
        L.append("N required: " + " | ".join(f"{m} {rq(r['req'][m])} ({', '.join(f[:4] + ' ' + rq(r['req_fam'][m][f]) for f in FAMS)})" for m in METHODS))
        L.append("share within 0.5% [item-clustered 95% CI] / rollouts per candidate:")
        for N in GRID:
            L.append(f"  N={N:4d}: " + " | ".join(
                f"{m} {100*r['rows'][f'{m}_{N}']['share']:.1f} [{100*r['rows'][f'{m}_{N}']['ci'][0]:.1f}, {100*r['rows'][f'{m}_{N}']['ci'][1]:.1f}] /{r['rows'][f'{m}_{N}']['rpc']:.0f}"
                for m in METHODS))
        L.append("paired difference vs uniform, all states (points, CI):")
        for m in METHODS[1:]:
            L.append(f"  {m}: " + " | ".join(
                f"N={N} {100*r['diff'][f'{m}_all_{N}']['mean']:+.1f} [{100*r['diff'][f'{m}_all_{N}']['ci'][0]:.1f}, {100*r['diff'][f'{m}_all_{N}']['ci'][1]:.1f}]"
                for N in (50, 100, 250, 500, 1000)))
    return "\n".join(L)
