"""
Scenario generation with common random numbers (CRN).

A scenario is everything random over the horizon: daily demand and the
supplier outcome that WOULD apply to an order placed on that day. Supplier
draws are made for every (scenario, day) whether or not an order is placed,
so an order on day t always receives the same delivery outcome regardless of
what any candidate did on other days. This removes the policy-dependent
supply-stream desynchronisation present in twin/digital_twin.py.

Scenario r of state s is a deterministic function of (seed, state_id, r):
draws are generated in blocks of PROTOCOL.block_size scenarios from
np.random.default_rng([seed, state_id, block]). Any method that asks for
scenarios [0, n) therefore sees exactly the same futures.
"""
import os
import numpy as np
import pandas as pd

from .config import PROTOCOL

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

# Demand-model constants duplicated from twin/digital_twin.py (unchanged).
_N_FAMILIES = 6
_WEEKLY = np.array([0.90, 0.88, 0.90, 0.95, 1.05, 1.25, 1.15])
PROMO_PROB = 0.06
PROMO_MULT = 1.6
HOLIDAY_MULT = 1.35


def load_data():
    products = pd.read_pickle(os.path.join(DATA_DIR, "proxy_products.pkl"))
    calendar = pd.read_pickle(os.path.join(DATA_DIR, "proxy_calendar.pkl")).reset_index(drop=True)
    return products, calendar


class DemandModel:
    """Vectorised version of twin.digital_twin.make_demand_generator."""

    def __init__(self, products, calendar):
        self.fam_idx = products.set_index("item_nbr")["family_idx"].to_dict()
        self.base = products.set_index("item_nbr")["base_demand_rate"].to_dict()
        self.doy = calendar["doy"].to_numpy()
        self.dow = calendar["dow"].to_numpy()
        self.hol = calendar["is_holiday"].to_numpy().astype(bool)
        self.n_cal = len(calendar)

    def base_lambda(self, item, t0, H):
        """Non-promo Poisson rate for days t0..t0+H-1 (shape (H,))."""
        idx = (t0 + np.arange(H)) % self.n_cal
        phase = self.fam_idx[item] * (2 * np.pi / _N_FAMILIES)
        seasonal = 1.0 + 0.25 * np.sin(2 * np.pi * self.doy[idx] / 365 + phase)
        mult = seasonal * _WEEKLY[self.dow[idx]] * np.where(self.hol[idx], HOLIDAY_MULT, 1.0)
        return self.base[item] * mult

    def mean_demand(self, item, t0, H):
        """Expected demand including the promo mixture (used by policies)."""
        lam = self.base_lambda(item, t0, H)
        return np.maximum(0.1, lam) * (1 - PROMO_PROB) + np.maximum(0.1, lam * PROMO_MULT) * PROMO_PROB


def _draw_block(dm, item, t0, H, seed, state_id, block):
    B = PROTOCOL.block_size
    rng = np.random.default_rng([seed, state_id, block])
    lam0 = dm.base_lambda(item, t0, H)
    promo = rng.random((B, H)) < PROMO_PROB
    lam = np.maximum(0.1, lam0[None, :] * np.where(promo, PROMO_MULT, 1.0))
    demand = rng.poisson(lam).astype(np.int64)
    u_delay = rng.random((B, H))
    delay_int = rng.integers(1, 6, size=(B, H))
    z_fill = rng.standard_normal((B, H))
    z_lead = rng.standard_normal((B, H))
    return dict(demand=demand, u_delay=u_delay, delay_int=delay_int, z_fill=z_fill, z_lead=z_lead)


def draw_scenarios(dm, item, t0, H, seed, state_id, r_start, r_end):
    """Scenarios [r_start, r_end) as arrays of shape (R, H)."""
    B = PROTOCOL.block_size
    b0, b1 = r_start // B, (r_end + B - 1) // B
    blocks = [_draw_block(dm, item, t0, H, seed, state_id, b) for b in range(b0, b1)]
    out = {}
    for k in blocks[0]:
        arr = np.concatenate([blk[k] for blk in blocks], axis=0)
        out[k] = arr[r_start - b0 * B: r_end - b0 * B]
    return out
