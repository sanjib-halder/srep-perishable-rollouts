"""
Candidate order quantities (protocol §5.2).

From the start-of-day state, using only information available at decision
time (expected demand from the demand model, current stock and pipeline):

  * zero order;
  * the continuation policy's own (s,S) choice, and its order-up-to amount
    even when the reorder point is not hit;
  * point-forecast order-up-to levels covering k days after today, for k
    spread from the lead time up to lead time + shelf life (stock arriving
    after L days can be sold for at most shelf_life + 1 days);
  * demand quantiles over the lead time + 1 day (base-stock protection);
  * +/- perturbations of the (s,S) order-up-to amount.

All are rounded, clipped to [0, capacity headroom] and de-duplicated. The
optimum must be bracketed: `is_boundary` flags states whose best candidate is
the largest (or a non-zero smallest) one, which is reported as a diagnostic.
"""
import numpy as np

from .config import PROTOCOL
from .scenarios import PROMO_PROB, PROMO_MULT


def protection_demand_samples(dm, spec, t0, days, n=4000, seed=0):
    """Monte-Carlo draws of total demand over days t0+1..t0+days (separate RNG stream)."""
    rng = np.random.default_rng([seed, spec.item, t0, 4242])
    lam0 = dm.base_lambda(spec.item, t0 + 1, days)
    promo = rng.random((n, days)) < PROMO_PROB
    lam = np.maximum(0.1, lam0[None, :] * np.where(promo, PROMO_MULT, 1.0))
    return rng.poisson(lam).sum(axis=1)


def generate_candidates(dm, spec, state, policy, seed=0, samples=None):
    oh, pp = state.onhand[None, None, :], state.pipe[None, None, :]
    ip = float(policy.position(oh, pp, 0)[0, 0])
    s, S = policy.levels(0)
    L, SL = policy.L, spec.shelf_life
    cum = np.cumsum(policy.md[1:1 + L + SL + 1])          # expected demand over 1..k days after today

    up_to_S = max(0.0, S - ip)
    c = [0.0, float(policy(oh, pp, 0)[0, 0]), up_to_S]
    for k in np.unique(np.linspace(L, L + SL, PROTOCOL.candidate_coverage_levels).round().astype(int)):
        c.append(cum[k - 1] - ip)
    if samples is None:
        samples = protection_demand_samples(dm, spec, state.t0, L + 1, seed=seed)
    c += [np.quantile(samples, q) - ip for q in PROTOCOL.candidate_quantiles]
    scale = max(up_to_S, cum[L], 1.0)
    c += [up_to_S + f * scale for f in PROTOCOL.candidate_perturb_frac]
    headroom = max(0, spec.capacity - int(state.onhand.sum()) - int(state.pipe.sum()))
    return np.array(sorted({int(np.clip(np.rint(x), 0, headroom)) for x in c}), np.int64)


def is_boundary(cand, best_idx):
    """Best candidate at the top of the set, or at a non-zero bottom."""
    return bool(best_idx == len(cand) - 1 or (best_idx == 0 and cand[0] > 0))
