"""
Figures 2-4 of the WCSC 2027 manuscript (Fig. 1 is a drawn diagram and is not made here).

  Fig. 2  results/paper_fig2_frontier.{png,pdf}
          Share of decisions within 0.5% regret vs mean rollouts per candidate actually used,
          uniform / sequential elimination / standard OCBA; twin states (left), Favorita states (right);
          base costs, H = 14.
  Fig. 3  results/paper_fig3_separation.{png,pdf}
          Same, uniform vs sequential elimination, near-tied vs clearly separated twin states.
  Fig. 4  results/paper_fig4_required.{png,pdf}
          Uniform rollouts per candidate needed for >= 95% of decisions within 0.5% regret,
          by family x volume tertile, for the three shortage-to-waste ratios (twin states, H = 14).

Inputs (written by notebook 2):
  results/nb02_original_base.csv, nb02_original_low.csv, nb02_original_high.csv   twin states
  results/nb02_replication_base.csv                                                Favorita states
Usage, from the srep folder:
  python3 scripts/make_figures_2_4.py
Needs only numpy, pandas and matplotlib.
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "results")

THR = 0.005                      # regret threshold delta
TARGET = 0.95                    # required share of states gamma
GRID = [10, 25, 50, 100, 250, 500, 1000]
RATIO_LABEL = {"low": "1.0", "base": "2.73 (base)", "high": "5.0"}   # as in Table 2
H = 14

BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
#INK, INK2, LINE = "#1f1f1e", "#5f5e58", "#e4e3df"
INK, INK2, LINE = "#000000", "#000000", "#e4e3df"
METHODS = (("uniform", "Uniform", BLUE, "o"), ("seq_elim", "Seq. elimination", ORANGE, "s"), ("ocba", "OCBA", AQUA, "^"))
FAM_ORDER = ["BREAD/BAKERY", "PRODUCE", "DAIRY"]
FAM_LABEL = {"BREAD/BAKERY": "Bakery (3 d)", "PRODUCE": "Produce (5 d)", "DAIRY": "Dairy (10 d)"}
VOL_LABEL = ["Low volume\n(high CV)", "Medium", "High volume\n(low CV)"]

matplotlib.rcParams["savefig.dpi"] = 600
matplotlib.rcParams["font.family"] = "DejaVu Sans"


# ------------------------------------------------------------------ data
def load(names):
    df = pd.concat([pd.read_csv(os.path.join(RES, n)) for n in names], ignore_index=True)
    df["ok"] = df.r_rel <= THR                    # decision within 0.5% regret
    df["near_tied"] = df.margin_rel <= THR        # two best candidates within 0.5% of reference cost
    return df[df.H == H]


def frontier(d, method):
    """x: total rollouts / total candidates at each budget; y: % of states within the threshold."""
    k_total = d.drop_duplicates("state_id").K.sum()
    g = d[d.method == method].groupby("N")
    return g.rollouts.sum().values / k_total, 100 * g.ok.mean().values


def required_N(d):
    for N in GRID:
        s = d[d.N == N]
        if len(s) and s.ok.mean() >= TARGET:
            return N
    return np.inf


def style(ax):
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    for sp in ("left", "bottom"):
        ax.spines[sp].set_color(LINE)
    ax.tick_params(colors=INK2, labelsize=8, length=0)
    ax.grid(True, color=LINE, lw=0.6)
    ax.set_axisbelow(True)


def save(fig, name):
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(RES, f"{name}.{ext}"), bbox_inches="tight")
    plt.close(fig)
    print("wrote", f"results/{name}.png/.pdf")


# ------------------------------------------------------------------ Fig. 2
def fig2(twin, fav):
    panels = ((twin[twin.cost_ratio == "base"], "Twin states (n = 500)"),
              (fav[fav.cost_ratio == "base"], "Favorita states (n = 3,000)"))
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.9), dpi=200, sharey=True)
    for ax, (d, title) in zip(axes, panels):
        for m, lab, col, mk in METHODS:
            x, y = frontier(d, m)
            ax.plot(x, y, color=col, lw=2, marker=mk, ms=5, mec="white", mew=1, label=lab, zorder=3)
        ax.axhline(100 * TARGET, color=INK2, lw=1, ls=(0, (3, 3)))
        ax.set_xscale("log"); ax.set_ylim(58, 101)
        ax.set_title(title, fontsize=8, color=INK)
        ax.set_xlabel("Mean rollouts per candidate used (log scale)", fontsize=8, color=INK2)
        style(ax)
    axes[0].set_ylabel("States with regret ≤ 0.5% (%)", fontsize=8, color=INK2)
    axes[0].annotate("95% target", (10, 95), xytext=(2, 3), textcoords="offset points", fontsize=7, color=INK2)
    axes[1].legend(frameon=False, fontsize=7, loc="lower right")
    save(fig, "paper_fig2_frontier")


# ------------------------------------------------------------------ Fig. 3
def fig3(twin):
    d = twin[twin.cost_ratio == "base"]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.9), dpi=200, sharey=True)
    for ax, (name, mask) in zip(axes, (("Near-tied candidates (margin ≤ 0.5%)", d.near_tied),
                                        ("Clearly separated candidates", ~d.near_tied))):
        s = d[mask]
        for m, lab, col, mk in METHODS[:2]:
            g = s[s.method == m].groupby("N")
            x = g.rollouts.mean().values / s.K.mean()
            ax.plot(x, 100 * g.ok.mean().values, color=col, lw=2, marker=mk, ms=5, mec="white", mew=1,
                    label=lab, zorder=3)
        ax.axhline(100 * TARGET, color=INK2, lw=1, ls=(0, (3, 3)))
        ax.set_xscale("log")
        ax.set_title(f"{name}  (n = {s.state_id.nunique()})", fontsize=8, color=INK)
        ax.set_xlabel("Mean rollouts per candidate (log scale)", fontsize=8, color=INK2)
        style(ax)
    axes[0].set_ylabel("States with regret ≤ 0.5% (%)", fontsize=8, color=INK2)
    axes[0].legend(frameon=False, fontsize=7, loc="lower right")
    save(fig, "paper_fig3_separation")


# ------------------------------------------------------------------ Fig. 4
def fig4(twin):
    ramp = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
    fig, axes = plt.subplots(1, 3, figsize=(7.8, 2.6), dpi=200, sharey=True)
    for ax, r in zip(axes, ("low", "base", "high")):
        d = twin[(twin.cost_ratio == r) & (twin.method == "uniform")]
        for i, fam in enumerate(FAM_ORDER):
            for j in range(3):
                v = required_N(d[(d.family == fam) & (d.volume_tertile == j)])
                k = len(ramp) - 1 if not np.isfinite(v) else GRID.index(int(v))
                ax.add_patch(plt.Rectangle((j, 2 - i), 0.96, 0.96, color=ramp[k], lw=0))
                ax.text(j + 0.48, 2 - i + 0.48, ">1000" if not np.isfinite(v) else f"{int(v)}",
                        ha="center", va="center", fontsize=8, color="white" if k >= 3 else INK)
        ax.set_xlim(0, 3); ax.set_ylim(0, 3)
        ax.set_xticks([0.48, 1.48, 2.48]); ax.set_xticklabels(VOL_LABEL, fontsize=6.5, color=INK2)
        ax.set_yticks([2.48, 1.48, 0.48]); ax.set_yticklabels([FAM_LABEL[f] for f in FAM_ORDER], fontsize=7, color=INK2)
        ax.tick_params(length=0)
        for sp in ax.spines.values():
            sp.set_visible(False)
        ax.set_title(f"Shortage:waste = {RATIO_LABEL[r]}", fontsize=8, color=INK)
    save(fig, "paper_fig4_required")


if __name__ == "__main__":
    twin = load([f"nb02_original_{r}.csv" for r in ("base", "low", "high")])
    fav = load(["nb02_replication_base.csv"])
    # quick printout to check against Tables 3 and 6
    for name, d in (("twin", twin), ("favorita", fav)):
        b = d[(d.cost_ratio == "base") & (d.N == 250)]
        print(name, "base, N = 250:", {m: round(100 * b[b.method == m].ok.mean(), 1) for m, *_ in METHODS})
    fig2(twin, fav)
    fig3(twin)
    fig4(twin)
