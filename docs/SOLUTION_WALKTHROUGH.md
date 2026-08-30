# IMMUNIS — Solution Walkthrough

*An adversarial immune system for payment networks.*

---

## 1. The problem, and the shape of our answer

Payment fraud defence is reactive by construction. Fraud happens, chargebacks settle 45 to 90 days later, the data is labelled, and only then does the model retrain. That lag was survivable when a novel typology took a criminal crew months to invent and industrialise. Generative AI has cut that to hours, and the lag has not moved. The industry is now permanently one outbreak behind.

Immunology solved this problem a century ago, and the solution was not a faster autopsy. A vaccine manufactures a safe, high-fidelity replica of a pathogen *before* exposure, so the antibody already exists on day zero.

IMMUNIS applies that structure to payments:

| Immunology | IMMUNIS | Challenge pillar |
|---|---|---|
| Antigen discovery | Attack Atlas — a living, machine-readable catalogue of GenAI payment attack vectors, scored and auto-expanded | **Identify** |
| Attenuated strain synthesis | Multi-modal generators emitting realistic payment traffic plus the conversation, telemetry and mule graph around it | **Generate** |
| Antibody | A calibrated four-channel detector with reason codes | **Defend** |
| Immune memory and booster shots | A red agent that evolves against the live model; every evasion becomes a training label | **The closed loop** |

The measurable output is a metric we define and put on the front page: **Time-to-Immunity** — the number of adversarial generations required to drive a novel strain family's evasion rate below 5% while holding false positives inside budget. The industry's equivalent today is measured in months of chargeback data. In this run it is **1 generation** — 55 seconds of compute on a laptop.

---

## 2. Identify — the novel fraud attacks we found

The atlas ships **42 curated vectors** across 8 families, 7 payment rails and 6 attack surfaces, plus **10 machine-composed hybrids**. 14 of them have a working generator in the repository.

Crucially, the atlas is a **data structure, not prose**. Every vector is a typed record — rail, surface, kill chain, GenAI uplift, observable signals, historical analogue, detection gap, victim profile, mitigations — which means the generator keys off it, the detector is evaluated against it, and the discovery agent can recombine it. Threat score is computed, not asserted:

```
0.30 x detection_gap + 0.24 x genai_uplift + 0.20 x impact
  + 0.15 x scale_velocity + 0.11 x feasibility
```

The weighting is deliberate: *what we cannot currently see* dominates, because a cheap, scalable attack the incumbent stack misses deserves more red-team attention than an expensive one it already catches.

| Dimension | Breakdown |
|---|---|
| Family | Social engineering / APP (7), Card / rail exploitation (7), Authentication (6), Merchant / acquiring (6), Agentic commerce (5), Identity / onboarding (4), Money movement (4), Attacks on the defence (3) |
| Surface | authorisation (14), authentication (11), settlement (8), onboarding (4), model (3), dispute (2) |
| Rail | card_cnp (27), wallet (20), upi_p2p (16), upi_p2m (12), remittance (7), agentic (6), card_cp (6) |
| Priority | critical (21), high (15), medium (6) |

### 2.1 The vectors that matter most

Three groups are worth calling out, because they are the ones a 2019-vintage typology catalogue does not contain.

**Coercion-authorised payments** (`AV-DIGITAL-ARREST`, `AV-VOICE-CLONE`, `AV-VIDEO-DEEPFAKE-CALL`). The defining property is that the transaction is *technically perfect*: right customer, right device, right PIN, right geolocation. Every conventional authorisation feature reports legitimate — because it is. The customer really did authorise it. Pre-GenAI this required a fluent, confident human operator per victim who collapsed under improvised questions; a language model now runs the interrogation indefinitely, in the victim's own language and register, at near-zero marginal cost, while synthetic video supplies the uniform and the office.

