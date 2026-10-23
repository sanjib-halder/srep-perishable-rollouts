"""
Frozen protocol constants (Revised Protocol v1.0, 19 Oct 2026).

Everything an experiment depends on lives here so that the protocol freeze
can be recorded as a single file hash. Changing any value after the Day-2
benchmark must be logged as a dated amendment (protocol §1 status box).
"""
from dataclasses import dataclass, field, asdict
import hashlib
import json

# --------------------------------------------------------------------------
# Cost model. Values are copied from twin/digital_twin.py (Section 10.4) so
# the engine reproduces the twin exactly.
#
# J is a COST equivalent to -reward up to a policy-independent constant:
#   -R = order + holding + waste + stockout_penalty - (D - unmet) * p
#      = [order + holding + waste + stockout_penalty + unmet * p] - D * p
# Under CRN, sum(D * p) is identical for every candidate, so it is dropped
# (it would only inflate the regret denominator) -- but the LOST REVENUE on
# unmet demand (unmet * p) must stay. Dropping it makes "never order"
# optimal, because the twin's stockout penalty (0.50p) is below the unit
# purchase cost (0.55p).
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class CostParams:
    holding_per_unit_day: float = 0.03
    order_fixed: float = 8.0
    order_variable_frac: float = 0.55
    stockout_lost_revenue_frac: float = 1.0
    stockout_lost_margin_frac: float = 0.35
    stockout_service_penalty_frac: float = 0.15
    waste_frac: float = 0.55
    # End-of-horizon credit for stock still on hand or in the pipeline,
    # valued at purchase cost. Without it, every unit still unsold when the
    # rollout ends counts as pure cost and the horizon biases towards
    # under-ordering. Set to 0.0 to reproduce the twin's raw horizon reward.
    terminal_credit_frac: float = 0.55
    # A10 (Plan B cost-ratio factor): multiplies the whole per-unit stockout
    # cost. 1.0 = the twin's own costs (shortage-to-waste ratio 1.5/0.55 = 2.73).
    stockout_scale: float = 1.0

    @property
    def stockout_frac(self):
        return self.stockout_scale * (self.stockout_lost_revenue_frac + self.stockout_lost_margin_frac + self.stockout_service_penalty_frac)

    @property
    def shortage_to_waste_ratio(self):
        return self.stockout_frac / self.waste_frac


# --------------------------------------------------------------------------
# Experimental design constants.
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class Protocol:
    # Scope: perishable families only (shelf life 3/5/10 days). Shelf-stable
    # families (180-270 days) are excluded: a 7-14 day horizon cannot observe
    # the expiry consequences of their orders.
    families: tuple = ("BREAD/BAKERY", "PRODUCE", "DAIRY")
    horizons: tuple = (7, 14)
    primary_horizon: int = 14

    # Rollout budgets (per candidate). Branch rule uses 100.
    rollout_grid: tuple = (10, 25, 50, 100, 250, 500, 1000)
    branch_rollouts: int = 100
    operational_full_rollouts: int = 1000

    # Reference: increase until action identity and paired differences
    # stabilise (§5.4). Checked in this order.
    reference_grid: tuple = (5000, 10000, 20000, 40000, 80000)
    # The reference is ADEQUATE when every candidate's regret label is
    # settled: for each candidate, the paired difference d to the best has
    #   SE(d) <= ref_se_frac * threshold * J*        (precise), or
    #   |d - threshold * J*| >= ref_z * SE(d)         (clearly on one side).
    # Candidates with d < ref_z * SE(d) are statistical ties with the best.
    ref_se_frac: float = 0.1
    ref_z: float = 3.0

    # Branch rule (§4): relative regret <= 0.5% in >= 95% of states.
    branch_regret_threshold: float = 0.005
    branch_state_fraction: float = 0.95
    # Stop rule: "very small" budgets = these.
    stop_small_budgets: tuple = (10, 25)
    regret_eps: float = 1e-6

    # Paired sequential elimination (§7) -- frozen parameters.
    se_n0: int = 20
    se_batch: int = 10
    se_z: float = 1.96            # per-comparison two-sided 95%; no multiplicity correction (heuristic)

    # Scenario blocks: scenario r of state s is generated from block r // block_size.
    block_size: int = 10

    # Candidate generation (§5.2).
    candidate_quantiles: tuple = (0.9, 0.99)
    candidate_coverage_levels: int = 6
    candidate_perturb_frac: tuple = (-0.2, 0.2)

    # Continuation policy (§5.3): age-aware (s,S), i.e. the SGSG
    # BootstrapPolicy rule (safety 1.3, review horizon min(SL, max(L+3, 50)))
    # with projected-outdating correction. See engine.AgeAwareSSPolicy.
    cont_review_days: int = 1
    cont_safety_factor: float = 1.3

    # Seeds. Operational and reference streams are disjoint.
    seed_operational: int = 20261019
    seed_reference: int = 77_000_001
    seed_states_benchmark: int = 1_000
    seed_states_dev: int = 9_999    # dev/smoke-test states: never used for reported results

    n_benchmark_states: int = 500
    n_dev_states: int = 30


COSTS = CostParams()

# A10: shortage-to-waste cost-ratio levels for the Plan B regime factor.
_BASE_STOCKOUT = 1.0 + 0.35 + 0.15
COST_RATIOS = {"low": 1.0, "base": _BASE_STOCKOUT / 0.55, "high": 5.0}


def costs_for_ratio(level):
    return CostParams(stockout_scale=COST_RATIOS[level] * 0.55 / _BASE_STOCKOUT)
PROTOCOL = Protocol()


def protocol_hash():
    blob = json.dumps({"costs": asdict(COSTS), "protocol": asdict(PROTOCOL)}, sort_keys=True, default=list)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]
