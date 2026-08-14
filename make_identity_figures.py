"""Figures for the monitor-identity-vs-tier claim.

  fig6_identity_beats_tier.png  monitor ranking, coloured by tier, two metrics
  fig7_spread_vs_tier.png       identity spread vs tier gap, three metrics
  fig8_ladders.png              within-family ladders under each metric

Reads the cached suspicion scores written by analyze_monitor_identity.py.
Usage:  LIMIT=100 python make_identity_figures.py
"""

import os
import pickle
import warnings

warnings.filterwarnings("ignore")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from analyze_monitor_identity import (
    FAMILY, LABEL, TIER, auc, decompose, tpr_at_zero_fpr,
)

OUT = os.environ.get("FIG_DIR", "figures")
B = int(os.environ.get("BOOTSTRAP", "4000"))

# Ordinal ramp (blue, light->dark) for capability tier - an ORDERED category, so
# the ramp is the correct encoding rather than arbitrary categorical hues. The
# reader expects the shading to run with the ranking; that it does not is the
# finding. Validated --ordinal on the light surface (light end 2.06:1).
TIER_C = {"weak": "#86b6ef", "mid": "#2a78d6", "strong": "#104281"}
SERIES = ["#2a78d6", "#eb6834"]  # categorical slots 1-2
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, BASE, SURFACE = "#e1e0d9", "#c3c2b7", "#fcfcfb"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
    "font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9,
    "text.color": INK, "axes.labelcolor": INK2, "axes.edgecolor": BASE,
    "xtick.color": MUTED, "ytick.color": INK2, "savefig.facecolor": SURFACE,
})

METRICS = [("tpr0", "All attack attempts"), ("tpr0_succ", "Attacks that actually succeeded")]