**Agentic commerce** (`AV-AGENT-INJECT`, `AV-AGENT-MANDATE`, `AV-AGENT-REPLAY`, `AV-AGENT-SPOOF`, `AV-AGENT-COLLUDE`). This rail is being stood up across the industry right now and has no labelled fraud, because it has no history. A prompt-injected shopping agent buys the wrong thing from the wrong merchant under a completely valid consumer mandate; an over-scoped mandate is drawn to its ceiling by an agent the consumer genuinely authorised. A system that can only learn from historical losses has, by definition, nothing to learn here.

**Attacks on the defence itself** (`AV-MODEL-PROBE`, `AV-DATA-POISON`, `AV-ADV-PERTURB`). Every declined transaction is a labelled training example handed to the attacker for free. `AV-ADV-PERTURB` is the meta-vector — attacker-controlled parameters optimised against score feedback — and it is exactly what our red agent implements. Any attacker with outcome feedback can run the same optimisation, which is precisely why the defence must run it first.

### 2.2 Discovery: attackers compose, they do not invent

The discovery agent enumerates chainable pairs — where one stage's output capability satisfies the next stage's precondition — and scores composites with a bonus for straddling **observability boundaries**: different families, different rails, different surfaces. Those are the seams where each half looks unremarkable to the system that sees it and no single institution sees the whole, which is the structural blind spot only a network can close. A diversity guard caps how often any parent may appear, so the output is a spread of blind spots rather than ten variations on one. An optional Claude pass rewrites them into analyst-grade prose; the deterministic path runs identically without it, so the repository stays reproducible offline.

---

## 3. Generate — how the system simulates those attacks

The engine produces a ledger of **208,668 transactions** over 35 days across 2,191 customers and 709 merchants, of which 3,035 (1.45%) are fraudulent, alongside 4,713 conversations and 1,043 mule-graph edges.

Fidelity is not primarily a claim about the fraud. It is a claim about the **legitimate** traffic, and four design decisions carry it — each of which makes our own detection problem harder.

### 3.1 Attacks are injected into a calibrated population, not generated in isolation

Seven persona archetypes (salaried urban, student, senior citizen, gig worker, SME owner, high-net-worth, homemaker) each carry their own device set, home geography, MCC affinity, log-normal ticket distribution, circadian activity mixture, instrument mix and susceptibility — so victim selection is realistic rather than uniform, and coercion typologies land on the segments they land on in the real world. Demand carries salary-week spikes, weekend uplift, a pre-payday squeeze and a festival surge. Households share devices. A genuine new-account cohort exists, with no habitual payees yet. Fraud is overlaid on *that*, so a fraudulent transaction is only anomalous relative to a real behavioural baseline.

### 3.2 Roughly one in eleven legitimate transactions is deliberately anomalous

9.0% of legitimate traffic is a benign anomaly: genuine travel, a real first big-ticket purchase, a device upgrade, a first payment to a new landlord, a legitimate late-night payment, an out-of-character category, a retry burst. Each one mimics a different fraud tell.

This is the single most important decision in the build. Most synthetic-fraud demos report AUC above 0.999 because their legitimate traffic is homogeneous, which makes *unusual equals fraud* trivially true. By making legitimate traffic genuinely messy, our precision and false-positive numbers mean something — and, as Section 5.3 shows, our residual errors concentrate on exactly the benign anomalies a real issuer's do.

### 3.3 The model does not get complete telemetry, or correct labels

Session and behavioural telemetry is present on only 62% of the ledger, masked independently of the label — because in production it is missing for different channels, older app versions, third-party acquirers and browser restrictions. Missing values propagate as NaN and are never imputed to zero: *no screen share* and *we could not observe screen share* are different facts, and conflating them is how a model learns to treat an entire channel as low risk.

Training labels are corrupted the way reality corrupts them. 14% of fraud is never reported — coercion victims in particular rarely come forward — and a slice of legitimate traffic carries a false fraud label. In this run 258 training frauds are invisible to the model. Every metric in this document is nonetheless computed against ground truth.

### 3.4 Attacks are multi-modal, and attackers live ordinary lives

A coercion strain emits the scam transcript, the session telemetry (screen-share state, call state, hesitation, retries, app switches), the beneficiary graph and the transaction sequence — because that is what the fraud looks like end to end. Genuine conversations are generated for legitimate payments too, including urgent and emotional ones, so *has a transcript* is a signal rather than a label.

