"""Shared plot styling.

Capability tier is an ORDERED category, so it gets an ordinal ramp (one hue,
light to dark) rather than arbitrary categorical hues. That choice is load
bearing for the figures: a reader expects the shading to run with the ranking,
and the fact that it doesn't is the finding.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Ordinal ramp, blue, validated on the light surface (light end clears 2.06:1).
TIER_COLOR = {"weak": "#86b6ef", "mid": "#2a78d6", "strong": "#104281"}

# Categorical slots 1-2, for two-series comparisons.
SERIES = ("#2a78d6", "#eb6834")

INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"
SURFACE = "#fcfcfb"

RC_PARAMS = {
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "font.size": 9,
    "axes.titlesize": 10,
    "axes.labelsize": 9,
    "text.color": INK,
    "axes.labelcolor": INK_SECONDARY,
    "axes.edgecolor": BASELINE,
    "xtick.color": INK_MUTED,
    "ytick.color": INK_SECONDARY,
    "savefig.facecolor": SURFACE,
}


def apply_style() -> None:
    plt.rcParams.update(RC_PARAMS)


def style_axis(ax, xlabel: str = "", axis: str = "x") -> None:
    """Recessive grid, no box, no tick marks."""
    ax.grid(axis=axis, color=GRID, lw=0.6, zorder=0)
    ax.set_axisbelow(True)
    hide = ("top", "right", "left") if axis == "x" else ("top", "right")
    for spine in hide:
        ax.spines[spine].set_visible(False)
    if axis == "x":
        ax.spines["bottom"].set_color(BASELINE)
    ax.tick_params(length=0)
    if xlabel:
        ax.set_xlabel(xlabel, color=INK_SECONDARY)


def tier_legend(fig, tiers=("weak", "strong"),
                labels=("weak tier (cheap)", "strong tier (expensive)")) -> None:
    handles = [plt.Rectangle((0, 0), 1, 1, color=TIER_COLOR[t]) for t in tiers]
    fig.legend(handles, labels, loc="lower center", ncol=len(tiers), frameon=False,
               fontsize=8.5, bbox_to_anchor=(0.5, -0.015))
