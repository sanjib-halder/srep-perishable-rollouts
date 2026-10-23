# Rollout Budgets for Perishable Replenishment: Uniform versus Adaptive Allocation?

Code, decision states and results for

> S. Halder. *Rollout Budgets for Perishable Replenishment: Uniform versus Adaptive Allocation.* Submitted to WCSC 2027 (Springer LNNS).

The study measures how many simulated rollouts per candidate order a daily replenishment decision for
age-structured perishable inventory needs, and compares uniform allocation, a paired
sequential-elimination heuristic, standard OCBA and a paired-variance OCBA variant, on 500 states from a
grocery digital twin and 3,000 states reconstructed from Favorita store sales.

## Contents

| Folder | What it holds |
|---|---|
| `srep/` | Vectorised rollout engine (`engine.py`), scenarios with common random numbers, candidate generation, allocation methods and reference (`allocation.py`), Favorita replay and resampled demand (`favorita.py`, `sgsg_replay.py`, `empirical.py`), experiment runners (`experiment2.py`, `experiment3.py`) |
| `sgsg/`, `twin/` | The original grocery digital twin and its data generator, used unchanged as the reference the engine reproduces |
| `tests/` | Exactness test: engine vs. the original twin on identical random draws |
| `notebooks/` | Notebook 1 (Favorita audit, replication states), notebook 2 (replication, extended reference, timing), notebook 3 (paired OCBA, clustered intervals, 52-week window). The `_nb0x_as_script.py` files are the Terminal versions that produced the reported results |
| `scripts/` | Benchmark and timing, statistics, figures |
| `data/` | Twin product panel and calendar, the 500 benchmark states, 30 development states, the 3,000 Favorita decision states |
| `results/` | Per-state results, summaries and statistics used in the paper; `results/figures/` holds Figs. 1–4 |
| `docs/` | Protocol amendments recorded before and during the study |

## Installation

Python 3.9 or later.

```bash
pip install -r requirements.txt
python3 tests/test_engine_vs_twin.py          # engine == original twin; prints OK lines
```

## Reproducing the paper

All runs use fixed seeds. Times are for a 10-core Apple laptop.

| Paper item | Command | Output |
|---|---|---|
| Engine verification (§4.8) | `python3 tests/test_engine_vs_twin.py` | console |
| Network-scale timing (§5.2) | `python3 scripts/benchmark_compute.py --states 200` (reads `budget.json`) | `results/timing_official.json` |
| Pre-specified benchmark | `python3 scripts/day2_branch.py --signed-off --workers 10` | `results/day2_benchmark_*.csv` |
| Twin states with extended reference, Tables 3–5 (§5.3–5.5) | `FAV_DIR=/path/to/favorita python3 notebooks/_nb02_as_script.py`, then `python3 scripts/revision_stats.py` | `results/nb02_original_*.csv`, `results/revision_stats.json` |
| Favorita replication, Table 6 (§5.6) | `notebooks/_nb01_as_script.py`, then `notebooks/_nb02_as_script.py` (both need `FAV_DIR`) | `results/nb02_replication_*.csv`, `results/nb02_summary.md` |
| Paired-variance OCBA, clustered intervals, 52-week window | `cd notebooks && FAV_DIR=/path/to/favorita python3 nb03_extra_runs.py` | `results/nb03_*.csv`, `results/nb03_summary.md`, `results/nb03_stats.json` |
| Runtime of the adaptive method (§5.4) | `python3 scripts/time_adaptive.py` | console (`results/timing_adaptive_mac.json`) |
| Fig. 1 | `python3 scripts/make_figure1.py` | `results/paper_fig1_framework.*` |
| Figs. 2–4 | `python3 scripts/make_figures_2_4.py` | `results/paper_fig2–4_*` |

The figure scripts write to `results/`; the copies used in the paper are in `results/figures/`.

## Favorita data

The raw Favorita files are not redistributed here. See `data/README.md`.

## Notes

* Sequential elimination is a heuristic without multiplicity correction or error guarantees; the
  paired-variance OCBA variant is a heuristic sensitivity check, not a validated correlation-aware
  procedure (see the paper, §4.4–4.5).
* Regret is measured against a simulator-defined reference, not against realised waste or cost.

## Citation

If you use this code, please cite the paper above.

## Licence

MIT

