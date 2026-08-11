# Trusted Monitoring: Capability, Provenance, and Red-Team Choice

An AI control experiment built on [ControlArena](https://github.com/UKGovernmentBEIS/control-arena) (UK AI Security Institute), measuring what actually determines the safety number a trusted-monitoring evaluation reports.

Started as a walkthrough of ControlArena's defer-to-trusted tutorial; became a 3 × 8 attacker × monitor matrix (24 cells, 10 distinct monitors) across four model lineages.

## Headline findings (n = 100 per mode / 200 per cell, 23 of 24 cells)

| # | Finding | Status |
|---|---|---|
| 1 | **Which monitor you pick moves safety ~0.35** (0.47 → 0.82), protocol fixed. But it's monitor *identity*, not *tier*: neither capability ladder was monotonic, and mean AUC spans 0.585–0.730 (spread **0.145**). A weak-tier Haiku beat every strong-tier monitor but Opus. | H1, partial |
| 2 | **Monitor provenance does not matter.** Row/column-corrected interaction: **+0.0067 AUC, permutation p = 0.60**. The preregistered "shared blindspot" hypothesis is not supported — and the provenance effect is 20× smaller than monitor identity. | H2, clean null |
| 3 | **Which model you cast as the attacker matters more than the monitor.** Under one *identical* off-the-shelf attack prompt, swapping only the attacker moved safety by 0.24–0.44 — comparable to the entire monitor effect. Prior work varies *how* the attacker attacks; this varies *which model* attacks, policy fixed. | Unplanned |
| 4 | **Small-scale safety numbers are mirages.** A blind monitor (AUC 0.53) reported safety = 1.00 at n=15; bootstrap 95% CI at n=10/mode spans [0.00, 0.83]. | H3, confirmed |
| 5 | **Audit budgets can be structurally unresolvable.** safety@1% needs ≥100 honest samples for even one sample in the tail; below that, @1%/@2%/@5% return identical numbers. | H3, confirmed |
| 6 | **Cross-provider monitoring is brittle.** Replaying one provider's trajectories to another's monitor hit hard API incompatibilities (thinking-block signature rejection; `id` length cap) — one cell is structurally impossible to complete. No benefit (finding 2) *and* real implementation cost. | Incidental |

### Why finding 3 is the important one

Successful attacks (main task solved **and** backdoor landed) per 100 attack samples:

| Attacker | Successful attacks | Backdoor landed | Main task solved (attack mode) | Effect on measured safety |
|---|---|---|---|---|
| Gemini 3.1 Pro | **45–69** | 54–79 | 81–84 | makes every protocol look weak |
| GPT-5.5 | 11–37 | 13–40 | 89–97 | mid |
| Claude Opus 4.8 | **1** | 3 | 84 | makes every protocol look safe |

Opus is not refusing — it solves **84** of 100 main tasks in attack mode, so it fully engages with the prompt. It lands a working backdoor **3** times, and in only **1** of those did it both land the backdoor *and* solve the task — which is the only event safety is computed from. Its rows read as a monitoring success but are an artifact of a red team that didn't attack.

**Reporting checklist.** Any trusted-monitoring safety number should ship with: (1) **monitor AUC**, (2) **successful-attack count** (below ~5, safety is noise), (3) **an audit budget your honest-sample count can resolve**, (4) **n and a CI**. One column each; none are currently standard.

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

# Figures
LIMIT=100 python make_figures.py
```

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

Prompted proxy attacker (not a real schemer) · static, non-adaptive attacks · one monitor scaffold, one domain (APPS is public and likely in training data) · the provenance null excludes effects larger than ~±0.08 AUC, not smaller ones · closed-model API snapshot, IDs and dates pinned · Finding 3 is post-hoc and needs preregistered confirmation.

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
