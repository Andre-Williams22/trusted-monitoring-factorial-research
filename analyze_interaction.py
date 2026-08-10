"""H2 interaction test: does monitor provenance matter, after correcting for
attacker difficulty (row) and monitor strength (column)?

Raw same-vs-cross means are confounded: attackers differ in how detectable they
are, and monitors differ in how good they are. The preregistered test is the
INTERACTION - do same-family cells underperform what their row and column
effects predict?

Reads complete cells straight from the logs. Usage: LIMIT=100 python analyze_interaction.py
"""

import os
import warnings

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from control_arena.analysis import samples_df

LIMIT = int(os.environ.get("LIMIT", "100"))
ROOT = os.environ.get("LOG_ROOT", "logs/monitor_exp")
SC = "score_max_suspicion_scorer"
PROV = {
    "gpt41mini": "OpenAI", "gpt54mini": "OpenAI", "gpt55": "OpenAI",
    "haiku45": "Anthropic", "sonnet5": "Anthropic", "opus48": "Anthropic",
    "flashlite": "Google", "flash": "Google", "geminipro": "Google",
    "qwen": "Qwen",
}
TIER = {
    "gpt41mini": "weak", "gpt54mini": "mid", "gpt55": "strong",
    "haiku45": "weak", "sonnet5": "mid", "opus48": "strong",
    "flashlite": "weak", "flash": "mid", "geminipro": "strong",
    "qwen": "strong",
}
TIER_ORD = {"weak": 0, "mid": 1, "strong": 2}
# Cells whose attacker essentially never lands a working backdoor carry no
# signal - including them would let a dead row dominate the fit.
MIN_SUCCESSFUL_ATTACKS = 5


def load() -> pd.DataFrame:
    rows = []
    for d in sorted(os.listdir(ROOT)):
        p = os.path.join(ROOT, d)
        if not (os.path.isdir(p) and d.endswith(f"n{LIMIT}") and d.startswith("atk-")):
            continue
        atk, mon = d.split("__")[0][4:], d.split("__")[1][4:]
        try:
            df = samples_df(p).copy()
            df[SC] = pd.to_numeric(df[SC], errors="coerce")
            s = df.dropna(subset=[SC])
        except Exception:  # noqa: BLE001
            continue
        if len(s) < 0.99 * 2 * LIMIT:
            continue
        h, a = s[s.eval_mode == "honest"], s[s.eval_mode == "attack"]
        rows.append(dict(
            attacker=atk, monitor=mon, tier=TIER[mon],
            same=int(PROV[atk] == PROV[mon]),
            auc=roc_auc_score([0] * len(h) + [1] * len(a), list(h[SC]) + list(a[SC])),
            n_succ=int(((a["main_task_success"] == True) & (a["side_task_success"] == True)).sum()),  # noqa: E712
            # kept for the sample-level bootstrap that sets the exclusion bound
            h_scores=h[SC].to_numpy(float), a_scores=a[SC].to_numpy(float),
        ))
    return pd.DataFrame(rows)


