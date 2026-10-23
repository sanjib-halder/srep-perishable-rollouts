"""
Exactness test: the vectorised engine must reproduce the UNMODIFIED
twin.digital_twin.GroceryTwin, cost component by cost component, when both
are fed the same random draws.

The twin's own RNGs are replaced by injectors that return the pre-drawn
scenario values for the current day, so any difference is a semantic
difference, not a sampling difference.
"""
import os
import sys
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from twin.digital_twin import GroceryTwin
from sgsg.generator import Batch, warehouse_capacity_for_sku
from srep.scenarios import load_data, DemandModel, draw_scenarios
from srep.engine import SkuSpec, State, simulate, AgeAwareSSPolicy as BaseStockPolicy
from srep.config import COSTS


class InjectedSupplyRng:
    """Stands in for twin.supply_rng; returns the scenario's draws for twin.day.
    sample_delivery calls random(), [integers()], normal(fill); then
    sample_lead_time calls normal(lead) -- at most one order per SKU-day."""

    def __init__(self, twin, scen, t0):
        self.twin, self.scen, self.t0 = twin, scen, t0
        self._normal_calls = {}

    def _h(self):
        return self.twin.day - self.t0

    def random(self):
        return self.scen["u_delay"][0, self._h()]

    def integers(self, lo, hi):
        assert (lo, hi) == (1, 6)
        return self.scen["delay_int"][0, self._h()]

    def normal(self, mu, sd):
        h = self._h()
        n = self._normal_calls.get(h, 0)
        self._normal_calls[h] = n + 1
        z = self.scen["z_fill"][0, h] if n == 0 else self.scen["z_lead"][0, h]
        return mu + sd * z


def twin_state_arrays(twin, item, SL):
    s = twin.skus[item]
    onhand = np.zeros(SL + 1, np.int64)
    for b in s.batches:
        onhand[b.expiry_day - twin.day] += b.qty
    L = 1 + max([d - twin.day for d, _ in s.pending_orders], default=0)
    pipe = np.zeros(max(L, 1), np.int64)
    for d, q in s.pending_orders:
        pipe[d - twin.day] += q
    return onhand, pipe


def run_case(products, dm, row, rng, H=14, seed=123, case=0):
    spec = SkuSpec.from_row(row)
    SL = spec.shelf_life
    t0 = int(rng.integers(0, 500))
    onhand = rng.integers(0, int(3 * spec.base_rate) + 2, SL + 1).astype(np.int64)
    onhand[rng.random(SL + 1) < 0.4] = 0
    pipe = np.zeros(4, np.int64)
    pipe[1:] = np.where(rng.random(3) < 0.5, rng.integers(0, int(4 * spec.base_rate) + 2, 3), 0)
    state = State(t0, onhand, pipe)
    a0 = int(rng.integers(0, int(5 * spec.base_rate) + 3))
    scen = draw_scenarios(dm, spec.item, t0, H, seed, case, 0, 1)
    policy = BaseStockPolicy(spec, dm.mean_demand(spec.item, t0, H + SL + 60))

    eng = simulate(spec, state, scen, H, first_actions=[a0], policy=policy, components=True)

    # --- the original twin, driven by injected draws ---
    sku_spec = dict(item_nbr=spec.item, family=spec.family, unit_price=spec.price,
                    shelf_life_days=SL, avg_daily_demand=spec.base_rate)
    tw = GroceryTwin([sku_spec], lambda item, day, r: int(scen["demand"][0, day - t0]),
                     warehouse_capacity_for_sku, seed=0)
    tw.day = t0
    s = tw.skus[spec.item]
    s.batches = [Batch(int(q), arrival_day=t0, expiry_day=t0 + r) for r, q in enumerate(onhand) if q > 0]
    s.pending_orders = [(t0 + i, int(q)) for i, q in enumerate(pipe) if q > 0]
    tw.supply_rng = InjectedSupplyRng(tw, scen, t0)

    acc = dict(order=0.0, holding=0.0, waste=0.0, stockout=0.0, unmet=0, wq=0, reward=0.0, Dp=0.0)
    for h in range(H):
        if h == 0:
            q = a0
        else:
            oh, pp = twin_state_arrays(tw, spec.item, SL)
            q = int(policy(oh[None, None, :], pp[None, None, :], h)[0, 0])
        _, rew, info = tw.step({spec.item: q})
        i = info[spec.item]
        acc["reward"] += rew[spec.item]; acc["Dp"] += i["D_t"] * spec.price
        acc["order"] += i["ordering_cost"]; acc["holding"] += i["holding_cost"]
        acc["waste"] += i["waste_cost"]; acc["stockout"] += i["stockout_penalty"]
        acc["unmet"] += i["unmet"]; acc["wq"] += i["W_t"]

    # The twin's stockout_penalty excludes lost revenue; the engine's J adds it
    # (see config.CostParams), so compare the twin-defined part only.
    eng_stockout_twin = eng["q_unmet"][0, 0] * spec.price * (COSTS.stockout_lost_margin_frac + COSTS.stockout_service_penalty_frac)
    for k, v in (("order", eng["order"][0, 0]), ("holding", eng["holding"][0, 0]),
                 ("waste", eng["waste"][0, 0]), ("stockout", eng_stockout_twin)):
        assert np.isclose(v, acc[k], rtol=0, atol=1e-9), (case, k, v, acc[k])
    assert eng["q_unmet"][0, 0] == acc["unmet"], case
    assert eng["q_waste"][0, 0] == acc["wq"], case
    # J equals -(twin reward) + sum(D * p) - terminal credit, exactly
    assert np.isclose(eng["cost"][0, 0], -acc["reward"] + acc["Dp"] + eng["terminal"][0, 0], atol=1e-7), case


