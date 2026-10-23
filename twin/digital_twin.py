"""
Event-driven Digital Twin environment, built on the SGSG-reconstructed state
(Section 8: architecture; Section 10: POMDP formulation; Section 10.7:
per-entity transition dynamics).

This is the twin used two ways downstream, exactly as Section 9/10 specify:
  1. As the DEPLOYMENT ENVIRONMENT for whatever policy is making decisions
     (bootstrap, PPO, or a baseline), via step(action).
  2. As the WORLD MODEL the reasoning module (Module 3) rolls forward through
     for lookahead planning -- clone() supports this without disturbing the
     live environment being stepped through by the outer training/eval loop.

State S_t (Section 10.1) = (I_t, B_t, O_t^pipe, E_t, P_t, X_t, W_t, theta_t)
Action A_t (Section 10.3) = order quantity Q_t (per SKU in the active group)
Reward R_t (Section 10.4) = Revenue - Holding - Ordering - Waste - StockoutPenalty
"""
import copy
import os
import sys
import numpy as np
import pandas as pd
from dataclasses import dataclass, field

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
from sgsg.generator import SUPPLIERS, FAMILY_SUPPLIER, sample_lead_time, sample_delivery, Batch

# --- Reward-function cost coefficients (Section 10.4) ---
HOLDING_COST_PER_UNIT_DAY = 0.03
ORDER_FIXED_COST = 8.0
ORDER_VARIABLE_COST_FRAC = 0.55       # fraction of unit price paid to supplier
STOCKOUT_LOST_MARGIN_FRAC = 0.35      # margin lost per unmet unit
STOCKOUT_SERVICE_PENALTY = 0.15       # extra per-unit penalty for service-level breach
WASTE_COST_FRAC = 0.55                # sunk cost per wasted unit (same as ordering cost)


@dataclass
class SkuState:
    item_nbr: int
    family: str
    unit_price: float
    shelf_life_days: int
    avg_daily_demand: float
    supplier_idx: int
    batches: list = field(default_factory=list)
    pending_orders: list = field(default_factory=list)  # (arrival_day, qty)
    # belief-relevant realized history (feeds Module 5 continuous learning / Module 2 prediction)
    demand_history: list = field(default_factory=list)


