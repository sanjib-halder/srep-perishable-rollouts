"""
Simulation-allocation methods (protocol §6-7) and the large-rollout reference.

Budget unit: one ROLLOUT = one candidate simulated over one scenario for H
days. Uniform-N uses N x K rollouts; sequential elimination is given the
same total and may stop early.

Operational methods draw scenarios from seed_operational; the reference
draws from the disjoint seed_reference stream, so Monte-Carlo noise in an
operational estimate is never correlated with the reference it is scored on.
"""
from dataclasses import dataclass
import numpy as np

from .config import PROTOCOL, COSTS
from .scenarios import draw_scenarios
from .engine import simulate

CHUNK = 2000  # scenarios per engine call (bounds memory)


@dataclass
class Problem:
    spec: object
    state: object
    cand: np.ndarray
    policy: object
    H: int
    state_id: int
    dm: object
    costs_params: object = COSTS

    @property
    def K(self):
        return len(self.cand)

    def costs(self, seed, r0, r1, cols=None):
        """(r1-r0, K') matrix of total costs for candidates `cols` (default all)."""
        acts = self.cand if cols is None else self.cand[cols]
        out = []
        for a in range(r0, r1, CHUNK):
            b = min(r1, a + CHUNK)
            scen = draw_scenarios(self.dm, self.spec.item, self.state.t0, self.H, seed, self.state_id, a, b)
            out.append(simulate(self.spec, self.state, scen, self.H, acts, self.policy, costs=self.costs_params))
        return np.concatenate(out, axis=0)


# ------------------------------------------------------------------ reference
def reference(prob, grid=PROTOCOL.reference_grid):
    """Increase rollouts along `grid` until every candidate's regret label is
    settled (see config.Protocol.ref_se_frac / ref_z). Returns means, best
    index, R used, adequacy flag, paired-difference SEs and number of
    candidates statistically tied with the best."""
    P = PROTOCOL
    seed = P.seed_reference
    J_all = []
    n = 0
    history = []
    for R in grid:
        J_all.append(prob.costs(seed, n, R))
        n = R
        Jc = np.concatenate(J_all, 0)
        means = Jc.mean(0)
        best = int(np.argmin(means))
        d = means - means[best]
        se = (Jc - Jc[:, [best]]).std(0, ddof=1) / np.sqrt(n)
        thr = P.branch_regret_threshold * (abs(means[best]) + P.regret_eps)
        settled = (se <= P.ref_se_frac * thr) | (np.abs(d - thr) >= P.ref_z * se)
        settled[best] = True
        history.append(dict(R=R, best=best, unsettled=int((~settled).sum())))
        if settled.all():
            break
    ties = int(((d < P.ref_z * se) & (np.arange(prob.K) != best)).sum())
    return dict(means=means, best=best, R=n, converged=bool(settled.all()), paired_se=se,
                n_ties=ties, history=history)


# ------------------------------------------------------------------ operational
def uniform(prob, N, J=None):
    """Uniform allocation: N rollouts per candidate on scenarios [0, N).
    Pass a precomputed cost matrix J (>= N rows) to reuse simulations."""
    if J is None:
        J = prob.costs(PROTOCOL.seed_operational, 0, N)
    means = J[:N].mean(0)
    return dict(choice=int(np.argmin(means)), rollouts=N * prob.K, means=means)