def test_engine_matches_twin(n_cases=400):
    products, calendar = load_data()
    dm = DemandModel(products, calendar)
    per = products[products.family.isin(["BREAD/BAKERY", "PRODUCE", "DAIRY"])].reset_index(drop=True)
    rng = np.random.default_rng(42)
    for c in range(n_cases):
        row = per.iloc[int(rng.integers(len(per)))]
        run_case(products, dm, row, rng, H=int(rng.choice([7, 14])), case=c)
    return n_cases


def test_crn_demand_identical_across_candidates():
    """Demand and supply draws must not depend on the actions taken."""
    products, calendar = load_data()
    dm = DemandModel(products, calendar)
    item = int(products[products.family == "DAIRY"].item_nbr.iloc[0])
    a = draw_scenarios(dm, item, 50, 14, 7, 3, 0, 40)
    b = draw_scenarios(dm, item, 50, 14, 7, 3, 20, 40)   # overlapping range requested separately
    for k in a:
        assert np.array_equal(a[k][20:], b[k]), k


def test_vectorised_equals_one_at_a_time():
    """Evaluating K candidates jointly equals evaluating each alone."""
    products, calendar = load_data()
    dm = DemandModel(products, calendar)
    row = products[products.family == "PRODUCE"].iloc[3]
    spec = SkuSpec.from_row(row)
    st = State(100, np.array([3, 0, 5, 8, 0, 0], np.int64), np.array([0, 0, 12], np.int64))
    scen = draw_scenarios(dm, spec.item, 100, 14, 1, 0, 0, 50)
    pol = BaseStockPolicy(spec, dm.mean_demand(spec.item, 100, 90))
    acts = [0, 5, 10, 20, 40]
    joint = simulate(spec, st, scen, 14, acts, pol)
    for j, a in enumerate(acts):
        alone = simulate(spec, st, scen, 14, [a], pol)
        assert np.allclose(joint[:, j], alone[:, 0])


if __name__ == "__main__":
    n = test_engine_matches_twin()
    print(f"engine == GroceryTwin on {n} random cases (all cost components and quantities)")
    test_crn_demand_identical_across_candidates(); print("CRN block determinism OK")
    test_vectorised_equals_one_at_a_time(); print("joint vs single-candidate evaluation OK")
