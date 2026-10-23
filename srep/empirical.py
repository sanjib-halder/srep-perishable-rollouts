"""
Data-driven demand for rollouts (amendment A11, replication on raw Favorita).

Future demand for a store-item is resampled from that store-item's OWN past
sales, in 7-day blocks aligned by weekday, from a trailing window that ends
before the decision day (no look-ahead). A 14-day horizon uses two blocks
drawn independently. This keeps the real level, weekday pattern, zero days,
spikes and over-dispersion of the data, which the twin's Poisson model lacks.

Supplier draws and the scenario-indexing scheme are as in scenarios.py, so
common random numbers hold across candidates and methods.
"""
from dataclasses import dataclass
import numpy as np

from .config import PROTOCOL
from .engine import simulate
from .allocation import Problem, CHUNK

WINDOW = 182          # trailing days of history used for resampling (26 weeks)


class EmpiricalDemand:
    def __init__(self, hist, t, window=WINDOW, first=0):
        self.hist = np.asarray(hist, np.int64)
        self.t = int(t)
        lo = max(int(first), self.t - window)
        self.starts = np.array([s for s in range(lo, self.t - 6) if (self.t - s) % 7 == 0], np.int64)
        if len(self.starts) < 4:
            raise ValueError("fewer than 4 weekday-aligned weeks of history before the decision day")
        blocks = np.stack([self.hist[s:s + 7] for s in self.starts])      # (n_weeks, 7)
        self.weekday_mean = blocks.mean(0)                                 # expected demand on day t+j, j=0..6

    def mean_demand(self, n):
        return np.maximum(self.weekday_mean[np.arange(n) % 7], 0.0)

    def demand_paths(self, rng, R, H):
        nb = (H + 6) // 7
        pick = self.starts[rng.integers(0, len(self.starts), size=(R, nb))]       # (R, nb)
        offs = np.arange(7)
        d = self.hist[pick[:, :, None] + offs[None, None, :]].reshape(R, nb * 7)
        return d[:, :H]

    def draw(self, H, seed, state_id, r0, r1):
        B = PROTOCOL.block_size
        b0, b1 = r0 // B, (r1 + B - 1) // B
        out = []
        for b in range(b0, b1):
            rng = np.random.default_rng([seed, state_id, b, 31])
            out.append(dict(demand=self.demand_paths(rng, B, H),
                            u_delay=rng.random((B, H)), delay_int=rng.integers(1, 6, size=(B, H)),
                            z_fill=rng.standard_normal((B, H)), z_lead=rng.standard_normal((B, H))))
        res = {k: np.concatenate([o[k] for o in out])[r0 - b0 * B: r1 - b0 * B] for k in out[0]}
        return res

    def protection_samples(self, days, n=4000, seed=0):
        """Demand over the `days` days after the decision day (t+1 .. t+days)."""
        rng = np.random.default_rng([seed, self.t, 4242])
        return self.demand_paths(rng, n, days + 1)[:, 1:].sum(1)


@dataclass
class EmpiricalProblem(Problem):
    emp: object = None

    def costs(self, seed, r0, r1, cols=None):
        acts = self.cand if cols is None else self.cand[cols]
        out = []
        for a in range(r0, r1, CHUNK):
            b = min(r1, a + CHUNK)
            scen = self.emp.draw(self.H, seed, self.state_id, a, b)
            out.append(simulate(self.spec, self.state, scen, self.H, acts, self.policy, costs=self.costs_params))
        return np.concatenate(out, axis=0)
