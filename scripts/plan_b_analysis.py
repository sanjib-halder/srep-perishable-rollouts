"""
Plan B analysis (protocol §9-§13, A10).

Reads results/day2_benchmark_{base,low,high}.csv and writes:
  results/planB_tables.md        all tables, with state-cluster bootstrap CIs
  results/planB_summary.json     machine-readable headline numbers
  results/fig1_frontier.{png,pdf}       regret-compute frontier, base costs, H = 14
  results/fig2_required.{png,pdf}       rollouts needed per regime cell x cost ratio
  results/fig3_separation.{png,pdf}     uniform vs sequential elimination by candidate separation

Primary analysis: all states. Sensitivity: states whose reference is adequate.
CIs: 95% percentile bootstrap, resampling SKUs (items) with replacement (B = 2000),
so repeated states of the same SKU are not treated as independent.
"""
import json
import os
import sys

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from srep.config import PROTOCOL, COST_RATIOS

RES = os.path.join(ROOT, "results")
THR = PROTOCOL.branch_regret_threshold
TARGET = PROTOCOL.branch_state_fraction
B = 2000
RNG = np.random.default_rng(2026)

BLUE, ORANGE = "#2a78d6", "#eb6834"
INK, INK2, GRID = "#1f1f1e", "#5f5e58", "#e4e3df"
FAM_ORDER = ["BREAD/BAKERY", "PRODUCE", "DAIRY"]
FAM_LABEL = {"BREAD/BAKERY": "Bakery (3 d)", "PRODUCE": "Produce (5 d)", "DAIRY": "Dairy (10 d)"}
VOL_LABEL = {0: "Low volume\n(high CV)", 1: "Medium", 2: "High volume\n(low CV)"}
METH = {"uniform": "Uniform", "seq_elim": "Seq. elimination"}


# ----------------------------------------------------------------- helpers
def load():
    frames = []
    for r in ("base", "low", "high"):
        p = os.path.join(RES, f"day2_benchmark_{r}.csv")
        if os.path.exists(p):
            frames.append(pd.read_csv(p))
    df = pd.concat(frames, ignore_index=True)
    df["ok"] = df.r_rel <= THR
    df["near_tied"] = df.margin_rel <= THR
    df["rollouts_per_cand"] = df.rollouts / df.K
    return df


def cluster_boot(d, stat, by="item"):
    """Percentile CI for stat(d) resampling clusters (SKUs)."""
    groups = [g for _, g in d.groupby(by)]
    n = len(groups)
    vals = []
    for _ in range(B):
        idx = RNG.integers(0, n, n)
        vals.append(stat(pd.concat([groups[i] for i in idx], ignore_index=True)))
    return np.percentile(vals, [2.5, 97.5])


def fmt_ci(x, ci, pct=True):
    if pct:
        return f"{100*x:.1f}% [{100*ci[0]:.1f}, {100*ci[1]:.1f}]"
    return f"{x:.4f} [{ci[0]:.4f}, {ci[1]:.4f}]"


def required_N(d):
    """Smallest grid N at which >= TARGET of states meet the regret threshold."""
    for N in PROTOCOL.rollout_grid:
        s = d[d.N == N]
        if len(s) and s.ok.mean() >= TARGET:
            return N
    return np.inf


def style(ax):
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    for sp in ("left", "bottom"):
        ax.spines[sp].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=8, length=0)
    ax.grid(True, color=GRID, lw=0.6)
    ax.set_axisbelow(True)


# ----------------------------------------------------------------- tables
def table_main(df, H, ratio="base"):
    d = df[(df.cost_ratio == ratio) & (df.H == H)]
    rows = []
    for m in ("uniform", "seq_elim"):
        for N in PROTOCOL.rollout_grid:
            s = d[(d.method == m) & (d.N == N)]
            ci = cluster_boot(s, lambda x: x.ok.mean())
            rows.append(dict(method=METH[m], N=N, mean_rollouts=s.rollouts.mean(),
                             p_correct=s.correct.mean(), ok=s.ok.mean(), ok_ci=ci,
                             med=s.r_rel.median(), p95=s.r_rel.quantile(.95), mx=s.r_rel.max()))
    return pd.DataFrame(rows)


