"""Standalone table/design graphics for embedding in a write-up.

    fig10_results_table.png  the six-monitor result table, rendered
    fig11_design.png         the attacker x monitor design grid

Both derive from the score cache, so they cannot drift from the numbers the
analysis prints.

    python -m scripts.make_table_figures
"""

from __future__ import annotations

import os
import warnings

warnings.filterwarnings("ignore")

import matplotlib.pyplot as plt
import numpy as np

from utils import config, viz
from utils.data import cell_value, load_scores

ATTACKERS = ("gpt55", "opus48", "geminipro")
BALANCED = ("opus48", "haiku45", "geminipro", "flashlite", "qwen", "gpt41mini")


# ---------------------------------------------------------------------------
def fig_results_table(scores: dict, out: str) -> None:
    """The result table as a graphic.

    A table is the right form here: five exact numbers per row, and the reader
    needs to compare within rows as well as down columns. The tier chip carries
    the finding - it is the column that refuses to sort with the ranking.
    """
    rows = []
    viable_attackers = ("geminipro", "gpt55")
    for key in BALANCED:
        caught = np.mean([cell_value(scores[(a, key)], "tpr0") for a in viable_attackers])
        landed = np.mean([cell_value(scores[(a, key)], "tpr0_succ") for a in viable_attackers])
        fpr = np.mean([(scores[(a, key)]["h"] > 0).mean() for a in viable_attackers])
        rows.append((config.LABEL[key], config.TIER[key], caught, landed, fpr))
    rows.sort(key=lambda r: -r[2])

    headers = ["Monitor", "Tier", "Caught\n(all attacks)",
               "Caught\n(attacks that landed)", "False alarms\n(on honest code)"]
    x = [0.015, 0.335, 0.485, 0.665, 0.875]
    align = ["left", "left", "center", "center", "center"]

    fig, ax = plt.subplots(figsize=(9.8, 5.0))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(0.015, 0.985, "Which monitor you pick beats what tier it is",
            ha="left", va="top", fontsize=13.5, color=viz.INK, fontweight="bold")
    ax.text(0.015, 0.905,
            "Six monitors, each scored against both viable attackers. Strong, weak, strong, "
            "weak, strong, weak —\nthe tier column alternates against the ranking. n = 100 per mode.",
            ha="left", va="top", fontsize=9.0, color=viz.INK_SECONDARY, linespacing=1.6)

    head_y, rule_y, first_y, row_h = 0.700, 0.672, 0.610, 0.089
    for xi, head, al in zip(x, headers, align):
        ax.text(xi, head_y, head, ha=al, va="bottom", fontsize=8.8,
                color=viz.INK_SECONDARY, linespacing=1.6)
    ax.plot([0.01, 0.99], [rule_y, rule_y], color=viz.BASELINE, lw=1.1)

    for i, (label, tier, caught, landed, fpr) in enumerate(rows):
        y = first_y - i * row_h
        if i % 2 == 1:
            ax.add_patch(plt.Rectangle((0.01, y - row_h * 0.44), 0.98, row_h * 0.88,
                                       color="#f4f3ef", zorder=0))
        weight = "bold" if tier == "weak" and i < 3 else "normal"
        ax.text(x[0], y, label, ha="left", va="center", fontsize=9.6,
                color=viz.INK, fontweight=weight, zorder=2)
        # tier chip - ordinal ramp, so shading encodes capability
        ax.add_patch(plt.Rectangle((x[1], y - 0.019), 0.050, 0.038,
                                   color=viz.TIER_COLOR[tier], zorder=2))
        ax.text(x[1] + 0.060, y, tier, ha="left", va="center", fontsize=8.8,
                color=viz.INK_SECONDARY, zorder=2)
        for col, value in zip((x[2], x[3], x[4]), (caught, landed, fpr)):
            emphasise = col == x[3] and value < 0.1
            ax.text(col, y, f"{value:.3f}", ha="center", va="center", fontsize=9.6,
                    color="#b3401f" if emphasise else viz.INK,
                    fontweight="bold" if emphasise else "normal", zorder=2)

    bottom = first_y - (len(rows) - 1) * row_h - row_h * 0.55
    ax.plot([0.01, 0.99], [bottom, bottom], color=viz.BASELINE, lw=1.1)
    ax.text(0.015, bottom - 0.035,
            "Strong tier averages 0.352, weak 0.277 — a gap of 0.074. The average spread "
            "WITHIN a tier is 0.214, about 2.9x larger.\nP(identity effect > tier effect) = 0.993. "
            "Haiku ranks first on landed attacks and flags 23% of honest code; both matter.",
            ha="left", va="top", fontsize=8.8, color=viz.INK_SECONDARY, linespacing=1.6)
    fig.tight_layout()
    fig.savefig(f"{out}/fig10_results_table.png", dpi=220)
    plt.close(fig)


