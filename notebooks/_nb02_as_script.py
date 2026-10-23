"""Notebook 2 as a script. Usage:  FAV_DIR=/path/to/favorita/2017 python3 _nb02_as_script.py"""
def main():
    import os, sys, json, time, pickle, platform
    import numpy as np
    import pandas as pd
    from multiprocessing import Pool

    # ---------------- settings ----------------
    SREP_ROOT = ""   # folder containing srep/, sgsg/, data/ ; leave "" to detect automatically
    FAV_DIR = ""     # folder containing the raw Favorita items.csv and train.csv (your "2017" folder)
    WORKERS = os.cpu_count()
    N_REPL = int(os.environ.get("N_REPL", 3000))
    TEST_LIMIT = int(os.environ.get("NB02_TEST_LIMIT", 0))   # developer testing only; leave 0
    # ------------------------------------------

    def _find_root():
        if SREP_ROOT:
            return os.path.abspath(os.path.expanduser(SREP_ROOT))
        here = os.path.abspath(os.getcwd())
        for c in (here, os.path.dirname(here)):
            if os.path.exists(os.path.join(c, "srep", "engine.py")):
                return c
        raise FileNotFoundError("set SREP_ROOT")
    ROOT = _find_root()
    sys.path.insert(0, ROOT)
    os.environ["PYTHONPATH"] = ROOT + os.pathsep + os.environ.get("PYTHONPATH", "")
    DATA, RES = os.path.join(ROOT, "data"), os.path.join(ROOT, "results")
    FAV_DIR = os.path.abspath(os.path.expanduser(FAV_DIR or os.environ.get("FAV_DIR", "")))
    assert os.path.exists(os.path.join(FAV_DIR, "train.csv")), f"Set FAV_DIR to the folder with items.csv and train.csv (got {FAV_DIR!r})"

    from srep.config import PROTOCOL, protocol_hash
    from srep.scenarios import load_data
    from srep.states import load_or_build
    from srep.favorita import load_perishable_panel, SHELF_LIFE
    from srep import experiment2 as X

    S = []
    def note(*a):
        s = " ".join(str(x) for x in a); print(s, flush=True); S.append(s)
    note("# Notebook 2 summary (amendment A11 — added after review)")
    note(f"python {platform.python_version()} | numpy {np.__version__} | pandas {pd.__version__} | {platform.platform()} | workers {WORKERS}")
    note(f"protocol hash {protocol_hash()} | started {time.strftime('%Y-%m-%d %H:%M')}")

    def pool_map(fn, jobs, label):
        t0, out = time.time(), []
        with Pool(WORKERS) as p:
            for i, r in enumerate(p.imap_unordered(fn, jobs, chunksize=2)):
                out.append(r)
                if (i + 1) % max(1, len(jobs) // 10) == 0:
                    print(f"  {label}: {i+1}/{len(jobs)} ({time.time()-t0:.0f}s)", flush=True)
        return out, time.time() - t0

    panel = load_perishable_panel(FAV_DIR, os.path.join(DATA, "favorita_perishable.pkl"))
    m = panel["meta"]
    note("\n## 1. Raw Favorita perishable panel")
    note(f"days {panel['days'][0].date()} .. {panel['days'][-1].date()} | train.csv rows read {panel['rows_read']:,}")
    note(f"store-items {len(m)} | stores {m.store_nbr.nunique()} | items {m.item_nbr.nunique()}")
    note(m.groupby("family").agg(store_items=("item_nbr", "size"), items=("item_nbr", "nunique"),
          mean_sales=("mean_sales", "median"), share_selling=("share_selling", "median")).round(2).to_string())
    disp = []
    for k, arr in list(panel["series"].items())[:: max(1, len(panel["series"]) // 400)]:
        a = arr[m.set_index(["store_nbr", "item_nbr"]).loc[k, "first"]:]
        if a.mean() > 0:
            disp.append(a.var() / a.mean())
    note("variance/mean of daily sales (Poisson = 1), quantiles: " +
         ", ".join(f"q{int(q*100)}={np.quantile(disp, q):.2f}" for q in (.25, .5, .75)))

    products, _ = load_data()
    family_price = products[products.family.isin(SHELF_LIFE)].groupby("family")["unit_price"].median().to_dict()
    path = os.path.join(DATA, "states_favorita_replication.pkl")
    note("\n## 2. Replication states")
    note("family median prices used (Favorita has no prices): " + ", ".join(f"{k} {v:.2f}" for k, v in family_price.items()))
    if os.path.exists(path):
        repl = pickle.load(open(path, "rb"))
    else:
        t0 = time.time()
        repl = X.build_replication_states(panel, N_REPL, seed=2027_1023, family_price=family_price, log=note)
        pickle.dump(repl, open(path, "wb"))
        note(f"built in {time.time()-t0:.0f}s")
    note(f"states {len(repl)} | store-items {len({(r['store'], r['item']) for r in repl})} | items {len({r['item'] for r in repl})} | "
         f"stores {len({r['store'] for r in repl})} | dates {min(r['date'] for r in repl)} .. {max(r['date'] for r in repl)}")
    HIST = {(r["store"], r["item"]): panel["series"][(r["store"], r["item"])] for r in repl}

    orig = load_or_build("benchmark")
    if TEST_LIMIT:
        orig = orig[:TEST_LIMIT]
    note("\n## 3. Original 500 states (twin demand) with OCBA and extended reference")
    for ratio in ("base", "low", "high"):
        out = os.path.join(RES, f"nb02_original_{ratio}.csv")
        if os.path.exists(out):
            continue
        jobs = [(rec, H, ratio) for H in PROTOCOL.horizons for rec in orig]
        res, secs = pool_map(X.original_worker, jobs, f"original/{ratio}")
        pd.DataFrame([r for rows in res for r in rows]).to_csv(out, index=False)
        note(f"original/{ratio}: {len(jobs)} state-horizons in {secs:.0f}s")

    note("\n## 4. Replication (raw Favorita, empirical demand)")
    plan = [("base", (7, 14)), ("low", (14,)), ("high", (14,))]
    for ratio, Hs in plan:
        out = os.path.join(RES, f"nb02_replication_{ratio}.csv")
        if os.path.exists(out):
            continue
        jobs = [(rec, HIST[(rec["store"], rec["item"])], H, ratio) for H in Hs for rec in repl]
        res, secs = pool_map(X.replication_worker, jobs, f"replication/{ratio}")
        pd.DataFrame([r for rows in res for r in rows]).to_csv(out, index=False)
        note(f"replication/{ratio}: {len(jobs)} state-horizons in {secs:.0f}s")

    out = os.path.join(RES, "nb02_widegrid.csv")
    if not os.path.exists(out):
        rng = np.random.default_rng(5)
        jobs = [("original", orig[i], None, 14) for i in rng.choice(len(orig), min(100, len(orig)), replace=False)]
        jobs += [("replication", repl[i], HIST[(repl[i]["store"], repl[i]["item"])], 14) for i in rng.choice(len(repl), min(100, len(repl)), replace=False)]
        res, secs = pool_map(X.widegrid_worker, jobs, "widegrid")
        pd.DataFrame(res).to_csv(out, index=False)

    out = os.path.join(RES, "nb02_timing.json")
    if not os.path.exists(out):
        jobs = [(orig[i % len(orig)], 14, 1000) for i in range(TEST_LIMIT * 10 if TEST_LIMIT else 50_000)]
        runs = []
        for rep in range(3):
            t0 = time.time()
            with Pool(WORKERS) as p:
                list(p.imap_unordered(X.timing_worker, jobs, chunksize=50))
            runs.append(time.time() - t0)
            print(f"  timing run {rep+1}: {runs[-1]:.1f}s", flush=True)
        json.dump(dict(decisions=len(jobs), N=1000, H=14, workers=WORKERS, seconds=runs,
                       includes="problem build + candidate generation + scenario generation + simulation + selection"),
                  open(out, "w"), indent=2)

    def req(g):
        for N in PROTOCOL.rollout_grid:
            if (g[g.N == N].r_rel <= 0.005).mean() >= 0.95:
                return str(N)
        return ">1000"

    def section(df, title):
        note(f"\n### {title}")
        st = df.drop_duplicates(["state_id", "H", "cost_ratio"])
        note("reference adequate: " + ", ".join(f"{r}/H{h} {g.ref_converged.mean():.3f}" for (r, h), g in st.groupby(["cost_ratio", "H"])) +
             " | candidate-edge: " + ", ".join(f"{r}/H{h} {g.boundary.mean():.3f}" for (r, h), g in st.groupby(["cost_ratio", "H"])) +
             " | near-tied: " + ", ".join(f"{r}/H{h} {(g.margin_rel <= .005).mean():.3f}" for (r, h), g in st.groupby(["cost_ratio", "H"])))
        for (r, h), g in df.groupby(["cost_ratio", "H"]):
            t = g.groupby(["method", "N"]).agg(ok=("r_rel", lambda x: (x <= .005).mean()), p95=("r_rel", lambda x: x.quantile(.95)),
                                               rpc=("rollouts", "sum")).reset_index()
            t["rpc"] = t["rpc"] / g.drop_duplicates("state_id").K.sum()
            wide = t.pivot(index="N", columns="method", values="ok").round(3)
            rpc = t.pivot(index="N", columns="method", values="rpc").round(0)
            note(f"\n{title} | ratio {r} | H {h} | n states {g.state_id.nunique()}")
            note("share of states with regret <= 0.5%:\n" + wide.to_string())
            note("rollouts used per candidate (ratio of totals):\n" + rpc.to_string())
            note("N required (>=95% within 0.5%): " + " | ".join(
                f"{m}: all {req(g[g.method == m])}, " + ", ".join(f"{f[:4]} {req(g[(g.method == m) & (g.family == f)])}" for f in SHELF_LIFE)
                for m in X.METHODS))
            adq = g[g.ref_converged]
            note("adequate-reference subset, share ok at N=100/250/500: " + " | ".join(
                f"{m}: " + "/".join(f"{(adq[(adq.method == m) & (adq.N == N)].r_rel <= .005).mean():.3f}" for N in (100, 250, 500))
                for m in X.METHODS))

    O = pd.concat([pd.read_csv(os.path.join(RES, f"nb02_original_{r}.csv")) for r in ("base", "low", "high")])
    section(O, "Original 500 states (twin demand)")
    R = pd.concat([pd.read_csv(os.path.join(RES, f"nb02_replication_{r}.csv")) for r in ("base", "low", "high")])
    section(R, "Replication on raw Favorita (empirical demand)")
    note("replication demand CV (std/mean over trailing 26 weeks), quantiles: " +
         ", ".join(f"q{int(q*100)}={R.drop_duplicates('state_id').demand_cv.quantile(q):.2f}" for q in (.25, .5, .75)))

    W = pd.read_csv(os.path.join(RES, "nb02_widegrid.csv"))
    note("\n### 5. Wider-grid check (gap of best candidate to best of a 24-point grid, relative to J*)")
    note(W.groupby("set").agg(n=("gap_rel", "size"), median=("gap_rel", "median"), p95=("gap_rel", lambda x: x.quantile(.95)),
                              max=("gap_rel", "max"), share_over_0_5pct=("gap_rel", lambda x: (x > .005).mean()),
                              grid_best_outside_range=("grid_best_outside_set_range", "mean")).round(4).to_string())

    T = json.load(open(os.path.join(RES, "nb02_timing.json")))
    note("\n### 6. Measured end-to-end timing")
    note(f"{T['decisions']:,} decisions, N=1000, H=14, {T['workers']} workers: runs {', '.join(f'{s:.1f}s' for s in T['seconds'])} "
         f"(median {np.median(T['seconds']):.1f}s); includes {T['includes']}")

    with open(os.path.join(RES, "nb02_summary.md"), "w") as fh:
        fh.write("\n".join(S))
    print("\nWrote results/nb02_summary.md — please send it.")


if __name__ == '__main__':
    main()
