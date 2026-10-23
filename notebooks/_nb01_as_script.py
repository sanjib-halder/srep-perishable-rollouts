import os, sys, json, time, pickle, platform, hashlib
import numpy as np
import pandas as pd

# ---- set this if the automatic detection fails (path to the folder that contains srep/, sgsg/, data/) ----
SREP_ROOT = ""        # e.g. "/path/to/srep"

def _find_root():
    if SREP_ROOT:
        return os.path.abspath(os.path.expanduser(SREP_ROOT))
    try:
        here = os.path.abspath(os.getcwd())
    except PermissionError:
        raise PermissionError(
            "macOS is blocking access to the current folder (common for cloud-synced folders such as Google Drive). "
            "Either set SREP_ROOT above, run `python3 _nb01_as_script.py` from Terminal, or give the app running "
            "Jupyter access in System Settings > Privacy & Security > Files and Folders / Full Disk Access.")
    for cand in (here, os.path.dirname(here)):
        if os.path.exists(os.path.join(cand, "srep", "engine.py")):
            return cand
    raise FileNotFoundError("Could not find the srep project; set SREP_ROOT at the top of this cell.")

ROOT = _find_root()
try:
    os.listdir(ROOT)
except PermissionError:
    raise PermissionError(f"macOS blocks reading {ROOT}. Grant the Jupyter app Full Disk Access, run the .py from Terminal, "
                          "or move the srep folder out of the synced drive (e.g. to ~/srep).")
sys.path.insert(0, ROOT)
DATA, RES = os.path.join(ROOT, "data"), os.path.join(ROOT, "results")
os.makedirs(RES, exist_ok=True)

from srep.config import PROTOCOL, protocol_hash
from srep.scenarios import load_data, DemandModel
from srep.engine import SkuSpec, State
from sgsg.generator import (run_sgsg_for_sku_store, SUPPLIERS, FAMILY_SUPPLIER, sample_lead_time,
                            sample_delivery, BootstrapPolicy, Batch, warehouse_capacity_for_sku)

SUMMARY = []          # lines collected for results/nb01_summary.md
def note(*a):
    s = " ".join(str(x) for x in a); print(s); SUMMARY.append(s)

note("## Environment")
note(f"python {platform.python_version()} | numpy {np.__version__} | pandas {pd.__version__} | {platform.platform()}")
note(f"protocol hash {protocol_hash()}")

SALES_PATH = os.path.join(DATA, "proxy_sales.pkl")
assert os.path.exists(SALES_PATH), f"Copy proxy_sales.pkl into {DATA}"
sales = pd.read_pickle(SALES_PATH)
products, calendar = load_data()

note("\n## 1. Sales panel")
note(f"file: {SALES_PATH} ({os.path.getsize(SALES_PATH)/1e6:.1f} MB) | sha256[:12] "
     f"{hashlib.sha256(open(SALES_PATH,'rb').read()).hexdigest()[:12]}")
note(f"shape {sales.shape}")
note("columns/dtypes: " + ", ".join(f"{c}:{t}" for c, t in sales.dtypes.astype(str).items()))
need = {"store_nbr", "item_nbr", "date", "unit_sales"}
missing = need - set(sales.columns)
assert not missing, f"sales panel lacks columns {missing}; send me this output"
sales["date"] = pd.to_datetime(sales["date"])
if "family" not in sales.columns:
    sales = sales.merge(products[["item_nbr", "family"]], on="item_nbr", how="left")
note(f"dates {sales.date.min().date()} .. {sales.date.max().date()} ({sales.date.nunique()} days)")
note(f"stores {sales.store_nbr.nunique()} | items {sales.item_nbr.nunique()} | store-items {sales.groupby(['store_nbr','item_nbr']).ngroups}")
note(f"missing values per column: {sales[list(need)].isna().sum().to_dict()}")
note(f"unit_sales: min {sales.unit_sales.min():.2f} | mean {sales.unit_sales.mean():.2f} | max {sales.unit_sales.max():.2f} | "
     f"share zero {(sales.unit_sales==0).mean():.3f} | share negative {(sales.unit_sales<0).mean():.4f} | "
     f"share non-integer {(sales.unit_sales % 1 != 0).mean():.4f}")
