# Protocol amendments (v1.0 → v1.1)

**Date:** 19 October 2026. **Status:** all made BEFORE any benchmark-state result was computed.
They were prompted by engineering checks and by the DEV state set (30 states, seed 9999), which is
never reported. No allocation-method parameter (n0, batch, z, grid, branch threshold) was changed
after the DEV runs.

Protocol hash after amendments: run `python -c "from srep.config import protocol_hash; print(protocol_hash())"`.

| # | Section | Change | Reason |
|---|---|---|---|
| A1 | §5.3 cost | J = order + holding + waste + stockout penalty + **lost revenue on unmet units**. Total demand × price is dropped as a constant. | J then equals −(twin reward) + constant, exactly (unit-tested). Without the lost revenue, "never order" was optimal in every DEV state, because the twin's stockout penalty (0.50p) is below the unit purchase cost (0.55p). |
| A2 | §5.3 cost | Terminal credit: stock on hand and in the pipeline at the horizon end is valued at purchase cost (0.55p). | Without it, every unsold unit at the horizon end counts as pure cost, which biases towards under-ordering. Set `terminal_credit_frac = 0` to disable. |
| A3 | §5.3 continuation | The continuation policy is the SGSG `BootstrapPolicy` (s,S) rule, made age-aware (stock projected to expire unsold is removed from the inventory position) and calendar-aware. | A pure base-stock rule orders every day and pays the fixed order cost (8) daily. Any large day-1 order then looked good just by suppressing later orders, which pushed the optimum far outside the candidate set. |
| A4 | §5.2 candidates | Zero; the (s,S) choice; order-up-to-S; point-forecast order-up-to over k = L…L+SL days (6 levels); 0.9/0.99 demand quantiles over L+1 days; ±20% of order-up-to-S. Rounded, clipped, de-duplicated, so K varies (2–12 on DEV, median 9). A boundary diagnostic flags states whose best candidate is the largest one. | The candidates must bracket the optimum. On DEV: 0/30 boundary states; the best candidate is within a median of 0.6% of one day's cost of a 14-point wide-grid optimum. |
| A5 | §5.4 reference | The reference grid runs 5k → 80k rollouts. The reference counts as adequate when every candidate's regret label is settled: SE(d) ≤ 0.1 × 0.5% × J*, or \|d − 0.5% × J*\| ≥ 3 SE(d). States that are not adequate are flagged; results are reported with and without them. | The original "stable paired differences" rule almost never held, because near-tied candidates whose differences are irrelevant keep moving. With the new rule, 95% of DEV state-horizons are adequate. |
| A6 | scope | Perishable families only (bakery 3 d, produce 5 d, dairy 10 d; 165 SKUs). | Shelf-stable families (180–270 d) cannot show the expiry consequences of an order within 7–14 days. |
| A7 | §5.1 CRN | Supply outcomes are drawn for every (scenario, day) whether or not an order is placed. | Removes the supply-stream desynchronisation in `twin/digital_twin.py`, so paired differences reflect only the actions. |
| A8 | §7 | Sequential elimination frozen at n0 = 20, batch = 10, z = 1.96, with no multiplicity correction. The budget is N × K rollouts, matched to Uniform-N. | §7 required these to be fixed before running. |
| A9 | §4, §9 | Rollout grid {10, 25, 50, 100, 250, 500, 1000}. "Very small budgets" means 10 or 25 rollouts meeting the criterion in every family. | Plan B needs a grid, and the stop rule needed a number. |

## Author decisions (19 October 2026, before any benchmark-state result)

* **A1–A9 accepted in full.** Protocol v1.1 is frozen with protocol hash `716b58310fc3c0e3`.
* **Regret normalisation unchanged.** The branch rule uses the protocol §4 definition,
  r_rel = regret / |J\*(14-day)|, with a threshold of 0.5%. `r_rel_daily = H × r_rel` is reported as a
  secondary, descriptive measure only and plays no part in the branch decision. In the paper, state that
  0.5% of the 14-day cost corresponds to 7% of one average day's cost.
* **Deviation D1 (19 Oct 2026):** `benchmark_compute.py` was run once on the author's MacBook Air in DEV
  mode before budget.json was complete. Timing results (median 15.6 ms per state at N = 1000, H = 14) were
  therefore seen before the budget was frozen, which deviates from protocol §2. The budget values are
  justified by the intended deployment alone. The paper's limitations section must disclose this
  deviation. No regret result had been computed at that point.
* **Day-2 regret benchmark is run by the assistant** in the cloud workspace. Regret does not depend on
  hardware. The timing benchmark (RQ1) is run on the author's MacBook Air, which is the hardware
  declared in budget.json.

## v1.2 — Plan B regime factors and sign-off (20–21 October 2026)

* **Sign-off (§17):** confirmed by the author before any benchmark-state regret result was computed.
* **OFFICIAL timing (RQ1):** MacBook Air, 10 cores, 24 GB RAM, 10 workers. Operational full rollout
  (N = 1000, H = 14) takes a mean of 15.5 ms per state, so 50,000 states take a projected 77 s
  against a 7,200 s nightly budget. The budget is met at every N up to 5,000 (378 s).
  → **Branch rule: PLAN B**, because full simulation is affordable. The surrogate is not built.
* **A10, Plan B regime factors, fixed before results:**
  - Shelf life: 3 / 5 / 10 days, given by product family.
  - Demand variability: volume tertile within family. Poisson CV falls as volume rises, so the demand
    model is unchanged.
  - Shortage-to-waste cost ratio: low = 1.0, base = 2.73 (the twin's own costs), high = 5.0. Only the
    per-unit stockout cost is scaled. Candidates and the continuation policy are cost-independent and so
    identical across ratios. Headline results use base; low and high are the robustness factor for H2.
  - Candidate separation: reference margin between the best and second-best candidate ≤ 0.5% of J*
    (near-tied) or above it (clear). This is the H3B stratum.
* Protocol hash after A10: `1efa0b18cd1078c6`. Base-ratio computations are identical to v1.1.
