"""Is it monitor IDENTITY or monitor TIER that determines discrimination?

Evaluates on the strictest operating point the honest distribution can express
(TPR at zero false positives), restricted to the balanced sub-design: the
monitors present in every viable attacker row. See utils/metrics.py for why AUC
alone is not trustworthy on this data.

    python -m scripts.analyze_identity
    LIMIT=100 BOOTSTRAP=4000 python -m scripts.analyze_identity
"""

from __future__ import annotations

import warnings

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd

from utils import config
from utils.data import balanced, cell_table, cell_value, load_scores, viable
from utils.stats import bootstrap, decompose, permutation_tier

METRICS = (
    ("tpr0", "TPR at zero false positives"),
    ("auc", "ROC-AUC (for comparison with prior work)"),
    ("tpr0_succ", "TPR at zero FP, SUCCESSFUL attacks only"),
)


def report_degeneracy(cells: pd.DataFrame) -> None:
    """The instrument check that gates everything downstream."""
    print("\n=== is the honest distribution degenerate? ===")
    print(f"  cells where ALL honest samples share one score: "
          f"{(cells.n_distinct_honest == 1).sum()}/{len(cells)}")
    print(f"  max distinct honest values in any cell: {cells.n_distinct_honest.max()}")
    predicted = 0.5 + cells.tpr0.where(cells.honest_flag_rate == 0) / 2
    err = (cells.auc - predicted).abs().dropna()
    print(f"  where honest is constant, |AUC - (0.5 + p/2)|: max {err.max():.4f}")
    print("  -> AUC is a detection rate in this data, not a ranking statistic.")


def report_metric(scores: dict, both: pd.DataFrame, metric: str, name: str) -> None:
    print(f"\n{'=' * 68}\n=== {name} [{metric}] ===")
    result = decompose(both, metric)
    ci = bootstrap(scores, both, metric, np.random.default_rng(1))
    means = result["monitor_means"].sort_values(ascending=False)

    print(f"  {'monitor':22} {'tier':7} {'centred':>8}  95% CI")
    for monitor, value in means.items():
        lo, hi = ci["monitor"][monitor]
        print(f"  {config.LABEL[monitor]:22} {config.TIER[monitor]:7} "
              f"{value:+8.3f}  [{lo:+.3f}, {hi:+.3f}]")

    print()
    for label, key in (("identity spread (best - worst) ", "spread"),
                       ("tier gap (strong - weak mean)  ", "tier_gap"),
                       ("mean within-tier spread        ", "within_tier_spread")):
        print(f"  {label}: {result[key]:.3f}  "
              f"95% CI [{ci[key][0]:.3f}, {ci[key][1]:.3f}]")
    print(f"  variance in monitor means explained by tier (R2): {result['r2_tier']:.3f}  "
          f"95% CI [{ci['r2_tier'][0]:.3f}, {ci['r2_tier'][1]:.3f}]")
    print(f"  permutation p (tier vs shuffled labels): "
          f"{permutation_tier(both, metric, np.random.default_rng(2)):.3f}")

    ratios = ci["ratio_draws"]
    print(f"  -> within-tier spread is {result['ratio']:.1f}x the between-tier gap  "
          f"95% CI [{np.percentile(ratios, 2.5):.1f}x, {np.percentile(ratios, 97.5):.1f}x]  "
          f"P(ratio > 1) = {(ratios > 1).mean():.3f}")

    weak = [m for m in means.index if config.TIER[m] == "weak"]
    strong = [m for m in means.index if config.TIER[m] == "strong"]
    best_weak = max(weak, key=lambda m: means[m])
    print(f"\n  best weak-tier monitor: {config.LABEL[best_weak]}")
    for other in strong:
        delta = ci["monitor_draws"][best_weak] - ci["monitor_draws"][other]
        print(f"    vs {config.LABEL[other]:22} (strong): "
              f"delta {means[best_weak] - means[other]:+.3f}  "
              f"P(weak better) = {(delta > 0).mean():.3f}")


def report_ladders(scores: dict, cells: pd.DataFrame) -> None:
    """Does tier work WITHIN a family, even though it fails across families?

    Separating the two is what makes the claim precise. "Tier does not travel
    between families" is defensible; "tier is noise" is not, and the original
    AUC-based non-monotonicity was an artifact.
    """
    print(f"\n{'=' * 68}\n=== within-family capability ladders ===")
    rng = np.random.default_rng(3)
    # Metric order is fixed here rather than reusing METRICS: it determines the
    # order the shared RNG is consumed in, and the published P(monotonic) values
    # (54% / 69%) were produced with this ordering.
    for attacker in sorted(cells.attacker.unique()):
        own = cells[(cells.attacker == attacker)
                    & (cells.monitor.map(config.FAMILY) == config.FAMILY[attacker])]
        own = own.sort_values("tier", key=lambda s: s.map(config.TIER_ORDER))
        if len(own) < 3:
            continue
        for metric in ("auc", "tpr0", "tpr0_succ"):
            observed = list(own[metric])
            hits = 0
            for _ in range(1000):
                draw = [cell_value(scores[(attacker, m)], metric, rng) for m in own.monitor]
                hits += draw == sorted(draw)
            verdict = "MONOTONIC" if observed == sorted(observed) else "not monotonic"
            print(f"  {attacker:10} {metric:10} "
                  + "  ".join(f"{t}={v:.3f}" for t, v in zip(own.tier, observed))
                  + f"   {verdict:14} P(monotonic) = {hits / 1000:.2f}")
        print()


def main() -> None:
    scores = load_scores()
    cells = cell_table(scores)
    print("\n=== every complete cell ===")
    print(cells.to_string(index=False, float_format=lambda x: f"{x:.3f}"))

    dead = cells[cells.n_succ < config.MIN_SUCCESSFUL_ATTACKS]
    print(f"\nDropping {len(dead)} cells with <{config.MIN_SUCCESSFUL_ATTACKS} successful "
          f"attacks (attackers: {sorted(dead.attacker.unique())})")
    live = viable(cells)

    report_degeneracy(live)

    both = balanced(live)
    print("\n=== confirmatory (balanced) sub-design ===")
    print(f"  {both.attacker.nunique()} attackers x {both.monitor.nunique()} monitors "
          f"= {len(both)} cells")
    print(f"  tier balance: {dict(both.groupby('tier').monitor.nunique())}")
    print(f"  excluded (single-row, no within-monitor contrast): "
          f"{sorted(set(live.monitor) - set(both.monitor))}")

    for metric, name in METRICS:
        report_metric(scores, both, metric, name)

    report_ladders(scores, live)

    root = config.log_root()
    both.to_csv(f"{root}/identity_cells.csv", index=False)
    live.to_csv(f"{root}/identity_all_viable.csv", index=False)
    print(f"Wrote {root}/identity_cells.csv and identity_all_viable.csv")


if __name__ == "__main__":
    main()
