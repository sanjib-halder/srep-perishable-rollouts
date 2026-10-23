"""
Writes the four manuscript figures with names that match the paper:

  results/paper_fig1_framework.{pdf,png}    Fig. 1  experimental framework (drawn here)
  results/paper_fig2_frontier.{pdf,png}     Fig. 2  decision quality vs simulation effort
  results/paper_fig3_separation.{pdf,png}   Fig. 3  near-tied vs clearly separated states
  results/paper_fig4_required.{pdf,png}     Fig. 4  rollouts required by regime

Figs. 2-4 are regenerated from results/day2_benchmark_*.csv with the same
code as scripts/plan_b_analysis.py, so they are identical to the analysis
figures. Run after the benchmark:  python3 scripts/make_paper_figures.py
"""
import os
import sys
import shutil

import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["savefig.dpi"] = 600          # print resolution for the PNGs
import matplotlib.figure
matplotlib.figure.Figure.suptitle = lambda self, *a, **k: None   # captions live in the paper, not in the image
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
RES = os.path.join(ROOT, "results")

INK, INK2, LINE = "#1f1f1e", "#5f5e58", "#9a998f"
FILL, FILL_M, FILL_R = "#f4f3ef", "#e1edfb", "#fdebe3"   # neutral, method (blue tint), reference (orange tint)
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"


def box(ax, x, y, w, h, title, lines, fill=FILL, edge=LINE, title_color=INK):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.01,rounding_size=0.015",
                                fc=fill, ec=edge, lw=0.9))
    ax.text(x + w / 2, y + h - 0.028, title, ha="center", va="top", fontsize=7.8,
            fontweight="bold", color=title_color)
    ax.text(x + w / 2, y + h - 0.072, "\n".join(lines), ha="center", va="top", fontsize=6.1,
            color=INK2, linespacing=1.35)


def arrow(ax, p, q, rad=0.0):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=9, lw=0.9, color=LINE,
                                 connectionstyle=f"arc3,rad={rad}", shrinkA=2, shrinkB=2))


def fig1():
    fig, ax = plt.subplots(figsize=(7.6, 4.4), dpi=200)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    box(ax, 0.01, 0.70, 0.27, 0.27, "Decision states",
        ["twin: 500 states, 157 items", "Favorita: 3,000 states, 636 items",
         "bakery 3 d · produce 5 d · dairy 10 d", "stock by age + orders in transit"])
    box(ax, 0.365, 0.70, 0.27, 0.27, "Candidate orders A(s)",
        ["zero order · (s,S) order", "order-up-to coverage levels",
         "90% / 99% demand quantiles", "±20% perturbations (2–12 orders)"])
    box(ax, 0.72, 0.70, 0.27, 0.27, "Rollout engine (CRN)",
        ["vectorised; equals grocery twin", "twin demand or resampled sales",
         "(s,S) continuation, H = 7 / 14 d", "cost J(s, a; ω), Eq. (5)"])
    arrow(ax, (0.28, 0.835), (0.365, 0.835))
    arrow(ax, (0.635, 0.835), (0.72, 0.835))
    w, y, h = 0.222, 0.36, 0.25
    xs = [0.01, 0.262, 0.514, 0.766]
    box(ax, xs[0], y, w, h, "Uniform", ["N rollouts per candidate", "N ∈ {10, …, 1000}", r"budget $N\cdot K_s$"],
        fill=FILL_M, edge=BLUE, title_color=BLUE)
    box(ax, xs[1], y, w, h, "Sequential elimination", [r"paired differences", r"drop if $\bar{D} - 1.96\,\hat{\sigma} > 0$", "may stop early"],
        fill=FILL_M, edge=ORANGE, title_color=ORANGE)
    box(ax, xs[2], y, w, h, "OCBA", ["marginal means, variances", "allocation ratios, Eq. (13)", "spends full budget"],
        fill=FILL_M, edge=AQUA, title_color=AQUA)
    box(ax, xs[3], y, w, h, "Reference", ["independent stream", "5,000 → 320,000 rollouts", "adequacy rule, Eq. (14)"], fill=FILL_R)
    ax.plot([0.855, 0.855], [0.70, 0.655], color=LINE, lw=0.9)
    ax.plot([xs[0] + w / 2, xs[3] + w / 2], [0.655, 0.655], color=LINE, lw=0.9)
    for x in xs:
        arrow(ax, (x + w / 2, 0.655), (x + w / 2, y + h))
    box(ax, 0.10, 0.03, 0.80, 0.24, "Evaluation",
        ["relative regret r(s), Eq. (15)  ·  share of states with r ≤ 0.5%  ·  rollouts actually used",
         r"rollouts required $N_{req}$, Eq. (16)  ·  paired method differences, item-clustered bootstrap CI",
         "measured end-to-end time  ·  regimes: family × volume × shortage-to-waste ratio"])
    for x in xs:
        arrow(ax, (x + w / 2, y), (0.5 + (x + w / 2 - 0.5) * 0.75, 0.27))
    for ext in ("pdf", "png"):
        fig.savefig(os.path.join(RES, f"paper_fig1_framework.{ext}"), bbox_inches="tight")
    plt.close(fig)


def figs_2_to_4():
    import plan_b_analysis as A
    df = A.load()
    A.fig_frontier(df)
    A.fig_separation(df)
    req = A.table_required(df, 14)          # bootstrap not needed for this table
    A.fig_required(req)
    for src, dst in (("fig1_frontier", "paper_fig2_frontier"),
                     ("fig3_separation", "paper_fig3_separation"),
                     ("fig2_required", "paper_fig4_required")):
        for ext in ("pdf", "png"):
            shutil.copyfile(os.path.join(RES, f"{src}.{ext}"), os.path.join(RES, f"{dst}.{ext}"))


if __name__ == "__main__":
    os.makedirs(RES, exist_ok=True)
    fig1()
    figs_2_to_4()
    print("wrote results/paper_fig1..4 (.pdf and .png)")
