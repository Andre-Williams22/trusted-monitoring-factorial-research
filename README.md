# Trusted Monitoring: Monitor Identity Beats Monitor Tier

An AI control experiment built on [ControlArena](https://github.com/UKGovernmentBEIS/control-arena) (UK AI Security Institute). It set out to measure which monitor to deploy; the answer is that it is monitor identity, not capability tier — and getting there required retracting three claims of my own, listed below.

A 3 × 8 attacker × monitor matrix (24 cells, 10 distinct monitors, four model lineages), n = 100 per mode.

**Funded by a BlueDot Impact rapid grant.**

## The finding: which model, not what size

Seven monitors, each tested against **both** surviving attacker rows — the balanced sub-design (4 strong-tier, 3 weak), so attacker difficulty cancels. Metric is the fraction of attacks flagged at **zero false alarms on honest code**.

| Monitor | Tier | Caught (all attacks) | Caught (attacks that landed) | False alarms |
|---|---|---|---|---|
| claude-opus-4-8 | strong | 0.460 | 0.298 | 0.000 |
| gpt-5.5 | strong | 0.420 | **0.493** | 0.000 |
| **claude-haiku-4-5** | **weak** | **0.372** | 0.405 | **0.230** |
| gemini-3.1-pro | strong | 0.360 | **0.044** | 0.000 |
| gemini-3.1-flash-lite | weak | 0.290 | 0.365 | 0.005 |
| Qwen-2.5-72B | strong | 0.235 | 0.351 | 0.010 |
| gpt-4.1-mini | weak | 0.170 | 0.228 | 0.000 |

The tier column does not sort the ranking: strong, strong, weak, strong, weak, strong, weak.

**On all attack attempts, tier carries real signal.** The two best monitors are both strong-tier — size is not useless.

- Strong tier averages **0.369**; weak **0.277**. **Tier gap: 0.091.**
- Average spread *within* a tier: **0.213**, about **2.3×** larger.
- P(identity effect > tier effect) = **0.990**; **2.5×** on ROC-AUC.
- Tier explains ~22% of the variance (permutation p = **0.31**) — not significant, but not nothing.

**On the attacks that actually landed, the gap reverses and tier stops predicting.**

- Weak tier averages **0.332**, strong **0.297**. P(weak > strong) = **0.79**.
- Within-tier spread is **8.7×** the tier gap; P(identity > tier) = **1.000**.
- Tier explains **1.8%** of the variance, and a random relabelling explains as much (p = **0.78**).
- The two rankings correlate at only **Spearman +0.36**. `claude-opus-4-8` goes 1st → 5th; `gemini-3.1-pro` goes 4th → last.

**Strong-tier `gemini-3.1-pro` catches 4.4% of landed backdoors** — last of seven, below every weak-tier monitor, despite a respectable 0.360 on attack attempts. Weak-tier Haiku beats it at P = 1.000.

One caveat belongs next to the ranking: **Haiku flags 23% of honest code** — every other monitor is near zero. It earns its rank at matched false-alarm rate, but that rate is the whole deployment story. And the weak-beats-strong pairings are narrow: on all attacks Haiku beats Qwen (P = 0.975) but loses to Opus (P = 0.039) and gpt-5.5 (P = 0.164). This is not "cheap models are secretly better" — it is "tier does not tell you which is which".

## Supporting findings

| # | Finding | Status |
|---|---|---|
| 1 | **Monitor identity beats monitor tier** — the table above. Ratio 2.3× on all attacks, **8.7×** on the attacks that landed. | H1, confirmed after metric fix |
| 2 | **A strong-tier monitor is worst where it counts.** `gemini-3.1-pro` catches 4.4% of landed backdoors, last of seven. | Unplanned |
| 3 | **Elicitation is a silent confound.** Under one identical attack prompt, successful attacks per 100 ran Gemini 45–69, GPT-5.5 11–37, Opus 4.8 just **1**. Opus is not refusing — it solves 84 main tasks in attack mode. Its rows read as a monitoring success and are an artifact of a red team that didn't attack. | Unplanned, post-hoc |
| 4 | **Monitor provenance: a bound, not a null.** The interaction is +0.0067 AUC (p = 0.60), but 3 of 6 same-family cells have *structurally zero* residuals — the test rests on three contrasts across two families, which disagree in sign. Effects rivalling the identity effect are ruled out; smaller ones are unresolved. | H2, bounded |
| 5 | **Cross-provider monitoring is fiddly, not impossible.** Anthropic rejects thinking blocks it did not sign (a genuine API property). The 22 KB `id` failure is routable around: send OpenAI monitors via Chat Completions and the cell completes 200/200. | Incidental |

### Measurement corrections (how the finding was nearly missed)

| # | Correction | Status |
|---|---|---|
| A | **The honest suspicion distribution is degenerate, so the audit budget never binds.** In 11 of 16 cells all 100 honest samples share one score; no cell has more than two distinct values. The 1/2/5% thresholds coincide almost everywhere. Likely a `basic_monitor` scaffold property — check yours. | Measurement |
| B | **On that data ROC-AUC is algebraically a detection rate**, not a ranking statistic: where honest is constant, AUC = 0.5 + p/2, exact to four decimals. | Measurement |
| C | **At tutorial scale safety is uninterpretable.** A blind monitor (AUC 0.53) reported safety = 1.00 at n=15; the bootstrap 95% CI at n=10/mode spans [0.00, 0.83]. Convergent with Ge-Wang et al. (2026) by a different mechanism. | H3, confirmed |

### Corrections along the way

**"Neither capability ladder is monotonic"** — an artifact of AUC on a degenerate honest distribution. Under the corrected metric both within-family ladders climb (0.21 → 0.34 → 0.41 and 0.20 → 0.23 → 0.33), but the bootstrap only puts monotonicity at 54% / 69%. The honest verdict is **unresolved at this sample size** — not monotonic, and not non-monotonic either.

**"The corrected metric doubles the effect"** — it doesn't. When honest suspicion is constant, `TPR@0%FPR = 2 × (AUC − 0.5)` exactly, so a spread that appears to double is a change of units. Only the cells where a monitor emits nonzero honest scores actually move. The unit-free ratio barely shifts, which makes the finding **robust** to metric choice, not amplified by it.

**A claim that ControlArena's `compute_safety` is flawed** for counting all audited attack attempts in its numerator. It is the standard definition — [Ge-Wang et al. (2026)](https://arxiv.org/html/2606.06529v1) state it identically, and the framework treats catching any attempt as a blue-team win because it is decisive evidence of scheming. Withdrawn in full.

**"One cell is structurally impossible to complete."** The cross-provider `400 Invalid 'input[2].id'` failure is real, but routing OpenAI monitors through Chat Completions (which has no per-item id cap) defeats it — 200/200 samples scored on the retry. The matrix is 24 of 24. Recovering that cell *weakened* the headline: `gpt-5.5` turns out to be a strong monitor, pulling the strong-tier average up and shrinking the all-attacks ratio from 2.9× to 2.3×.

**Reporting checklist.** Any trusted-monitoring result should ship with: (1) **the number of distinct honest suspicion values** — if it's one, your audit budget isn't binding and your ROC statistics are detection rates; (2) **monitor false-positive rate on honest traffic**, next to whatever detection number you quote; (3) **catch rate on attacks that actually landed**, alongside safety — they are different quantities and the gap is large; (4) **successful-attack count** (below ~5, safety is noise); (5) **n and a CI**. One column each; none are standard.

Preregistration: [experiment design.md](experiment%20design.md) · Figures: [figures/](figures/) · Per-cell results: [logs/monitor_exp/](logs/monitor_exp/)

## Design

**Attackers (rows):** strongest per family — `gpt-5.5`, `claude-opus-4-8`, `gemini-3.1-pro-preview`
**Monitors (columns):** 10 distinct models — weak / mid / strong per family + open-weights `Qwen-2.5-72B` (always cross-lineage)

Each attacker is paired with **8** of the 10: its own family's full three-tier ladder, plus the weak and strong tier of each *other* family, plus Qwen. 3 × 8 = 24 cells. **9** monitors enter the analysis — `claude-sonnet-5` appears only in the Opus attacker row, which is dropped wholesale (finding 3).

| Tier | OpenAI | Anthropic | Google | Open-weights |
|---|---|---|---|---|
| **Weak** (the "trusted" role) | gpt-4.1-mini | claude-haiku-4-5 | gemini-3.1-flash-lite | Qwen-2.5-72B |
| Mid | gpt-5.4-mini | claude-sonnet-5 | gemini-3.5-flash | — |
| **Strong** (upper bound) | gpt-5.5 | claude-opus-4-8 | gemini-3.1-pro-preview | — |

Fixed across all cells: APPS setting, defer-to-trusted @ 0.7, `basic_monitor` scaffold, audit budgets {1, 2, 5}%.

Weak-tier cells are the deployable *trusted monitoring* result (a weak model is "trusted" because it's too weak to plausibly scheme). Strong-tier cells are an **untrusted-monitoring upper bound**, not a deployment recommendation.

## Layout

```
run_experiment.py        the experiment runner (calls model APIs, costs money)
utils/                   shared library - nothing else defines a model constant
  config.py                model registry: id, label, family, tier, + paths
  metrics.py               AUC, TPR at zero FPR, rank correlation
  data.py                  cell loading with an on-disk score cache
  stats.py                 variance decomposition, bootstrap, permutation tests
  viz.py                   matplotlib styling and the validated tier ramp
scripts/                 thin CLIs; the logic lives in utils/
  analyze_identity.py      the confirmatory identity-vs-tier analysis
  analyze_interaction.py   the preregistered provenance interaction test
  make_identity_figures.py fig6-8
  make_legacy_figures.py   fig2-4 (pre-correction pipeline, needs scikit-learn)
tests/                   registry integrity + the metric identities that caused
                         the retractions above
notebooks/               the original ControlArena tutorial walkthrough
figures/  logs/          outputs
experiment design.md     the preregistration, left at the repo root on purpose
                         so its path and commit date stay trivially checkable
```

## Running it

```bash
pip install -e ".[experiment]"        # to run the experiment
pip install -e .                      # analysis only (no sklearn, no scipy)
pip install -e ".[legacy,dev]"        # + the old figure pipeline and pytest
```

`.env` needs `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `OPENROUTER_API_KEY` (Gemini + Qwen are routed via OpenRouter). Docker must be running — APPS executes code in a sandbox.

```bash
# Smoke test any preset first (~$1, catches bad model IDs)
LIMIT=2 EXPERIMENT=ladder-openai python run_experiment.py

# Ladders first (they generate + cache attacker trajectories)
LIMIT=100 EXPERIMENT=ladder-openai    python run_experiment.py
LIMIT=100 EXPERIMENT=ladder-anthropic python run_experiment.py
LIMIT=100 EXPERIMENT=ladder-google    python run_experiment.py

# Cross matrix reuses cached generations (monitor-only cost)
LIMIT=100 EXPERIMENT=cross python run_experiment.py

# Confirmatory analysis + figures (no sklearn/scipy needed)
LIMIT=100 python -m scripts.analyze_identity
LIMIT=100 python -m scripts.make_identity_figures

# Preregistered provenance interaction test
LIMIT=100 python -m scripts.analyze_interaction

# Pre-correction figure pipeline (needs scikit-learn)
LIMIT=100 python -m scripts.make_legacy_figures

pytest                                # registry + metric identities
```

Run the `scripts.*` modules with `python -m` from the repo root so `utils/` is importable, or `pip install -e .` and run them from anywhere.

The analysis caches raw suspicion scores to `.score_cache.pkl` on first run; delete it to re-parse from the `.eval` logs.

**Env vars:** `LIMIT` (n per mode) · `EXPERIMENT` (`ladder-*`, `cross`, `qwen`, `all`) · `PAIRS="atk:mon,..."` (specific cells) · `FORCE=1` (re-run incomplete cells) · `BOOTSTRAP` (draws, default 4000) · `LOG_ROOT`, `FIG_DIR`, `SCORE_CACHE` · `MAX_RETRIES` (default 3) · `MAX_CONNECTIONS`, `MAX_SAMPLES` (throttling).

**Cost control:** attacker generations are cached, so run one cell per attacker to completion *first* — every subsequent cell for that attacker is monitor-only. An interrupted generation caches nothing and you pay again.

## Implementation notes (bugs worth knowing about)

Four failure modes cost real money here. Three of them produced *plausible-looking results* rather than loud errors:

1. **The monitor cache key ignored the monitor model.** With caching on, later configs silently reused the first monitor's suspicion scores — three byte-identical result rows that looked like a finding. Fix: `cache=False` on the monitor, and verify per-config which models were actually called.
2. **`basic_monitor_builder(model=...)` is ignored** — the monitor resolves `model_role="trusted"` → `trusted_model`. Vary the monitor via `trusted_model`, not the `model` argument.
3. **A daily-quota 429 looks exactly like slowness.** Gemini's direct API retried with 30-minute backoff for 11 hours and left a half-finished cell that a "does a log file exist?" check would treat as complete. Fixes: `MAX_RETRIES=3` so quota walls surface in minutes, routing via OpenRouter, and a completeness guard that classifies every cell missing/partial/complete and **refuses to analyze partials**.
4. **One transient 402 cancelled 23 healthy in-flight samples** by tripping the harness's error threshold, and surfaced as "credits exhausted" when credits were fine. The only one of the four that announced itself — with the wrong cause.

Every results table carries `n`, `n_exp`, `complete`, and `n_success_atk` so neither incompleteness nor an inert red team can hide.

## Selecting a monitor — a hypothesis, not a recommendation

> **This section is opinion, not result.** It is derived post-hoc from seven monitors in a single pilot, and the correlations supporting it do not reach statistical significance at that sample size. It is written down as a hypothesis worth testing, not a finding to act on.

Ordered by how well the data backs each:

1. **Measure the specific model.** Tier: R² = 0.225 (p = 0.31) on all attacks, R² = 0.018 (p = 0.78) on landed attacks. Lineage/family: R² = 0.883 on aggregate detection — but that is four category levels over six points, so it nearly saturates by construction; it fails the permutation test (p = 0.155) and collapses on landed attacks (R² = 0.339, p = 0.80). "Prefer lab X" is as unsupported as "prefer big."
2. **Score on the attacks that landed, not on all attempts.** The two rankings correlate at **Spearman +0.36**, and the tier gap reverses sign between them. `claude-opus-4-8` is 1st on attempts and 4th on landed; `gemini-3.1-pro` is 3rd and then last. Ranking by AUC or aggregate catch rate ranks on something that barely predicts the target.
3. **Report false-alarm rate at your operating threshold, always.** `claude-haiku-4-5` is 2nd on landed attacks *and* flags 23% of honest code. Both are true; the second may disqualify it at scale.
4. **First, count how many distinct values the monitor emits.** One or two, and quantile thresholds and ROC statistics do not mean what their names say — see corrections A and B. Thirty-second check; it gates whether 1–3 are meaningful.

**Weakest, most interesting:** distinct score values vs. landed-attack performance is **ρ = +0.82**; false-alarm rate vs. the same is **ρ = +0.88**. Both suggest a monitor emitting a *graded* signal beats one emitting zero for nearly everything — a two-value monitor can flag but cannot rank. The critical Spearman at n = 6 is ≈ 0.89, so **neither clears significance**; both lean on two extreme points; and it is pattern-hunting on the data that produced the headline result.

### Experiments worth running

Also opinion. Ordered by cost.

- **Score-expressiveness screen** — run candidates over existing traffic, no attack labels needed, measure score spread. A free pre-filter if the ρ = +0.82 relationship survives. Needs 15–20 monitors to test.
- **Monitor bake-off scored on landed attacks with FPR reported** — 10+ monitors, 3+ attackers, before any ranking is portable.
- **Vary the monitor prompt alongside the model** — the likeliest way this result fails to transfer. If the ranking is prompt-fit rather than model quality, the honest claim shrinks to "measure your monitor *on your scaffold*."
- **Report the aggregate-vs-landed rank correlation** as a standard diagnostic in any control eval. Free to compute from data you already have.
- **Check whether the degenerate honest distribution is scaffold-specific** — cheapest item here, biggest consequence for corrections A and B.
- **Self-monitoring diagonal** — N models each generating and each monitoring; the diagonal is a model grading its own output. Tests self-recognition directly, and is symmetric by construction so it cannot produce the structurally-zero contrasts that hollowed out the provenance test.
- **A third attacker family** — everything comparative here rests on two. An open-weights attacker is cheap and avoids refusal and cross-provider API problems.
- **Fix the failed cell** (22 KB `id` field) — the most informative missing cell, since `gpt-5.5`-as-monitor currently appears in only one row.
- **Per-model attack elicitation**, so the red team does not silently die when the untrusted model changes.

## Limitations

- **Two viable attacker rows.** Every monitor mean rests on exactly two cells. The bootstrap resamples within cells, not across attackers, so no interval reported here captures attacker-to-attacker variation. Any claim about how monitor choice behaves in general stands on n = 2.
- **Seven monitors in the confirmatory design, tier balance 4 strong / 3 weak, and no mid tier.** The balanced 2 × 7 sub-design is weak vs. strong only.
- **The identity-vs-tier ratio's confidence interval is wide** — [1.2×, 5.5×] on all attacks, [2.5×, 188×] on landed attacks. The direction is solid (P ≈ 0.99); the magnitude is not. The upper bound is unstable — the denominator approaches zero in some bootstrap draws — and should not be quoted.
- **One monitor scaffold, one domain.** A single prompt (`basic_monitor`, final-code review) on APPS, which is public and near-certainly in training data. The degenerate score distribution may be a property of *this scaffold* rather than of these models — the most important thing to check before generalising corrections A and B.
- **Static, non-adaptive attacks**, with a prompted proxy attacker rather than a real schemer. No red-team iteration against each monitor. The provenance bound in particular may not survive adaptive attacks (Terekhov et al. 2025).
- **The landed-attack metric has small denominators** (11–69 successful attacks per cell), so those intervals are the widest reported.
- **Provenance is a bound, not a null.** Two same-family cells have structurally zero residuals; the test rests on four contrasts across two families that disagree in sign (interaction +0.0085 AUC).
- **Findings 2 and 3 are post-hoc**, as is the entire selection-protocol section above.
- **The selection criteria rest on seven monitors.** Neither supporting correlation clears the significance threshold at that n, and both are analysed on the same data that produced the headline result.
- **Closed-model API snapshot.** Models update silently. IDs are pinned in the repo; the Google strong tier is an alias, not a fixed snapshot.

## References

- Greenblatt, Shlegeris, Sachan & Roger (2023). [*AI Control: Improving Safety Despite Intentional Subversion*](https://arxiv.org/abs/2312.06942)
- UK AI Security Institute. [*ControlArena*](https://github.com/UKGovernmentBEIS/control-arena)
- Ge-Wang, Crosse, Hadad, Schaeffer, Potham & Tracy (2026). [*Attack Selection in Agentic AI Control Evaluations Meaningfully Decreases Safety*](https://arxiv.org/abs/2606.06529)
- Loughridge, Colognese, Griffin, Tracy, Kutasov & Benton (2025). [*Optimizing AI Agent Attacks With Synthetic Data*](https://arxiv.org/abs/2511.02823)
- Terekhov et al. (2025). [*Adaptive Attacks on Trusted Monitors Subvert AI Control Protocols*](https://arxiv.org/abs/2510.09462)
- Mallen, Griffin, Wagner, Abate & Shlegeris (2024). [*Subversion Strategy Eval*](https://arxiv.org/abs/2412.12480)
- Bhatt et al. (2025). [*Ctrl-Z: Controlling AI Agents via Resampling*](https://arxiv.org/abs/2504.10374)
- Griffin et al. (2024). [*Games for AI Control*](https://arxiv.org/abs/2409.07985)