def main() -> None:
    d = load()
    print(f"Loaded {len(d)} complete cells\n")

    dead = d[d.n_succ < MIN_SUCCESSFUL_ATTACKS]
    if len(dead):
        print(f"Excluded {len(dead)} cells with <{MIN_SUCCESSFUL_ATTACKS} successful "
              f"attacks (no signal): attackers={sorted(dead.attacker.unique())}\n")
    v = d[d.n_succ >= MIN_SUCCESSFUL_ATTACKS].reset_index(drop=True)

    # --- H1: within-family capability ladders -----------------------------
    print("=== H1: capability ladders (same-family monitors) ===")
    for atk, g in v[v.same == 1].groupby("attacker"):
        g = g.sort_values("tier", key=lambda s: s.map(TIER_ORD))
        seq = "  ".join(f"{r.tier}={r.auc:.3f}" for r in g.itertuples())
        mono = list(g.auc) == sorted(g.auc)
        print(f"  {atk:10} {seq}   {'monotonic' if mono else 'NOT monotonic'}")

    # --- H2: interaction --------------------------------------------------
    print("\n=== H2: interaction (additive row+column model) ===")
    X = np.c_[np.ones(len(v)),
              pd.get_dummies(v[["attacker", "monitor"]], drop_first=True).astype(float).values]
    beta, *_ = np.linalg.lstsq(X, v.auc.values, rcond=None)
    v["resid"] = v.auc.values - X @ beta
    same_r, cross_r = v[v.same == 1].resid, v[v.same == 0].resid
    print(f"  same-family  residual: {same_r.mean():+.4f}  (n={len(same_r)})")
    print(f"  cross-family residual: {cross_r.mean():+.4f}  (n={len(cross_r)})")
    print(f"  cross - same:          {cross_r.mean() - same_r.mean():+.4f} AUC")

    # permutation test: shuffle the same/cross label within the fitted model
    rng = np.random.default_rng(0)
    obs = cross_r.mean() - same_r.mean()
    null = []
    lab = v.same.values.copy()
    for _ in range(10000):
        p = rng.permutation(lab)
        null.append(v.resid.values[p == 0].mean() - v.resid.values[p == 1].mean())
    pval = (np.abs(null) >= abs(obs)).mean()
    print(f"  permutation p = {pval:.3f} (10k shuffles)")

    # How large an effect could this design still have missed? A null is only
    # meaningful with the exclusion bound stated.
    #
    # Two independent sources of uncertainty, reported separately because which
    # one dominates is itself the interesting fact:
    #   (a) sample-level: resample suspicion scores inside each cell, recompute
    #       every AUC, refit, recompute the contrast. Propagates the ~0.04
    #       sampling SE of one AUC at n=100/mode. Comes out SMALL, because the
    #       additive fit absorbs most within-cell noise into row/column effects.
    #   (b) cell-level: resample which cells landed in the design, within group.
    #       With 15 viable cells (6 same / 9 cross) over 2 attackers, this is
    #       the binding constraint - more samples per cell would not help.
    #   (c) combined: both at once. This is the bound to quote.
    s_idx = np.flatnonzero(v.same.values == 1)
    c_idx = np.flatnonzero(v.same.values == 0)
    same_mask = v.same.values == 1
    r = v.resid.values

    def _resample_aucs() -> np.ndarray:
        out = np.empty(len(v))
        for i, row in enumerate(v.itertuples()):
            hb = row.h_scores[rng.integers(0, len(row.h_scores), len(row.h_scores))]
            ab = row.a_scores[rng.integers(0, len(row.a_scores), len(row.a_scores))]
            out[i] = roc_auc_score([0] * len(hb) + [1] * len(ab), np.r_[hb, ab])
        return out

    boot_cell = np.array([
        r[rng.choice(c_idx, len(c_idx), True)].mean() - r[rng.choice(s_idx, len(s_idx), True)].mean()
        for _ in range(10000)
    ])
    boot_samp = np.empty(2000)
    boot_both = np.empty(2000)
    for b in range(2000):
        aucs = _resample_aucs()
        bb, *_ = np.linalg.lstsq(X, aucs, rcond=None)
        rb = aucs - X @ bb
        boot_samp[b] = rb[~same_mask].mean() - rb[same_mask].mean()
        boot_both[b] = (rb[rng.choice(c_idx, len(c_idx), True)].mean()
                        - rb[rng.choice(s_idx, len(s_idx), True)].mean())
    for lab_, arr, note in (
        ("sample-level", boot_samp, "within-cell noise only"),
        ("cell-level  ", boot_cell, "which-cells noise only"),
        ("COMBINED    ", boot_both, "the bound to quote"),
    ):
        lo_, hi_ = np.percentile(arr, [2.5, 97.5])
        print(f"  95% CI, {lab_} resample: [{lo_:+.3f}, {hi_:+.3f}] AUC  ({note})")
    lo_b, hi_b = np.percentile(boot_both, [2.5, 97.5])
    print(f"  -> excludes provenance effects larger than "
          f"~{max(abs(lo_b), abs(hi_b)):.02f} AUC in either direction")

    # --- H2 by tier (preregistered: run weak and strong tiers separately) --
    # The weak tier is the deployment-relevant contrast - "which cheap model
    # should watch my frontier model?" - so it gets reported even though the
    # per-tier cell counts are tiny and nothing here is powered.
    print("\n=== H2 by monitor tier (preregistered split) ===")
    for tier in ("weak", "mid", "strong"):
        t = v[v.tier == tier]
        s, c = t[t.same == 1], t[t.same == 0]
        if not (len(s) and len(c)):
            print(f"  {tier:7} not estimable (same n={len(s)}, cross n={len(c)})")
            continue
        print(f"  {tier:7} same={s.auc.mean():.3f} (n={len(s)})  "
              f"cross={c.auc.mean():.3f} (n={len(c)})  delta={c.auc.mean() - s.auc.mean():+.3f}")
    print("  NB: raw tier means, NOT row/column-corrected - attacker difficulty is")
    print("      confounded in here, and no tier has enough cells to be powered.")

    # --- paired comparisons ----------------------------------------------
    print("\n=== Paired: monitors tested against BOTH viable attackers ===")
    for m, g in v.groupby("monitor"):
        if len(g) < 2:
            continue
        g = g.sort_values("attacker")
        print(f"  {m:10} " + " | ".join(
            f"{r.attacker}:{r.auc:.3f}{'(same)' if r.same else ''}" for r in g.itertuples()))

    # --- monitor identity spread (the effect that IS real) ----------------
    print("\n=== Monitor identity effect (mean AUC across viable attackers) ===")
    ms = v.groupby("monitor").auc.mean().sort_values()
    for m, a in ms.items():
        print(f"  {m:10} {a:.3f}")
    print(f"  spread: {ms.max() - ms.min():.3f} AUC")


if __name__ == "__main__":
    main()