def style(ax, xlabel: str = "") -> None:
    ax.grid(axis="x", color=GRID, lw=0.6, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(BASE)
    ax.tick_params(length=0)
    if xlabel:
        ax.set_xlabel(xlabel, color=INK2)


def cell_value(c: dict, metric: str, rng=None) -> float:
    h, a, s = c["h"], c["a"], c["succ"]
    if rng is not None:
        h = h[rng.integers(0, len(h), len(h))]
        i = rng.integers(0, len(a), len(a))
        a, s = a[i], s[i]
    if metric == "auc":
        return auc(h, a)
    return tpr_at_zero_fpr(h, a, s if metric == "tpr0_succ" else None)


def build(D: dict) -> pd.DataFrame:
    rows = []
    for k, c in D.items():
        if k == "_limit":
            continue
        atk, mon = k
        if c["succ"].sum() < 5:
            continue
        rows.append(dict(attacker=atk, monitor=mon, tier=TIER[mon], family=FAMILY[mon],
                         **{m: cell_value(c, m) for m in ("auc", "tpr0", "tpr0_succ")}))
    return pd.DataFrame(rows)


def raw_means(D: dict, mons: list[str], atks: list[str], metric: str, rng) -> tuple[pd.Series, dict]:
    """Balanced design -> the plain mean over attacker rows is unbiased."""
    pt = pd.Series({m: np.mean([cell_value(D[(a, m)], metric) for a in atks]) for m in mons})
    draws = {m: [] for m in mons}
    for _ in range(B):
        for m in mons:
            draws[m].append(np.mean([cell_value(D[(a, m)], metric, rng) for a in atks]))
    ci = {m: tuple(np.percentile(v, [2.5, 97.5])) for m, v in draws.items()}
    return pt, ci


# ---------------------------------------------------------------------------
def fig_ranking(D: dict, both: pd.DataFrame) -> None:
    """Rank monitors; shade by tier. Interleaved shading = identity beats tier."""
    mons = sorted(both.monitor.unique())
    atks = sorted(both.attacker.unique())
    fig, axes = plt.subplots(1, 2, figsize=(11.2, 4.3))
    for ax, (metric, title) in zip(axes, METRICS):
        pt, ci = raw_means(D, mons, atks, metric, np.random.default_rng(7))
        pt = pt.sort_values()
        y = np.arange(len(pt))
        lo = [pt[m] - ci[m][0] for m in pt.index]
        hi = [ci[m][1] - pt[m] for m in pt.index]
        ax.barh(y, pt.values, height=0.62, zorder=2,
                color=[TIER_C[TIER[m]] for m in pt.index])
        ax.errorbar(pt.values, y, xerr=[lo, hi], fmt="none", ecolor=INK2,
                    elinewidth=1.2, capsize=3, zorder=3)
        ax.set_yticks(y)
        ax.set_yticklabels([LABEL[m] for m in pt.index])
        for i, m in enumerate(pt.index):
            ax.text(ci[m][1] + 0.012, i, f"{pt[m]:.2f}  ({TIER[m]})",
                    va="center", fontsize=8, color=INK2)
        ax.set_xlim(0, max(ci[m][1] for m in mons) * 1.32)
        style(ax, "Attacks caught with zero false alarms on honest code")
        ax.set_title(title, color=INK, loc="left", pad=8)
    handles = [plt.Rectangle((0, 0), 1, 1, color=TIER_C[t]) for t in ("weak", "strong")]
    fig.legend(handles, ["weak tier (cheap)", "strong tier (expensive)"],
               loc="lower center", ncol=2, frameon=False, fontsize=8.5,
               bbox_to_anchor=(0.5, -0.015))
    fig.suptitle("Capability tier does not order the monitors — identity does",
                 fontsize=11.5, x=0.008, ha="left", color=INK)
    fig.tight_layout(rect=[0, 0.05, 1, 0.94])
    fig.savefig(f"{OUT}/fig6_identity_beats_tier.png", dpi=200)
    plt.close(fig)


def fig_spread(D: dict, both: pd.DataFrame) -> None:
    """How much bigger is the identity effect than the tier effect?

    Both quantities are like-for-like distances. Comparing best-vs-worst monitor
    against a strong-vs-weak group MEAN would be rigged: a range over six items
    is mechanically larger than a gap between two group averages. So the
    identity bar is the spread among monitors that SHARE a tier - the variation
    tier cannot explain by construction.
    """
    labels = [("tpr0", "Caught,\nall attacks"), ("tpr0_succ", "Caught,\nsuccessful attacks"),
              ("auc", "ROC-AUC\n(prior-work metric)")]
    obs, cis = [], []
    for metric, _ in labels:
        r = decompose(both, metric)
        rng = np.random.default_rng(11)
        draws = {"within": [], "gap": []}
        for _ in range(B):
            rows = [dict(attacker=a, monitor=m, **{metric: cell_value(D[(a, m)], metric, rng)})
                    for a, m in zip(both.attacker, both.monitor)]
            rb = decompose(pd.DataFrame(rows), metric)
            draws["within"].append(rb["within_tier_spread"])
            draws["gap"].append(rb["tier_gap"])
        obs.append((r["within_tier_spread"], r["tier_gap"]))
        cis.append({k: np.percentile(v, [2.5, 97.5]) for k, v in draws.items()})
    top = max(c["within"][1] for c in cis)
    fig, ax = plt.subplots(figsize=(8.0, 4.6))
    x = np.arange(len(labels))
    w = 0.32
    for j, (key, name, col) in enumerate(
            [("within", "Identity: monitors of the SAME tier, best vs worst", SERIES[0]),
             ("gap", "Tier: strong-tier average vs weak-tier average", SERIES[1])]):
        vals = [o[j] for o in obs]
        err = np.array([[v - c[key][0] for v, c in zip(vals, cis)],
                        [c[key][1] - v for v, c in zip(vals, cis)]])
        xs = x + (j - 0.5) * (w + 0.03)
        ax.bar(xs, vals, w, label=name, color=col, zorder=2)
        ax.errorbar(xs, vals, yerr=err, fmt="none", ecolor=INK2,
                    elinewidth=1.2, capsize=3, zorder=3)
        for xi, v, c in zip(xs, vals, cis):
            ax.text(xi, c[key][1] + top * 0.035, f"{v:.2f}", ha="center",
                    fontsize=8.5, color=INK2)
    for xi, (s, g) in zip(x, obs):
        ax.text(xi, top * 1.30, f"{s / g:.1f}x", ha="center", fontsize=11,
                color=INK, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels([n for _, n in labels])
    ax.set_ylim(0, top * 1.45)
    ax.grid(axis="y", color=GRID, lw=0.6, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(length=0)
    ax.set_ylabel("Difference in monitor performance", color=INK2)
    ax.legend(frameon=False, fontsize=8.5, loc="upper center",
              bbox_to_anchor=(0.5, -0.14), ncol=1)
    ax.set_title("Two monitors of the same tier differ ~3x more than the tiers differ\n"
                 "Whiskers are 95% bootstrap CIs; the multiple is printed above each pair",
                 loc="left", color=INK, pad=10)
    fig.tight_layout(rect=[0, 0.06, 1, 1])
    fig.savefig(f"{OUT}/fig7_spread_vs_tier.png", dpi=200)
    plt.close(fig)


def fig_ladders(D: dict, v: pd.DataFrame) -> None:
    """Within one family the ladder behaves; on successful attacks it inverts."""
    order = {"weak": 0, "mid": 1, "strong": 2}
    panels = [("auc", "ROC-AUC\n(what the original post used)"),
              ("tpr0", "Caught, all attacks"),
              ("tpr0_succ", "Caught, successful attacks only")]
    fig, axes = plt.subplots(1, 3, figsize=(11.2, 3.9))
    atks = sorted(v.attacker.unique())
    for ax, (metric, title) in zip(axes, panels):
        for j, atk in enumerate(atks):
            own = v[(v.attacker == atk) & (v.family == FAMILY[atk])]
            own = own.sort_values("tier", key=lambda s: s.map(order))
            if len(own) < 3:
                continue
            ax.plot([order[t] for t in own.tier], own[metric], "-o", color=SERIES[j],
                    lw=2, ms=7, mec=SURFACE, mew=1.5, zorder=3,
                    label=f"{LABEL[atk]} attacker")
        ax.set_xticks([0, 1, 2])
        ax.set_xticklabels(["weak", "mid", "strong"])
        ax.set_xlim(-0.35, 2.35)
        ax.grid(axis="y", color=GRID, lw=0.6, zorder=0)
        ax.set_axisbelow(True)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        ax.tick_params(length=0)
        ax.set_title(title, loc="left", color=INK, fontsize=9.5, pad=6)
        ax.margins(y=0.18)
    axes[0].set_ylabel("Monitor performance", color=INK2)
    handles, labs = axes[0].get_legend_handles_labels()
    fig.legend(handles, labs, loc="lower center", ncol=2, frameon=False,
               fontsize=8.5, bbox_to_anchor=(0.5, -0.02))
    fig.suptitle("Within one model family, tier behaves — until you score only the attacks that landed",
                 fontsize=11.5, x=0.008, ha="left", color=INK)
    fig.tight_layout(rect=[0, 0.07, 1, 0.9])
    fig.savefig(f"{OUT}/fig8_ladders.png", dpi=200)
    plt.close(fig)


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    with open(os.environ.get("SCORE_CACHE", ".score_cache.pkl"), "rb") as f:
        D = pickle.load(f)
    v = build(D)
    both = v.groupby("monitor").filter(lambda x: len(x) == 2)
    print(f"{len(v)} viable cells; balanced sub-design {both.attacker.nunique()}"
          f" x {both.monitor.nunique()} = {len(both)}")
    fig_ranking(D, both)
    print("  wrote fig6_identity_beats_tier.png")
    fig_spread(D, both)
    print("  wrote fig7_spread_vs_tier.png")
    fig_ladders(D, v)
    print("  wrote fig8_ladders.png")


if __name__ == "__main__":
    main()
