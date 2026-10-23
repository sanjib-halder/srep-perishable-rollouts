"""
Vectorised rollout engine for one SKU.

Evaluates K candidate day-1 orders under R common scenarios over H days in a
single NumPy pass. Semantics reproduce twin.digital_twin.GroceryTwin.step
exactly (verified in tests/test_engine_vs_twin.py):

  each day:  receive arrivals -> realise demand -> fulfil FEFO -> expire
             -> place (capacity-clipped) order -> book costs -> age stock

State convention (start of a day, before receipts):
  onhand[r]  units whose expiry_day - today == r, r = 0..shelf_life
             (r = 0 units can still be sold today, then expire)
  pipe[i]    units arriving i days from today (i = 0 arrives today)

Decision timing: an order for day h is chosen from the START-of-day state
(as an outside caller of GroceryTwin.step must) and placed at end of day.
"""
from dataclasses import dataclass
import numpy as np

from sgsg.generator import SUPPLIERS, FAMILY_SUPPLIER, warehouse_capacity_for_sku
from .config import COSTS, PROTOCOL


@dataclass
class SkuSpec:
    item: int
    family: str
    price: float
    shelf_life: int
    base_rate: float
    supplier_idx: int
    capacity: int

    @classmethod
    def from_row(cls, row):
        fam = row["family"]
        return cls(item=int(row["item_nbr"]), family=fam, price=float(row["unit_price"]),
                   shelf_life=int(row["shelf_life_days"]), base_rate=float(row["base_demand_rate"]),
                   supplier_idx=FAMILY_SUPPLIER[fam],
                   capacity=warehouse_capacity_for_sku(float(row["base_demand_rate"]), int(row["shelf_life_days"])))

    @property
    def supplier(self):
        return SUPPLIERS[self.supplier_idx]


@dataclass
class State:
    t0: int                 # absolute calendar day of the decision
    onhand: np.ndarray      # (shelf_life+1,) int64, index = remaining days
    pipe: np.ndarray        # (L,) int64, index = days until arrival

    def copy(self):
        return State(self.t0, self.onhand.copy(), self.pipe.copy())


def supply_outcomes(spec, scen):
    """Delivery outcome that applies to an order placed on (scenario, day).
    Mirrors sgsg.generator.sample_delivery / sample_lead_time draw-for-draw."""
    sup = spec.supplier
    delay = np.where(scen["u_delay"] < (1.0 - sup.reliability), scen["delay_int"], 0)
    fill = np.clip(sup.base_fill_rate + 0.03 * scen["z_fill"], 0.5, 1.0)
    base_lt = np.maximum(1, np.rint(sup.mean_lead_time + sup.std_lead_time * scen["z_lead"]).astype(np.int64))
    return fill, base_lt + delay


class BaseStockPolicy:
    """Age-aware base-stock continuation policy (protocol §5.3), vectorised.

    Order-up-to level S_h = safety * E[demand over today + lead + review days].
    Inventory position counts on-hand and pipeline stock, minus on-hand stock
    projected to expire unsold under FEFO with expected demand:
        projected outdating = max_r ( C_r - E_r )^+
    where C_r = on-hand units with remaining life <= r and E_r = expected
    demand over days h..h+r.
    """

    def __init__(self, spec, mean_demand, safety=None):
        sup = spec.supplier
        self.lead = int(round(sup.mean_lead_time + (1 - sup.reliability) * 3.0))
        self.P = self.lead + PROTOCOL.cont_review_days
        self.safety = PROTOCOL.cont_safety_factor if safety is None else safety
        self.md = mean_demand                       # (>= H + shelf_life + P,)
        self.SL = spec.shelf_life

    def order_up_to(self, h):
        return self.safety * self.md[h:h + self.P].sum()

    def effective_position(self, onhand, pipe, h):
        cum_stock = np.cumsum(onhand, axis=-1)
        cum_dem = np.cumsum(self.md[h:h + self.SL + 1])
        outdate = np.maximum(cum_stock - cum_dem, 0).max(axis=-1)
        return onhand.sum(-1) + pipe.sum(-1) - outdate

    def __call__(self, onhand, pipe, h):
        return np.maximum(0, np.rint(self.order_up_to(h) - self.effective_position(onhand, pipe, h))).astype(np.int64)