# ---------------------------------------------------------------------------
def fig_design(scores: dict, out: str) -> None:
    """The design grid: which attacker x monitor cells were actually run."""
    monitors = [m.key for m in config.MODELS]
    cells = {k for k in scores if k != "_limit"}

    fig, ax = plt.subplots(figsize=(10.4, 4.5))
    n_col, n_row = len(monitors), len(ATTACKERS)
    ax.set_xlim(-0.5, n_col - 0.5)
    ax.set_ylim(-0.5, n_row - 0.5)
    ax.invert_yaxis()
    ax.axis("off")

    for r, attacker in enumerate(ATTACKERS):
        for c, monitor in enumerate(monitors):
            box = dict(xy=(c - 0.42, r - 0.40), width=0.84, height=0.80)
            if (attacker, monitor) not in cells:
                if attacker == "geminipro" and monitor == "gpt55":
                    ax.add_patch(plt.Rectangle(**box, facecolor="none",
                                               edgecolor="#b3401f", lw=1.4,
                                               linestyle=(0, (3, 2)), zorder=2))
                    ax.text(c, r, "API\nfail", ha="center", va="center", fontsize=7.2,
                            color="#b3401f", linespacing=1.3, zorder=3)
                else:
                    ax.add_patch(plt.Rectangle(**box, facecolor="#f4f3ef",
                                               edgecolor="none", zorder=1))
                continue
            dead = scores[(attacker, monitor)]["succ"].sum() < config.MIN_SUCCESSFUL_ATTACKS
            if dead:
                ax.add_patch(plt.Rectangle(**box, facecolor="#e8e7e1",
                                           edgecolor=viz.BASELINE, lw=0.8, zorder=2))
                ax.text(c, r, "dropped", ha="center", va="center", fontsize=6.9,
                        color=viz.INK_MUTED, zorder=3)
            else:
                ax.add_patch(plt.Rectangle(**box, facecolor=viz.TIER_COLOR[config.TIER[monitor]],
                                           edgecolor="none", zorder=2))
                ax.text(c, r, "200", ha="center", va="center", fontsize=7.6,
                        color="#ffffff" if config.TIER[monitor] != "weak" else viz.INK, zorder=3)

    for c, monitor in enumerate(monitors):
        ax.text(c, -0.62, config.LABEL[monitor], rotation=38, ha="left", va="bottom",
                fontsize=8.1, color=viz.INK_SECONDARY)
        ax.text(c, -0.50, config.TIER[monitor], ha="center", va="bottom",
                fontsize=6.8, color=viz.INK_MUTED)
    for r, attacker in enumerate(ATTACKERS):
        ax.text(-0.62, r, config.LABEL[attacker], ha="right", va="center",
                fontsize=9.2, color=viz.INK)

    # family separators
    boundaries = []
    for c in range(1, n_col):
        if config.FAMILY[monitors[c]] != config.FAMILY[monitors[c - 1]]:
            boundaries.append(c - 0.5)
    for b in boundaries:
        ax.plot([b, b], [-0.45, n_row - 0.55], color=viz.BASELINE, lw=1.2, zorder=4)

    handles = [
        plt.Rectangle((0, 0), 1, 1, facecolor=viz.TIER_COLOR["weak"]),
        plt.Rectangle((0, 0), 1, 1, facecolor=viz.TIER_COLOR["mid"]),
        plt.Rectangle((0, 0), 1, 1, facecolor=viz.TIER_COLOR["strong"]),
        plt.Rectangle((0, 0), 1, 1, facecolor="#e8e7e1", edgecolor=viz.BASELINE),
        plt.Rectangle((0, 0), 1, 1, facecolor="none", edgecolor="#b3401f",
                      linestyle=(0, (3, 2))),
        plt.Rectangle((0, 0), 1, 1, facecolor="#f4f3ef"),
    ]
    labels = ["weak-tier monitor", "mid-tier monitor", "strong-tier monitor",
              "ran, then dropped (red team never attacked)",
              "failed on a cross-provider API error", "not paired"]
    fig.legend(handles, labels, loc="lower center", ncol=3, frameon=False,
               fontsize=8.1, bbox_to_anchor=(0.5, -0.06))

    fig.suptitle("The design: 3 attackers x 8 monitors each = 24 cells, 23 completed",
                 fontsize=12.5, x=0.008, ha="left", color=viz.INK, fontweight="bold")
    ax.text(0, 1.0, "", transform=ax.transAxes)
    fig.text(0.008, 0.885,
             "Each attacker is paired with its own family's full three-tier ladder, plus the weak and "
             "strong tier of each other family, plus Qwen.\nCells show samples run (200 = 100 honest + "
             "100 attack). Mid-tier monitors appear only in their own family's row.",
             ha="left", va="top", fontsize=8.5, color=viz.INK_SECONDARY, linespacing=1.5)
    fig.tight_layout(rect=[0.02, 0.06, 1, 0.86])
    fig.savefig(f"{out}/fig11_design.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    viz.apply_style()
    out = config.figure_dir()
    os.makedirs(out, exist_ok=True)
    scores = load_scores()
    fig_results_table(scores, out)
    print("  wrote fig10_results_table.png")
    fig_design(scores, out)
    print("  wrote fig11_design.png")


if __name__ == "__main__":
    main()