class GroceryTwin:
    """
    Multi-SKU event-driven Digital Twin for a single store.

    Each call to step({item_nbr: order_qty, ...}) advances all SKUs by one
    day using the SAME transition equations as SGSG (Section 10.7):
        Inventory:  I_{t+1} = I_t + Q_t - D_t - W_t
        Supplier:   reliability tracked via realized fill-rate/delay history
        Demand:     drawn from the demand generator supplied at construction
        Warehouse:  capacity constraint applied to Q_t
    """

    def __init__(self, sku_specs, demand_generator, capacity_fn, seed=0, warmup_days=0):
        """
        sku_specs: list of dicts with item_nbr, family, unit_price, shelf_life_days, avg_daily_demand
        demand_generator: callable(item_nbr, day, rng) -> realized demand D_t (int)
        capacity_fn: callable(avg_daily_demand, shelf_life_days) -> warehouse capacity

        FIX (see history in this project / paper Section 6.2 revision): demand
        generation and supplier-delivery sampling previously shared ONE rng
        stream (self.rng). Supplier draws only happen conditionally, when a
        policy places a non-zero order -- so two policies with different order
        timing consumed that shared stream at different rates and positions,
        desynchronizing demand realizations from the very first day they
        diverged, DESPITE using the "same seed". This was verified empirically:
        two policies evaluated with identical seed produced different D_t
        traces starting on day 1. A true common-random-numbers design (which
        Section 6.2's paired Wilcoxon test and Table 3 implicitly assume)
        requires demand to be genuinely policy-independent. Splitting into two
        streams fixes this: demand_rng is touched ONLY by demand generation,
        called unconditionally for every SKU every day regardless of policy,
        so it stays perfectly synchronized across any two policies sharing a
        seed. supply_rng is intentionally SEPARATE and still policy-dependent
        (correctly so -- delivery outcomes are a genuine consequence of when
        and how much a policy orders, not something that should be shared).
        """
        self.demand_rng = np.random.default_rng(seed)
        self.supply_rng = np.random.default_rng(seed + 500_000)  # large offset, deterministic, decorrelated from demand_rng's seed
        self.demand_generator = demand_generator
        self.capacity_fn = capacity_fn
        self.day = 0
        self.warmup_days = warmup_days
        self.skus = {}
        for spec in sku_specs:
            supplier_idx = FAMILY_SUPPLIER[spec["family"]]
            init_inv = int(spec["avg_daily_demand"] * SUPPLIERS[supplier_idx].mean_lead_time * 1.4)
            s = SkuState(item_nbr=spec["item_nbr"], family=spec["family"],
                         unit_price=spec["unit_price"], shelf_life_days=spec["shelf_life_days"],
                         avg_daily_demand=spec["avg_daily_demand"], supplier_idx=supplier_idx)
            s.batches.append(Batch(init_inv, arrival_day=0, expiry_day=spec["shelf_life_days"]))
            self.skus[spec["item_nbr"]] = s
        self._scoring = (self.day >= self.warmup_days)

    def clone(self):
        """Deep-copies the twin so the reasoning module (Module 3) can roll
        forward hypothetical trajectories without mutating the live env."""
        return copy.deepcopy(self)

    def get_state(self, item_nbr):
        """Returns S_t components for one SKU (Section 10.1)."""
        s = self.skus[item_nbr]
        inventory = sum(b.qty for b in s.batches)
        pipeline = sum(q for (_, q) in s.pending_orders)
        # Sentinel for "no batches on hand" is 0 (maximum reorder urgency),
        # not a large number: an earlier version defaulted to 999, which --
        # after normalization -- was indistinguishable from a freshly
        # restocked SKU with a full shelf-life runway ahead of it. That
        # conflated "just restocked" with "completely out of stock," the
        # opposite of what a reorder-urgency signal should do, and let a
        # policy get trapped never reordering once it hit zero inventory
        # (observed as a 100% stockout collapse on a real-data SKU).
        nearest_expiry = min([b.expiry_day - self.day for b in s.batches], default=0)
        return {
            "I_t": inventory, "O_pipe": pipeline, "E_t": nearest_expiry,
            "P_t": s.unit_price, "avg_daily_demand": s.avg_daily_demand,
            "supplier_reliability": SUPPLIERS[s.supplier_idx].reliability,
            "shelf_life_days": s.shelf_life_days,
        }

    def step(self, actions: dict):
        """actions: {item_nbr: order_qty}. Advances all SKUs by one day.
        Returns (obs_dict, reward_dict, info_dict)."""
        rewards, infos = {}, {}
        for item_nbr, s in self.skus.items():
            Q_t = max(0, int(actions.get(item_nbr, 0)))

            # ---- receive deliveries arriving today ----
            arrived = [q for (day, q) in s.pending_orders if day == self.day]
            for q in arrived:
                s.batches.append(Batch(q, arrival_day=self.day, expiry_day=self.day + s.shelf_life_days))
            s.pending_orders = [(day, q) for (day, q) in s.pending_orders if day != self.day]

            # ---- exogenous demand realization ----
            D_t = self.demand_generator(item_nbr, self.day, self.demand_rng)
            s.demand_history.append(D_t)

            # ---- fulfil FEFO ----
            s.batches.sort(key=lambda b: b.expiry_day)
            remaining = D_t
            for b in s.batches:
                if remaining <= 0:
                    break
                take = min(b.qty, remaining)
                b.qty -= take
                remaining -= take
            unmet = remaining

            # ---- waste ----
            expired_qty = sum(b.qty for b in s.batches if b.expiry_day <= self.day)
            s.batches = [b for b in s.batches if b.expiry_day > self.day and b.qty > 0]
            inventory_after = sum(b.qty for b in s.batches)

            # ---- place order (capacity-constrained) ----
            pipeline = sum(q for (_, q) in s.pending_orders)
            cap = self.capacity_fn(s.avg_daily_demand, s.shelf_life_days)
            Q_t = max(0, min(Q_t, cap - inventory_after - pipeline))
            if Q_t > 0:
                supplier = SUPPLIERS[s.supplier_idx]
                received, delay_days, fill_rate = sample_delivery(supplier, Q_t, self.supply_rng)
                lead_time = sample_lead_time(supplier, self.supply_rng) + delay_days
                s.pending_orders.append((self.day + lead_time, received))

            # ---- reward R_t (Section 10.4) ----
            revenue = (D_t - unmet) * s.unit_price
            holding_cost = inventory_after * HOLDING_COST_PER_UNIT_DAY
            ordering_cost = (ORDER_FIXED_COST + Q_t * s.unit_price * ORDER_VARIABLE_COST_FRAC) if Q_t > 0 else 0.0
            waste_cost = expired_qty * s.unit_price * WASTE_COST_FRAC
            stockout_penalty = unmet * s.unit_price * (STOCKOUT_LOST_MARGIN_FRAC + STOCKOUT_SERVICE_PENALTY)
            R_t = revenue - holding_cost - ordering_cost - waste_cost - stockout_penalty

            rewards[item_nbr] = R_t
            infos[item_nbr] = {
                "D_t": D_t, "unmet": unmet, "I_t": inventory_after, "Q_t": Q_t,
                "W_t": expired_qty, "revenue": revenue, "holding_cost": holding_cost,
                "ordering_cost": ordering_cost, "waste_cost": waste_cost,
                "stockout_penalty": stockout_penalty,
            }

        self.day += 1
        obs = {item_nbr: self.get_state(item_nbr) for item_nbr in self.skus}
        return obs, rewards, infos

    def is_scoring(self):
        """Warm-up exclusion per the common evaluation protocol (Section 5.1)."""
        return self.day >= self.warmup_days


