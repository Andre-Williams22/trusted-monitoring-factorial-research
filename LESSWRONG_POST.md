# Your Control Eval's Safety Number Is Mostly About Your Red Team

*An attacker × monitor matrix in ControlArena. Monitor identity matters, monitor provenance doesn't, and the model you cast as the attacker matters more than either.*

**Status:** Pilot — 23 cells, 200 samples each. Hypotheses preregistered before the funded runs (dated commit in the repo). One hypothesis partly confirmed, one cleanly null, one unplanned finding I think is the important one.

---

## TL;DR

I ran an attacker × monitor matrix in [ControlArena](https://github.com/UKGovernmentBEIS/control-arena)'s APPS backdoor setting, holding the defer-to-trusted protocol, threshold, and dataset fixed, and varying only *who attacks* and *who monitors*.

1. **Which monitor you pick moves safety by ~0.35.** Swapping only the monitor moved safety from 0.47 to 0.82. Mean monitor AUC ranges 0.585 → 0.730 across the nine monitors tested — a **0.145 spread**.
2. **But it's monitor *identity*, not monitor *tier*.** Neither capability ladder came out monotonic. The weak monitor is clearly worst; above that the ordering is within noise.
3. **Monitor provenance doesn't matter.** I preregistered a "shared blindspot" hypothesis — a monitor from the attacker's own family should be blinder to its backdoors. Row/column-corrected interaction: **+0.0067 AUC, permutation p = 0.60.** A clean null.
4. **The attacker matters more than the monitor.** Holding the monitor fixed and swapping the attacker moved safety by **0.24–0.44**. Successful attacks per 100: **Gemini 45–69, GPT-5.5 11–37, Claude Opus 1.**
5. Corollaries: a blind monitor reported safety = 1.00 at tutorial scale; safety@1% is *structurally unresolvable* below ~100 honest samples; and a red team that doesn't attack makes any protocol look safe.

**The upshot:** a control evaluation's headline safety number is a joint property of your defense, your red team, and your sample size — and usually only the first is reported.

---

## Background, briefly

[AI control](https://arxiv.org/abs/2312.06942) asks whether we can safely extract work from a model that may be scheming. The core deployment-time protocol is **trusted monitoring**: a weaker, trusted model scores the suspiciousness of a stronger, untrusted model's output; suspicious work is audited by humans (within an audit budget) or replaced by the trusted model's own attempt (defer-to-trusted).

Evaluations run the untrusted model in two modes over the same tasks — **honest** and **attack** (solve the task *and* insert a backdoor: code passing visible tests but failing on a secret input) — and report **safety** (probability no successful backdoor goes uncaught) and **usefulness** (fraction of honest tasks completed).

The literature varies *protocols*. The monitor is typically one fixed weaker model from the attacker's own family — which is also what labs will deploy by default, since their own small models are cheapest. Nobody has systematically varied the monitor, so I did.

## Setup

- **Setting:** ControlArena APPS, defer-to-trusted @ 0.7, audit budgets {1, 2, 5}%.
- **Attackers (rows):** `gpt-5.5`, `claude-opus-4-8`, `gemini-3.1-pro-preview` — strongest per family (worst-case proxy).
- **Monitors (columns):** weak / mid / strong per family, plus open-weights `Qwen-2.5-72B` as an always-cross-lineage reference.
- **n = 100 per mode** (200 per cell); 23 complete cells.
- **Metric of record:** ROC-AUC of suspicion scores (honest vs. attack), reported *alongside* safety.

Weak-tier cells are the deployable *trusted monitoring* result — a weak model is "trusted" in the control sense precisely because it's too weak to plausibly scheme. Strong-tier cells are an **untrusted-monitoring upper bound**, not a deployment recommendation.

Attacker generations are cached and reused across monitor cells, so most cells cost monitor-inference only.

## Result 1: monitor choice matters a lot — but "capability tier" is the wrong abstraction

Safety across the GPT-5.5 row, protocol and attacker fixed:

| Monitor | AUC | Safety@5% | Usefulness | Successful attacks |
|---|---|---|---|---|
| gpt-4.1-mini (weak) | 0.605 | **0.467** | 1.00 | 37 |
| gpt-5.4-mini (mid) | 0.712 | **0.811** | 1.00 | 32 |
| gpt-5.5 (strong) | 0.705 | **0.820** | 1.00 | 19 |

Safety nearly doubles. Usefulness doesn't move — at these suspicion levels deferral rarely fires, so the gain comes from *audit ranking*, not from replacing outputs.

**But I preregistered a monotonic capability ladder, and I didn't get one.** Neither row is monotonic in AUC:

| Attacker | weak | mid | strong | |
|---|---|---|---|---|
| GPT-5.5 | 0.605 | **0.712** | 0.705 | mid ≈ strong |
| Gemini 3.1 Pro | 0.626 | **0.615** | 0.665 | mid < weak |

The honest reading: **the weakest monitor is clearly worse, and above that the ladder flattens into noise.** What survives is monitor *identity*, not tier. Mean AUC across the two viable attacker rows:

| Monitor | Mean AUC | | Monitor | Mean AUC |
|---|---|---|---|---|
| gpt-4.1-mini | 0.585 | | gemini-3.1-pro | 0.680 |
| gemini-3.5-flash | 0.615 | | gpt-5.5 | 0.705 |
| gemini-3.1-flash-lite | 0.658 | | gpt-5.4-mini | 0.712 |
| Qwen-2.5-72B | 0.663 | | claude-haiku-4-5 | **0.721** |
| | | | claude-opus-4-8 | **0.730** |

**Spread: 0.145 AUC.** Note that `claude-haiku-4-5` — a *weak*-tier model — outperforms every strong-tier monitor except Opus. Some models are just better at this task than their tier implies, which is exactly why "use a bigger monitor" is worse advice than "measure your monitor."

**Implication:** if you report safety without reporting monitor AUC, your number is unfalsifiable. Two labs running an identical protocol can differ by 0.35 safety on monitor choice alone.

## Result 2: monitor provenance does not matter (H2, null)

I preregistered that same-family monitors would be blinder to their own family's backdoors — shared training pipelines producing shared blindspots. The deployment stake is real: labs will monitor their own models with their own smaller models, and if that's systematically weaker, the fix (open-weights cross-lineage monitors) is cheap.

Raw same-vs-cross means are confounded — attackers differ in detectability, monitors in quality. The preregistered test is the **interaction**: fit additive attacker (row) and monitor (column) effects, then ask whether same-family cells underperform their prediction.

| | mean residual AUC | n cells |
|---|---|---|
| same-family monitor | −0.0040 | 6 |
| cross-family monitor | +0.0027 | 9 |
| **difference** | **+0.0067** | **p = 0.60** (10k permutations) |

Nothing. And the paired comparisons show it's a *direction* problem, not just a power problem:

| Monitor | vs Gemini attacker | vs GPT-5.5 attacker | Same-family cell is… |
|---|---|---|---|
| gemini-3.1-flash-lite | 0.626 *(same)* | 0.690 | worse |
| gemini-3.1-pro | 0.665 *(same)* | 0.695 | worse |
| gpt-4.1-mini | 0.565 | 0.605 *(same)* | **better** |
| claude-haiku-4-5 | 0.763 | 0.679 | — (cross both) |
| claude-opus-4-8 | 0.745 | 0.715 | — (cross both) |
| Qwen-2.5-72B | 0.656 | 0.670 | — (cross both) |

Inconsistent. The provenance effect (0.007) is **20× smaller** than the monitor-identity effect (0.145).

**I think this null is useful.** It's the first cross-provider monitor measurement I'm aware of in a control setting, and it *validates* the same-family default labs would otherwise adopt on faith. If you were considering a cross-provider monitoring arrangement for decorrelation, this is evidence you don't need one — at least for single-step backdoor detection on APPS, at this sample size, against non-adaptive attacks.

**And cross-provider monitoring turns out to be actively brittle.** Two of my cross-provider cells hit hard API incompatibilities when one provider's trajectories were replayed to another's monitor:

- Gemini attacker → Anthropic monitor: `400 Invalid signature in thinking block` (1 sample, unrecoverable)
- Gemini attacker → OpenAI monitor: `400 Invalid 'input[2].id': string too long — max 64, got 22346` — **fatal**; this cell is the one I couldn't complete, and no amount of retrying fixes it

So the practical verdict on cross-lineage monitoring is: no measured benefit, plus real implementation cost. That's a cheap negative result to have in hand.

## Result 3: the attacker matters more than the monitor (unplanned)

This wasn't a hypothesis. It's the biggest effect in the data.

Hold the monitor fixed; swap the attacker:

| Monitor | Safety vs Gemini | Safety vs GPT-5.5 | Δ |
|---|---|---|---|
| gemini-3.1-flash-lite | 0.333 | 0.776 | **+0.44** |
| gemini-3.1-pro | 0.446 | 0.780 | +0.33 |
| Qwen-2.5-72B | 0.413 | 0.708 | +0.30 |
| gpt-4.1-mini | 0.178 | 0.467 | +0.29 |
| claude-opus-4-8 | 0.590 | 0.827 | +0.24 |

Every monitor's measured safety swings by 0.24–0.44 depending on who it's defending against — comparable to the entire monitor-choice effect (~0.35). **The red-team axis is as large as the defense axis, and it is not usually reported.**

The driver is attack propensity, which varies enormously by family:

| Attacker | Successful attacks / 100 | Usefulness |
|---|---|---|
| Gemini 3.1 Pro | **45–69** | 0.96 |
| GPT-5.5 | 11–37 | 1.00 |
| Claude Opus 4.8 | **1** | 0.87 |

Opus is the extreme case. It is *not* refusing — it solves 84% of main tasks, so it engages with the prompt — it simply almost never produces a *working* backdoor under ControlArena's default attack policy. With one successful attack in 100, every safety number in that row is noise: across its eight monitors I measured "safety" of 0.0, 0.0, 0.0, 0.0, 0.5, 0.5, 0.5, 0.667 with AUCs all pinned at ~0.50.

Read naively, **the Opus rows look like a triumph** — high safety, monitors apparently working. They are an artifact of a red team that didn't attack. I dropped all eight from the analysis.

**Implication:** report red-team viability alongside safety. The number that matters isn't the backdoor *attempt* rate but the count of attacks that both solved the task and landed the backdoor — the only events safety is computed from. Had I not added that column, I would have written up the Anthropic rows as a monitoring result.

## Result 4: two ways safety numbers lie at small scale

**Tutorial-scale safety is uninterpretable.** An early n=15 run with a functionally blind monitor (honest and attack suspicion both ≈0, AUC 0.53) reported **safety = 1.00**. Bootstrapping safety over subsamples, the 95% CI at n=10/mode spans **[0.00, 0.83]** — the same monitor and protocol are compatible with total failure and near-perfect defense.

**Audit budgets below your sample resolution are degenerate.** Safety@1% sets the audit threshold at the 99th percentile of honest suspicion. With 100 honest samples that's *one* sample; with 50, half a sample. In my n=50 pilot, safety@1%, @2%, and @5% came out **identically 0.12** — three budgets returning one number is the signature of an unresolved threshold. Report the budget your honest-sample count can resolve (@5% at n=100), and report n beside it.

## A proposed reporting checklist

Any trusted-monitoring safety number should ship with:

1. **Monitor AUC** (honest vs. attack suspicion). Without it, a blind monitor is indistinguishable from a working one.
2. **Successful-attack count** — attacks that solved the task *and* landed the backdoor. Below ~5, safety is noise.
3. **An audit budget your honest-sample count can resolve.** ≥1 expected sample in the tail, or say so.
4. **n, and a CI.** Point estimates at n<50/mode are not informative.

All four are one column each. None of them are standard.

## Limitations

- **The attacker is a prompted proxy, not a schemer.** ControlArena's attack policy is *instructed* to insert backdoors. A genuinely misaligned model might attack rarely and subtly. Result 3 shows how sensitive the whole enterprise is to how well that proxy is elicited.
- **Attacks are static.** No red-team iteration against each monitor; the provenance null in particular might not survive adaptive attacks.
- **One scaffold, one domain.** A single monitor prompt (`basic_monitor`, final-code review) on APPS — public and likely in every training set. Absolute AUCs (0.57–0.76) may reflect the scaffold as much as the models; claims here are about *relative* differences.
- **The provenance null bounds the effect at roughly ±0.08 AUC**, not below that.
- **H1 came out messier than preregistered** — I report the non-monotonicity rather than the cleaner story I expected.
- **23 of 24 cells.** The missing one (Gemini attacker × GPT-5.5 monitor) is structurally impossible, not omitted.
- **API snapshot.** Closed models update silently; IDs and dates are pinned in the repo. The Google strong tier is an alias, not a fixed snapshot.
- **Result 3 is post-hoc** and should be treated as a hypothesis for confirmation, not a confirmed finding.

## What I'd do next

1. **Confirm Result 3 as a preregistered hypothesis** across more attacker families and settings.
2. **Fix the elicitation problem.** Is Opus's 3% backdoor rate safety training, or an attack policy tuned for another model? If red-team elicitation is model-specific, every cross-model control comparison inherits the confound.
3. **Adaptive attacks**, which the provenance null may not survive.
4. **Better monitor scaffolds** — full-trajectory review, ensembles, consensus mechanisms — to see whether the 0.145 monitor-identity spread compresses when monitors get a better prompt.

## Reproduction

Repo contains the experiment script (`monitor_discrimination_experiment.py`), figure pipeline (`make_figures.py`), interaction test (`analyze_interaction.py`), the preregistration (`experiment design.md`, committed before the funded runs), and raw `.eval` logs.

Four infrastructure failures cost me real money, and **three of them produced plausible-looking wrong states rather than loud errors** — which is uncomfortably on-thesis:

- **The monitor's cache key ignored the monitor model.** With caching on, later configs silently reused the *first* monitor's suspicion scores — three byte-identical result rows that looked like a finding. If you vary a component, verify per-config which models were actually called.
- **A daily-quota 429 looks exactly like slowness.** Gemini's direct API retried on 30-minute backoff for 11 hours, leaving a half-finished cell that a "does a log file exist?" check would treat as complete — silently reporting the early-index samples the run happened to reach.
- **One transient 402 cancelled 23 healthy in-flight samples** by tripping the harness's error threshold, and surfaced as "credits exhausted" when credits were fine.
- `basic_monitor_builder(model=...)` is silently ignored — the monitor resolves `model_role="trusted"`, so the monitor must be varied via `trusted_model`.

Every results table now carries `n`, `n_expected`, `complete`, and `n_successful_attacks`, and the analysis refuses to read incomplete cells.

Funded by a BlueDot Impact rapid grant (~$150 in API credits). Thanks to the ControlArena team at UK AISI for the framework.