class AgeAwareSSPolicy(BaseStockPolicy):
    """Continuation policy (protocol §5.3, amended): the SGSG BootstrapPolicy
    (s,S) rule -- the same rule that generated the historical order trace --
    made age-aware and calendar-aware.

      s_h = safety * E[demand over the L days after today]
      S_h = safety * E[demand over the R_h days after today],
            R_h = min(shelf_life, max(L + 3, 50))  (BootstrapPolicy's review horizon)
      IP  = effective position (stock projected to expire unsold removed)
            minus today's expected demand, because the twin's BootstrapPolicy
            decides at END of day while an outside caller decides at the start.
      order S_h - IP if IP <= s_h, else 0.

    A pure base-stock rule orders every day and so pays the fixed order cost
    daily; with K = 8 that makes any large day-1 order look good simply by
    suppressing later orders. (s,S) does not have that defect.
    """

    def __init__(self, spec, mean_demand, safety=None):
        super().__init__(spec, mean_demand, safety)
        self.L = max(1, int(round(spec.supplier.mean_lead_time)))
        self.RH = min(spec.shelf_life, max(self.L + 3, 50))

    def levels(self, h):
        s = self.safety * self.md[h + 1:h + 1 + self.L].sum()
        S = self.safety * self.md[h + 1:h + 1 + max(self.RH, self.L + 1)].sum()
        return s, max(S, s + 1)

    def position(self, onhand, pipe, h):
        return self.effective_position(onhand, pipe, h) - self.md[h]

    def __call__(self, onhand, pipe, h):
        s, S = self.levels(h)
        ip = self.position(onhand, pipe, h)
        return np.where(ip <= s, np.maximum(0, np.rint(S - ip)), 0).astype(np.int64)


def simulate(spec, state, scen, H, first_actions=None, policy=None, costs=COSTS,
             return_state=False, components=False):
    """
    Roll forward R scenarios x K candidates for H days.

    first_actions: (K,) order quantities for day 0, or None to let `policy`
                   decide day 0 as well (closed-loop / state generation).
    policy:        callable(onhand, pipe, h) -> (R,K) orders for days >= 1.
    Returns total cost (R,K), or a dict of per-component totals if components.
    """
    R = scen["demand"].shape[0]
    K = 1 if first_actions is None else len(first_actions)
    SL = spec.shelf_life
    fill, lead = supply_outcomes(spec, scen)
    L = max(len(state.pipe), int(lead[:, :H].max()) + 1)

    onhand = np.zeros((R, K, SL + 1), np.int64)
    onhand[:] = state.onhand[None, None, :]
    pipe = np.zeros((R, K, L), np.int64)
    pipe[:, :, :len(state.pipe)] = state.pipe[None, None, :]

    p = spec.price
    tot = {k: np.zeros((R, K)) for k in ("order", "holding", "waste", "stockout")}
    qty = {k: np.zeros((R, K)) for k in ("demand", "unmet", "waste", "ordered")}
    ri = np.arange(R)[:, None]
    ki = np.arange(K)[None, :]

    for h in range(H):
        # decision from start-of-day state
        if h == 0 and first_actions is not None:
            Q = np.broadcast_to(np.asarray(first_actions, np.int64)[None, :], (R, K)).copy()
        else:
            Q = policy(onhand, pipe, h)
            Q = np.broadcast_to(Q, (R, K)).astype(np.int64).copy()
        Q = np.maximum(Q, 0)

        # receive
        onhand[:, :, SL] += pipe[:, :, 0]
        pipe[:, :, 0] = 0
        # demand + FEFO fulfilment
        D = scen["demand"][:, h][:, None, None]
        cum = np.cumsum(onhand, axis=-1)
        take = np.clip(D - (cum - onhand), 0, onhand)
        onhand -= take
        unmet = np.maximum(D[..., 0] - cum[..., -1], 0)
        # expiry
        expired = onhand[:, :, 0].copy()
        onhand[:, :, 0] = 0
        inv_after = onhand.sum(-1)
        # order, capacity-clipped exactly as the twin does
        Q = np.maximum(0, np.minimum(Q, spec.capacity - inv_after - pipe.sum(-1)))
        rec = np.rint(Q * fill[:, h][:, None]).astype(np.int64)
        placed = Q > 0
        pipe[ri, ki, lead[:, h][:, None]] += np.where(placed, rec, 0)

        tot["holding"] += inv_after * costs.holding_per_unit_day
        tot["order"] += np.where(placed, costs.order_fixed + Q * p * costs.order_variable_frac, 0.0)
        tot["waste"] += expired * p * costs.waste_frac
        tot["stockout"] += unmet * p * costs.stockout_frac
        if components:
            qty["demand"] += D[..., 0]
            qty["unmet"] += unmet
            qty["waste"] += expired
            qty["ordered"] += Q

        # age one day
        onhand[:, :, :-1] = onhand[:, :, 1:]
        onhand[:, :, -1] = 0
        pipe[:, :, :-1] = pipe[:, :, 1:]
        pipe[:, :, -1] = 0

    terminal = -(onhand.sum(-1) + pipe.sum(-1)) * p * costs.terminal_credit_frac
    total = tot["order"] + tot["holding"] + tot["waste"] + tot["stockout"] + terminal
    out = {"cost": total, "terminal": terminal, **tot, **{"q_" + k: v for k, v in qty.items()}} if components else total
    if return_state:
        return out, (onhand, pipe)
    return out