def table_matched(df, H, ratio="base"):
    """Seq. elimination minus uniform at the same budget N x K (paired by state)."""
    d = df[(df.cost_ratio == ratio) & (df.H == H)]
    u = d[d.method == "uniform"].set_index(["state_id", "N"])
    s = d[d.method == "seq_elim"].set_index(["state_id", "N"])
    j = u[["item", "r_rel", "ok", "rollouts", "near_tied"]].join(
        s[["r_rel", "ok", "rollouts"]], rsuffix="_se").reset_index()
    j["d_rel"] = j.r_rel_se - j.r_rel
    j["d_ok"] = j.ok_se.astype(float) - j.ok.astype(float)
    j["roll_ratio"] = j.rollouts_se / j.rollouts
    rows = []
    for stratum, g0 in (("all", j), ("near-tied", j[j.near_tied]), ("clear", j[~j.near_tied])):
        for N in PROTOCOL.rollout_grid:
            g = g0[g0.N == N]
            if len(g) < 5:
                continue
            ci_ok = cluster_boot(g, lambda x: x.d_ok.mean())
            ci_rel = cluster_boot(g, lambda x: x.d_rel.mean())
            rows.append(dict(stratum=stratum, N=N, n=len(g), d_ok=g.d_ok.mean(), d_ok_ci=ci_ok,
                             d_rel=g.d_rel.mean(), d_rel_ci=ci_rel, roll_ratio=g.roll_ratio.mean()))
    return pd.DataFrame(rows)


def table_required(df, H, method="uniform"):
    d = df[(df.H == H) & (df.method == method)]
    rows = []
    for ratio in ("low", "base", "high"):
        dr = d[d.cost_ratio == ratio]
        if not len(dr):
            continue
        for fam in FAM_ORDER:
            for vt in (0, 1, 2):
                c = dr[(dr.family == fam) & (dr.volume_tertile == vt)]
                rows.append(dict(cost_ratio=ratio, family=fam, volume_tertile=vt,
                                 n_states=c.state_id.nunique(), N_required=required_N(c),
                                 ok_at_100=c[c.N == 100].ok.mean()))
            c = dr[dr.family == fam]
            rows.append(dict(cost_ratio=ratio, family=fam, volume_tertile="all",
                             n_states=c.state_id.nunique(), N_required=required_N(c),
                             ok_at_100=c[c.N == 100].ok.mean()))
        rows.append(dict(cost_ratio=ratio, family="all", volume_tertile="all",
                         n_states=dr.state_id.nunique(), N_required=required_N(dr),
                         ok_at_100=dr[dr.N == 100].ok.mean()))
    return pd.DataFrame(rows)


# ----------------------------------------------------------------- figures
def fig_frontier(df, H=14):
    d = df[(df.cost_ratio == "base") & (df.H == H)]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.0), dpi=200)
    specs = (("uniform", BLUE, "o"), ("seq_elim", ORANGE, "s"))
    for ax, (ylab, f) in zip(axes, (("States with regret ≤ 0.5% (%)", lambda s: 100 * s.ok.mean()),
                                    ("95th-percentile relative regret (%)", lambda s: 100 * s.r_rel.quantile(.95)))):
        for m, col, mk in specs:
            g = d[d.method == m].groupby("N")
            x = g.rollouts.mean().values / d.K.mean()
            y = np.array([f(s) for _, s in g])
            ax.plot(x, y, color=col, lw=2, marker=mk, ms=5, mec="white", mew=1, label=METH[m], zorder=3)
        ax.set_xscale("log")
        ax.set_xlabel("Mean rollouts per candidate (log scale)", fontsize=8, color=INK2)
        ax.set_ylabel(ylab, fontsize=8, color=INK2)
        style(ax)
    axes[0].axhline(100 * TARGET, color=INK2, lw=1, ls=(0, (3, 3)), zorder=2)
    axes[0].annotate("95% criterion", (axes[0].get_xlim()[0], 100 * TARGET), xytext=(4, 3),
                     textcoords="offset points", fontsize=7, color=INK2)
    axes[1].axhline(100 * THR, color=INK2, lw=1, ls=(0, (3, 3)), zorder=2)
    axes[1].annotate("0.5% threshold", (axes[1].get_xlim()[0], 100 * THR), xytext=(4, 3),
                     textcoords="offset points", fontsize=7, color=INK2)
    axes[0].legend(frameon=False, fontsize=7, loc="lower right")
    axes[1].legend(frameon=False, fontsize=7, loc="upper right")
    fig.suptitle(f"Decision quality vs simulation effort (base costs, H = {H}, {d.state_id.nunique()} states)",
                 fontsize=9, color=INK, x=0.01, ha="left")
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(RES, f"fig1_frontier.{ext}"), bbox_inches="tight")
    plt.close(fig)


