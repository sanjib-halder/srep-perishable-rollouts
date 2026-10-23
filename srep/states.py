"""
Benchmark decision states (protocol §6 / §7).

A state is produced by running the engine closed-loop from the twin's own
initial condition (init stock = avg demand x mean lead time x 1.4, fresh)
for a random warm-up under a randomly mis-tuned base-stock policy, with an
optional order-skip disruption. This yields realistic but heterogeneous
inventory positions: overstocked, understocked, ageing stock, empty shelves.

Stratification: family (shelf life 3 / 5 / 10 days) x demand-volume tertile.
Two disjoint sets exist: BENCHMARK (reported results) and DEV (smoke tests
only -- nothing from DEV is ever reported).
"""
import os
import pickle
import numpy as np

from .config import PROTOCOL
from .scenarios import load_data, DemandModel, draw_scenarios, DATA_DIR
from .engine import SkuSpec, State, simulate, AgeAwareSSPolicy


class _SkipWindow:
    def __init__(self, policy, start, end):
        self.p, self.s, self.e = policy, start, end

    def __call__(self, onhand, pipe, h):
        q = self.p(onhand, pipe, h)
        return q * 0 if self.s <= h < self.e else q


def perishable_products(products):
    per = products[products.family.isin(PROTOCOL.families)].copy()
    per["volume_tertile"] = per.groupby("family")["base_demand_rate"].transform(
        lambda x: np.digitize(x, np.quantile(x, [1 / 3, 2 / 3])))
    return per.reset_index(drop=True)


def generate_states(n, seed, products=None, calendar=None):
    if products is None:
        products, calendar = load_data()
    dm = DemandModel(products, calendar)
    per = perishable_products(products)
    cells = [(f, v) for f in PROTOCOL.families for v in range(3)]
    rng = np.random.default_rng(seed)
    out = []
    for sid in range(n):
        fam, vt = cells[sid % len(cells)]
        pool = per[(per.family == fam) & (per.volume_tertile == vt)]
        row = pool.iloc[int(rng.integers(len(pool)))]
        spec = SkuSpec.from_row(row)
        W = int(rng.integers(21, 61))
        t0 = int(rng.integers(W + 1, dm.n_cal - 30))
        sf = float(rng.uniform(0.6, 1.8))
        init = np.zeros(spec.shelf_life + 1, np.int64)
        init[spec.shelf_life] = int(spec.base_rate * spec.supplier.mean_lead_time * 1.4)
        start = State(t0 - W, init, np.zeros(1, np.int64))
        pol = AgeAwareSSPolicy(spec, dm.mean_demand(spec.item, t0 - W, W + spec.shelf_life + 60), safety=sf)
        disrupted = rng.random() < 0.2
        if disrupted:
            d0 = W - int(rng.integers(1, 5))
            pol = _SkipWindow(pol, d0, W)
        scen = draw_scenarios(dm, spec.item, t0 - W, W, seed, sid, 0, 1)
        _, (oh, pp) = simulate(spec, start, scen, W, first_actions=None, policy=pol, return_state=True)
        pipe = pp[0, 0]
        last = np.nonzero(pipe)[0]
        pipe = pipe[: (last[-1] + 1 if len(last) else 1)]
        out.append(dict(state_id=sid, item=spec.item, family=fam, shelf_life=spec.shelf_life,
                        volume_tertile=int(vt), base_rate=spec.base_rate, warmup=W, safety=sf,
                        disrupted=bool(disrupted), state=State(t0, oh[0, 0].copy(), pipe.copy())))
    return out


def load_or_build(kind):
    assert kind in ("benchmark", "dev")
    path = os.path.join(DATA_DIR, f"states_{kind}.pkl")
    if os.path.exists(path):
        with open(path, "rb") as f:
            return pickle.load(f)
    n = PROTOCOL.n_benchmark_states if kind == "benchmark" else PROTOCOL.n_dev_states
    seed = PROTOCOL.seed_states_benchmark if kind == "benchmark" else PROTOCOL.seed_states_dev
    states = generate_states(n, seed)
    with open(path, "wb") as f:
        pickle.dump(states, f)
    return states