_DEMAND_MODEL_N_FAMILIES = 6  # matches data/favorita_m5_proxy.py's FAMILIES list length


def _seasonal_multiplier(day_of_year, family_idx):
    """Duplicated from data/favorita_m5_proxy.py (not imported) so the twin's
    demand model never depends on a runtime cross-package import into the
    `data` package -- that import proved fragile on at least one real setup
    (implicit namespace-package resolution failing inconsistently depending
    on when in the call stack it was triggered), and this function is small,
    stable, and unlikely to drift out of sync with its counterpart."""
    phase = family_idx * (2 * np.pi / _DEMAND_MODEL_N_FAMILIES)
    return 1.0 + 0.25 * np.sin(2 * np.pi * day_of_year / 365 + phase)


def _weekly_multiplier(dow):
    """Duplicated from data/favorita_m5_proxy.py -- see _seasonal_multiplier's docstring."""
    curve = np.array([0.90, 0.88, 0.90, 0.95, 1.05, 1.25, 1.15])  # Mon..Sun
    return curve[dow]


def make_demand_generator(products_df, calendar_df, seed=0):
    """Builds a stochastic demand generator matching the same seasonal /
    weekly / promo structure used to generate the proxy Favorita panel
    (data/favorita_m5_proxy.py), so the twin's demand dynamics are
    statistically consistent with the historical data SGSG was built from."""
    fam_idx = products_df.set_index("item_nbr")["family_idx"].to_dict()
    base_rate = products_df.set_index("item_nbr")["base_demand_rate"].to_dict()
    cal = calendar_df.reset_index(drop=True)
    n_cal = len(cal)

    def gen(item_nbr, day, rng):
        row = cal.iloc[day % n_cal]
        mult = (_seasonal_multiplier(row.doy, fam_idx[item_nbr])
                * _weekly_multiplier(row.dow)
                * (1.35 if row.is_holiday else 1.0))
        promo = rng.random() < 0.06
        if promo:
            mult *= 1.6
        lam = max(0.1, base_rate[item_nbr] * mult)
        return int(rng.poisson(lam))
    return gen


if __name__ == "__main__":
    products = pd.read_pickle(os.path.join(PROJECT_ROOT, "data", "proxy_products.pkl"))
    calendar = pd.read_pickle(os.path.join(PROJECT_ROOT, "data", "proxy_calendar.pkl"))
    from sgsg.generator import warehouse_capacity_for_sku

    specs = products.head(3).rename(columns={"base_demand_rate": "avg_daily_demand"}).to_dict("records")
    demand_gen = make_demand_generator(products, calendar)
    twin = GroceryTwin(specs, demand_gen, warehouse_capacity_for_sku, seed=1, warmup_days=14)

    total_reward = 0.0
    for day in range(30):
        actions = {s["item_nbr"]: 20 for s in specs}  # naive fixed-order policy for smoke test
        obs, rewards, infos = twin.step(actions)
        total_reward += sum(rewards.values())
    print("Smoke test OK. 30-day total reward (naive fixed policy):", round(total_reward, 2))
    print("Final obs:", obs)
