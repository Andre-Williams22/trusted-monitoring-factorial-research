"""Figures for the monitor-identity-vs-tier claim.

    fig6_identity_beats_tier.png  monitor ranking, shaded by tier, two metrics
    fig7_spread_vs_tier.png       same-tier spread vs the tier gap
    fig8_ladders.png              within-family ladders under each metric

    python -m scripts.make_identity_figures
"""

from __future__ import annotations

import os
import warnings

warnings.filterwarnings("ignore")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from utils import config, viz
from utils.data import balanced, cell_value, load_scores, viable
from utils.stats import decompose, monitor_means

RANK_PANELS = (("tpr0", "All attack attempts"),
               ("tpr0_succ", "Attacks that actually succeeded"))


def _frame(scores: dict) -> pd.DataFrame:
    rows = []
    for key, cell in scores.items():
        if key == "_limit":
            continue
        attacker, monitor = key
        rows.append(dict(
            attacker=attacker, monitor=monitor,
            tier=config.TIER[monitor], family=config.FAMILY[monitor],
            n_succ=int(cell["succ"].sum()),
            **{m: cell_value(cell, m) for m in ("auc", "tpr0", "tpr0_succ")},
        ))
    return pd.DataFrame(rows)


def fig_ranking(scores: dict, both: pd.DataFrame, out: str) -> None:
    """Rank monitors, shade by tier. Interleaved shading is the finding."""
    monitors = sorted(both.monitor.unique())
    attackers = sorted(both.attacker.unique())
    fig, axes = plt.subplots(1, 2, figsize=(11.2, 4.3))
    for ax, (metric, title) in zip(axes, RANK_PANELS):
        point, ci = monitor_means(scores, monitors, attackers, metric,
                                  np.random.default_rng(7))
        point = point.sort_values()
        y = np.arange(len(point))
        lo = [point[m] - ci[m][0] for m in point.index]
        hi = [ci[m][1] - point[m] for m in point.index]
        ax.barh(y, point.values, height=0.62, zorder=2,
                color=[viz.TIER_COLOR[config.TIER[m]] for m in point.index])
        ax.errorbar(point.values, y, xerr=[lo, hi], fmt="none",
                    ecolor=viz.INK_SECONDARY, elinewidth=1.2, capsize=3, zorder=3)
        ax.set_yticks(y)
        ax.set_yticklabels([config.LABEL[m] for m in point.index])
        for i, m in enumerate(point.index):
            ax.text(ci[m][1] + 0.012, i, f"{point[m]:.2f}  ({config.TIER[m]})",
                    va="center", fontsize=8, color=viz.INK_SECONDARY)
        ax.set_xlim(0, max(ci[m][1] for m in monitors) * 1.32)
        viz.style_axis(ax, "Attacks caught with zero false alarms on honest code")
        ax.set_title(title, color=viz.INK, loc="left", pad=8)
    viz.tier_legend(fig)
    fig.suptitle("Capability tier does not order the monitors — identity does",
                 fontsize=11.5, x=0.008, ha="left", color=viz.INK)
    fig.tight_layout(rect=[0, 0.05, 1, 0.94])
    fig.savefig(f"{out}/fig6_identity_beats_tier.png", dpi=200)
    plt.close(fig)


