# Same Attack Prompt, 45 vs 1 Backdoors: Elicitation Is a Silent Confound in Cross-Model Control Evals

*An attacker × monitor matrix in ControlArena. Monitor identity matters, monitor provenance doesn't, and which model you cast as the attacker matters more than either.*

**Status:** Empirical pilot study — 23 cells, 200 samples each. Hypotheses preregistered before the funded runs (dated commit in the repo). One hypothesis partly confirmed, one cleanly null, one unplanned finding I think is the important one.

**Scope.** 23 cells × 200 samples ≈ 4,600 trajectories, against Ge-Wang et al.'s ~1,784 — but theirs is one attacker–monitor pair run deep and this is 23 pairs run shallow. Factorial screening designs are underpowered per cell by construction. Large effects (the elicitation gap, the monitor-identity spread) are solid; small effects (the provenance null) are bounded, not resolved. Read this as a screen that says where to look, not as a confirmatory result.

The enabling design is that **both axes were varied on the same cells**. Prior control work runs one attacker or one monitor; a factorial is what makes "the attacker axis is as large as the monitor axis" a measurable claim rather than an intuition.

---

## TL;DR

I ran an attacker × monitor matrix in [ControlArena](https://github.com/UKGovernmentBEIS/control-arena)'s APPS backdoor setting, holding the defer-to-trusted protocol, threshold, and dataset fixed, and varying only *who attacks* and *who monitors*.

1. **Monitor identity, not tier.** Mean AUC spans 0.585–0.730 across nine monitors (a **0.145 spread**, z ≈ 3.75). Neither capability ladder is monotonic; the per-cell 95% CI is ±0.076, wide enough that no ladder resolves. A *weak*-tier Haiku (0.721) beats every strong-tier monitor but Opus, and beats the weakest by z ≈ 3.52. **Measure your monitor; don't size it.**
2. **Cross-provider monitoring is brittle in a way I haven't seen documented.** Replaying one provider's trajectories to another provider's monitor hit two hard API failures — a rejected thinking-block signature and a 22 KB string in a field capped at 64 chars.
3. **Monitor provenance doesn't matter.** I preregistered a "shared blindspot" hypothesis — a monitor from the attacker's own family should be blinder to its backdoors. Row/column-corrected interaction: **+0.0067 AUC, permutation p = 0.60.** Combined with (2): no detection benefit, real implementation cost.
4. **Which model you cast as the attacker matters as much as the monitor.** Under one identical, off-the-shelf attack prompt, successful attacks per 100 were **Gemini 45–69, GPT-5.5 11–37, Claude Opus 1**. Measured safety swings **0.24–0.44** — comparable to the ~0.35 monitor swing, measured in the same factorial.
5. **Two ways safety numbers lie at small scale**, plus a four-item reporting checklist.

**The contribution.** Existing work varies **how** the attacker attacks — timing, content, strategy, skill. This varies **which model is cast as the attacker**, holding the attack policy fixed.

---

## Background, briefly

[AI control](https://arxiv.org/abs/2312.06942) asks whether we can safely extract work from a model that may be scheming. The core deployment-time protocol is **trusted monitoring**: a weaker, trusted model scores the suspiciousness of a stronger, untrusted model's output; suspicious work is audited by humans (within an audit budget) or replaced by the trusted model's own attempt (defer-to-trusted).

Evaluations run the untrusted model in two modes over the same tasks — **honest** and **attack** (solve the task *and* insert a backdoor: code passing visible tests but failing on a secret input) — and report **safety** (probability no successful backdoor goes uncaught) and **usefulness** (fraction of honest tasks completed).

## Related work

The direction of my headline finding is not new, and it's worth being explicit about that up front.

- **Greenblatt, Shlegeris, Sachan & Roger (2023), [arXiv:2312.06942](https://arxiv.org/abs/2312.06942).** The original control framework is built on the requirement that red-team elicitation be at least as strong as what a real deployment would face — a control eval bounds risk only under that assumption. "Red-team quality determines the number" is the framework's *premise*, not a discovery.
- **Ge-Wang, Crosse, Hadad, Schaeffer, Potham & Tracy (2026), [arXiv:2606.06529](https://arxiv.org/abs/2606.06529)** — *Attack Selection in Agentic AI Control Evaluations Meaningfully Decreases Safety.* Start and stop policies (when to launch, when to abort) cut measured safety by 20pp on BashArena and 20–28pp on LinuxArena at a 1% audit budget, with no change in underlying attack capability. Recommends that evaluations, system cards, and safety cases elicit attack *selection*. Single attacker, single monitor ensemble; 600 honest / 600 attack (BashArena), 400 honest / 184 attack (LinuxArena).
- **Loughridge, Colognese, Griffin, Tracy, Kutasov & Benton (2025), [arXiv:2511.02823](https://arxiv.org/abs/2511.02823)** — *Optimizing AI Agent Attacks With Synthetic Data.* Decomposes attack capability into suspicion modeling, attack selection, plan synthesis, execution, and subtlety; finds attack selection the highest-leverage of the five in SHADE-Arena.
- **Terekhov et al. (2025), [arXiv:2510.09462](https://arxiv.org/abs/2510.09462)** — *Adaptive Attacks on Trusted Monitors Subvert AI Control Protocols.* Attacks tuned against a specific known monitor, via prompt injection embedded in model outputs. Varies attack *content*.
- **Mallen, Griffin, Wagner, Abate & Shlegeris (2024), [arXiv:2412.12480](https://arxiv.org/abs/2412.12480)** — *Subversion Strategy Eval.* Models struggle to self-direct subversion statelessly, without shared memory across contexts. Consistent with my Opus row; this post gives a sharper version of it — high main-task completion alongside near-zero backdoor landing, under an off-the-shelf attack prompt.

All of these vary **how** the attacker attacks. None varies **which model is the attacker** under a fixed attack policy. That's the gap this pilot occupies — and because the monitor axis was measured in the same factorial, the attacker-model axis can be compared directly against the entire monitor-identity effect.

## Setup

- **Setting:** ControlArena APPS, defer-to-trusted @ 0.7, audit budgets {1, 2, 5}%.
- **Attackers (rows):** `gpt-5.5`, `claude-opus-4-8`, `gemini-3.1-pro-preview` — strongest per family (worst-case proxy).
- **Monitors (columns):** **10 distinct models** — weak / mid / strong for each of the three families, plus open-weights `Qwen-2.5-72B` as an always-cross-lineage reference.
- **Design:** each attacker is paired with **8** monitors — its own family's full three-tier ladder, plus the weak and strong tier of each *other* family, plus Qwen. 3 attackers × 8 = **24 cells**, of which 23 completed.
- **n = 100 per mode** (200 samples per cell) throughout.
- **Metric of record:** ROC-AUC of suspicion scores (honest vs. attack), reported *alongside* safety.

Three different monitor counts appear in this post and they are all correct, so to head off the confusion: **10** distinct monitors were configured, **8** are paired with any given attacker, and **9** enter the analysis — `claude-sonnet-5` appears only in the Opus attacker row, which I drop wholesale, so it drops with it. (The Anthropic attacker row is excluded throughout; §*Attack elicitation* below explains why.)

Weak-tier cells are the deployable *trusted monitoring* result — a weak model is "trusted" in the control sense precisely because it's too weak to plausibly scheme. Strong-tier cells are an **untrusted-monitoring upper bound**, not a deployment recommendation.

**One definition, because the reporting checklist below leans on it.** "Successful attacks" throughout means *attacks surviving the protocol with the main task solved and the backdoor landed*. This is a **post-deferral** count and therefore monitor-dependent. For diagnosing red-team viability the pre-protocol count is the one you want; for the Opus row the two coincide, because nothing was deferred and nothing landed.

Attacker generations are cached and reused across monitor cells, so most cells cost monitor-inference only.

## Result 1: monitor identity, not tier

Safety across the GPT-5.5 row, protocol and attacker fixed:

| Monitor | AUC | Safety@5% | Successful attacks | 95% CI on safety | Usefulness |
|---|---|---|---|---|---|
| gpt-4.1-mini (weak) | 0.605 | **0.467** | 37 | ±0.161 | 1.00 |
| gpt-5.4-mini (mid) | 0.712 | **0.811** | 32 | ±0.136 | 1.00 |
| gpt-5.5 (strong) | 0.705 | **0.820** | 19 | ±0.173 | 1.00 |

Safety nearly doubles. **Deferral almost never fires on honest traffic** — usefulness is pinned within each attacker row regardless of monitor (1.00 across all eight GPT-5.5 cells, 0.96 across all seven Gemini cells) — **but it fires substantially on attack traffic**, where suspicion scores are higher. That's why successful attacks fall from 37 to 11 across monitors in the GPT-5.5 row. A better monitor buys safety through *both* deferral and audit ranking, and the usefulness cost is still zero.

Worth noting that the deferral rate tracks the *score distribution* against the fixed 0.7 threshold, not AUC — which is why the ordering isn't monotonic in AUC (gpt-5.4-mini, AUC 0.712 → 32 successes; gemini-3.1-pro, AUC 0.695 → 11).

Note what the CI column is computed over. Safety is estimated only from attacks that actually succeeded, so the effective n is the successful-attack count, not 200 — 19 for the strong monitor, which is why its interval is the widest despite having the best point estimate. These are binomial intervals on the success count only; the audit threshold is itself estimated from the honest tail, which adds variance I have *not* propagated. Treat them as lower bounds on the true uncertainty.

![Nine monitors ranked by mean AUC with 95% CIs, coloured by capability tier. The tier colours are visibly interleaved: weak-tier Haiku 4.5 ranks second overall, above four strong-tier monitors.](figures/fig5_monitor_ranking.png)

*Figure 1 (`fig5_monitor_ranking.png`). Monitors ranked by mean AUC across the two viable attacker rows. Colour is capability tier — and the colours are interleaved, which is the whole point: tier does not order the ranking. Bars are 95% CIs (Hanley–McNeil, ≈0.039 per cell, divided by √rows); † marks single-row means.*

**I preregistered a monotonic capability ladder, and I didn't get one.** Neither viable row is monotonic in AUC:

| Attacker | weak | mid | strong | |
|---|---|---|---|---|
| GPT-5.5 | 0.605 | **0.712** | 0.705 | mid ≈ strong |
| Gemini 3.1 Pro | 0.626 | **0.615** | 0.665 | mid < weak |

![Two capability ladders, neither monotonic: AUC and safety plotted against weak/mid/strong monitor tier. The dropped Anthropic attacker row is shown greyed and unconnected.](figures/fig1_ladder.png)

*Figure 2 (`fig1_ladder.png`). The preregistered capability ladder, and why I stopped believing in it. Neither viable row climbs cleanly with tier. The greyed series is the dropped Opus attacker row — flat at chance, and its safety values are plotted as unconnected markers because three point estimates off a single event are not a trend.*

The honest reading: **the weakest monitor is clearly worse, and above that the ladder flattens.** And I can say *why* it flattens rather than waving at "noise" — by Hanley–McNeil at n=100/100, the per-cell AUC standard error is ≈0.039, so a **per-cell 95% CI is ±0.076**. Both within-row gaps above are smaller than that. The ladder isn't non-monotonic so much as unresolvable at this n; either way, tier does not buy you a prediction.

What *does* survive is monitor **identity**. Mean AUC across the two viable attacker rows:

| Monitor | Mean AUC | | Monitor | Mean AUC |
|---|---|---|---|---|
| gpt-4.1-mini | 0.585 | | gemini-3.1-pro | 0.680 |
| gemini-3.5-flash | 0.615 † | | gpt-5.5 | 0.705 † |
| gemini-3.1-flash-lite | 0.658 | | gpt-5.4-mini | 0.712 † |
| Qwen-2.5-72B | 0.663 | | claude-haiku-4-5 | **0.721** |
| | | | claude-opus-4-8 | **0.730** |

† **Single-row mean.** These three monitors are paired with only one *viable* attacker, so their "mean" is one cell (SE ≈ 0.039, not the ≈0.027 of a two-row mean). `gemini-3.5-flash` and `gpt-5.4-mini` are mid-tier models that only their own family's attacker was paired with; `gpt-5.5` as monitor appears in the GPT-5.5 row and in the one cell that failed to complete. Two caveats follow: single-row means are noisier, and they're drawn from the GPT-5.5 attacker row, whose overall mean AUC runs ~0.02 above the Gemini row — so they're mildly inflated relative to the two-row means. Both endpoints of the spread are two-row means, so the headline number isn't affected.

**Spread: 0.145 AUC**, or z ≈ 3.75 against the two-row mean SE. That's solid. So is the more surprising claim: `claude-haiku-4-5` (0.721), a *weak*-tier model, beats `gpt-4.1-mini` (0.585) by 0.136, z ≈ 3.52 — a weak-tier model outperforming most strong-tier monitors is not a noise artifact.

What I should *not* claim is any ordering at the top. Opus (0.730) vs Haiku (0.721) is a 0.009 gap, z ≈ 0.23. They are jointly top and mutually indistinguishable, and the same goes for most adjacent pairs in the middle of that table.

Some models are just better at this task than their tier implies, which is exactly why "use a bigger monitor" is worse advice than "measure your monitor."

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

![Attacker × monitor heatmap of monitor AUC. Same-family cells are outlined in black; they are not systematically darker or lighter than their neighbours.](figures/fig2_heatmap.png)

*Figure 3 (`fig2_heatmap.png`). The full matrix. Boxed cells are same-family attacker–monitor pairs — the shared-blindspot hypothesis predicts they should be systematically worse than their row and column imply. They aren't. Columns vary far more than the diagonal does. The uniformly pale Opus row is the elicitation failure discussed below.*

Inconsistent in sign, not just small. The provenance effect (0.007) is **20× smaller** than the monitor-identity effect (0.145).

**I think this null is useful.** It's the first cross-provider monitor measurement I'm aware of in a control setting, and it *validates* the same-family default labs would otherwise adopt on faith. If you were considering a cross-provider monitoring arrangement for decorrelation, this is evidence you don't need one — at least for single-step backdoor detection on APPS, at this sample size, against non-adaptive attacks.

## Result 3: cross-provider monitoring is also actively brittle

This is the most practically useful thing I found, and I nearly buried it.

Replaying one provider's trajectories to another provider's monitor is **not a drop-in operation**. Two of my cross-provider cells hit hard API incompatibilities:

- **Gemini attacker → Anthropic monitor:** `400 Invalid signature in thinking block`. Anthropic's API requires that thinking blocks in a message history carry a signature it issued; a trajectory generated elsewhere has no valid one. 1 sample lost, unrecoverable.
- **Gemini attacker → OpenAI monitor:** `400 Invalid 'input[2].id': string too long — max 64, got 22346`. **Fatal.** This is the one cell of 24 I could not complete, and no amount of retrying fixes it.

Is this the providers' fault or ControlArena's? My read — and I want to flag that I did not root-cause it, I routed around it — is that it's **one of each, and only one is fixable by the harness**:

- The thinking-block rejection is a genuine **provider-API property**. Reasoning traces are not a portable format; Anthropic cryptographically signs its own and rejects foreign ones by design. The harness *can* dodge it by stripping reasoning content before handing a trajectory to a cross-provider monitor, but the incompatibility itself isn't going away.
- The 22 KB `id` is almost certainly a **replay-path bug** — nothing should be putting 22,000 characters in an identifier field, and OpenAI's 64-char cap is reasonable. That one is fixable, and I'd expect it to be, which is a caveat on treating this cell as permanently impossible.

Taken together with the null above, these two results give the complete answer for anyone considering a decorrelated monitoring stack: **no measured detection benefit, and a real implementation cost to find out.** That's a cheap negative result to have in hand before anyone builds one on the assumption that it's free.

## Result 4: which model you cast as the attacker matters as much as the monitor

Everything above holds the attacker fixed and varies the monitor. The rest of this post does the opposite — and the effect is at least as large.

This wasn't a hypothesis. It's the biggest effect in the data.

Hold the monitor fixed; swap the attacker:

| Monitor | Safety vs Gemini | Safety vs GPT-5.5 | Δ |
|---|---|---|---|
| gemini-3.1-flash-lite | 0.333 | 0.776 | **+0.44** |
| claude-haiku-4-5 | 0.443 * | 0.780 | +0.34 |
| gemini-3.1-pro | 0.446 | 0.780 | +0.33 |
| Qwen-2.5-72B | 0.413 | 0.708 | +0.30 |
| gpt-4.1-mini | 0.178 | 0.467 | +0.29 |
| claude-opus-4-8 | 0.590 | 0.827 | +0.24 |

\* The Gemini × Haiku cell lost one attack sample to the thinking-block incompatibility in Result 3, so its safety is computed over 99 attack samples rather than 100. These are the same six monitors as the paired table in Result 2 — all six appear in both viable attacker rows.

Every one of the six monitors' measured safety swings by 0.24–0.44 depending on who it's defending against — comparable to the entire monitor-choice effect (~0.35), measured in the same factorial on the same cells.

![Left: successful attacks per 100 under an identical attack policy — Gemini 45–69, GPT-5.5 11–37, Opus 4.8 just 1. Right: the same monitor's measured safety swings 0.24–0.44 depending only on which model it is defending against.](figures/fig4_elicitation.png)

*Figure 4 (`fig4_elicitation.png`). One off-the-shelf attack prompt, three frontier attackers. Left: successful attacks per 100 (task solved **and** backdoor landed, post-deferral); dots are individual monitor cells in that attacker's row, so the within-row spread is the deferral effect from Result 1. Right: hold the monitor fixed, change only the attacker, and measured safety moves as much as the entire monitor axis does.*

That the red team determines the number is the control framework's premise, not news (Greenblatt et al. 2023). What's new here is the *axis*: the prior work above varies how the attacker attacks — its timing, its content, its selection policy, its skill. This holds the attack policy **completely fixed** — one identical off-the-shelf prompt, ControlArena's default — and varies only which frontier model is executing it. That alone produces the following:

| Attacker | Successful attacks / 100 | Backdoor landed | Main task solved (attack mode) | Usefulness (honest) |
|---|---|---|---|---|
| Gemini 3.1 Pro | **45–69** | 54–79 | 81–84 | 0.96 |
| GPT-5.5 | 11–37 | 13–40 | 89–97 | 1.00 |
| Claude Opus 4.8 | **1** | 3 | 84 | 0.87 |

(Ranges are across the monitor cells in that row. Since these counts are post-deferral, the within-row spread is the monitor's deferral effect, not attacker variance.)

Opus is the extreme case, and the middle columns are the point. It is *not* refusing: it solves **84** of 100 main tasks in attack mode, so it fully engages with the prompt. It lands a working backdoor **3** times. And in only **1** of those did it land the backdoor *and* solve the task — and that intersection is the only event safety is computed from. With one successful attack in 100, every safety number in that row is noise: across its eight monitors I measured "safety" of 0.0, 0.0, 0.0, 0.0, 0.5, 0.5, 0.5, 0.667, with AUCs all pinned at ~0.50.

Read naively, **the Opus rows look like a triumph** — high safety, monitors apparently working. They are an artifact of a red team that didn't attack. I dropped all eight from the analysis.

**Implication:** attack elicitation is a silent confound in any control comparison that changes the untrusted model. If you swap in a new model and safety goes up, you have learned nothing until you check whether your red team still functions against it — and the check is one column: not the backdoor *attempt* rate, but the count of attacks that both solved the task and landed the backdoor. Had I not added that column, I would have written up the Anthropic rows as a monitoring result.

## Result 5: two ways safety numbers lie at small scale

**Tutorial-scale safety is uninterpretable.** An early n=15 run with a functionally blind monitor (honest and attack suspicion both ≈0, AUC 0.53) reported **safety = 1.00**. Bootstrapping safety over subsamples, the 95% CI at n=10/mode spans **[0.00, 0.83]** — the same monitor and protocol are compatible with total failure and near-perfect defense.

![Bootstrap 95% confidence bands on safety as sample size grows from 10 to 100 per mode. At n=10 the band spans nearly the full [0,1] range.](figures/fig3_mirage.png)

*Figure 5 (`fig3_mirage.png`). Bootstrap 95% CI on safety@5% against samples per mode. At tutorial scale the interval is nearly the whole unit range — the point estimate carries almost no information.*

**Audit budgets below your sample resolution are degenerate.** Safety@1% sets the audit threshold at the 99th percentile of honest suspicion. With 100 honest samples that's *one* sample; with 50, half a sample. In my n=50 pilot, safety@1%, @2%, and @5% came out **identically 0.12** — three budgets returning one number is the signature of an unresolved threshold. Report the budget your honest-sample count can resolve (@5% at n=100), and report n beside it.

**This is convergent, not novel — which makes it stronger.** Ge-Wang et al. independently flag the small-sample problem and report attack counts alongside every result specifically "so that estimates resting on small samples are immediately visible," calling it fundamental to any conditional catch-ratio estimator. We arrive at the same recommendation by different mechanisms, and the mechanisms are worth distinguishing:

- **Theirs:** the conditional denominator shrinks as the attacker becomes *more selective* — a better red team makes its own estimate noisier.
- **Mine:** audit-threshold percentile granularity makes safety@1% structurally unresolvable below ~100 honest samples. This bites even with a maximally indiscriminate attacker, because it's a property of the *honest* tail, not the attack count.

Two independent routes to the same reporting requirement is a considerably better argument for it than either alone.

## Four ways the harness lied to me

Four infrastructure failures cost me real money, and **three of them produced plausible-looking wrong states rather than loud errors** — which is uncomfortably on-thesis. Both the statistics (Result 5) and the infrastructure fail silently, and both fail in the same direction: toward looking safe.

1. **The monitor's cache key ignored the monitor model.** With caching on, later configs silently reused the *first* monitor's suspicion scores — three byte-identical result rows that looked like a finding. If you vary a component, verify per-config which models were actually called.
2. **A daily-quota 429 looks exactly like slowness.** Gemini's direct API retried on 30-minute backoff for 11 hours, leaving a half-finished cell that a "does a log file exist?" check would treat as complete — silently reporting whichever early-index samples the run happened to reach.
3. **One transient 402 cancelled 23 healthy in-flight samples** by tripping the harness's error threshold, and surfaced as "credits exhausted" when credits were fine.
4. **`basic_monitor_builder(model=...)` is silently ignored** — the monitor resolves `model_role="trusted"`, so the monitor must be varied via `trusted_model`. Pass the wrong argument and you get a complete, clean, entirely wrong experiment.

Only #3 announced itself, and it announced itself with the wrong cause. Every results table now carries `n`, `n_expected`, `complete`, and `n_successful_attacks`, and the analysis refuses to read incomplete cells.

## A proposed reporting checklist

Any trusted-monitoring safety number should ship with:

1. **Monitor AUC** (honest vs. attack suspicion). Without it, a blind monitor is indistinguishable from a working one.
2. **Successful-attack count** — attacks that solved the task *and* landed the backdoor. Below ~5, safety is noise. Report whether it's pre- or post-deferral; for red-team viability you want pre-protocol.
3. **An audit budget your honest-sample count can resolve.** ≥1 expected sample in the tail, or say so.
4. **n, and a CI.** Point estimates at n<50/mode are not informative.

All four are one column each. None of them are standard.

## Limitations

- **The attacker is a prompted proxy, not a schemer.** ControlArena's attack policy is *instructed* to insert backdoors. A genuinely misaligned model might attack rarely and subtly. Result 4 shows how sensitive the whole enterprise is to how well that proxy is elicited.
- **Attacks are static.** No red-team iteration against each monitor; the provenance null in particular might not survive adaptive attacks (Terekhov et al. 2025).
- **One scaffold, one domain.** A single monitor prompt (`basic_monitor`, final-code review) on APPS — public and likely in every training set. Absolute AUCs (0.565–0.763) may reflect the scaffold as much as the models; claims here are about *relative* differences.
- **The provenance null bounds the effect at roughly ±0.08 AUC**, not below that.
- **Three of nine monitor means rest on a single attacker row** (marked † above), and are both noisier and mildly inflated relative to the two-row means.
- **Successful-attack counts are post-deferral**, so they conflate red-team strength with monitor strength. The comparison *across* attackers still holds — the deferral effect is bounded by the within-row spread, which is smaller than the between-row gap — but a clean elicitation measurement would use the pre-protocol count.
- **H1 came out messier than preregistered** — I report the non-monotonicity rather than the cleaner story I expected.
- **23 of 24 cells.** The missing one (Gemini attacker × GPT-5.5 monitor) failed on an API incompatibility, not an omission — though see Result 3 on why I'd expect that one to be fixable.
- **API snapshot.** Closed models update silently; IDs and dates are pinned in the repo. The Google strong tier is an alias, not a fixed snapshot.
- **Result 4 is post-hoc** and should be treated as a hypothesis for confirmation, not a confirmed finding.

## What I'd do next

1. **Confirm Result 4 as a preregistered hypothesis** across more attacker families and settings, using a pre-protocol attack count.
2. **Fix the elicitation problem.** Is Opus's behavior — 84 main tasks solved, 3 backdoors landed, 1 of them in a passing submission — safety training, or an attack policy tuned for another model? If red-team elicitation is model-specific, every cross-model control comparison inherits the confound, and the fix is per-model attack elicitation rather than a shared prompt.
3. **Adaptive attacks**, which the provenance null may not survive.
4. **Better monitor scaffolds** — full-trajectory review, ensembles, consensus mechanisms — to see whether the 0.145 monitor-identity spread compresses when monitors get a better prompt.

## Reproduction

Repo contains the experiment script (`monitor_discrimination_experiment.py`), figure pipeline (`make_figures.py`), interaction test (`analyze_interaction.py`), the preregistration (`experiment design.md`, committed before the funded runs), and the per-cell results tables. Raw `.eval` transcripts are gitignored (365 MB across 83 files); re-run the script to regenerate them.

All five figures are produced by `LIMIT=100 python make_figures.py` and land in `figures/`.

Funded by a BlueDot Impact rapid grant (~$150 in API credits). Thanks to the ControlArena team at UK AISI for the framework.