Every attacker-controlled identity also emits ordinary cover traffic (1,084 transactions in this run). A mule account whose every transaction is fraudulent is a simulation artefact, not a mule, and would hand the detector a shortcut instead of a typology.

### 3.5 The strain parameter space

Every injector exposes the same eight continuous knobs — the levers a real operator actually controls: `aggression`, `velocity`, `device_hygiene`, `spread`, `mimicry`, `dwell`, `stealth` and `narrative_intensity`. This is the contract with the red agent, and it is what makes the loop closable: the red agent does not invent new code, it discovers new *parameterisations* of known typologies that the current model fails on — which is how attack evolution actually works in the field.

### 3.6 What each generator produced

| Typology | Campaigns | Transactions | Labelled fraud | Value extracted |
|---|---:|---:|---:|---:|
| Wallet token provisioning fraud | 48 | 192 | 192 | Rs 96.55 L |
| Coercion-authorised payment (digital arrest) | 145 | 290 | 290 | Rs 89.76 L |
| Behavioural-biometric cloning | 54 | 162 | 162 | Rs 79.31 L |
| Cloned-voice distress / executive request | 153 | 215 | 215 | Rs 63.65 L |
| Adversary-in-the-middle OTP relay | 64 | 256 | 256 | Rs 45.83 L |
| Synthetic identity bust-out | 21 | 462 | 189 | Rs 37.68 L |
| First-party misuse / generated disputes | 31 | 217 | 217 | Rs 33.02 L |
| Over-scoped agent payment mandate | 29 | 172 | 172 | Rs 27.65 L |
| Synthetic merchant / transaction laundering | 9 | 207 | 207 | Rs 20.93 L |
| Deepfake KYC onboarding to mule cash-out | 15 | 180 | 180 | Rs 18.63 L |
| Fan-in / fan-out mule layering | 5 | 315 | 315 | Rs 7.64 L |
| QR tampering / collect-request abuse | 21 | 210 | 210 | Rs 6.14 L |
| Prompt-injected shopping agent | 64 | 192 | 192 | Rs 4.87 L |
| BIN enumeration / card testing | 7 | 238 | 238 | Rs 14,557 |

The gap between transactions and labelled fraud on the synthetic-identity and deepfake-KYC generators is deliberate: the nurture phase of a synthetic identity is real, settled, repaid activity and is labelled legitimate. Only the bust-out is fraud. Labelling the account as fraudulent from birth would leak the answer into training and inflate every metric downstream.

---

## 4. Defend — the detection and mitigation model

The detector fuses four channels with a noisy-OR over 110 strictly causal features.

1. **Supervised gradient boosting** over velocity, novelty, temporal, geo, device, merchant, graph, session, auth and mandate features. Trees, not a deep net, because an issuer has to deploy, monitor and explain this — and because trees win on tabular payment data.
2. **A graph channel** — fan-in and fan-out, pass-through ratio, dwell time on received value, shared-device components, payer diversity on young beneficiaries. This is what catches a mule mid-chain, and it is the clearest argument for a *network* doing this: no single bank sees more than one layer of the tree.
3. **An unsupervised novelty channel** (isolation forest fitted on legitimate training traffic only), contributing only in its extreme tail so it adds zero-day recall without flooding the alert queue.
4. **A rule layer** — 14 high-precision deterministic conjunctions. Every fraud team keeps rules for good reasons: they are auditable, they can be shipped in an afternoon when a new typology lands mid-quarter, and a regulator can read them.

Plus a **narrative channel**: TF-IDF and logistic regression over the pre-transaction conversation, fitted on training-split episodes only, entering the tabular model as a single feature.

### 4.1 Causality and leakage control

Features are computed in one streaming pass in timestamp order, maintaining per-entity state — the same shape a Flink or Kafka job would have in production. There is no group-by over the full dataset anywhere, and a test truncates the ledger and asserts the surviving rows' features are unchanged.

