"""Re-create notebook-2 stage 3 (original 500 states, OCBA, 320k reference) for confidence intervals."""
import os, sys, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, ROOT)
import pandas as pd
from multiprocessing import Pool
from srep.config import PROTOCOL
from srep.states import load_or_build
from srep import experiment2 as X
if __name__ == "__main__":
    orig = load_or_build("benchmark")
    for ratio in ("base", "low", "high"):
        out = os.path.join(ROOT, "results", f"nb02_original_{ratio}.csv")
        if os.path.exists(out): continue
        jobs = [(rec, H, ratio) for H in PROTOCOL.horizons for rec in orig]
        t = time.time()
        with Pool(os.cpu_count()) as p:
            res = list(p.imap_unordered(X.original_worker, jobs, chunksize=2))
        pd.DataFrame([r for rows in res for r in rows]).to_csv(out, index=False)
        print(ratio, f"{time.time()-t:.0f}s", flush=True)
