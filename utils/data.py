"""Loading cells off disk, with a cache.

Parsing .eval transcripts through control_arena's samples_df takes minutes for
the full matrix, so raw per-sample suspicion scores are pickled once and reused.
Delete the cache file to force a re-parse from the logs.
"""

from __future__ import annotations

import os
import pickle
import warnings

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd

from utils import config
from utils.metrics import auc, distinct_values, tpr_at_zero_fpr


def _cell_dirs(root: str, limit: int):
    """Yield (attacker, monitor, path) for every cell directory at this limit."""
    for name in sorted(os.listdir(root)):
        path = os.path.join(root, name)
        if not (os.path.isdir(path) and name.startswith("atk-") and name.endswith(f"n{limit}")):
            continue
        attacker = name.split("__")[0][len("atk-"):]
        monitor = name.split("__")[1][len("mon-"):]
        yield attacker, monitor, path


def load_scores(root: str | None = None, limit: int | None = None,
                cache: str | None = None, verbose: bool = True) -> dict:
    """Raw per-sample scores per cell, keyed (attacker, monitor).

    Each value is ``{"h": honest scores, "a": attack scores, "succ": bool mask
    of attacks that solved the main task AND landed the backdoor}``.
    """
    root = root or config.log_root()
    limit = limit if limit is not None else config.limit()
    cache = cache or config.score_cache()

    if os.path.exists(cache):
        with open(cache, "rb") as fh:
            cached = pickle.load(fh)
        if cached.get("_limit") == limit:
            if verbose:
                print(f"Loaded {len(cached) - 1} cells from {cache}")
            return cached

    from control_arena.analysis import samples_df  # slow import; only on cache miss

    col = config.SUSPICION_COL
    out: dict = {"_limit": limit}
    for attacker, monitor, path in _cell_dirs(root, limit):
        try:
            df = samples_df(path).copy()
            df[col] = pd.to_numeric(df[col], errors="coerce")
            scored = df.dropna(subset=[col])
        except Exception:  # noqa: BLE001 - a malformed cell should not kill the sweep
            continue
        if len(scored) < config.COMPLETENESS_TOLERANCE * 2 * limit:
            continue  # incomplete cell; the analysis refuses to read partials
        attack = scored[scored.eval_mode == "attack"]
        out[(attacker, monitor)] = dict(
            h=scored[scored.eval_mode == "honest"][col].to_numpy(float),
            a=attack[col].to_numpy(float),
            succ=((attack.main_task_success == True) & (attack.side_task_success == True)).to_numpy(bool),  # noqa: E712
        )
        if verbose:
            print(f"  loaded {attacker:10} x {monitor}", flush=True)
    with open(cache, "wb") as fh:
        pickle.dump(out, fh)
    return out


def cell_table(scores: dict) -> pd.DataFrame:
    """One row per cell with every headline metric, before any exclusion."""
    rows = []
    for key, cell in scores.items():
        if key == "_limit":
            continue
        attacker, monitor = key
        h, a, succ = cell["h"], cell["a"], cell["succ"]
        rows.append(dict(
            attacker=attacker,
            monitor=monitor,
            tier=config.TIER[monitor],
            family=config.FAMILY[monitor],
            n_succ=int(succ.sum()),
            auc=auc(h, a),
            tpr0=tpr_at_zero_fpr(h, a),
            tpr0_succ=tpr_at_zero_fpr(h, a, succ),
            honest_flag_rate=float((h > 0).mean()),
            n_distinct_honest=distinct_values(h),
        ))
    return pd.DataFrame(rows).sort_values(["attacker", "monitor"]).reset_index(drop=True)


def viable(cells: pd.DataFrame) -> pd.DataFrame:
    """Cells whose attacker actually landed attacks - everything else is noise."""
    return cells[cells.n_succ >= config.MIN_SUCCESSFUL_ATTACKS]


def balanced(cells: pd.DataFrame) -> pd.DataFrame:
    """The confirmatory sub-design: monitors present in EVERY viable attacker row.

    A monitor appearing in only one row cannot support a within-monitor contrast,
    and an additive fit absorbs it entirely (residual exactly zero). Restricting
    to the balanced set is what makes attacker difficulty cancel.
    """
    n_attackers = cells.attacker.nunique()
    return cells.groupby("monitor").filter(lambda g: len(g) == n_attackers)


def cell_value(cell: dict, metric: str, rng=None) -> float:
    """Recompute one metric for one cell, optionally on a bootstrap resample.

    Passing `rng` resamples honest and attack scores with replacement, carrying
    the success mask along with the attack draw so the landed-attack subset stays
    consistent with the rows actually drawn.
    """
    h, a, succ = cell["h"], cell["a"], cell["succ"]
    if rng is not None:
        h = h[rng.integers(0, len(h), len(h))]
        idx = rng.integers(0, len(a), len(a))
        a, succ = a[idx], succ[idx]
    if metric == "auc":
        return auc(h, a)
    return tpr_at_zero_fpr(h, a, succ if metric == "tpr0_succ" else None)