def fig_required(req):
    ratios = [r for r in ("low", "base", "high") if r in set(req.cost_ratio)]
    grid = list(PROTOCOL.rollout_grid)
    ramp = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
    fig, axes = plt.subplots(1, len(ratios), figsize=(2.6 * len(ratios), 2.6), dpi=200, sharey=True)
    axes = np.atleast_1d(axes)
    for ax, r in zip(axes, ratios):
        t = req[(req.cost_ratio == r) & (req.family != "all") & (req.volume_tertile != "all")]
        M = np.zeros((3, 3))
        for i, fam in enumerate(FAM_ORDER):
            for j in range(3):
                M[i, j] = t[(t.family == fam) & (t.volume_tertile == j)].N_required.iloc[0]
        for i in range(3):
            for j in range(3):
                v = M[i, j]
                k = len(ramp) - 1 if not np.isfinite(v) else grid.index(int(v))
                ax.add_patch(plt.Rectangle((j, 2 - i), 0.96, 0.96, color=ramp[k], lw=0))
                ax.text(j + 0.48, 2 - i + 0.48, ">1000" if not np.isfinite(v) else f"{int(v)}",
                        ha="center", va="center", fontsize=8, color="white" if k >= 3 else INK)
        ax.set_xlim(0, 3); ax.set_ylim(0, 3)
        ax.set_xticks([0.48, 1.48, 2.48]); ax.set_xticklabels([VOL_LABEL[j] for j in range(3)], fontsize=6.5, color=INK2)
        ax.set_yticks([2.48, 1.48, 0.48]); ax.set_yticklabels([FAM_LABEL[f] for f in FAM_ORDER], fontsize=7, color=INK2)
        ax.tick_params(length=0)
        for sp in ax.spines.values():
            sp.set_visible(False)
        ax.set_title(f"Shortage:waste = {COST_RATIOS[r]:.1f}" + (" (base)" if r == "base" else ""),
                     fontsize=8, color=INK)
    fig.suptitle("Uniform rollouts per candidate needed for ≥95% of states within 0.5% regret (H = 14)",
                 fontsize=9, color=INK, x=0.01, ha="left")
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(RES, f"fig2_required.{ext}"), bbox_inches="tight")
    plt.close(fig)


def fig_separation(df, H=14):
    d = df[(df.cost_ratio == "base") & (df.H == H)]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.9), dpi=200, sharey=True)
    for ax, (name, mask) in zip(axes, (("Near-tied candidates (margin ≤ 0.5%)", d.near_tied),
                                        ("Clearly separated candidates", ~d.near_tied))):
        s = d[mask]
        for m, col, mk in (("uniform", BLUE, "o"), ("seq_elim", ORANGE, "s")):
            g = s[s.method == m].groupby("N")
            x = g.rollouts.mean().values / s.K.mean()
            y = 100 * g.ok.mean().values
            ax.plot(x, y, color=col, lw=2, marker=mk, ms=5, mec="white", mew=1, label=METH[m], zorder=3)
        ax.axhline(100 * TARGET, color=INK2, lw=1, ls=(0, (3, 3)))
        ax.set_xscale("log")
        ax.set_title(f"{name}  (n = {s.state_id.nunique()})", fontsize=8, color=INK)
        ax.set_xlabel("Mean rollouts per candidate (log scale)", fontsize=8, color=INK2)
        style(ax)
    axes[0].set_ylabel("States with regret ≤ 0.5% (%)", fontsize=8, color=INK2)
    axes[0].legend(frameon=False, fontsize=7, loc="lower right")
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(RES, f"fig3_separation.{ext}"), bbox_inches="tight")
    plt.close(fig)


# ----------------------------------------------------------------- main
def md_table(df, cols, header):
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    for _, r in df.iterrows():
        out.append("| " + " | ".join(c(r) if callable(c) else str(r[c]) for c in cols) + " |")
    return "\n".join(out)


