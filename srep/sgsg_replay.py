"""
SGSG replay with start-of-day state snapshots.

Line-for-line copy of sgsg.generator.run_sgsg_for_sku_store that also records,
on chosen days, the stock by remaining shelf life and the orders in transit by
days-to-arrival -- the State the rollout engine needs. Equality with the
original function is checked in notebook 1 (200 series, 0 mismatches).
"""
import numpy as np
from sgsg.generator import (SUPPLIERS, FAMILY_SUPPLIER, sample_lead_time, sample_delivery,
                            BootstrapPolicy, Batch, warehouse_capacity_for_sku)


def replay_with_snapshots(demand_series, shelf_life_days, family, n_days, seed, snap_days=()):
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
            take = min(b.qty, remaining_demand)
            b.qty -= take
            remaining_demand -= take
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
    return np.array(rows), snaps, avg_daily_demand
