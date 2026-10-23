"""
Notebook 3 (script) -- extra runs requested in review.

  A. Paired-variance OCBA added to uniform / sequential elimination / OCBA,
     twin states (500) and Favorita states (3,000), H = 14, cost ratios low/base/high.
  B. Resampling-window test: Favorita states, base costs, H = 14, 52-week window
     (vs the 26-week window of the main replication).
  C. Summary with item-clustered (and store-clustered) bootstrap intervals.

Usage (from Terminal, in srep/notebooks):
    FAV_DIR="/path/to/favorita/2017" python3 nb03_extra_runs.py
Each stage is skipped if its output exists; rerun the same command after an interruption.
Send me: results/nb03_summary.md  and  results/nb03_stats.json
"""
import os, sys, json, time, pickle, platform


def main():
    import numpy as np
    import pandas as pd
    from multiprocessing import Pool

    ROOT = os.environ.get("SREP_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, ROOT)
    os.environ["PYTHONPATH"] = ROOT + os.pathsep + os.environ.get("PYTHONPATH", "")
    DATA, RES = os.path.join(ROOT, "data"), os.path.join(ROOT, "results")
    WORKERS = int(os.environ.get("WORKERS", os.cpu_count()))
    TEST = int(os.environ.get("NB03_TEST_LIMIT", 0))         # developer testing only

    from srep.config import PROTOCOL, protocol_hash
    from srep.states import load_or_build
    from srep.favorita import load_perishable_panel
    from srep import experiment3 as X3
    from srep.report3 import summarise, to_markdown

    FAV_DIR = os.path.abspath(os.path.expanduser(os.environ.get("FAV_DIR", "")))
    panel = load_perishable_panel(FAV_DIR, os.path.join(DATA, "favorita_perishable.pkl"))   # cached by notebook 2
    repl = pickle.load(open(os.path.join(DATA, "states_favorita_replication.pkl"), "rb"))
    orig = load_or_build("benchmark")
    if TEST:
        repl, orig = repl[:TEST], orig[:TEST]
    HIST = {(r["store"], r["item"]): panel["series"][(r["store"], r["item"])] for r in repl}

    def pool_map(fn, jobs, label):
        t0, out = time.time(), []
        with Pool(WORKERS) as p:
            for i, r in enumerate(p.imap_unordered(fn, jobs, chunksize=2)):
                out.append(r)
                if (i + 1) % max(1, len(jobs) // 10) == 0:
                    print(f"  {label}: {i+1}/{len(jobs)} ({time.time()-t0:.0f}s)", flush=True)
        return out, time.time() - t0

    log = [f"# Notebook 3 summary", f"python {platform.python_version()} | numpy {np.__version__} | pandas {pd.__version__} | "
           f"workers {WORKERS} | protocol hash {protocol_hash()} | {time.strftime('%Y-%m-%d %H:%M')}"]

    # ---- A. twin states, four methods
    for ratio in ("base", "low", "high"):
        out = os.path.join(RES, f"nb03_original_{ratio}.csv")
        if not os.path.exists(out):
            res, secs = pool_map(X3.original_worker, [(r, 14, ratio) for r in orig], f"A twin/{ratio}")
            pd.DataFrame([x for rows in res for x in rows]).to_csv(out, index=False)
            log.append(f"A twin/{ratio}: {secs:.0f}s")

    # ---- A. Favorita states, four methods, 26-week window
    for ratio in ("base", "low", "high"):
        out = os.path.join(RES, f"nb03_replication_w26_{ratio}.csv")
        if not os.path.exists(out):
            jobs = [(r, HIST[(r["store"], r["item"])], 14, ratio, 182) for r in repl]
            res, secs = pool_map(X3.replication_worker, jobs, f"A favorita/{ratio}")
            pd.DataFrame([x for rows in res for x in rows]).to_csv(out, index=False)
            log.append(f"A favorita/{ratio}: {secs:.0f}s")

    # ---- B. 52-week window
    out = os.path.join(RES, "nb03_replication_w52_base.csv")
    if not os.path.exists(out):
        jobs = [(r, HIST[(r["store"], r["item"])], 14, "base", 364) for r in repl]
        res, secs = pool_map(X3.replication_worker, jobs, "B window52/base")
        pd.DataFrame([x for rows in res for x in rows]).to_csv(out, index=False)
        log.append(f"B window52/base: {secs:.0f}s")

    # ---- C. summary
    O = pd.concat([pd.read_csv(os.path.join(RES, f"nb03_original_{r}.csv")) for r in ("base", "low", "high")])
    R26 = pd.concat([pd.read_csv(os.path.join(RES, f"nb03_replication_w26_{r}.csv")) for r in ("base", "low", "high")])
    R52 = pd.read_csv(os.path.join(RES, "nb03_replication_w52_base.csv"))
    stats = {}
    stats.update(summarise(O, "twin"))
    stats.update(summarise(R26, "favorita_w26"))
    stats.update(summarise(R26[R26.cost_ratio == "base"], "favorita_w26_storecluster", cluster="store"))
    stats.update(summarise(R52, "favorita_w52"))
    wk = R52.drop_duplicates("state_id").weeks_available
    stats["window52_weeks_available"] = {f"q{q}": float(wk.quantile(q / 100)) for q in (5, 25, 50, 75, 95)}
    json.dump(stats, open(os.path.join(RES, "nb03_stats.json"), "w"), indent=1)
    log.append("\nweeks of history actually used with the 52-week window: " +
               ", ".join(f"{k} {v:.0f}" for k, v in stats["window52_weeks_available"].items()))
    log.append(to_markdown({k: v for k, v in stats.items() if isinstance(v, dict) and "rows" in v}))
    open(os.path.join(RES, "nb03_summary.md"), "w").write("\n".join(log))
    print("\n".join(log[:4]))
    print("\nWrote results/nb03_summary.md and results/nb03_stats.json -- please send both.")


if __name__ == "__main__":
    main()
