# Trusted Monitoring: Monitor Identity Beats Monitor Tier

An AI control experiment built on [ControlArena](https://github.com/UKGovernmentBEIS/control-arena) (UK AI Security Institute). It set out to measure which monitor to deploy; the answer is that it is monitor identity, not capability tier — and getting there required retracting three claims of my own, listed below.

A 3 × 8 attacker × monitor matrix (24 cells, 10 distinct monitors, four model lineages), n = 100 per mode.

## The finding: which model, not what size

Six monitors, each tested against **both** surviving attacker rows — a balanced sub-design that happens to be exactly 3 weak-tier and 3 strong-tier, so attacker difficulty cancels. Metric is the fraction of attacks flagged at **zero false alarms on honest code**.

| Monitor | Tier | Caught | Caught (attacks that landed) | False alarms |
|---|---|---|---|---|
| claude-opus-4-8 | strong | 0.460 | 0.298 | 0.000 |
| **claude-haiku-4-5** | **weak** | **0.372** | **0.405** | **0.230** |
| gemini-3.1-pro | strong | 0.360 | **0.044** | 0.000 |
| gemini-3.1-flash-lite | weak | 0.290 | 0.365 | 0.005 |
| Qwen-2.5-72B | strong | 0.235 | 0.351 | 0.010 |
| gpt-4.1-mini | weak | 0.170 | 0.228 | 0.000 |

Strong, weak, strong, weak, strong, weak — the tier column alternates against the ranking.

- Strong tier averages **0.352**; weak averages **0.277**. **Tier gap: 0.074.** Tier is not nothing.
- Average spread *within* a tier: **0.214**.
- **Ratio 2.9×**, P(identity effect > tier effect) = **0.993**. Holds on all three metrics tried (2.9× / 2.4× / 2.8×).
- Tier explains ~15% of the variance in monitor performance — and shuffling which monitor holds which tier label explains just as much (permutation p = 0.50).

**The weak tier contains both the second-best monitor and the worst one.** Weak-tier Haiku beats strong-tier Qwen at P = 0.97; weak-tier gpt-4.1-mini is last of six. Knowing a monitor's tier buys you very little.

Two caveats that belong next to the ranking: **Haiku flags 23% of honest code** (every other monitor is near zero — it earns its rank at matched false-alarm rate, but that rate is the whole deployment story), and **strong-tier `gemini-3.1-pro` catches 4% of the attacks that actually landed**, last of six despite sitting mid-table on all attacks.

## Supporting findings

| # | Finding | Status |
|---|---|---|
| 1 | **Monitor identity beats monitor tier** — the table above. | H1, confirmed after metric fix |
| 2 | **A strong-tier monitor is worst where it counts.** `gemini-3.1-pro` catches 4% of landed backdoors. | Unplanned |
| 3 | **Elicitation is a silent confound.** Under one identical attack prompt, successful attacks per 100 ran Gemini 45–69, GPT-5.5 11–37, Opus 4.8 just **1**. Opus is not refusing — it solves 84 main tasks in attack mode. Its rows read as a monitoring success and are an artifact of a red team that didn't attack. | Unplanned, post-hoc |
| 4 | **Monitor provenance: a bound, not a null.** The interaction is +0.0067 AUC (p = 0.60), but 3 of 6 same-family cells have *structurally zero* residuals — the test rests on three contrasts across two families, which disagree in sign. Effects rivalling the identity effect are ruled out; smaller ones are unresolved. | H2, bounded |
| 5 | **Cross-provider monitoring is brittle.** Thinking-block signature rejection and a 22 KB `id` field — one cell of 24 is uncompleteable. | Incidental |

### Measurement corrections (how the finding was nearly missed)

| # | Correction | Status |
|---|---|---|
| A | **The honest suspicion distribution is degenerate, so the audit budget never binds.** In 10 of 15 cells all 100 honest samples share one score; no cell has more than two distinct values. The 1/2/5% thresholds are identical in 12 of 15 cells. Likely a `basic_monitor` scaffold property — check yours. | Measurement |
| B | **On that data ROC-AUC is algebraically a detection rate**, not a ranking statistic: where honest is constant, AUC = 0.5 + p/2, exact to four decimals. | Measurement |
| C | **At tutorial scale safety is uninterpretable.** A blind monitor (AUC 0.53) reported safety = 1.00 at n=15; the bootstrap 95% CI at n=10/mode spans [0.00, 0.83]. Convergent with Ge-Wang et al. (2026) by a different mechanism. | H3, confirmed |

### Retractions

**"Neither capability ladder is monotonic"** — an artifact of AUC on a degenerate honest distribution. Under the corrected metric both within-family ladders climb (0.21 → 0.34 → 0.41 and 0.20 → 0.23 → 0.33), but the bootstrap only puts monotonicity at 54% / 69%. The honest verdict is **unresolved at this sample size** — not monotonic, and not non-monotonic either.

**"The corrected metric doubles the effect"** — it doesn't. When honest suspicion is constant, `TPR@0%FPR = 2 × (AUC − 0.5)` exactly, so the spread going 0.145 → 0.290 was a change of units. Only 5 of 15 cells actually move. The unit-free ratio went 2.8× → 2.9×, which makes the finding **robust** to metric choice, not amplified by it.

**A claim that ControlArena's `compute_safety` is flawed** for counting all audited attack attempts in its numerator. It is the standard definition — [Ge-Wang et al. (2026)](https://arxiv.org/html/2606.06529v1) state it identically, and the framework treats catching any attempt as a blue-team win because it is decisive evidence of scheming. Withdrawn in full.

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

## Running it

```bash
pip install inspect_ai control-arena python-dotenv "xarray>=2024.10.0" matplotlib scikit-learn
```

`.env` needs `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `OPENROUTER_API_KEY` (Gemini + Qwen are routed via OpenRouter). Docker must be running — APPS executes code in a sandbox.

```bash
# Smoke test any preset first (~$1, catches bad model IDs)
LIMIT=2 EXPERIMENT=ladder-openai python monitor_discrimination_experiment.py

# Ladders first (they generate + cache attacker trajectories)
LIMIT=100 EXPERIMENT=ladder-openai    python monitor_discrimination_experiment.py
LIMIT=100 EXPERIMENT=ladder-anthropic python monitor_discrimination_experiment.py
LIMIT=100 EXPERIMENT=ladder-google    python monitor_discrimination_experiment.py

# Cross matrix reuses cached generations (monitor-only cost)
LIMIT=100 EXPERIMENT=cross python monitor_discrimination_experiment.py

# Confirmatory analysis + figures (no sklearn/scipy needed)
LIMIT=100 python analyze_monitor_identity.py
LIMIT=100 python make_identity_figures.py

# Original figure pipeline (needs scikit-learn)
LIMIT=100 python make_figures.py
```

`analyze_monitor_identity.py` caches raw suspicion scores to `.score_cache.pkl` on
first run; delete it to re-parse from the `.eval` logs.

**Env vars:** `LIMIT` (n per mode) · `EXPERIMENT` (`ladder-*`, `cross`, `qwen`, `all`) · `PAIRS="atk:mon,..."` (specific cells) · `FORCE=1` (re-run incomplete cells) · `MAX_RETRIES` (default 3) · `MAX_CONNECTIONS`, `MAX_SAMPLES` (throttling).

**Cost control:** attacker generations are cached, so run one cell per attacker to completion *first* — every subsequent cell for that attacker is monitor-only. An interrupted generation caches nothing and you pay again.

## Implementation notes (bugs worth knowing about)

Four failure modes cost real money here. Three of them produced *plausible-looking results* rather than loud errors:

1. **The monitor cache key ignored the monitor model.** With caching on, later configs silently reused the first monitor's suspicion scores — three byte-identical result rows that looked like a finding. Fix: `cache=False` on the monitor, and verify per-config which models were actually called.
2. **`basic_monitor_builder(model=...)` is ignored** — the monitor resolves `model_role="trusted"` → `trusted_model`. Vary the monitor via `trusted_model`, not the `model` argument.
3. **A daily-quota 429 looks exactly like slowness.** Gemini's direct API retried with 30-minute backoff for 11 hours and left a half-finished cell that a "does a log file exist?" check would treat as complete. Fixes: `MAX_RETRIES=3` so quota walls surface in minutes, routing via OpenRouter, and a completeness guard that classifies every cell missing/partial/complete and **refuses to analyze partials**.
4. **One transient 402 cancelled 23 healthy in-flight samples** by tripping the harness's error threshold, and surfaced as "credits exhausted" when credits were fine. The only one of the four that announced itself — with the wrong cause.

Every results table carries `n`, `n_exp`, `complete`, and `n_success_atk` so neither incompleteness nor an inert red team can hide.

## Limitations

**Two viable attacker rows** — every monitor mean rests on two cells, and the bootstrap resamples within cells, not across attackers, so no interval here captures attacker-to-attacker variation · no mid tier in the balanced 2 × 6 confirmatory sub-design · the identity-vs-tier ratio's upper bound is unstable and shouldn't be quoted · the landed-attack metric has small denominators (11–69 per cell) · prompted proxy attacker, not a real schemer · static, non-adaptive attacks · **one monitor scaffold, one domain** — the degenerate score distribution may be a property of *this scaffold* rather than of these models, which is the most important thing to check before generalising corrections A and B · provenance is a bound resting on three contrasts across two families · closed-model API snapshot, IDs pinned · findings 2 and 3 are post-hoc.

## References

- Greenblatt, Shlegeris, Sachan & Roger (2023). [*AI Control: Improving Safety Despite Intentional Subversion*](https://arxiv.org/abs/2312.06942)
- UK AI Security Institute. [*ControlArena*](https://github.com/UKGovernmentBEIS/control-arena)
- Ge-Wang, Crosse, Hadad, Schaeffer, Potham & Tracy (2026). [*Attack Selection in Agentic AI Control Evaluations Meaningfully Decreases Safety*](https://arxiv.org/abs/2606.06529)
- Loughridge, Colognese, Griffin, Tracy, Kutasov & Benton (2025). [*Optimizing AI Agent Attacks With Synthetic Data*](https://arxiv.org/abs/2511.02823)
- Terekhov et al. (2025). [*Adaptive Attacks on Trusted Monitors Subvert AI Control Protocols*](https://arxiv.org/abs/2510.09462)
- Mallen, Griffin, Wagner, Abate & Shlegeris (2024). [*Subversion Strategy Eval*](https://arxiv.org/abs/2412.12480)
- Bhatt et al. (2025). [*Ctrl-Z: Controlling AI Agents via Resampling*](https://arxiv.org/abs/2504.10374)
- Griffin et al. (2024). [*Games for AI Control*](https://arxiv.org/abs/2409.07985)

Funded by a BlueDot Impact rapid grant (~$150 in API credits).