fam = pd.DataFrame({"rows": sales.groupby("family").size(),
                    "store_items": sales.drop_duplicates(["store_nbr", "item_nbr"]).groupby("family").size()})
note("by family:\n" + fam.to_string())
lens = sales.groupby(["store_nbr", "item_nbr"]).size()
note(f"series length per store-item: min {lens.min()} | median {int(lens.median())} | max {lens.max()}")
cal_dates = set(pd.to_datetime(calendar["date"]).dt.normalize())
note(f"sales dates covered by calendar: {sales.date.dt.normalize().isin(cal_dates).mean():.4f}")

dm = DemandModel(products, calendar)
cal = calendar.copy(); cal["date"] = pd.to_datetime(cal["date"]).dt.normalize()
cal_idx = dict(zip(cal["date"], range(len(cal))))
per = sales[sales.family.isin(PROTOCOL.families)].copy()
per["t"] = per["date"].dt.normalize().map(cal_idx)

def model_mean(item, t):
    return float(dm.mean_demand(item, int(t), 1)[0])

rows = []
for (s, i), g in per.groupby(["store_nbr", "item_nbr"]):
    g = g.dropna(subset=["t"])
    if len(g) < 60:
        continue
    exp = np.array([model_mean(i, t) for t in g["t"].values[:: max(1, len(g)//60)]])
    obs = g["unit_sales"].values[:: max(1, len(g)//60)]
    rows.append(dict(store_nbr=s, item_nbr=i, family=g.family.iloc[0], obs_mean=obs.mean(), model_mean=exp.mean(),
                     ratio=obs.mean() / max(exp.mean(), 1e-9),
                     corr=np.corrcoef(obs, exp)[0, 1] if obs.std() > 0 and exp.std() > 0 else np.nan,
                     disp=g["unit_sales"].var() / max(g["unit_sales"].mean(), 1e-9)))
fit = pd.DataFrame(rows)
note("\n## 2. Store-level sales vs twin demand model (perishable store-items)")
note(f"store-items checked: {len(fit)}")
note("ratio observed/model mean, quantiles: " + ", ".join(f"q{int(q*100)}={fit.ratio.quantile(q):.2f}" for q in (0.05, .25, .5, .75, .95)))
note("correlation of daily pattern (median): " + f"{fit['corr'].median():.2f}")
note("variance/mean of daily sales (Poisson = 1), quantiles: " + ", ".join(f"q{int(q*100)}={fit.disp.quantile(q):.2f}" for q in (.25, .5, .75)))
by_store = fit.groupby("store_nbr").ratio.median()
note(f"store-level median ratio: min {by_store.min():.2f} | median {by_store.median():.2f} | max {by_store.max():.2f}")
SCALE_NEEDED = bool((fit.ratio.quantile(.75) > 1.25) or (fit.ratio.quantile(.25) < 0.8))
note(f"store scaling needed (IQR of ratio outside 0.8–1.25): {SCALE_NEEDED}")

def replay_with_snapshots(demand_series, shelf_life_days, family, n_days, seed, snap_days=()):
    '''Line-for-line copy of sgsg.generator.run_sgsg_for_sku_store that also records the
    start-of-day state (stock by remaining life, orders by days-to-arrival) on snap_days.'''
    rng = np.random.default_rng(seed)
    supplier = SUPPLIERS[FAMILY_SUPPLIER[family]]
    avg_daily_demand = max(1.0, np.mean(demand_series[: min(30, len(demand_series))]))
    base_lead_time = sample_lead_time(supplier, rng)
    policy = BootstrapPolicy(avg_daily_demand, base_lead_time, shelf_life_days)
    inventory = int(avg_daily_demand * base_lead_time * 1.6)
    batches = [Batch(inventory, arrival_day=0, expiry_day=shelf_life_days)]
    pending_orders = []
    rows, snaps, snap_set = [], {}, set(snap_days)
    for t in range(n_days):
        if t in snap_set:
            oh = np.zeros(shelf_life_days + 1, np.int64)
            for b in batches:
                oh[b.expiry_day - t] += b.qty
            L = 1 + max([d - t for d, _ in pending_orders], default=0)
            pp = np.zeros(max(L, 1), np.int64)
            for d, q in pending_orders:
                pp[d - t] += q
            snaps[t] = (oh, pp)
        D_t = int(demand_series[t])
        arrived_today = [q for (day, q) in pending_orders if day == t]
        for q in arrived_today:
            batches.append(Batch(q, arrival_day=t, expiry_day=t + shelf_life_days))
        pending_orders = [(day, q) for (day, q) in pending_orders if day != t]
        batches.sort(key=lambda b: b.expiry_day)
        remaining_demand = D_t
        for b in batches:
            if remaining_demand <= 0:
                break
            take = min(b.qty, remaining_demand); b.qty -= take; remaining_demand -= take
        unmet_demand = remaining_demand
        expired_qty = sum(b.qty for b in batches if b.expiry_day <= t)
        batches = [b for b in batches if b.expiry_day > t and b.qty > 0]
        inventory = sum(b.qty for b in batches)
        in_pipeline = sum(q for (_, q) in pending_orders)
        inventory_position = inventory + in_pipeline
        Q_t = policy.decide(inventory_position)
        Q_t = min(Q_t, warehouse_capacity_for_sku(avg_daily_demand, shelf_life_days) - inventory_position)
        Q_t = max(0, Q_t)
        if Q_t > 0:
            received, delay_days, fill_rate = sample_delivery(supplier, Q_t, rng)
            lead_time = sample_lead_time(supplier, rng) + delay_days
            pending_orders.append((t + lead_time, received))
        rows.append((D_t, unmet_demand, inventory, Q_t, expired_qty, in_pipeline))
    return np.array(rows), snaps

# seeds exactly as sgsg/build_state.py assigns them: 1000 + position in groupby order over ALL store-items
keys = list(sales.groupby(["store_nbr", "item_nbr"]).groups.keys())
SEED_OF = {k: 1000 + j for j, k in enumerate(keys)}
shelf = products.set_index("item_nbr")["shelf_life_days"].to_dict()
series = {k: g.sort_values("date") for k, g in sales[sales.family.isin(PROTOCOL.families)].groupby(["store_nbr", "item_nbr"])}

rng_check = np.random.default_rng(7)
check_keys = [list(series)[j] for j in rng_check.choice(len(series), size=min(200, len(series)), replace=False)]
t0 = time.time(); bad = 0
for k in check_keys:
    g = series[k]; d = g["unit_sales"].values; fam_k = g["family"].iloc[0]
    ref = run_sgsg_for_sku_store(d, shelf[k[1]], fam_k, len(d), SEED_OF[k])["panel"]
    mine, _ = replay_with_snapshots(d, shelf[k[1]], fam_k, len(d), SEED_OF[k])
    refa = ref[["D_t", "unmet_demand", "I_t", "Q_t", "W_t", "in_pipeline"]].values
    bad += int(not np.array_equal(refa, mine))
note("\n## 3. SGSG replay check")
note(f"replay == run_sgsg_for_sku_store on {len(check_keys)} random perishable store-items: mismatches = {bad} ({time.time()-t0:.1f}s)")
assert bad == 0, "Replay differs from SGSG -- stop and send me this output"

N_REPL = 3000          # replication states (≈ 333 per family × volume cell)
SEED_REPL = 2027_1022

note("\n## 4. Replication states")
vol = fit.set_index(["store_nbr", "item_nbr"])["obs_mean"] if len(fit) else None
meta = pd.DataFrame([dict(store_nbr=k[0], item_nbr=k[1], family=g["family"].iloc[0], n=len(g),
                          mean_sales=float(g["unit_sales"].mean())) for k, g in series.items()])
meta = meta[meta.n >= 120].copy()
meta["volume_tertile"] = meta.groupby("family")["mean_sales"].transform(
    lambda x: np.digitize(x, np.quantile(x, [1/3, 2/3])))
cells_ = [(f, v) for f in PROTOCOL.families for v in range(3)]
note(f"eligible store-items (>=120 days): {len(meta)} | items covered: {meta.item_nbr.nunique()} of "
     f"{products[products.family.isin(PROTOCOL.families)].shape[0]} perishable items")

rng = np.random.default_rng(SEED_REPL)
picks = []
for sid in range(N_REPL):
    f, v = cells_[sid % len(cells_)]
    pool = meta[(meta.family == f) & (meta.volume_tertile == v)]
    row = pool.iloc[int(rng.integers(len(pool)))]
    t = int(rng.integers(60, int(row.n) - 30))
    picks.append((sid, (row.store_nbr, row.item_nbr), t, f, v))

states, t0 = [], time.time()
by_key = {}
for sid, k, t, f, v in picks:
    by_key.setdefault(k, []).append((sid, t, f, v))
for k, lst in by_key.items():
    g = series[k]; d = g["unit_sales"].values
    _, snaps = replay_with_snapshots(d, shelf[k[1]], g["family"].iloc[0], len(d), SEED_OF[k], snap_days=[t for _, t, _, _ in lst])
    dates = g["date"].dt.normalize().values
    for sid, t, f, v in lst:
        oh, pp = snaps[t]
        last = np.nonzero(pp)[0]; pp = pp[: (last[-1] + 1 if len(last) else 1)]
        t_cal = cal_idx.get(pd.Timestamp(dates[t]))
        states.append(dict(state_id=100000 + sid, item=int(k[1]), store=int(k[0]), family=f, volume_tertile=int(v),
                           shelf_life=int(shelf[k[1]]), base_rate=float(products.set_index("item_nbr").loc[k[1], "base_demand_rate"]),
                           obs_mean_sales=float(meta.set_index(["store_nbr", "item_nbr"]).loc[k, "mean_sales"]),
                           date=str(pd.Timestamp(dates[t]).date()), source="sgsg_replay", disrupted=False,
                           state=State(int(t_cal), oh.copy(), pp.copy())))
states.sort(key=lambda r: r["state_id"])
note(f"built {len(states)} states from {len(by_key)} store-items, {len({r['item'] for r in states})} items, "
     f"{len({r['store'] for r in states})} stores ({time.time()-t0:.1f}s)")
assert all(r["state"].t0 is not None for r in states), "a decision date is missing from the calendar"

df_s = pd.DataFrame([dict(family=r["family"], vt=r["volume_tertile"], onhand=int(r["state"].onhand.sum()),
                          pipeline=int(r["state"].pipe.sum()), empty=int(r["state"].onhand.sum() == 0),
                          old=int(r["state"].onhand[:2].sum()), mean=r["obs_mean_sales"]) for r in states])
note("state profile by family (means; 'cover' = (onhand+pipeline)/mean daily sales):")
df_s["cover"] = (df_s["onhand"] + df_s["pipeline"]) / df_s["mean"].clip(lower=0.5)
note(df_s.groupby("family")[["onhand", "pipeline", "cover", "empty", "old"]].mean().round(2).to_string())

with open(os.path.join(DATA, "states_replication.pkl"), "wb") as fh:
    pickle.dump(states, fh)
note(f"saved data/states_replication.pkl")

path = os.path.join(RES, "nb01_summary.md")
with open(path, "w") as fh:
    fh.write("\n".join(SUMMARY))
fit.to_csv(os.path.join(RES, "nb01_demand_fit.csv"), index=False)
print("\nWrote", path, "and results/nb01_demand_fit.csv")