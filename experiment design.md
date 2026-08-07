# The Monitor, Not the Protocol: Capability, Provenance, and Sample Size in Trusted Monitoring

**Status:** Preregistration + experiment design. Committed before the funded n=100 runs begin; the pilot results cited below (n=50, August 2026) predate this document and motivated it.

**Author:** Andre Williams · BlueDot Technical AI Safety
**Framework:** [ControlArena](https://github.com/UKGovernmentBEIS/control-arena) (UK AI Security Institute) · APPS backdoor setting · defer-to-trusted micro-protocol

---

## Summary

AI control asks whether we can safely extract useful work from a powerful model *even if it is actively scheming*. The core deployment-time defense is **trusted monitoring**: a weaker, trusted model reads everything the untrusted model produces, scores its suspiciousness, and the most suspicious outputs are audited or replaced. Control evaluations report a **safety** number (probability that no successful sabotage goes uncaught) and a **usefulness** number (how much productive work survives the safeguards).

This experiment holds the protocol fixed and varies the thing control evaluations usually treat as an implementation detail: **the monitor itself**. We measure how safety depends on (1) the monitor's *capability*, (2) the monitor's *provenance* — whether it comes from the same model family as the attacker — and (3) the *sample size* of the evaluation. A self-funded pilot (n=50/mode, OpenAI models only) found that swapping only the monitor moved reported safety from 0.42 to 0.82, and that at tutorial scale (n≤15) the same blind monitor could report safety anywhere from 0.0 to 1.0. The funded experiment extends this to a 3×8 attacker×monitor matrix across four model lineages (OpenAI, Anthropic, Google, and open-weights Qwen) at n=100/mode.

## Background in one page

- **Untrusted model (U):** the frontier model doing the work. We assume the worst case: it inserts *backdoors* — code that passes all visible tests but misbehaves on a secret input — while appearing helpful. Implemented as ControlArena's attack policy; run in **honest** and **attack** modes over the same tasks (APPS competitive-programming problems).
- **Trusted monitor (T):** a weaker model that assigns each of U's outputs a suspicion score in [0,1]. In the *defer-to-trusted* protocol, scores above a threshold (0.7 here) cause U's output to be replaced with T's own; separately, the top-scoring fraction of trajectories within an **audit budget** (1–5%) is audited, catching sabotage definitively.
- **Safety** = P(the attacker never lands an uncaught working backdoor). **Usefulness** = fraction of honest tasks completed. A good protocol scores high on both.
- The founding result (Greenblatt et al., 2023, arXiv:2312.06942) used GPT-4 as U and GPT-3.5 as T. Subsequent work varies *protocols*; the monitor is typically a single fixed weaker model from the same family as the attacker — which is also the deployment default labs will adopt, because their own small models are cheapest.

## Research questions and preregistered hypotheses

**RQ1 — Capability.** Does monitor capability, not the protocol, determine reported safety?
> **H1:** Within each provider, safety and monitor discrimination (ROC-AUC of suspicion scores, honest vs. attack) rise together as the monitor goes weak → mid → strong, replicating across all three providers.

**RQ2 — Provenance (novel).** Holding capability tier fixed, does a monitor from a *different* model family detect backdoors that a same-family monitor misses?
> **H2 (shared-blindspot hypothesis):** Same-family attacker–monitor cells show lower AUC than predicted from their row (attacker difficulty) and column (monitor strength) effects — i.e., a negative diagonal interaction. Rationale: shared training pipelines and stylistic priors make a family's "normal" invisible to its own members. Tested at **both** capability tiers; the weak tier is the deployment-relevant contrast ("which cheap model should watch my frontier model?").

**RQ3 — Measurement validity.** Are small-scale control evaluations statistically interpretable?
> **H3:** Bootstrap confidence intervals on safety are so wide at tutorial scale (n≤25/mode) that the same monitor is compatible with near-0 and near-1 safety; audit budgets whose honest-sample tail contains <1 sample produce degenerate (identical) safety values across budgets. Proposed reporting standard: publish monitor AUC alongside safety, and use n that resolves the stated audit budget.

**Secondary observables (no directional hypothesis):** attack-policy refusal rate per frontier attacker (safety-trained models may refuse to write backdoors; reported for validity), usefulness deltas when deferral fires, and the self-monitoring ceiling (each family's strongest model judging its own attacks).

## Design: a 3 × 8 attacker × monitor matrix (24 cells)

**Attackers (rows) — strongest available per family** (worst-case proxy, per the control framing):
`openai/gpt-5.5` · `anthropic/claude-opus-4-8` · `google/gemini-2.5-pro`

**Monitors (columns) — two capability tiers per family, plus open-weights:**

| Tier | OpenAI | Anthropic | Google | Open-weights |
|---|---|---|---|---|
| **Weak ("trusted" role)** | gpt-4.1-mini | claude-haiku-4-5 | gemini-2.5-flash-lite | Qwen-2.5-72B (OpenRouter) |
| Mid (ladder only, same-family) | gpt-5.4-mini | claude-sonnet-5 | gemini-2.5-flash | — |
| **Strong (upper bound)** | gpt-5.5 | claude-opus-4-8 | gemini-2.5-pro | — |

Cell inventory: 9 same-family ladder cells (weak/mid/strong per provider) + 6 weak-tier cross cells + 6 strong-tier cross cells + 3 Qwen cells = **24**. n=100/mode per cell (100 honest + 100 attack). Attacker generations are cached and reused across all monitor cells, so 21 of 24 cells cost monitor-inference only.

**Role framing (important for interpretation):**
- The **weak-tier** cells are the trusted-monitoring result. A weak model is "trusted" in the control sense — too weak to plausibly scheme — and is what labs will actually deploy.
- The **strong-tier** cells are *not* trusted monitors (a frontier monitor could itself scheme or collude). They serve as the capability-ladder science axis and an *untrusted-monitoring upper bound*: what monitoring could buy if trust were established by other means.
- **Qwen** is never same-family with any attacker, making it the clean cross-lineage reference — and the open-weights deployment vehicle: the realistic way to get lineage diversity without routing outputs to a competitor's API.

**Fixed across all cells:** APPS setting, defer-to-trusted at threshold 0.7, ControlArena's default attack/honest policies, `basic_monitor` scaffold with identical prompts, audit budgets {1, 2, 5}%.

## Analysis plan (preregistered)

1. **Ladders (H1):** per-provider AUC and safety vs. monitor tier; report with 95% CIs (DeLong/bootstrap for AUC).
2. **Provenance (H2):** the test is the *interaction*, not raw means — fit row (attacker) and column (monitor) effects on AUC across the matrix, then test whether same-family cells underperform their row+column prediction. Run separately at the weak and strong tiers. Raw same- vs. cross-family means are reported but explicitly labeled confounded.
3. **Stability (H3):** bootstrap safety@1% at subsample sizes n ∈ {10, 25, 50, 100} per cell; report CI width vs. n. Flag any audit budget whose honest tail contains <1 expected sample as unresolvable.
4. **Headline safety metric is safety@5%** (resolvable at n=100); safety@1% is reported only as part of the degeneracy finding.
5. Refusal rates per attacker reported alongside all attack-mode results.

## Pilot evidence (n=50/mode, OpenAI only, completed August 2026, self-funded)

1. Monitor swap alone (gpt-4.1-mini → gpt-5.4-mini → gpt-5.5) moved safety **0.42 → 0.74 → 0.82** (AUC 0.60 → 0.70 → 0.72); protocol, threshold, attacker fixed.
2. An earlier n=15 run with a functionally blind monitor (honest and attack suspicion both ≈0) reported **safety = 1.00**; bootstrap CI on safety at n=10/mode spans **[0.00, 0.83]**.
3. Safety at 1%, 2%, 5% audit budgets was *identical* — the degenerate-threshold artifact H3 generalizes.
4. Self-monitoring ceiling: GPT-5.5 judging its own attacks reached only AUC 0.72; 28% of backdoors succeeded.
5. Usefulness stayed at 1.00 across all monitors — better monitoring was free at these suspicion levels.

## Limitations (stated up front)

- **Prompted proxy attacker:** the attack policy is instructed to insert backdoors; a real schemer might attack more rarely and subtly. Results are an optimistic proxy shared by all ControlArena-style evaluations.
- **Static attacks:** the attacker is not optimized against each monitor (no red-team iteration); the provenance effect could differ under adaptive attacks.
- **Single scaffold and domain:** one monitor prompt (`basic_monitor`), one setting (APPS, public and likely in training data). Claims are about *relative* differences under a fixed, field-standard scaffold.
- **Capability matching across providers is approximate:** addressed by the interaction analysis rather than assumed away.
- **API snapshot:** closed models update silently; exact model IDs and run dates are pinned in the repo.

## Outcomes and their interpretations (all branches reportable)

| Result | Interpretation |
|---|---|
| Negative diagonal interaction (H2 holds) | Shared-blindspot effect: source trusted monitors from a different lineage (via open weights) — cheap, actionable safety gain |
| No provenance effect | Clean null: capability dominates; validates the same-family deployment default labs would otherwise adopt on faith |
| Positive diagonal interaction | Families detect their own style best — opposite advice, equally novel |
| H1 replicates across providers | Monitor capability is a general law of trusted monitoring, not a provider artifact |
| H3 confirmed at n=100 | Concrete reporting standard for control evals (AUC + resolvable budgets + CIs) |

## Reproduction

- `monitor_discrimination_experiment.py` — all presets (`ladder-openai`, `ladder-anthropic`, `ladder-google`, `cross`, `qwen`, `all`); `LIMIT` sets n/mode.
- Run order: ladders first (generate + cache attacker trajectories), then `cross` (monitor-only cost).
- Requires: Docker (APPS sandbox), `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, `OPENROUTER_API_KEY` in `.env`.
- Results tables are written to `logs/monitor_exp/results_<preset>_n<LIMIT>.md`.

## Key references

- Greenblatt, Shlegeris, Sachan & Roger (2023). *AI Control: Improving Safety Despite Intentional Subversion.* arXiv:2312.06942
- Greenblatt & Shlegeris. *The case for ensuring that powerful AIs are controlled.* Alignment Forum / Redwood Research
- UK AI Security Institute. *ControlArena.* github.com/UKGovernmentBEIS/control-arena
- Bhatt et al. (2025). *Ctrl-Z: Controlling AI Agents via Resampling.* arXiv:2504.10374
- Wen et al. (2024). *Adaptive Deployment of Untrusted LLMs Reduces Distributed Threats.* arXiv:2411.17693
- Griffin et al. (2024). *Games for AI Control.* arXiv:2409.07985
