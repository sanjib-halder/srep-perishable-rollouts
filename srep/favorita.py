"""
Raw Favorita (Kaggle 'favorita-grocery-sales-forecasting') -> perishable store-item daily panel.

train.csv lists only store-item-days with recorded sales, so a missing day
inside a store-item's active range is a zero-sales day. unit_sales can be
fractional (items sold by weight) or negative (returns); the panel rounds to
whole units and floors at zero, because the inventory model counts units.

Only BREAD/BAKERY, PRODUCE and DAIRY are kept (protocol scope). The result is
cached as data/favorita_perishable.pkl so the 4-5 GB CSV is read only once.
"""
import os
import pickle
import time
import numpy as np
import pandas as pd

FAMILIES = ("BREAD/BAKERY", "PRODUCE", "DAIRY")
SHELF_LIFE = {"BREAD/BAKERY": 3, "PRODUCE": 5, "DAIRY": 10}   # twin's per-family shelf lives


def load_perishable_panel(fav_dir, cache_path, start="2015-08-01", end="2017-08-15", chunksize=5_000_000, log=print):
    if os.path.exists(cache_path):
        with open(cache_path, "rb") as f:
            return pickle.load(f)
    items = pd.read_csv(os.path.join(fav_dir, "items.csv"))
    keep = items[items.family.isin(FAMILIES)].set_index("item_nbr")
    keep_ids = set(keep.index)
    t0 = time.time()
    parts = []
    reader = pd.read_csv(os.path.join(fav_dir, "train.csv"), usecols=["date", "store_nbr", "item_nbr", "unit_sales"],
                         dtype={"store_nbr": "int16", "item_nbr": "int32", "unit_sales": "float32"},
                         parse_dates=["date"], chunksize=chunksize)
    n_rows = 0
    for i, ch in enumerate(reader):
        n_rows += len(ch)
        ch = ch[(ch.date >= start) & (ch.date <= end) & ch.item_nbr.isin(keep_ids)]
        if len(ch):
            parts.append(ch)
        log(f"  chunk {i+1}: {n_rows/1e6:.0f}M rows read, {sum(len(p) for p in parts)/1e6:.2f}M kept ({time.time()-t0:.0f}s)")
    df = pd.concat(parts, ignore_index=True)
    df["unit_sales"] = np.maximum(np.rint(df.unit_sales.values), 0).astype(np.int32)
    df = df.groupby(["store_nbr", "item_nbr", "date"], as_index=False)["unit_sales"].sum()

    days = pd.date_range(start, end, freq="D")
    day_idx = {d: i for i, d in enumerate(days)}
    series, meta = {}, []
    for (s, it), g in df.groupby(["store_nbr", "item_nbr"]):
        idx = g.date.map(day_idx).values
        first, last = int(idx.min()), int(idx.max())
        arr = np.zeros(len(days), np.int32)
        arr[idx] = g.unit_sales.values
        series[(int(s), int(it))] = arr
        active = arr[first:last + 1]
        meta.append(dict(store_nbr=int(s), item_nbr=int(it), family=keep.loc[it, "family"],
                         item_class=int(keep.loc[it, "class"]), perishable_flag=int(keep.loc[it, "perishable"]),
                         first=first, last=last, active_days=last - first + 1,
                         share_selling=float((active > 0).mean()), mean_sales=float(active.mean())))
    panel = dict(days=days, series=series, meta=pd.DataFrame(meta), rows_read=n_rows)
    with open(cache_path, "wb") as f:
        pickle.dump(panel, f)
    return panel
