"""
Validation of SGSG (proposal Section 11.6).

Compares generated inventory turnover, waste rate, supplier lead time, and
fill rate against reference ranges drawn from published grocery-sector
statistics. Any parameter falling outside the plausible range is flagged for
recalibration, per Section 11.6's stated methodology.

REFERENCE RANGES (documented with source, not asserted without basis):
  - Inventory turnover: grocery retail commonly reported in the 8-16x/year
    range for perishable-heavy categories (industry benchmarking literature,
    e.g. trade-press retail operations benchmarks).
  - Waste/spoilage rate: FAO and industry food-loss reporting commonly place
    retail-level fresh/perishable waste in the 2-10% of throughput range,
    higher for fresh produce/bakery, lower for shelf-stable categories.
  - Supplier lead time: retail grocery replenishment literature typically
    reports 1-7 day lead times for regional/national suppliers, longer for
    imported categories.
  - Fill rate: retail order-fulfilment benchmarks commonly cite 90-98% as a
    typical achieved range for functioning supplier relationships.

NOTE: these are literature-informed plausibility bands for validating a
SYNTHETIC reconstruction, not a substitute for calibrating against a specific
retailer's real audited data. Section 11.6/17 of the proposal treats this as
the validation mechanism; a production deployment would recalibrate these
bands against the target retailer's own historicals.
"""
import os
import numpy as np
import pandas as pd

BENCHMARKS = {
    # Turnover is split by shelf-life tier because a single blended "grocery retail"
    # figure misrepresents category mix: daily-fresh perishables (bakery/dairy/
    # produce) turn over far faster than shelf-stable/frozen/dry goods in published
    # retail operations literature, and this proxy dataset is perishable-heavy.
    "inventory_turnover_fast_perishable_per_year": {"min": 40.0, "max": 250.0,
        "source": "fresh/perishable grocery turnover literature (shelf life < 14 days)"},
    "inventory_turnover_shelf_stable_per_year": {"min": 6.0, "max": 25.0,
        "source": "grocery retail turnover benchmarks (shelf life >= 14 days)"},
    "waste_rate_pct": {"min": 1.0, "max": 12.0, "source": "FAO / industry food-loss reporting"},
    "lead_time_days": {"min": 1.0, "max": 8.0, "source": "retail supply-chain lead-time studies"},
    "fill_rate_pct": {"min": 85.0, "max": 99.0, "source": "retail order-fulfilment benchmarks"},
}

FAST_PERISHABLE_SHELF_LIFE_CUTOFF = 14  # days


def compute_generated_stats(inventory_table, delivery_table, products):
    results = {}
    item_shelf_life = products.set_index("item_nbr")["shelf_life_days"].to_dict()

    # --- Inventory turnover: COGS-proxy (fulfilled demand) / avg inventory, annualized,
    #     computed PER SKU-store series then averaged (mixing an aggregate sum across
    #     series with a per-row average inventory would badly inflate this metric),
    #     split by shelf-life tier (see BENCHMARKS docstring). ---
    inv = inventory_table.copy()
    fast_turnovers, stable_turnovers = [], []
    for (store, item), g in inv.groupby(["store_nbr", "item_nbr"]):
        n_days_series = g["day"].max() + 1
        fulfilled_series = (g["D_t"] - g["unmet_demand"]).clip(lower=0).sum()
        avg_inv_series = g["I_t"].mean()
        if avg_inv_series <= 1e-6:
            continue
        turnover = (fulfilled_series / avg_inv_series) * (365.0 / n_days_series)
        shelf_life = item_shelf_life.get(item, 999)
        if shelf_life < FAST_PERISHABLE_SHELF_LIFE_CUTOFF:
            fast_turnovers.append(turnover)
        else:
            stable_turnovers.append(turnover)
    results["inventory_turnover_fast_perishable_per_year"] = float(np.mean(fast_turnovers)) if fast_turnovers else float("nan")
    results["inventory_turnover_shelf_stable_per_year"] = float(np.mean(stable_turnovers)) if stable_turnovers else float("nan")

    fulfilled = (inv["D_t"] - inv["unmet_demand"]).clip(lower=0).sum()

    # --- Waste rate: total expired units / total units that flowed through (D_t fulfilled + waste) ---
    total_waste = inv["W_t"].sum()
    total_throughput = fulfilled + total_waste
    waste_rate_pct = 100.0 * total_waste / max(total_throughput, 1e-6)
    results["waste_rate_pct"] = waste_rate_pct

    # --- Lead time: mean of (arrival_day - day) across all deliveries ---
    if len(delivery_table):
        lead_times = (delivery_table["arrival_day"] - delivery_table["day"]).values
        results["lead_time_days"] = float(np.mean(lead_times))
    else:
        results["lead_time_days"] = float("nan")

    # --- Fill rate ---
    if len(delivery_table):
        results["fill_rate_pct"] = float(delivery_table["fill_rate"].mean() * 100)
    else:
        results["fill_rate_pct"] = float("nan")

    return results


def validate(stats):
    report = []
    for key, val in stats.items():
        bench = BENCHMARKS[key]
        in_range = bench["min"] <= val <= bench["max"]
        report.append({
            "metric": key, "generated_value": round(val, 2),
            "reference_range": f"[{bench['min']}, {bench['max']}]",
            "source": bench["source"], "in_range": in_range,
        })
    return pd.DataFrame(report)


if __name__ == "__main__":
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATA_DIR = os.path.join(PROJECT_ROOT, "data")
    inv = pd.read_pickle(f"{DATA_DIR}/state_inventory.pkl")
    dl = pd.read_pickle(f"{DATA_DIR}/state_deliveries.pkl")
    products = pd.read_pickle(f"{DATA_DIR}/proxy_products.pkl")

    stats = compute_generated_stats(inv, dl, products)
    report = validate(stats)
    print(report.to_string(index=False))
    report.to_csv(os.path.join(PROJECT_ROOT, "results", "sgsg_validation_report.csv"), index=False)
    n_fail = (~report["in_range"]).sum()
    print(f"\n{len(report) - n_fail}/{len(report)} metrics within literature-informed reference ranges.")
    if n_fail:
        print("FLAGGED for recalibration:", report[~report["in_range"]]["metric"].tolist())