Simulator internals are never featurised: `susceptibility` (which drives victim selection), `vector_id`, `strain_id`, `campaign_id`, `benign_anomaly`, and the transaction's own `dispute_filed`. The customer's *prior* dispute history is used instead, because that genuinely is available at authorisation time.

The train/test split is **temporal**, not random. A random split on payment data leaks: the same campaign, mule account and device appear on both sides. Time is the only split that answers the question a bank actually asks — will this work next week?

### 4.2 Calibration, the operating point, and mitigation

Probabilities are isotonically calibrated on a held-out temporal slice (Brier score 0.00184), so the threshold can be chosen against an explicit cost matrix rather than an arbitrary 0.5. We report two operating points: the cost-optimal one, and the review-budget one at a 2% alert rate, because most institutions are staffed rather than optimised.

The cost matrix is explicit: Rs 55 per analyst review, Rs 420 per false decline, 72% of a missed fraud's value borne by the network, and 35% of alerts hard-declined rather than stepped up. Mitigation is graded accordingly — approve, review, step-up, decline — rather than a binary block, and every alert carries reason codes produced by ablation against the deployed scoring function, so an analyst can act on it and a regulator can read it.

---

## 5. Efficacy results

| Metric | Before the arena | After the arena |
|---|---|---|
| ROC-AUC | 0.9978 | **0.9961** |
| PR-AUC | 0.9631 | **0.9845** |
| Recall @ 2.0% alert budget | 97.0% | **98.9%** |
| Precision (simulation prevalence) | 61.0% | **62.3%** |
| False-positive rate | 0.793% | **0.764%** |
| Value recall | 96.3% | **98.6%** |
| Brier score | 0.00231 | **0.00184** |

Test slice: 62,601 future transactions, 790 fraudulent.

### 5.1 Precision, reported twice

The simulation runs at 1.26% fraud prevalence — hot, so that every typology has enough examples to learn from. A real card or UPI portfolio runs nearer 0.12%. Bayes-adjusted to that prevalence, precision is **13.5%** — about 7 alerts reviewed per fraud found, which is a staffing number an operations team recognises. Reporting only the in-simulation figure would be flattering and useless.

### 5.2 Recall by typology

An average hides the family you are blind to, so this is the table that matters.

| Typology | n | Recall | Value recall | Held out |
|---|---:|---:|---:|:--:|
| Behavioural-biometric cloning | 60 | 91.7% | 92.4% | yes |
| First-party misuse / generated disputes | 74 | 94.6% | 99.2% |  |
| Prompt-injected shopping agent | 72 | 100.0% | 100.0% |  |
| Over-scoped agent payment mandate | 42 | 100.0% | 100.0% | yes |
| Adversary-in-the-middle OTP relay | 56 | 100.0% | 100.0% |  |
| BIN enumeration / card testing | 102 | 100.0% | 100.0% |  |
| Deepfake KYC onboarding to mule cash-out | 24 | 100.0% | 100.0% |  |
| Coercion-authorised payment (digital arrest) | 84 | 100.0% | 100.0% |  |
| Synthetic merchant / transaction laundering | 33 | 100.0% | 100.0% |  |
| Fan-in / fan-out mule layering | 63 | 100.0% | 100.0% |  |
| QR tampering / collect-request abuse | 60 | 100.0% | 100.0% |  |
| Wallet token provisioning fraud | 64 | 100.0% | 100.0% |  |
| Cloned-voice distress / executive request | 56 | 100.0% | 100.0% |  |

### 5.3 False positives, by what kind of legitimate the transaction was

This is the table most synthetic-fraud submissions leave out. A low overall false-positive rate is easy if your legitimate traffic is boring; the rate that matters is the one on the hard negatives.

| Legitimate behaviour | n | False-positive rate | vs ordinary traffic |
|---|---:|---:|---:|
| big ticket | 735 | 4.35% | 6.6x |
| travel | 1,436 | 3.06% | 4.6x |
| category excursion | 528 | 1.14% | 1.7x |
| new beneficiary | 824 | 0.85% | 1.3x |
| new device | 2,229 | 0.72% | 1.1x |
| Ordinary legitimate traffic | 55,416 | 0.66% | — |
| night activity | 355 | 0.56% | 0.9x |
| burst | 288 | 0.00% | 0.0x |

