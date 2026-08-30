# IMMUNIS — The Adversarial Immune System for Payment Networks

> **Mastercard Innovation Challenge 2026 · Track: AI Defense Lab for Payment Security**
> One-line pitch: **We manufacture the fraud that hasn't happened yet, and vaccinate the network before the criminals get there.**

---

## 1. The decision, up front

I evaluated a dozen framings for this challenge and picked the one that scores highest against the five published judging criteria (attack diversity · simulation fidelity · detection efficacy · novelty · real-world feasibility) **and** has a defensible business on the other side of it.

**The idea:** an **immune system** for payment rails.

Biology gets this right and payments gets it wrong. A vaccine works by manufacturing a safe, high-fidelity replica of a pathogen *before* you are exposed, so your body already carries the antibody on day zero. Payment fraud defence does the opposite: it waits for real losses, waits 45–90 days for chargebacks and dispute data to settle, labels them, and *then* retrains. The industry is permanently one outbreak behind — and GenAI just shortened the attacker's iteration cycle from months to hours.

IMMUNIS closes that loop:

| Immunology | IMMUNIS | Challenge pillar |
|---|---|---|
| Antigen discovery | Attack Atlas — a living, machine-readable catalogue of GenAI-enabled payment attack vectors, scored and auto-expanded by an LLM discovery agent | **Identify** |
| Attenuated strain synthesis | Multi-modal attack generators that emit realistic payment traffic *plus* the social-engineering conversation, device telemetry and mule-graph structure around it | **Generate** |
| Antibody / adaptive immunity | A hybrid detector (gradient boosting + graph + sequence + narrative fusion + novelty channel) with calibrated probabilities and reason codes | **Defend** |
| Immune memory & booster shots | **Red-vs-Blue co-evolution arena** — the red agent evolves evasive strains against the live model; every evasion is mined as a hard negative and folded into the next training round | **The closed loop** |

The measurable output of the loop is a metric I define and put on the front page of the product: **Time-to-Immunity (TTI)** — the number of adversarial generations (and wall-clock minutes) required to drive a novel attack family's evasion rate below 5% while holding false positives inside budget. Today, the industry's equivalent number is measured in months of chargeback data. We move it to minutes.

---

## 2. Why this wins, criterion by criterion

### Diversity of attacks identified
The Attack Atlas ships with **42 distinct attack vectors** spanning six payment rails (card-present, card-not-present, UPI P2P, UPI P2M, tokenised/wallet, agentic commerce) and five surfaces (onboarding, authentication, authorisation, settlement, dispute). Each vector is a typed record — rail, channel, kill chain, GenAI uplift factor, observable signals, historical analogue, detectability gap — not prose. A discovery agent recombines TTPs across vectors to propose *novel* hybrid strains and scores them on `impact × feasibility × genai_uplift × detection_gap`, so the atlas grows rather than being a static list.

Crucially the atlas includes vectors most teams will miss because they are 2026-native, not 2019-native:
- **Agentic-commerce fraud** — prompt-injected shopping agents, over-scoped agent mandates, agent-token replay and agent-identity spoofing. Mastercard is actively standing up Agent Pay / agentic tokens; this is the rail that has no fraud model yet.
- **Behavioural-biometric cloning** — GenAI reproducing a victim's typing cadence, swipe dynamics and navigation rhythm to defeat passive behavioural auth.
- **Coercion-authorised payments** ("digital arrest", deepfake-voice CEO fraud) — where the transaction is *technically perfect*: right customer, right device, right OTP, right geolocation. Every conventional feature says legitimate. This is the hardest and fastest-growing class in India and it is the one that best justifies our cross-modal approach.

### Fidelity of attacks in simulation
Two design choices carry the fidelity claim:

1. **Attacks are injected into a calibrated base population, not generated in isolation.** We simulate 2,000 cardholders with persona archetypes (salaried urban, student, senior citizen, gig worker, SME owner, HNI), each with their own device set, home geography, MCC affinity, log-normal ticket distribution, circadian activity mixture and instrument mix — over a multi-week horizon with salary-day spikes, weekend effects and festival surges. Fraud is then overlaid on top of *that* stream, so a fraudulent transaction is only anomalous relative to a real behavioural baseline.

2. **We deliberately inject ~3% benign anomalies into legitimate traffic** — genuine travel, first-time high-value purchases, device upgrades, new beneficiaries. This is the single most important fidelity decision in the whole build. Most synthetic-fraud demos score AUC 0.999 because their legitimate traffic is boringly homogeneous, so "weird = fraud" is trivially true. By making legitimate traffic genuinely messy, our precision and false-positive numbers mean something, and the low-FPR claim survives contact with a real portfolio.

Attacks are also **multi-modal**: a coercion strain emits a scam conversation transcript, session telemetry (screen-share active, call in progress, hesitation and retry pattern), the beneficiary graph and the transaction sequence — because that is what the fraud actually looks like end-to-end.

### Detection efficacy
A hybrid, deliberately un-exotic stack — because feasibility is a judging criterion and a bank cannot deploy a research artefact:
- gradient-boosted trees over ~90 causally-computed features (velocity, novelty, geo, device, merchant, graph, session, auth),
- a **graph channel** (fan-in/fan-out, pass-through ratio, shared-device components, community risk) for mule networks,
- a **narrative channel** that turns the pre-transaction conversation into a numeric coercion score and fuses it with the tabular model — the part no production fraud stack does today,
- an **unsupervised novelty channel** that fires on strains no label has ever seen,
- a high-precision deterministic rule layer for regulator-explainable hard stops,
- isotonic calibration and a **cost-optimised operating threshold** (fraud loss vs review cost vs customer friction) rather than an arbitrary 0.5.

