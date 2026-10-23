"""
Stochastic Grocery Store Generator (SGSG)
==========================================
Implements G = (S, T, Theta) as specified in Research_Proposal_Revised.docx
Section 11.2-11.4:

Generative sequence per SKU-store-period (matches the DBN in Figure 1):
  Weather, Holiday  -->  Demand D_t
                    -->  Inventory I_t  (flow eq., Section 11.3)
                    -->  Reorder Trigger
                    -->  Purchase Order Q_t   (BOOTSTRAP POLICY -- not DC^2T)
                    -->  Supplier assignment / lead time
                    -->  Delivery outcome (fill rate, delay)
                    -->  Inventory I_{t+1}

The bootstrap policy (an (s,S) heuristic) exists ONLY to produce a
historically plausible purchase-order trace so SGSG is not circular
(Section 11.2). DC^2T's reasoning/RL modules replace this policy later,
during twin-based training and evaluation (twin/digital_twin.py).
"""
import numpy as np
import pandas as pd
from dataclasses import dataclass, field


@dataclass
class SupplierProfile:
    name: str
    mean_lead_time: float
    std_lead_time: float
    reliability: float      # in (0,1]; drives delay probability and fill rate
    base_fill_rate: float


# Theta: calibration seeds. Flagged per Section 11.3 as seeds, not sourced
# ground truth -- validated in sgsg/validation.py and swept in eval/sensitivity.py
SUPPLIERS = [
    SupplierProfile("S1-Regional", mean_lead_time=2.0, std_lead_time=0.5, reliability=0.97, base_fill_rate=0.98),
    SupplierProfile("S2-National", mean_lead_time=3.5, std_lead_time=1.0, reliability=0.93, base_fill_rate=0.95),
    SupplierProfile("S3-Import", mean_lead_time=6.0, std_lead_time=2.0, reliability=0.87, base_fill_rate=0.90),
]

FAMILY_SUPPLIER = {
    "BREAD/BAKERY": 0, "DAIRY": 0, "PRODUCE": 0,
    "FROZEN FOODS": 1, "GROCERY I": 1, "BEVERAGES": 2,
}

def warehouse_capacity_for_sku(avg_daily_demand, shelf_life_days):
    """Static per-SKU shelf/warehouse capacity (Section 11.3), sized relative to
    the SKU's own demand and shelf life rather than one constant across all
    SKUs -- a flat cap silently truncates the order-up-to level for
    higher-velocity or long-shelf-life categories regardless of what the
    replenishment policy actually calls for. Sized generously (10x a
    plausible max cycle stock) so it acts as a genuine capacity ceiling
    rather than an accidental binding constraint; Phase 1 (Section 16) would
    calibrate this against a real warehouse footprint per category."""
    return int(max(200, avg_daily_demand * max(shelf_life_days, 60) * 2))


def sample_lead_time(supplier: SupplierProfile, rng):
    lt = rng.normal(supplier.mean_lead_time, supplier.std_lead_time)
    return max(1, round(lt))  # truncated: never negative/zero


def sample_delivery(supplier: SupplierProfile, order_qty, rng):
    """Bernoulli delay + fill-rate shortfall, both driven by supplier reliability
    (Section 11.3)."""
    delay_prob = 1.0 - supplier.reliability  # more reliable -> less delay
    delay_days = rng.integers(1, 6) if rng.random() < delay_prob else 0
    fill_rate = np.clip(rng.normal(supplier.base_fill_rate, 0.03), 0.5, 1.0)
    received = int(round(order_qty * fill_rate))
    return received, delay_days, fill_rate


class BootstrapPolicy:
    """(s,S)-style heuristic used ONLY to seed a historically plausible
    purchase-order trace (Section 11.2, item 5). This is NOT DC^2T; DC^2T
    replaces this at decision time and is benchmarked against it as a naive
    baseline (Section 12.1).

    Shelf-life aware: the order-up-to level is capped so it does not exceed
    what can plausibly sell before expiry, which is a standard real-world
    constraint for perishables replenishment (ordering a week of bread when
    it molds in 3 days is not a realistic bootstrap policy)."""

    def __init__(self, avg_daily_demand, lead_time, shelf_life_days, safety_factor=1.3):
        # Perishables (short shelf life) are capped by shelf life so stock doesn't
        # rot; shelf-stable items instead follow a normal ~3.5-week periodic-review
        # replenishment cycle typical of center-store grocery categories, rather
        # than being capped at lead_time+3 (which is far too tight and would force
        # unrealistically frequent small orders / unrealistically low average stock
        # for genuinely non-perishable goods).
        review_horizon = min(shelf_life_days, max(lead_time + 3, 50))
        self.s = int(avg_daily_demand * lead_time * safety_factor)
        self.S = int(avg_daily_demand * max(review_horizon, lead_time + 1) * safety_factor)
        self.S = max(self.S, self.s + 1)

    def decide(self, inventory_position):
        if inventory_position <= self.s:
            return max(0, self.S - inventory_position)
        return 0