Our residual errors concentrate on genuine big-ticket purchases — which is exactly where a real issuer's do, and is the honest cost of catching bust-out and account-takeover cash-outs.

### 5.4 Zero-day holdout — the result that matters

Two attack families were removed from training entirely, to measure cold generalisation to a typology with no labelled history.

| Held-out family | Cold start | After the arena | Lift |
|---|---:|---:|---:|
| Over-scoped agent payment mandate | 100.0% | 100.0% | +0.0 pt |
| Behavioural-biometric cloning | 71.7% | 91.7% | +20.0 pt |

The *cold start* column is what a conventional programme achieves on a typology it has never seen a labelled example of. The *after the arena* column is the same families once the red agent manufactured them and the blue model retrained on those synthetic strains. No real loss, no chargeback data and no defrauded customer was involved in closing that gap.

This is the entire thesis of the system in one table — and it is not a leak, because the labels came from attacks IMMUNIS generated itself, in a sandbox, against its own detector.

The unsupervised channel's contribution is honestly split. Legitimate traffic reaches the 99th novelty percentile at 0.9923. One held-out family sits far outside the legitimate manifold and the channel sees it coming; the other is engineered to look normal and it does not — which is precisely the gap the arena exists to close.

### 5.5 What each channel is worth

Each row is a model retrained from scratch with that channel's features removed. This is the question a bank asks before paying for any of it.

| Channel removed | ROC-AUC | PR-AUC | Delta PR-AUC | Recall | Delta recall |
|---|---:|---:|---:|---:|---:|
| nothing (full model) | 0.9978 | 0.9631 | — | 97.0% | — |
| narrative | 0.9971 | 0.9613 | -0.0018 | 96.7% | -0.2 pt |
| graph | 0.9960 | 0.9336 | -0.0295 | 92.8% | -4.2 pt |
| session | 0.9866 | 0.9156 | -0.0475 | 92.0% | -4.9 pt |

### 5.6 A negative result we are keeping

Our thesis was that reading the pre-transaction conversation would catch coercion payments the transaction side cannot see. The ablation above says the narrative channel is worth roughly nothing at portfolio level. Rather than explain that away, we built the experiment that could have rescued it: a high-mimicry operator — aged mule beneficiaries, amounts shaped under step-up thresholds, the victim taken off screen share before authorising, session pacing close to their own baseline — swept across how greedy they are. Low greed is the regime where every amount-based signal should go quiet and the conversation is the only evidence left.

| Aggression | n | Mean amount | Amount z | With narrative | Without | Lift |
|---:|---:|---:|---:|---:|---:|---:|
| 0.06 | 162 | Rs 16,741 | +2.06 | 100.0% | 100.0% | +0.000 |
| 0.12 | 171 | Rs 21,313 | +2.26 | 100.0% | 100.0% | +0.000 |
| 0.22 | 228 | Rs 19,122 | +1.95 | 100.0% | 100.0% | +0.000 |
| 0.40 | 234 | Rs 23,269 | +1.93 | 100.0% | 100.0% | +0.000 |
| 0.65 | 305 | Rs 25,060 | +1.83 | 100.0% | 100.0% | +0.000 |

The lift is zero at every point: beneficiary novelty and account age already carry this typology in our simulation. We would still ship the channel — a coercion alert an analyst can justify to a regulator is worth more than one they cannot, and it is the only signal left on the 38% of traffic with no session telemetry — but it is a design bet, not a measured win, and we label it that way. We would rather present a null result honestly than a claim we did not earn.

---

## 6. The closed loop — red versus blue

Each generation the red agent instantiates a population of 56 strains into real transactions, injects them into a warm slice of the ledger, and reads back the only feedback a real attacker has: does this get through?

The initial population is seeded from four **operator archetypes** — the documented parameterisation, a well-resourced professional crew, a cheap fast opportunist, and a threshold-hugging shaper — because seeding only from documented defaults would measure the detector against the attack as it is written up today, which is precisely the mistake this system exists to avoid.