And the honesty test that most submissions won't run: a **zero-day holdout**, where entire attack families are removed from training and the model is measured on them cold. That number — not the headline AUC — is the one that predicts real-world performance.

### Novelty
The closed loop is the novelty, not any single model. Specifically: **the red agent optimises against the live decision boundary of the deployed blue model, under realism and profitability constraints.** It is an evolutionary search where fitness = evasion rate, penalised for attacks that are implausible or unprofitable — so it cannot cheat by evolving toward attacks no criminal would bother running. The survivors are exactly the blind spots, and they become the next training batch. Nobody in the payments industry runs continuous adversarial self-play against their production fraud model; everybody in adjacent industries (malware, spam, ad fraud) already does.

### Real-world feasibility
Nothing here needs a research cluster. The engine is CPU-only Python with scikit-learn; scoring is single-digit milliseconds; the model consumes features an issuer already has at authorisation time. Deployment path in Section 4.

---

## 3. The business motive

**Who pays, and why.**

Mastercard's fraud franchise (Decision Intelligence, Brighterion, Ekata, NuDetect) sells *models*. The structural weakness of a model business is that models decay, and the decay rate is set by the attacker's iteration speed — which GenAI has just multiplied. IMMUNIS is not a competing model. It is **the factory that keeps those models fresh**, and it sells on three distinct lines:

**1. Pre-breach immunisation (subscription, per issuer/acquirer).**
Today an issuer learns about a new typology from its own losses. We sell the attack *before* it arrives: a monthly stream of synthetic, high-fidelity strains for emerging vectors, plus the retrained detector weights and the evaluation evidence. Priced against fraud basis points saved, which is a number every risk officer already has on a slide.

**2. Adversarial assurance & model validation (per engagement).**
Regulators (RBI's model-risk and cyber-resilience expectations, EU DORA, US SR 11-7) increasingly require evidence that a model was *stress-tested*, not just backtested. IMMUNIS emits exactly that evidence pack: which attack vectors were tried, at what parameter ranges, what evaded, what the residual risk is. This is a compliance line item, which means it is a budget line item.

**3. Network herd immunity — the moat.**
This is the part only a network can build. Mastercard sits between thousands of issuers and acquirers. When the red agent finds an evasion gap against one participant's configuration, the antibody propagates to every participant, without any of them sharing customer data — only synthetic strains and model updates move. The value of the system grows superlinearly with participants, and it cannot be replicated by any single bank or any point-solution vendor. That is a genuine network-effect moat, and it is the strategic reason this belongs at Mastercard specifically rather than anywhere else.

**Why now.** Three curves cross in 2026: GenAI collapses the attacker's cost per novel attack; agentic commerce opens a payment rail with no fraud history to train on; and regulators start demanding adversarial evidence. A system that manufactures labelled fraud on demand is the only answer to a rail that has no labels yet.

**Cost of being wrong is asymmetric in our favour.** A missed fraud costs the network the transaction value plus dispute handling. A false positive costs a declined good customer. IMMUNIS optimises the threshold against that explicit cost matrix and reports rupees saved per 100k transactions — so the pitch to a bank is arithmetic, not adjectives.

---

## 4. Real-world deployment path

The prototype is architected so each pillar maps to something a payment network can actually run:

| Prototype component | Production form |
|---|---|
| Population + behaviour simulator | Sits in a pre-prod sandbox seeded from de-identified portfolio statistics — no PII ever needed, since we synthesise from distributions |
| Attack injectors | A strain library, versioned like threat-intel signatures, shipped to participants |
| Feature pipeline | Causally computed, single-pass, streaming-safe — the same code runs on Flink/Kafka at authorisation time |
| Detector | Exportable GBM + rule layer; ~2–5 ms scoring; deployable as a challenger model behind the incumbent before promotion |
| Red-vs-Blue arena | A scheduled CI job. Fraud defence becomes a build pipeline with a failing test, not a quarterly review |
| Reason codes | Regulator- and analyst-facing explanations attached to every alert |

**Guardrails.** The generators emit only synthetic entities and never touch real cardholders. The red agent operates strictly against our own detector inside a sandbox, its strain parameters live behind a documented realism constraint set, and the repository publishes attack *behavioural patterns and telemetry signatures* — the observable fingerprint a defender needs — not operational playbooks, scripts or infrastructure an attacker could lift. That line is drawn deliberately and is documented in `docs/RESPONSIBLE_USE.md`.

---

## 5. What is actually built in this repository

Not a slide-deck idea — a running system.

- **`engine/`** — the three pillars as a clean Python package: `identify/` (atlas + discovery agent + threat scoring), `generate/` (population, behaviour, rails, 14 attack injectors, narrative generator, mule graph), `defend/` (features, hybrid model, calibration, evaluation, reason codes), `redteam/` (constrained evolutionary evader), `loop/` (co-evolution orchestrator, Time-to-Immunity).
- **`api/`** — FastAPI service exposing the atlas, simulation runs, live scoring and a server-sent-event stream of the arena.
- **`web/`** — Next.js prototype: landing page, Attack Atlas explorer, Simulation Studio, Defense Console (curves, per-attack recall, threshold/cost slider, live scoring with reason codes), and the Red-vs-Blue Arena. Runs standalone off baked artefacts, and lights up in LIVE mode when the engine is running.
- **`docs/`** — architecture, attack atlas write-up, auto-generated results, solution walkthrough, responsible-use policy.

Everything is reproducible from one command, seeded, and CPU-only.

---

## 6. The one-sentence version for the judges

> Payment fraud defence is reactive because labels arrive after the losses; IMMUNIS makes labels arrive *before* the losses by manufacturing the attack itself, and proves it by letting a red agent evolve against the live model until the model wins.
