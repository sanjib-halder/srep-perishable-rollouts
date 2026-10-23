"""Assemble a Problem (spec, state, candidates, continuation policy) for a state record."""
from .scenarios import load_data, DemandModel
from .engine import SkuSpec, AgeAwareSSPolicy
from .candidates import generate_candidates
from .allocation import Problem

_CACHE = {}


def context():
    if "ctx" not in _CACHE:
        products, calendar = load_data()
        _CACHE["ctx"] = (products, calendar, DemandModel(products, calendar),
                         products.set_index("item_nbr"))
    return _CACHE["ctx"]


def build_problem(rec, H, costs=None):
    products, calendar, dm, by_item = context()
    row = by_item.loc[rec["item"]].copy()
    row["item_nbr"] = rec["item"]
    spec = SkuSpec.from_row(row)
    st = rec["state"]
    policy = AgeAwareSSPolicy(spec, dm.mean_demand(spec.item, st.t0, H + spec.shelf_life + 60))
    cand = generate_candidates(dm, spec, st, policy)
    pr = Problem(spec=spec, state=st, cand=cand, policy=policy, H=H, state_id=rec["state_id"], dm=dm)
    if costs is not None:
        pr.costs_params = costs
    return pr