**Fitness is evasion net of operating cost, subject to a value floor.** Unconstrained adversarial search always finds the same degenerate answer: make the attack so small, so slow and so expensive that it evades everything and earns nothing. That is a surrender, not an evasion, and a defence hardened against it learns nothing. So clean attested devices cost money, deep mule inventory costs recruitment, high mimicry costs operator hours per victim, and patience ties up working capital. The strains that survive are the ones a real crew would actually run — which is what makes retraining on them worth anything.

Every evasion is mined as a hard negative at elevated weight, the blue model retrains, and the same strains are re-scored to measure the immunity gained. The blue model is then re-measured on a **frozen future test slice at constant alert budget**, so a recall gain is only counted if the false-positive cost did not move.

| Gen | Attacks | Evasion found | After retrain | Mined | Blue AUC | Recall | FPR | Budget |
|---:|---:|---:|---:|---:|---:|---:|---:|:--:|
| 0 | 2,687 | 5.95% | 0.20% | 156 | 0.9993 | 98.23% | 0.772% | ok |
| 1 | 2,472 | 1.53% | 0.11% | 36 | 0.9987 | 97.72% | 0.778% | ok |
| 2 | 2,420 | 0.58% | 0.07% | 15 | 0.9995 | 98.48% | 0.768% | ok |
| 3 | 2,475 | 0.41% | 0.26% | 11 | 0.9994 | 98.73% | 0.765% | ok |
| 4 | 2,524 | 0.48% | 0.04% | 11 | 0.9996 | 98.73% | 0.767% | ok |
| 5 | 2,539 | 0.06% | 0.04% | 1 | 0.9980 | 99.11% | 0.762% | ok |
| 6 | 2,331 | 0.00% | 0.00% | 0 | 0.9980 | 99.11% | 0.762% | ok |
| 7 | 2,373 | 0.16% | 0.00% | 3 | 0.9961 | 98.86% | 0.764% | ok |

The red agent found **5.9% peak evasion** against the shipped model. Across the run the blue model gained **+1.9 points of recall** and +2.3 points of value recall while its false-positive rate moved -0.029 points, against a ceiling of 0.99% it was not allowed to exceed. 233 evading transactions were mined and folded back into training.

**Time-to-Immunity: 1 generation.**

---

## 7. Real-world feasibility in live payment environments

Nothing here needs a research cluster. The engine is CPU-only Python with scikit-learn; the whole pipeline runs end to end in 663 seconds on a laptop, and per-transaction scoring including reason codes is single-digit milliseconds.

| Prototype component | Production form |
|---|---|
| Population and behaviour simulator | Pre-production sandbox seeded from de-identified portfolio statistics. No PII is ever required, because everything is synthesised from distributions |
| Attack injectors | A strain library, versioned like threat-intel signatures and distributed to participants |
| Feature pipeline | Causal, single-pass, streaming-safe — the same code shape runs on Flink/Kafka at authorisation time |
| Detector | Exportable gradient-boosted model plus rule layer; 2 to 5 ms scoring; deployable as a challenger behind the incumbent before promotion |
| Rule layer | Ships independently of the model when a typology lands mid-quarter |
| Red vs Blue arena | A scheduled CI job. Fraud defence becomes a build pipeline with a failing test, not a quarterly review |
| Reason codes | Attached to every alert for analyst and regulator consumption |
| Artefacts | The model-risk evidence pack: what was tried, at what parameter ranges, what evaded, what residual risk remains |

**Adoption path.** An issuer runs IMMUNIS as a challenger model against shadow traffic, comparing its alerts to the incumbent's for one cycle. The rule layer can ship immediately and independently. The arena runs nightly in CI, and the first time it produces a strain the production model misses, the value proposition proves itself without anyone having lost money.

---

## 8. Novelty of the solution

The novelty is the closed loop, not any individual model.

