# Trusted Monitoring: What the Safety Number Is Actually Measuring

An AI control experiment built on [ControlArena](https://github.com/UKGovernmentBEIS/control-arena) (UK AI Security Institute). It set out to measure which monitor to deploy; the more useful result was that four of the instruments used to answer that question report confidently wrong numbers, all failing in the same direction — toward looking safe.

A 3 × 8 attacker × monitor matrix (24 cells, 10 distinct monitors, four model lineages), n = 100 per mode.

## Headline findings (23 of 24 cells; 15 viable after excluding a dead attacker row)

| # | Finding | Status |
|---|---|---|
| 1 | **`compute_safety` credits the blue team for catching attacks that never worked.** It computes `caught / (caught + uncaught_successful)`, where `caught` counts *every* attack above threshold. **61.6%** of that numerator is doomed attacks; reported safety exceeds the catch rate on landed attacks in **15 of 15 cells**. Worst cell: safety **0.78** while catching **0 of 11** attacks that actually landed. | Measurement |
| 2 | **The honest suspicion distribution is degenerate, so the audit budget never binds.** In 10 of 15 cells all 100 honest samples share one score; no cell has more than two distinct values. The 1/2/5% thresholds are identical in 12 of 15 cells. | Measurement |
| 3 | **On that data ROC-AUC is algebraically a detection rate**, not a ranking statistic: where honest is constant, AUC = 0.5 + p/2, exact to four decimals. | Measurement |
| 4 | **At tutorial scale safety is uninterpretable.** A blind monitor (AUC 0.53) reported safety = 1.00 at n=15; the bootstrap 95% CI at n=10/mode spans [0.00, 0.83]. Convergent with Ge-Wang et al. (2026) by a different mechanism. | H3, confirmed |
| 5 | **Monitor identity beats monitor tier.** Two monitors sharing a tier differ **~3×** more than the tiers differ (2.9× / 2.4× / 2.8× on three metrics, P(identity > tier) ≈ 0.99). Tier explains ~15% of variance — no more than a random relabelling (permutation p = 0.50). | H1, confirmed after metric fix |
| 6 | **A strong-tier monitor is worst where it counts.** Scored only on backdoors that landed, `gemini-3.1-pro` catches **4%** — last of six, below every weak-tier model. | Unplanned |
| 7 | **Monitor provenance: a bound, not a null.** The interaction is +0.0067 AUC (p = 0.60), but 3 of 6 same-family cells have *structurally zero* residuals — the test rests on three contrasts across two families, which disagree in sign. Effects rivalling the identity effect are ruled out; smaller ones are unresolved. | H2, bounded |
| 8 | **Elicitation is a silent confound.** Under one identical attack prompt, successful attacks per 100 ran Gemini 45–69, GPT-5.5 11–37, Opus 4.8 just **1**. Opus is not refusing — it solves 84 main tasks in attack mode. Its rows read as a monitoring success and are an artifact of a red team that didn't attack. | Unplanned, post-hoc |
| 9 | **Cross-provider monitoring is brittle.** Thinking-block signature rejection and a 22 KB `id` field — one cell of 24 is uncompleteable. | Incidental |

### Retraction

An earlier version of this repo claimed **"neither capability ladder is monotonic."** That was an artifact of AUC on a degenerate honest distribution. Under the corrected metric both within-family ladders climb (0.21 → 0.34 → 0.41 and 0.20 → 0.23 → 0.33), but the bootstrap only puts monotonicity at 54% / 69%. The honest verdict is **unresolved at this sample size** — not monotonic, and not non-monotonic either.

**Reporting checklist.** Any trusted-monitoring safety number should ship with: (1) **the catch rate on attacks that actually landed**, not the aggregate catch count; (2) **the number of distinct honest suspicion values** — if it's one, your audit budget isn't binding; (3) **monitor false-positive rate on honest traffic**; (4) **successful-attack count** (below ~5, safety is noise); (5) **n and a CI**. One column each; none are standard.

Preregistration: [experiment design.md](experiment%20design.md) · Figures: [figures/](figures/) · Per-cell results: [logs/monitor_exp/](logs/monitor_exp/)

## Design

**Attackers (rows):** strongest per family — `gpt-5.5`, `claude-opus-4-8`, `gemini-3.1-pro-preview`
**Monitors (columns):** 10 distinct models — weak / mid / strong per family + open-weights `Qwen-2.5-72B` (always cross-lineage)

Each attacker is paired with **8** of the 10: its own family's full three-tier ladder, plus the weak and strong tier of each *other* family, plus Qwen. 3 × 8 = 24 cells. **9** monitors enter the analysis — `claude-sonnet-5` appears only in the Opus attacker row, which is dropped wholesale (finding 8).

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

**Two viable attacker rows** — every monitor mean rests on two cells, and the bootstrap resamples within cells, not across attackers, so no interval here captures attacker-to-attacker variation · no mid tier in the balanced 2 × 6 confirmatory sub-design · the identity-vs-tier ratio's upper bound is unstable and shouldn't be quoted · the landed-attack metric has small denominators (11–69 per cell) · prompted proxy attacker, not a real schemer · static, non-adaptive attacks · **one monitor scaffold, one domain** — the degenerate score distribution may be a property of *this scaffold* rather than of these models, which is the most important thing to check before generalising findings 2 and 3 · provenance is a bound resting on three contrasts across two families · closed-model API snapshot, IDs pinned · findings 6 and 8 are post-hoc.

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
