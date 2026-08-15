"""Variance decomposition, bootstrap intervals, permutation tests.

The question these answer: does a monitor's capability TIER predict how well it
discriminates, or does the specific model identity dominate? Everything here
operates on the balanced sub-design, where row effects cancel.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from utils import config
from utils.data import cell_value


def decompose(perf: pd.DataFrame, metric: str) -> dict:
    """Row-centre, then split monitor variance into between-tier and within-tier.

    Row-centring removes attacker difficulty, which is the larger effect and is
    not what the claim is about. What remains is attributable to the monitor.
    `r2_tier` is the share of that remaining variance tier explains; if tier were
    the right abstraction it would sit near 1.
    """
    df = perf.copy()
    df["centred"] = df[metric] - df.groupby("attacker")[metric].transform("mean")
    means = df.groupby("monitor").centred.mean()
    tiers = pd.Series({key: config.TIER[key] for key in means.index})
    grand = means.mean()
    tier_means = means.groupby(tiers).transform("mean")
    ss_total = float(((means - grand) ** 2).sum())
    ss_between = float(((tier_means - grand) ** 2).sum())
    within = float(means.groupby(tiers).apply(lambda g: g.max() - g.min()).mean())
    gap = float(means.groupby(tiers).mean().max() - means.groupby(tiers).mean().min())
    return dict(
        monitor_means=means,
        spread=float(means.max() - means.min()),
        r2_tier=ss_between / ss_total if ss_total > 0 else np.nan,
        tier_gap=gap,
        within_tier_spread=within,
        # The headline is a RATIO, so it needs its own interval: the component
        # CIs can overlap while the ratio stays comfortably above 1, because
        # numerator and denominator move together across bootstrap draws.
        ratio=within / gap if gap > 0 else np.inf,
    )


def bootstrap(scores: dict, cells: pd.DataFrame, metric: str, rng,
              draws: int | None = None) -> dict:
    """Resample suspicion scores within every cell, recompute the whole chain.

    One iteration perturbs all cells at once, so the derived statistics inherit a
    coherent joint interval rather than being assembled from independent per-cell
    intervals.
    """
    draws = draws if draws is not None else config.bootstrap_draws()
    keys = list(zip(cells.attacker, cells.monitor))
    tracked = ("spread", "r2_tier", "tier_gap", "within_tier_spread", "ratio")
    out: dict[str, list] = {k: [] for k in tracked}
    per_monitor: dict[str, list] = {m: [] for m in cells.monitor.unique()}

    for _ in range(draws):
        rows = [
            dict(attacker=a, monitor=m, **{metric: cell_value(scores[(a, m)], metric, rng)})
            for a, m in keys
        ]
        result = decompose(pd.DataFrame(rows), metric)
        for key in tracked:
            out[key].append(result[key])
        for monitor, value in result["monitor_means"].items():
            per_monitor[monitor].append(value)

    ci = {k: tuple(np.percentile(v, [2.5, 97.5])) for k, v in out.items()}
    ci["ratio_draws"] = np.asarray(out["ratio"])
    ci["monitor"] = {m: tuple(np.percentile(v, [2.5, 97.5])) for m, v in per_monitor.items()}
    ci["monitor_draws"] = {m: np.asarray(v) for m, v in per_monitor.items()}
    return ci


def permutation_tier(perf: pd.DataFrame, metric: str, rng, draws: int = 10_000) -> float:
    """Could tier's apparent explanatory power arise from shuffled labels?

    Shuffles which monitor holds which tier label and refits. A large p means tier
    explains no more of the monitor variance than an arbitrary partition would.
    """
    observed = decompose(perf, metric)["r2_tier"]
    monitors = sorted(perf.monitor.unique())
    labels = [config.TIER[m] for m in monitors]
    saved = {m: config.TIER[m] for m in monitors}
    null = []
    try:
        for _ in range(draws):
            config.TIER.update(dict(zip(monitors, rng.permutation(labels))))
            null.append(decompose(perf, metric)["r2_tier"])
    finally:
        config.TIER.update(saved)  # never leave the registry mutated
    return float((np.asarray(null) >= observed).mean())


def permutation_label(labels, values, rng, draws: int = 20_000) -> tuple[float, float]:
    """Generic 'does this categorical label explain variance?' test.

    Returns (R2, p). Needed because a label with many levels over few points -
    family, with four levels over six monitors - saturates by construction, so a
    high R2 is not evidence on its own.
    """
    labels = np.asarray(labels)
    values = np.asarray(values, dtype=float)

    def r2(lab):
        grouped = pd.Series(values).groupby(pd.Series(lab)).transform("mean")
        denom = ((values - values.mean()) ** 2).sum()
        return 1 - ((values - grouped) ** 2).sum() / denom if denom > 0 else np.nan

    observed = r2(labels)
    null = [r2(rng.permutation(labels)) for _ in range(draws)]
    return float(observed), float(np.mean(np.asarray(null) >= observed))


def monitor_means(scores: dict, monitors, attackers, metric: str, rng,
                  draws: int | None = None) -> tuple[pd.Series, dict]:
    """Raw (uncentred) per-monitor means with bootstrap CIs.

    On a balanced design the plain mean over attacker rows is unbiased, so these
    are the numbers to display - `decompose` centres them, which is right for the
    variance work but wrong for a table a reader will interpret directly.
    """
    draws = draws if draws is not None else config.bootstrap_draws()
    point = pd.Series({
        m: np.mean([cell_value(scores[(a, m)], metric) for a in attackers]) for m in monitors
    })
    per_monitor: dict[str, list] = {m: [] for m in monitors}
    for _ in range(draws):
        for m in monitors:
            per_monitor[m].append(
                np.mean([cell_value(scores[(a, m)], metric, rng) for a in attackers])
            )
    ci = {m: tuple(np.percentile(v, [2.5, 97.5])) for m, v in per_monitor.items()}
    return point, ci
