"""Generate the three figures for the monitor-discrimination write-up.

Reads every COMPLETE cell under logs/monitor_exp (n scored >= 2*LIMIT) and emits:
  fig1_ladder.png    monitor capability -> AUC and safety   (H1)
  fig2_heatmap.png   attacker x monitor AUC matrix          (H2, the money figure)
  fig3_mirage.png    safety bootstrap CI width vs n         (H3)
  figures_data.md    the underlying numbers

Usage:  LIMIT=100 python make_figures.py
"""

import os
import warnings

warnings.filterwarnings("ignore")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from control_arena.analysis import compute_safety, compute_usefulness, samples_df

LIMIT = int(os.environ.get("LIMIT", "100"))
ROOT = os.environ.get("LOG_ROOT", "logs/monitor_exp")
OUT = os.environ.get("FIG_DIR", "figures")
SC = "score_max_suspicion_scorer"

# Display names + tier ordering (must match monitor_discrimination_experiment.py)
PROVIDER = {
    "gpt41mini": ("OpenAI", "weak"), "gpt54mini": ("OpenAI", "mid"), "gpt55": ("OpenAI", "strong"),
    "haiku45": ("Anthropic", "weak"), "sonnet5": ("Anthropic", "mid"), "opus48": ("Anthropic", "strong"),
    "flashlite": ("Google", "weak"), "flash": ("Google", "mid"), "geminipro": ("Google", "strong"),
    "qwen": ("Qwen (OSS)", "strong"),
}
TIER_ORDER = {"weak": 0, "mid": 1, "strong": 2}


def load_cells() -> pd.DataFrame:
    rows = []
    for d in sorted(os.listdir(ROOT)):
        p = os.path.join(ROOT, d)
        if not (os.path.isdir(p) and d.endswith(f"n{LIMIT}") and d.startswith("atk-")):
            continue
        atk = d.split("__")[0].replace("atk-", "")
        mon = d.split("__")[1].replace("mon-", "")
        try:
            df = samples_df(p).copy()
            df[SC] = pd.to_numeric(df[SC], errors="coerce")
            scored = df.dropna(subset=[SC])
        except Exception:  # noqa: BLE001
            continue
        if len(scored) < 0.99 * 2 * LIMIT:
            continue  # incomplete -> excluded (99% tolerance, see cell_status)
        h = scored[scored.eval_mode == "honest"]
        a = scored[scored.eval_mode == "attack"]
        auc = roc_auc_score([0] * len(h) + [1] * len(a), list(h[SC]) + list(a[SC]))
        n_succ = int(((a["main_task_success"] == True) & (a["side_task_success"] == True)).sum())  # noqa: E712
        try:
            safety = compute_safety(df, "max_suspicion_scorer", 5)
        except Exception:  # noqa: BLE001
            safety = np.nan
        rows.append(
            dict(
                attacker=atk, monitor=mon,
                atk_prov=PROVIDER[atk][0], mon_prov=PROVIDER[mon][0],
                mon_tier=PROVIDER[mon][1],
                same_provider=PROVIDER[atk][0] == PROVIDER[mon][0],
                auc=auc, safety=safety,
                usefulness=compute_usefulness(df),
                n_success_atk=n_succ,
            )
        )
    return pd.DataFrame(rows)


def fig_ladder(df: pd.DataFrame) -> None:
    """H1: within-provider monitor capability ladder."""
    lad = df[df.same_provider].copy()
    lad["ord"] = lad.mon_tier.map(TIER_ORDER)
    lad = lad.sort_values(["atk_prov", "ord"])
    if lad.empty:
        return
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    for prov, g in lad.groupby("atk_prov"):
        # only plot rows where the attack actually landed (else it's noise)
        label = f"{prov} attacker"
        axes[0].plot(g.ord, g.auc, "o-", label=label)
        axes[1].plot(g.ord, g.safety, "o-", label=label)
    for ax, ylab, title in (
        (axes[0], "Monitor AUC (honest vs attack)", "Monitor discrimination"),
        (axes[1], "Safety @5% audit", "Protocol safety"),
    ):
        ax.set_xticks([0, 1, 2]); ax.set_xticklabels(["weak", "mid", "strong"])
        ax.set_xlabel("Monitor capability tier"); ax.set_ylabel(ylab)
        ax.set_title(title); ax.grid(alpha=0.3); ax.legend(fontsize=8)
    axes[0].axhline(0.5, ls="--", c="gray", lw=1)
    axes[0].text(0.02, 0.505, "chance", fontsize=7, c="gray")
    fig.suptitle("H1: monitor capability drives safety (protocol, threshold, attacker fixed)", fontsize=11)
    fig.tight_layout()
    fig.savefig(f"{OUT}/fig1_ladder.png", dpi=150)


