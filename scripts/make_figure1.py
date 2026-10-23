"""Fig. 1 of the paper (experimental framework).  Usage:  python3 scripts/make_figure1.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_paper_figures import fig1, RES

if __name__ == "__main__":
    os.makedirs(RES, exist_ok=True)
    fig1()
    print("wrote results/paper_fig1_framework.png/.pdf")
