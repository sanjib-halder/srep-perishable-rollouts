"""
Applies SGSG (generator.py) across every store x SKU pair in the Favorita/M5
proxy panel to reconstruct the full latent operational state
(Section 11: relational schema -- Inventory, Purchase Orders, Suppliers,
Deliveries, Expiry Batches, Stockout Events).
"""
import os
import sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
import numpy as np
import pandas as pd
from sgsg.generator import run_sgsg_for_sku_store

DATA_DIR = os.path.join(PROJECT_ROOT, "data")


def build_full_state():
    sales = pd.read_pickle(f"{DATA_DIR}/proxy_sales.pkl")
    products = pd.read_pickle(f"{DATA_DIR}/proxy_products.pkl")

    all_panels, all_pos, all_deliveries, all_stockouts = [], [], [], []
    seed = 1000
    for (store, item), grp in sales.groupby(["store_nbr", "item_nbr"]):
        grp = grp.sort_values("date").reset_index(drop=True)
        family = grp["family"].iloc[0]
        shelf_life = int(products.loc[products.item_nbr == item, "shelf_life_days"].iloc[0])
        demand_series = grp["unit_sales"].values
        out = run_sgsg_for_sku_store(demand_series, shelf_life, family, len(demand_series), seed)
        seed += 1

        panel = out["panel"]
        panel["store_nbr"] = store
        panel["item_nbr"] = item
        panel["date"] = grp["date"].values

        for name, df in [("purchase_orders", out["purchase_orders"]),
                          ("deliveries", out["deliveries"]),
                          ("stockout_events", out["stockout_events"])]:
            if len(df) > 0:
                df = df.copy()
                df["store_nbr"] = store
                df["item_nbr"] = item

        all_panels.append(panel)
        if len(out["purchase_orders"]):
            po = out["purchase_orders"].copy(); po["store_nbr"] = store; po["item_nbr"] = item
            all_pos.append(po)
        if len(out["deliveries"]):
            dl = out["deliveries"].copy(); dl["store_nbr"] = store; dl["item_nbr"] = item
            all_deliveries.append(dl)
        if len(out["stockout_events"]):
            so = out["stockout_events"].copy(); so["store_nbr"] = store; so["item_nbr"] = item
            all_stockouts.append(so)

    inventory_table = pd.concat(all_panels, ignore_index=True)
    po_table = pd.concat(all_pos, ignore_index=True) if all_pos else pd.DataFrame()
    delivery_table = pd.concat(all_deliveries, ignore_index=True) if all_deliveries else pd.DataFrame()
    stockout_table = pd.concat(all_stockouts, ignore_index=True) if all_stockouts else pd.DataFrame()

    inventory_table.to_pickle(f"{DATA_DIR}/state_inventory.pkl")
    po_table.to_pickle(f"{DATA_DIR}/state_purchase_orders.pkl")
    delivery_table.to_pickle(f"{DATA_DIR}/state_deliveries.pkl")
    stockout_table.to_pickle(f"{DATA_DIR}/state_stockouts.pkl")

    return inventory_table, po_table, delivery_table, stockout_table


if __name__ == "__main__":
    inv, po, dl, so = build_full_state()
    print("Reconstructed relational schema (Section 11.5):")
    print(f"  Inventory panel:   {inv.shape}")
    print(f"  Purchase orders:   {po.shape}")
    print(f"  Deliveries:        {dl.shape}")
    print(f"  Stockout events:   {so.shape}")
    print("\nSample inventory rows:")
    print(inv.head())