def main():
    df = load()
    st = df.drop_duplicates(["state_id", "H", "cost_ratio"])
    out = ["# Plan B results (auto-generated by scripts/plan_b_analysis.py)\n",
           f"Protocol hash: {json.load(open(os.path.join(RES, 'day2_benchmark_base_decision.json')))['protocol_hash']}\n",
           f"States: {df.state_id.nunique()}; horizons {sorted(df.H.unique())}; cost ratios {sorted(df.cost_ratio.unique())}.\n",
           "## Reference quality\n",
           md_table(st.groupby(["cost_ratio", "H"]).agg(adequate=("ref_converged", "mean"), boundary=("boundary", "mean"),
                                                        near_tied=("near_tied", "mean"), K=("K", "mean")).reset_index(),
                    ["cost_ratio", "H", lambda r: f"{100*r.adequate:.1f}%", lambda r: f"{100*r.boundary:.1f}%",
                     lambda r: f"{100*r.near_tied:.1f}%", lambda r: f"{r.K:.1f}"],
                    ["cost ratio", "H", "reference adequate", "best at candidate boundary", "near-tied states", "mean K"]), ""]

    summary = {}
    for H in PROTOCOL.horizons:
        t = table_main(df, H)
        out += [f"## Table 1 (H = {H}, base costs): decision quality by method and budget\n",
                md_table(t, ["method", "N", lambda r: f"{r.mean_rollouts:.0f}", lambda r: f"{100*r.p_correct:.1f}%",
                             lambda r: fmt_ci(r.ok, r.ok_ci), lambda r: f"{100*r.med:.3f}%",
                             lambda r: f"{100*r.p95:.3f}%", lambda r: f"{100*r.mx:.3f}%"],
                         ["method", "N/candidate (budget)", "mean rollouts used", "P(reference-best)",
                          "states ≤0.5% regret [95% CI]", "median regret", "p95 regret", "max regret"]), ""]
        summary[f"H{H}_main"] = t.drop(columns="ok_ci").to_dict("records")

        tm = table_matched(df, H)
        out += [f"## Table 2 (H = {H}, base): sequential elimination − uniform at matched budget (paired)\n",
                "Positive Δ share = SE better; negative Δ regret = SE better. `rollout ratio` = SE rollouts used / budget.\n",
                md_table(tm, ["stratum", "N", "n", lambda r: fmt_ci(r.d_ok, r.d_ok_ci),
                              lambda r: f"{100*r.d_rel:.4f}% [{100*r.d_rel_ci[0]:.4f}, {100*r.d_rel_ci[1]:.4f}]",
                              lambda r: f"{r.roll_ratio:.2f}"],
                         ["stratum", "N", "states", "Δ share ≤0.5% [CI]", "Δ mean regret [CI]", "rollout ratio"]), ""]
        summary[f"H{H}_matched"] = tm.drop(columns=["d_ok_ci", "d_rel_ci"]).to_dict("records")

        req = table_required(df, H)
        out += [f"## Table 3 (H = {H}): uniform rollouts per candidate required (≥95% of states within 0.5%)\n",
                md_table(req, ["cost_ratio", "family", "volume_tertile", "n_states",
                               lambda r: ">1000" if not np.isfinite(r.N_required) else str(int(r.N_required)),
                               lambda r: f"{100*r.ok_at_100:.1f}%"],
                         ["cost ratio", "family", "volume tertile", "states", "N required", "share ok at N=100"]), ""]
        summary[f"H{H}_required"] = req.replace({np.inf: None}).to_dict("records")
        if H == PROTOCOL.primary_horizon:
            fig_required(req)

    # sensitivity: adequate references only
    adq = df[df.ref_converged]
    out += ["## Sensitivity: adequate references only (H = 14, base)\n"]
    t = table_main(adq, 14)
    out += [md_table(t, ["method", "N", lambda r: fmt_ci(r.ok, r.ok_ci), lambda r: f"{100*r.p95:.3f}%"],
                     ["method", "N", "states ≤0.5% [CI]", "p95 regret"]), ""]

    fig_frontier(df)
    fig_separation(df)
    with open(os.path.join(RES, "planB_tables.md"), "w") as f:
        f.write("\n".join(out))
    with open(os.path.join(RES, "planB_summary.json"), "w") as f:
        json.dump(summary, f, indent=1, default=float)
    print("\n".join(out))


if __name__ == "__main__":
    main()