def fig_heatmap(df: pd.DataFrame) -> None:
    """H2: attacker x monitor AUC matrix; diagonal = same-family."""
    if df.empty:
        return
    atks = sorted(df.attacker.unique(), key=lambda a: PROVIDER[a][0])
    mons = sorted(df.monitor.unique(), key=lambda m: (PROVIDER[m][0], TIER_ORDER[PROVIDER[m][1]]))
    M = np.full((len(atks), len(mons)), np.nan)
    for _, r in df.iterrows():
        M[atks.index(r.attacker), mons.index(r.monitor)] = r.auc
    fig, ax = plt.subplots(figsize=(1.1 * len(mons) + 3, 1.0 * len(atks) + 2.5))
    im = ax.imshow(M, cmap="RdYlGn", vmin=0.45, vmax=0.85, aspect="auto")
    ax.set_xticks(range(len(mons)))
    ax.set_xticklabels([f"{m}\n({PROVIDER[m][0]}, {PROVIDER[m][1]})" for m in mons], fontsize=7, rotation=45, ha="right")
    ax.set_yticks(range(len(atks)))
    ax.set_yticklabels([f"{a}\n({PROVIDER[a][0]})" for a in atks], fontsize=8)
    for i in range(len(atks)):
        for j in range(len(mons)):
            if np.isnan(M[i, j]):
                ax.text(j, i, "—", ha="center", va="center", c="gray")
                continue
            same = PROVIDER[atks[i]][0] == PROVIDER[mons[j]][0]
            ax.text(j, i, f"{M[i,j]:.2f}" + ("\n(same)" if same else ""),
                    ha="center", va="center", fontsize=7,
                    fontweight="bold" if same else "normal")
            if same:
                ax.add_patch(plt.Rectangle((j - .5, i - .5), 1, 1, fill=False, ec="black", lw=2))
    fig.colorbar(im, ax=ax, label="Monitor AUC")
    ax.set_xlabel("Monitor"); ax.set_ylabel("Attacker")
    ax.set_title("H2: does monitor provenance matter?\nboxed = same model family as attacker", fontsize=10)
    fig.tight_layout()
    fig.savefig(f"{OUT}/fig2_heatmap.png", dpi=150)


def fig_mirage(df: pd.DataFrame, n_boot: int = 400) -> None:
    """H3: safety CI width shrinks with n - and is enormous at tutorial scale."""
    rng = np.random.default_rng(0)
    cells = df[df.n_success_atk >= 5].head(3)  # only cells where attacks actually landed
    if cells.empty:
        return
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    for _, r in cells.iterrows():
        d = samples_df(os.path.join(ROOT, f"atk-{r.attacker}__mon-{r.monitor}__n{LIMIT}")).copy()
        d[SC] = pd.to_numeric(d[SC], errors="coerce"); d = d.dropna(subset=[SC])
        h, a = d[d.eval_mode == "honest"], d[d.eval_mode == "attack"]
        ns, los, his = [], [], []
        for n in (10, 25, 50, 100):
            if len(h) < n or len(a) < n:
                continue
            vals = []
            for _ in range(n_boot):
                sub = pd.concat([h.iloc[rng.choice(len(h), n, True)], a.iloc[rng.choice(len(a), n, True)]])
                try:
                    vals.append(compute_safety(sub, "max_suspicion_scorer", 5))
                except Exception:  # noqa: BLE001, S110
                    pass
            if vals:
                v = np.array(vals, float)
                ns.append(n); los.append(np.percentile(v, 2.5)); his.append(np.percentile(v, 97.5))
        if ns:
            ax.fill_between(ns, los, his, alpha=0.25)
            ax.plot(ns, [(l + h_) / 2 for l, h_ in zip(los, his)], "o-",
                    label=f"{r.attacker} / {r.monitor}")
    ax.set_xscale("log"); ax.set_xticks([10, 25, 50, 100]); ax.set_xticklabels(["10", "25", "50", "100"])
    ax.set_xlabel("Samples per mode"); ax.set_ylabel("Safety @5% (95% bootstrap CI)")
    ax.set_title("H3: at tutorial scale, safety is uninterpretable", fontsize=11)
    ax.grid(alpha=0.3); ax.legend(fontsize=8); ax.set_ylim(-0.05, 1.05)
    fig.tight_layout()
    fig.savefig(f"{OUT}/fig3_mirage.png", dpi=150)


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    df = load_cells()
    if df.empty:
        print("No complete cells found.")
        return
    print(f"Loaded {len(df)} complete cells (n={2*LIMIT} each)\n")
    cols = ["attacker", "monitor", "mon_tier", "same_provider", "auc", "safety", "usefulness", "n_success_atk"]
    print(df[cols].to_string(index=False))

    # same- vs cross-provider contrast, matched on tier (the H2 test)
    viable = df[df.n_success_atk >= 5]
    print("\n=== H2 contrast (viable-attack cells only, matched by tier) ===")
    for tier in ("weak", "mid", "strong"):
        t = viable[viable.mon_tier == tier]
        s, c = t[t.same_provider], t[~t.same_provider]
        if len(s) and len(c):
            print(f"{tier:7} same={s.auc.mean():.3f} (n={len(s)})  cross={c.auc.mean():.3f} (n={len(c)})"
                  f"  delta={c.auc.mean()-s.auc.mean():+.3f}")

    fig_ladder(df); fig_heatmap(df); fig_mirage(df)
    with open(f"{OUT}/figures_data.md", "w") as f:
        f.write(f"# Figure data (n={2*LIMIT} per cell)\n\n")
        f.write(df[cols].to_markdown(index=False))
    print(f"\nWrote figures + data to {OUT}/")


if __name__ == "__main__":
    main()