**The red agent optimises against the live decision boundary of the deployed blue model, under realism and profitability constraints, and its survivors become the next training batch.** Adjacent industries — malware, spam, ad fraud — have run continuous adversarial self-play for years. Payments has not, because the labelling loop runs through chargebacks and chargebacks are slow. Manufacturing the fraud removes the dependency on that loop entirely.

Three supporting choices are also, as far as we know, unusual in this space:

- **Cross-modal generation and fusion.** Attacks emit the conversation, the session telemetry, the graph and the transaction together, and the detector consumes all four. (Our own measurement says the narrative channel does not pay off yet — reported in Section 5.6 rather than buried.)
- **Deliberately hard negatives.** Benign anomalies, missing telemetry, label noise, cover traffic from mule identities, and a genuine new-account cohort — all of which lower our own headline numbers and raise their credibility.
- **Time-to-Immunity as the product metric.** Not AUC. The question a network should be asking is *how fast can we become immune to something new*, and that number has not existed before.

---

## 9. Business case

Mastercard's fraud franchise sells models. The structural weakness of a model business is that models decay, and the decay rate is set by the attacker's iteration speed — which GenAI has just multiplied. IMMUNIS is not a competing model; it is the factory that keeps those models fresh, and it sells on three lines.

**1. Pre-breach immunisation** — subscription, per issuer or acquirer. Today a bank learns a new typology from its own losses. We ship the attack before it arrives: a monthly stream of synthetic strains for emerging vectors, plus retrained weights and the evaluation evidence. Priced against fraud basis points saved, a number every risk officer already has on a slide.

**2. Adversarial assurance and model validation** — per engagement, and a compliance line item. Model-risk and cyber-resilience expectations (RBI, EU DORA, US SR 11-7) increasingly require evidence that a model was stress-tested, not merely backtested. IMMUNIS emits exactly that evidence pack.

**3. Network herd immunity** — the moat, and the part only a network can build. When the red agent finds an evasion gap against one participant's configuration, the antibody propagates to every participant without any customer data moving: only synthetic strains and model updates. Value grows superlinearly with participants and cannot be replicated by a single bank or a point vendor. That is the strategic reason this belongs at a network rather than anywhere else.

**Why now.** Three curves cross in 2026: GenAI collapses the attacker's cost per novel attack, agentic commerce opens a rail with no fraud history to train on, and regulators begin asking for adversarial evidence. A system that manufactures labelled fraud on demand is the only answer to a rail that has no labels yet.

---

## 10. Responsible use, and limitations

Every entity, transaction and conversation is synthetic; no real cardholder data exists in this repository or is required by it. The atlas publishes observable behaviour and telemetry signatures — what a defender needs — and deliberately excludes operational playbooks, tooling, prompts and infrastructure. The red agent operates only against our own detector, in-process, with no network access and no interface to any payment system. Full policy in `docs/RESPONSIBLE_USE.md`.

Limitations we would want a judge to hold us to:

- **Simulated data is not real data.** Our generators encode our beliefs about how fraud looks. A production deployment must be calibrated against de-identified portfolio statistics before its numbers mean anything about that portfolio.
- **The conversation transcripts are template-generated**, so the narrative channel's in-sample separability is an upper bound. This is part of why we treat its stress-test result, not its AUC, as the evidence.
- **The red agent searches parameters, not code.** It cannot invent a typology outside the atlas. Closing that gap — an agent that proposes new generators, not just new parameterisations — is the obvious next step.
- **Time-to-Immunity is measured against our own generators.** It is a real number about a real loop, but the loop's coverage is bounded by the atlas, and the atlas is bounded by what we thought of.

---

## 11. Reproducing every number in this document

```bash
cd engine
pip install -r requirements.txt
python -m immunis.cli run --profile demo --seed 20260831
python ../scripts/make_docs.py
```

Run environment: Python 3.12.10, Windows-11-10.0.26200-SP0, CPU only, 663s end to end. Stage timings: identify 0.01s, generate 22.8s, defend 236.33s, arena 378.77s, artefacts 24.97s.

The web prototype in `web/` renders these same artefacts; every figure on the site comes from this pipeline and nothing is hand-entered.