def fig_spread(scores: dict, both: pd.DataFrame, out: str) -> None:
    """How much bigger is the identity effect than the tier effect?

    Both bars are like-for-like distances. Comparing best-vs-worst monitor
    against a strong-vs-weak group MEAN would be rigged: a range over six items
    is mechanically larger than a gap between two averages. So the identity bar
    is the spread among monitors that SHARE a tier - variation tier cannot
    explain by construction.
    """
    panels = (("tpr0", "Caught,\nall attacks"),
              ("tpr0_succ", "Caught,\nsuccessful attacks"),
              ("auc", "ROC-AUC\n(prior-work metric)"))
    observed, cis = [], []
    for metric, _ in panels:
        result = decompose(both, metric)
        rng = np.random.default_rng(11)
        draws = {"within": [], "gap": []}
        for _ in range(config.bootstrap_draws()):
            rows = [dict(attacker=a, monitor=m,
                         **{metric: cell_value(scores[(a, m)], metric, rng)})
                    for a, m in zip(both.attacker, both.monitor)]
            boot = decompose(pd.DataFrame(rows), metric)
            draws["within"].append(boot["within_tier_spread"])
            draws["gap"].append(boot["tier_gap"])
        observed.append((result["within_tier_spread"], result["tier_gap"]))
        cis.append({k: np.percentile(v, [2.5, 97.5]) for k, v in draws.items()})

    top = max(c["within"][1] for c in cis)
    fig, ax = plt.subplots(figsize=(8.4, 5.0))
    x = np.arange(len(panels))
    width = 0.32
    series = (("within", "Identity: monitors of the SAME tier, best vs worst", viz.SERIES[0]),
              ("gap", "Tier: strong-tier average vs weak-tier average", viz.SERIES[1]))
    for j, (key, name, color) in enumerate(series):
        values = [o[j] for o in observed]
        err = np.array([[v - c[key][0] for v, c in zip(values, cis)],
                        [c[key][1] - v for v, c in zip(values, cis)]])
        xs = x + (j - 0.5) * (width + 0.03)
        ax.bar(xs, values, width, label=name, color=color, zorder=2)
        ax.errorbar(xs, values, yerr=err, fmt="none", ecolor=viz.INK_SECONDARY,
                    elinewidth=1.2, capsize=3, zorder=3)
        for xi, v, c in zip(xs, values, cis):
            ax.text(xi, c[key][1] + top * 0.035, f"{v:.2f}", ha="center",
                    fontsize=8.5, color=viz.INK_SECONDARY)
    for xi, (within, gap) in zip(x, observed):
        ax.text(xi, top * 1.30, f"{within / gap:.1f}x", ha="center", fontsize=11,
                color=viz.INK, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels([n for _, n in panels])
    ax.set_ylim(0, top * 1.45)
    viz.style_axis(ax, axis="y")
    ax.set_ylabel("Difference in monitor performance", color=viz.INK_SECONDARY)
    ax.legend(frameon=False, fontsize=8.5, loc="upper center",
              bbox_to_anchor=(0.5, -0.16), ncol=1)
    ax.set_title("Two monitors of the same tier differ 2–9x more than the tiers differ\n"
                 "Whiskers are 95% bootstrap CIs. On landed attacks the tier gap also reverses "
                 "sign — weak ahead of strong —\nso the orange bar there is a magnitude, not a "
                 "strong-tier advantage.",
                 loc="left", color=viz.INK, pad=10, fontsize=9.5)
    fig.tight_layout(rect=[0, 0.06, 1, 1])
    fig.savefig(f"{out}/fig7_spread_vs_tier.png", dpi=200)
    plt.close(fig)


def fig_ladders(cells: pd.DataFrame, out: str) -> None:
    """Within one family the ladder behaves; on landed attacks it inverts."""
    panels = (("auc", "ROC-AUC\n(the uncorrected metric)"),
              ("tpr0", "Caught, all attacks"),
              ("tpr0_succ", "Caught, successful attacks only"))
    fig, axes = plt.subplots(1, 3, figsize=(11.2, 3.9))
    attackers = sorted(cells.attacker.unique())
    for ax, (metric, title) in zip(axes, panels):
        for j, attacker in enumerate(attackers):
            own = cells[(cells.attacker == attacker)
                        & (cells.family == config.FAMILY[attacker])]
            own = own.sort_values("tier", key=lambda s: s.map(config.TIER_ORDER))
            if len(own) < 3:
                continue
            ax.plot([config.TIER_ORDER[t] for t in own.tier], own[metric], "-o",
                    color=viz.SERIES[j], lw=2, ms=7, mec=viz.SURFACE, mew=1.5,
                    zorder=3, label=f"{config.LABEL[attacker]} attacker")
        ax.set_xticks([0, 1, 2])
        ax.set_xticklabels(["weak", "mid", "strong"])
        ax.set_xlim(-0.35, 2.35)
        viz.style_axis(ax, axis="y")
        ax.set_title(title, loc="left", color=viz.INK, fontsize=9.5, pad=6)
        ax.margins(y=0.18)
    axes[0].set_ylabel("Monitor performance", color=viz.INK_SECONDARY)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=2, frameon=False,
               fontsize=8.5, bbox_to_anchor=(0.5, -0.02))
    fig.suptitle("Within one model family, tier behaves — until you score only "
                 "the attacks that landed",
                 fontsize=11.5, x=0.008, ha="left", color=viz.INK)
    fig.tight_layout(rect=[0, 0.07, 1, 0.9])
    fig.savefig(f"{out}/fig8_ladders.png", dpi=200)
    plt.close(fig)


def main() -> None:
    viz.apply_style()
    out = config.figure_dir()
    os.makedirs(out, exist_ok=True)
    scores = load_scores()
    cells = viable(_frame(scores))
    both = balanced(cells)
    print(f"{len(cells)} viable cells; balanced sub-design "
          f"{both.attacker.nunique()} x {both.monitor.nunique()} = {len(both)}")
    fig_ranking(scores, both, out)
    print("  wrote fig6_identity_beats_tier.png")
    fig_spread(scores, both, out)
    print("  wrote fig7_spread_vs_tier.png")
    fig_ladders(cells, out)
    print("  wrote fig8_ladders.png")


if __name__ == "__main__":
    main()