def sequential_elimination(prob, budget, n0=PROTOCOL.se_n0, batch=PROTOCOL.se_batch, z=PROTOCOL.se_z, J=None):
    """Paired sequential elimination (protocol §7). Heuristic: per-comparison
    z bounds on PAIRED differences to the incumbent, no multiplicity
    correction, no probability-of-correct-selection guarantee.

    All surviving candidates always share the same scenario index set [0, n),
    so every comparison is a CRN-paired comparison. `J` may be a precomputed
    (>= needed rows, K) cost matrix on the operational stream; otherwise
    simulations are run on demand for survivors only."""
    K = prob.K
    alive = np.ones(K, bool)
    cols = {}
    used = 0
    n = 0

    def extend(m):
        nonlocal used, n
        idx = np.nonzero(alive)[0]
        if J is not None:
            new = J[n:n + m][:, idx]
        else:
            new = prob.costs(PROTOCOL.seed_operational, n, n + m, cols=idx)
        for j, k in enumerate(idx):
            cols.setdefault(k, []).append(new[:, j])
        used += m * len(idx)
        n += m

    first = min(n0, max(1, budget // K))
    extend(first)
    while True:
        idx = np.nonzero(alive)[0]
        M = np.column_stack([np.concatenate(cols[k])[:n] for k in idx])
        means = M.mean(0)
        inc = int(np.argmin(means))
        if n >= 2:
            D = M - M[:, [inc]]
            se = D.std(0, ddof=1) / np.sqrt(n)
            worse = (D.mean(0) - z * se > 0)
            worse[inc] = False
            alive[idx[worse]] = False
        idx = np.nonzero(alive)[0]
        if len(idx) == 1:
            break
        room = (budget - used) // len(idx)
        if room < 1:
            break
        extend(min(batch, room))
    idx = np.nonzero(alive)[0]
    M = np.column_stack([np.concatenate(cols[k])[:n] for k in idx])
    choice = int(idx[np.argmin(M.mean(0))])
    return dict(choice=choice, rollouts=used, n_final=n, survivors=int(len(idx)))


def regret(ref, choice, H):
    best = ref["best"]
    J = ref["means"]
    r_abs = float(J[choice] - J[best])
    return dict(regret_abs=r_abs,
                r_rel=r_abs / (abs(J[best]) + PROTOCOL.regret_eps),            # protocol §4 definition
                r_rel_daily=r_abs / (abs(J[best]) / H + PROTOCOL.regret_eps),   # per average day of cost
                correct=bool(choice == best))


def ocba(prob, budget, n0=PROTOCOL.se_n0, delta_per_cand=PROTOCOL.se_batch, J=None):
    """Optimal computing budget allocation (Chen et al., 2000), sequential version.

    Start with n0 rollouts per candidate; then repeatedly add delta_per_cand x K
    rollouts, distributed so that the allocation approaches the OCBA ratios
        N_i / N_j = (s_i / d_i)^2 / (s_j / d_j)^2   for i, j != b,
        N_b = s_b * sqrt( sum_{i != b} N_i^2 / s_i^2 ),
    where b is the current best, d_i its mean gap to candidate i and s_i the
    sample standard deviation of candidate i. Candidate i always uses scenarios
    [0, N_i), so overlapping scenarios remain common across candidates.
    Spends the whole budget; selects the lowest sample mean.
    `J` is an operational-stream cost matrix with at least `budget` rows."""
    K = prob.K
    if J is None:
        J = prob.costs(PROTOCOL.seed_operational, 0, budget)
    n0 = max(2, min(n0, budget // K))
    n = np.full(K, n0)
    used = n0 * K
    step = max(K, delta_per_cand * K)
    while used < budget:
        means = np.array([J[:n[i], i].mean() for i in range(K)])
        sds = np.array([J[:n[i], i].std(ddof=1) for i in range(K)]) + 1e-9
        b = int(np.argmin(means))
        d = np.abs(means - means[b])
        d[d < 1e-9] = 1e-9
        r = (sds / d) ** 2
        r[b] = 0.0
        others = np.arange(K) != b
        r[b] = sds[b] * np.sqrt(np.sum(r[others] ** 2 / sds[others] ** 2)) if K > 1 else 1.0
        total = min(budget, used + step)
        target = total * r / r.sum()
        add = np.maximum(0, np.floor(target - n)).astype(int)
        room = total - used
        if add.sum() > room:
            add = np.floor(add * room / add.sum()).astype(int)
        if add.sum() == 0:
            add[b] = room
        n = n + add
        used += int(add.sum())
    means = np.array([J[:n[i], i].mean() for i in range(K)])
    return dict(choice=int(np.argmin(means)), rollouts=int(used), n_max=int(n.max()))


def ocba_paired(prob, budget, n0=PROTOCOL.se_n0, delta_per_cand=PROTOCOL.se_batch, J=None):
    """OCBA with correlation-aware noise (in the spirit of Fu et al., 2007, correlated sampling).

    Identical to `ocba` except for the noise used in the allocation ratios: the
    marginal standard deviation of each non-best candidate a is replaced by the
    standard deviation of its paired difference to the current best b, on the
    common scenarios both have, divided by sqrt(2); the best uses the root mean
    square of these values. Under common random numbers this is much smaller
    than the marginal spread, so near-tied pairs are recognised as close but
    cheap to separate."""
    K = prob.K
    if J is None:
        J = prob.costs(PROTOCOL.seed_operational, 0, budget)
    n0 = max(2, min(n0, budget // K))
    n = np.full(K, n0)
    used = n0 * K
    step = max(K, delta_per_cand * K)
    while used < budget:
        means = np.array([J[:n[i], i].mean() for i in range(K)])
        b = int(np.argmin(means))
        sd = np.empty(K)
        for i in range(K):
            if i == b:
                continue
            m = min(n[i], n[b])
            sd[i] = (J[:m, i] - J[:m, b]).std(ddof=1) / np.sqrt(2) + 1e-9
        others = np.arange(K) != b
        sd[b] = np.sqrt(np.mean(sd[others] ** 2)) if K > 1 else 1.0
        d = np.abs(means - means[b]); d[d < 1e-9] = 1e-9
        r = (sd / d) ** 2
        r[b] = sd[b] * np.sqrt(np.sum(r[others] ** 2 / sd[others] ** 2)) if K > 1 else 1.0
        total = min(budget, used + step)
        target = total * r / r.sum()
        add = np.maximum(0, np.floor(target - n)).astype(int)
        room = total - used
        if add.sum() > room:
            add = np.floor(add * room / add.sum()).astype(int)
        if add.sum() == 0:
            add[b] = room
        n = n + add
        used += int(add.sum())
    means = np.array([J[:n[i], i].mean() for i in range(K)])
    return dict(choice=int(np.argmin(means)), rollouts=int(used), n_max=int(n.max()))