class Batch:
    __slots__ = ("qty", "arrival_day", "expiry_day")

    def __init__(self, qty, arrival_day, expiry_day):
        self.qty = qty
        self.arrival_day = arrival_day
        self.expiry_day = expiry_day


def run_sgsg_for_sku_store(demand_series, shelf_life_days, family, n_days, seed):
    """
    Executes the SGSG generative sequence (Section 11.2) for one SKU-store pair
    over n_days, using observed sales (demand_series) as D_t, and reconstructs
    the full latent operational state: inventory, purchase orders, supplier
    assignment/delivery, batch-level waste, and stockout events.

    Returns a per-day DataFrame implementing the flow equation
        I_t = I_{t-1} + Q_t - D_t - W_t      (Section 11.3)
    plus the auxiliary event tables (Section 11.5: Purchase Orders, Deliveries,
    Expiry Batches, Stockout Events).
    """
    rng = np.random.default_rng(seed)
    supplier = SUPPLIERS[FAMILY_SUPPLIER[family]]
    avg_daily_demand = max(1.0, np.mean(demand_series[: min(30, len(demand_series))]))
    base_lead_time = sample_lead_time(supplier, rng)
    policy = BootstrapPolicy(avg_daily_demand, base_lead_time, shelf_life_days)

    inventory = int(avg_daily_demand * base_lead_time * 1.6)  # initial stock
    batches = [Batch(inventory, arrival_day=0, expiry_day=shelf_life_days)]
    pending_orders = []  # (arrival_day, qty)

    rows = []
    po_log = []
    delivery_log = []
    stockout_log = []

    for t in range(n_days):
        # ---- 1. exogenous demand (already generated upstream: Favorita/M5 proxy) ----
        D_t = int(demand_series[t])

        # ---- 2. receive any deliveries arriving today ----
        arrived_today = [q for (day, q) in pending_orders if day == t]
        for q in arrived_today:
            batches.append(Batch(q, arrival_day=t, expiry_day=t + shelf_life_days))
        pending_orders = [(day, q) for (day, q) in pending_orders if day != t]

        # ---- 3. fulfil demand FIFO/FEFO (earliest-expiry-first) from batches ----
        batches.sort(key=lambda b: b.expiry_day)
        remaining_demand = D_t
        for b in batches:
            if remaining_demand <= 0:
                break
            take = min(b.qty, remaining_demand)
            b.qty -= take
            remaining_demand -= take
        unmet_demand = remaining_demand  # stockout if > 0
        if unmet_demand > 0:
            stockout_log.append({"day": t, "unmet": unmet_demand})

        # ---- 4. waste: batches past expiry (Section 11.3) ----
        expired_qty = sum(b.qty for b in batches if b.expiry_day <= t)
        batches = [b for b in batches if b.expiry_day > t and b.qty > 0]

        inventory = sum(b.qty for b in batches)

        # ---- 5. reorder trigger + bootstrap purchase order (Section 11.2, item 4-5) ----
        in_pipeline = sum(q for (_, q) in pending_orders)
        inventory_position = inventory + in_pipeline
        Q_t = policy.decide(inventory_position)
        Q_t = min(Q_t, warehouse_capacity_for_sku(avg_daily_demand, shelf_life_days) - inventory_position)  # capacity constraint
        Q_t = max(0, Q_t)

        if Q_t > 0:
            received, delay_days, fill_rate = sample_delivery(supplier, Q_t, rng)
            lead_time = sample_lead_time(supplier, rng) + delay_days
            arrival_day = t + lead_time
            pending_orders.append((arrival_day, received))
            po_log.append({"day": t, "ordered": Q_t, "supplier": supplier.name})
            delivery_log.append({"day": t, "arrival_day": arrival_day, "received": received,
                                  "delay_days": delay_days, "fill_rate": fill_rate})

        rows.append({
            "day": t, "family": family, "D_t": D_t, "unmet_demand": unmet_demand,
            "I_t": inventory, "Q_t": Q_t, "W_t": expired_qty,
            "in_pipeline": in_pipeline, "supplier": supplier.name,
        })

    panel = pd.DataFrame(rows)
    return {
        "panel": panel,
        "purchase_orders": pd.DataFrame(po_log),
        "deliveries": pd.DataFrame(delivery_log),
        "stockout_events": pd.DataFrame(stockout_log),
        "supplier": supplier.name,
    }


if __name__ == "__main__":
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    demand = np.random.default_rng(0).poisson(15, 200)
    out = run_sgsg_for_sku_store(demand, shelf_life_days=7, family="DAIRY", n_days=200, seed=1)
    print(out["panel"].head(10))
    print("Total waste:", out["panel"]["W_t"].sum(), "| Total stockout events:", len(out["stockout_events"]))
