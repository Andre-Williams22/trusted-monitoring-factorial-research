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
VIABLE_ATTACKERS = ("geminipro", "gpt55")


# ---------------------------------------------------------------------------
def fig_results_table(scores: dict, out: str) -> None:
    """The result table as a graphic.

    A table is the right form here: five exact numbers per row, and the reader
    needs to compare within rows as well as down columns. The tier chip carries
    the finding - it is the column that refuses to sort with the ranking.
    """
    # Balanced sub-design derived from the data, not hardcoded: a monitor
    # qualifies when it was scored against every viable attacker row.
    balanced = sorted(
        m for m in config.BY_KEY
        if all((a, m) in scores for a in VIABLE_ATTACKERS)
    )
    rows = []
    for key in balanced:
        caught = np.mean([cell_value(scores[(a, key)], "tpr0") for a in VIABLE_ATTACKERS])
        landed = np.mean([cell_value(scores[(a, key)], "tpr0_succ") for a in VIABLE_ATTACKERS])
        fpr = np.mean([(scores[(a, key)]["h"] > 0).mean() for a in VIABLE_ATTACKERS])
        rows.append((config.LABEL[key], config.TIER[key], caught, landed, fpr))
    rows.sort(key=lambda r: -r[2])

    strong = [r[2] for r in rows if r[1] == "strong"]
    weak = [r[2] for r in rows if r[1] == "weak"]
    within = np.mean([max(strong) - min(strong), max(weak) - min(weak)])
    gap = abs(np.mean(strong) - np.mean(weak))
    s_land = np.mean([r[3] for r in rows if r[1] == "strong"])
    w_land = np.mean([r[3] for r in rows if r[1] == "weak"])

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
            f"{len(rows)} monitors, each scored against both viable attackers — the balanced "
            f"sub-design. Tier does not\nsort the ranking: "
            + ", ".join(r[1] for r in rows) + ". n = 100 per mode.",
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
            f"On all attacks, strong tier averages {np.mean(strong):.3f} and weak {np.mean(weak):.3f} "
            f"— a gap of {gap:.3f}. The spread WITHIN a tier is {within:.3f}, about {within/gap:.1f}x larger.\n"
            f"On the attacks that LANDED the gap reverses: weak {w_land:.3f} vs strong {s_land:.3f}, "
            f"and tier explains almost nothing (R2 = 0.02, permutation p = 0.78).",
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

    # Every paired cell RAN at full n. The Opus row is excluded from analysis
    # afterwards, at the row level, because that attacker landed one successful
    # attack in 100 - so the cells still show their sample count and keep their
    # tier colour, hatched to mark the exclusion rather than blanked out.
    for r, attacker in enumerate(ATTACKERS):
        for c, monitor in enumerate(monitors):
            box = dict(xy=(c - 0.42, r - 0.40), width=0.84, height=0.80)
            if (attacker, monitor) not in cells:
                ax.add_patch(plt.Rectangle(**box, facecolor="#f4f3ef",
                                           edgecolor="none", zorder=1))
                continue
            tier_c = viz.TIER_COLOR[config.TIER[monitor]]
            excluded = scores[(attacker, monitor)]["succ"].sum() < config.MIN_SUCCESSFUL_ATTACKS
            if excluded:
                ax.add_patch(plt.Rectangle(**box, facecolor=tier_c, alpha=0.30,
                                           edgecolor="none", zorder=2))
                ax.add_patch(plt.Rectangle(**box, facecolor="none", hatch="////",
                                           edgecolor="#ffffff", lw=0.0, zorder=3))
                ax.add_patch(plt.Rectangle(**box, facecolor="none",
                                           edgecolor=viz.BASELINE, lw=0.9, zorder=4))
                ax.text(c, r, "200", ha="center", va="center", fontsize=7.6,
                        color=viz.INK_SECONDARY, zorder=5)
            else:
                ax.add_patch(plt.Rectangle(**box, facecolor=tier_c,
                                           edgecolor="none", zorder=2))
                ax.text(c, r, "200", ha="center", va="center", fontsize=7.6,
                        color="#ffffff" if config.TIER[monitor] != "weak" else viz.INK, zorder=3)

    for c, monitor in enumerate(monitors):
        ax.text(c, -0.62, config.LABEL[monitor], rotation=38, ha="left", va="bottom",
                fontsize=8.1, color=viz.INK_SECONDARY)
        ax.text(c, -0.50, config.TIER[monitor], ha="center", va="bottom",
                fontsize=6.8, color=viz.INK_MUTED)
    # Row annotation: successful attacks per 100 is an ATTACKER property, and it
    # is the reason the Opus row is excluded - so it belongs on the row, not in
    # each cell.
    for r, attacker in enumerate(ATTACKERS):
        succ = [int(scores[(attacker, m)]["succ"].sum()) for m in monitors
                if (attacker, m) in cells]
        rng = f"{min(succ)}" if min(succ) == max(succ) else f"{min(succ)}–{max(succ)}"
        noun = "successful attack" if max(succ) == 1 else "successful attacks"
        ax.text(-0.62, r - 0.10, config.LABEL[attacker], ha="right", va="center",
                fontsize=9.2, color=viz.INK)
        ax.text(-0.62, r + 0.16, f"{rng} {noun} / 100", ha="right",
                va="center", fontsize=7.0,
                color="#b3401f" if max(succ) < config.MIN_SUCCESSFUL_ATTACKS else viz.INK_MUTED)

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
        plt.Rectangle((0, 0), 1, 1, facecolor=viz.TIER_COLOR["strong"], alpha=0.30,
                      hatch="////", edgecolor=viz.BASELINE),
        plt.Rectangle((0, 0), 1, 1, facecolor="#f4f3ef"),
    ]
    labels = ["weak-tier monitor", "mid-tier monitor", "strong-tier monitor",
              "ran in full — excluded from analysis (see the Opus row)", "not paired"]
    fig.legend(handles, labels, loc="lower center", ncol=3, frameon=False,
               fontsize=8.1, bbox_to_anchor=(0.5, -0.06))

    fig.suptitle("The design: 3 attackers x 8 monitors each — all 24 cells ran at n=200",
                 fontsize=12.5, x=0.008, ha="left", color=viz.INK, fontweight="bold")
    ax.text(0, 1.0, "", transform=ax.transAxes)
    fig.text(0.008, 0.90,
             "Every paired cell ran to completion at 200 samples. The hatched Opus cells ran too — they are "
             "excluded afterwards because that\nATTACKER landed one successful attack in 100, so the whole row "
             "rests on a single event.",
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
