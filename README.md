# IMMUNIS — Adversarial Immune System for Payment Networks

> We manufacture the fraud that hasn't happened yet, and vaccinate the network before the criminals get there.

Payment fraud defence is reactive because labels arrive *after* the losses: real
fraud happens, chargebacks settle 45–90 days later, the data is labelled, and
only then does the model retrain. GenAI has cut the attacker's iteration cycle
from months to hours, so the industry is now permanently an outbreak behind.

IMMUNIS closes that loop. It **identifies** emerging GenAI payment fraud
vectors, **generates** them at high fidelity into a realistic payment ledger,
**defends** against them with a calibrated hybrid detector, and then lets a
**red agent evolve against the live model** until the model wins — turning
every evasion into tomorrow's training label.

---

## Quick start

```bash
git clone <this-repo> && cd immunis
```

**1 · Run the engine** (CPU only, no GPU, ~7 minutes on a laptop)

```bash
cd engine && pip install -r requirements.txt && python -m immunis.cli run
```

This regenerates every number in the submission and every JSON the web
prototype reads, into `artifacts/` and `web/public/data/`.

**2 · Run the prototype**

```bash
cd web && npm install && npm run dev
```

Open <http://localhost:3000>.

**3 · Optional — the live API**

```bash
pip install -r engine/requirements.txt && uvicorn api.main:app --port 8000
```

---

## What is in here

| Path | What it is |
|---|---|
| `engine/immunis/identify/` | The Attack Atlas: 42 typed vectors + a composition-based discovery agent |
| `engine/immunis/generate/` | Population, behaviour, 14 attack injectors, conversation generator, mule graph |
| `engine/immunis/defend/` | Causal features, four-channel detector, calibration, evaluation, reason codes |
| `engine/immunis/redteam/` | Constrained evolutionary evader and its realism/cost model |
| `engine/immunis/loop/` | Co-evolution orchestrator and Time-to-Immunity |
| `api/` | FastAPI service: live scoring, on-demand simulation, arena SSE stream |
| `web/` | Next.js prototype — landing page, Atlas, Studio, Defense, Arena, Live Console |
| `docs/` | Architecture, attack atlas write-up, results, responsible use guidelines |
| `artifacts/` | Generated JSON — the single source of truth for every figure on the site |

---

## The three pillars

### 1 · Identify

`engine/immunis/identify/`

**42 curated attack vectors** across 8 families, 7 payment rails and 6 attack
surfaces, each a typed record — rail, surface, kill chain, GenAI uplift,
observable signals, historical analogue, detection gap — rather than prose. A
**discovery agent** composes chainable pairs into hybrids and scores them with a
bonus for straddling *observability boundaries*, the seams where each half looks
unremarkable to the system that sees it.

Threat score is computed, not asserted:

```
0.30·detection_gap + 0.24·genai_uplift + 0.20·impact
+ 0.15·scale_velocity + 0.11·feasibility
```

weighted so that *what we cannot currently see* dominates.

The atlas deliberately includes vectors most catalogues miss because they are
2026-native: prompt-injected shopping agents, over-scoped agent mandates,
agent-token replay, behavioural-biometric cloning, and coercion-authorised
payments where the transaction is technically perfect.

```bash
python -m immunis.cli atlas          # print it
python -m immunis.cli atlas --json   # machine-readable
```

### 2 · Generate

`engine/immunis/generate/`

**14 attack injectors** emit transactions into a *calibrated base population* —
2,000+ customers across 7 persona archetypes with their own devices, home
geography, MCC affinity, log-normal tickets, circadian mixtures and instrument
mixes, over a multi-week horizon with salary-day spikes, weekend effects and a
festival surge.

Four fidelity decisions carry the claim, and each of them makes the problem
*harder*:

1. **~9% of legitimate traffic is deliberately anomalous** — genuine travel,
   first big-ticket purchases, device upgrades, first payments to a new
   landlord. Every one mimics a fraud tell. Without them, "unusual equals
   fraud" is trivially true and every metric downstream is fiction.
2. **Session telemetry is missing on ~38% of the ledger**, at the same rate for
   fraud and legitimate traffic — because in production it is missing too.
   `NaN` is propagated, never imputed to zero.
3. **Training labels are wrong on purpose** — 14% of fraud is never reported,
   and a slice of legitimate traffic carries a false fraud label. Evaluation
   always uses ground truth.
4. **Attacks are multi-modal.** A coercion strain emits the scam transcript,
   the session telemetry, the beneficiary graph *and* the transactions.

Genuine conversations are generated for legitimate payments too — including
urgent, emotional ones — so "has a transcript" is a signal rather than a label.

### 3 · Defend

`engine/immunis/defend/`

Four channels fused with a noisy-OR:

- **Supervised GBM** over ~110 strictly causal features (velocity, novelty,
  geo, device, merchant, graph, session, auth, mandate). One streaming pass in
  timestamp order — the same shape a Flink/Kafka job would have.
- **Graph channel** — fan-in/out, pass-through ratio, dwell time, shared-device
  components, payer diversity on young beneficiaries.
- **Novelty channel** — isolation forest fitted on legitimate traffic only,
  contributing in its extreme tail so it adds zero-day recall without flooding
  the queue.
- **Rule layer** — 14 high-precision deterministic conjunctions. Auditable,
  shippable in an afternoon, readable by a regulator.
- **Narrative channel** — TF-IDF + logistic regression over the pre-transaction
  conversation, fitted on training-split episodes only.

Split is **temporal**, not random. Probabilities are **isotonically
calibrated**. The operating threshold is chosen against an explicit cost matrix
and reported next to the review-budget threshold.

### The loop

`engine/immunis/redteam/` + `engine/immunis/loop/`

Each generation the red agent instantiates a population of strains — (family,
8-dimensional parameter vector) — into real transactions, injects them into a
warm slice of the ledger, and reads back the only feedback a real attacker has:
does this get through?

Fitness is **evasion net of operating cost, subject to a value floor**. Clean
attested devices cost money. Deep mule inventory costs recruitment. High
mimicry costs operator hours. Patience ties up capital. A strain that evades
but earns nothing scores near zero — so the survivors are strains a real crew
would actually run.

Every evasion is mined as a hard negative, the blue model retrains, and the
same strains are re-scored. **Time-to-Immunity** is the first generation where
post-retrain evasion falls below 5% with the false-positive budget intact.

---

## Reproducing the numbers

```bash
cd engine
python -m immunis.cli run --profile demo    # ~7 min,  209k transactions (default)
python -m immunis.cli run --profile full    # ~25 min, 490k transactions
python -m immunis.cli run --profile fast    # ~90 s,   44k transactions
```

Everything is seeded. `(seed, profile)` determines the run bit-for-bit; each
stochastic component draws from a named substream, so adding a component never
shifts an existing one.

```bash
python -m immunis.cli simulate --dump-ledger   # write the full ledger as NDJSON
python -m immunis.cli score                    # score + explain one transaction
pytest -q                                      # leakage and fidelity guardrails
```

The test suite is not a coverage exercise — each test pins an invariant that,
if broken, would silently turn a headline number into a lie. Notably
`test_features_are_causal` truncates the ledger and asserts the surviving rows'
features are unchanged.

---

## Honest reporting

Findings we could have buried and did not:

- **Precision is reported twice.** The simulation runs at ~1.3% fraud so every
  typology is learnable; a real portfolio runs nearer 0.12%. Both the
  in-simulation figure and the Bayes-adjusted figure are on the page.
- **The narrative channel does not earn its place at portfolio level.** We built
  a targeted stress test sweeping operator greed on high-mimicry coercion, and
  it showed no measurable lift — beneficiary novelty and amount deviation
  already carry that typology. The measurement is in `detection.json` and on
  the Defense Console. We would still ship it (regulatory explainability, and
  robustness when telemetry is absent), and we say so rather than claiming a
  result we did not get.
- **Zero-day recall is not uniform.** One held-out family generalises perfectly
  cold; the other starts at ~72%. The arena closes the gap — and we label that
  clearly as *after* the red agent manufactured the family, not as a cold-start
  number.
- **Residual false positives concentrate on genuine big-ticket purchases**, which
  is exactly where a real issuer's do.

See [`docs/RESULTS.md`](docs/RESULTS.md).

---

## Responsible use

Everything here is synthetic — no real cardholder, merchant or transaction data
is used anywhere. The atlas describes **observable behaviour and telemetry
signatures**, which is what a defender needs to build controls; it deliberately
contains no operational playbooks, tooling, prompts or infrastructure. The red
agent operates strictly against our own detector inside a sandbox. See
[`docs/RESPONSIBLE_USE.md`](docs/RESPONSIBLE_USE.md).

---

## Architecture at a glance

```
                        ┌──────────────────────────────────────────┐
                        │            artifacts/*.json              │
                        │  single source of truth for every figure │
                        └────────────▲──────────────┬──────────────┘
                                     │              │
   ┌───────────┐   ┌───────────┐   ┌─┴─────────┐  ┌─▼─────────┐   ┌──────────┐
   │ identify  │──▶│ generate  │──▶│  defend   │─▶│   loop    │   │   web/   │
   │  atlas +  │   │ population│   │ features  │  │  arena    │   │ Next.js  │
   │ discovery │   │ injectors │   │ 4 channels│  │  TTI      │   │ prototype│
   └───────────┘   │ narrative │   │ calibrate │  └─────┬─────┘   └──────────┘
        ▲          │   graph   │   │ explain   │        │              ▲
        │          └───────────┘   └───────────┘        │              │
        │                ▲                              │         ┌────┴────┐
        │                └──── mined evasions ──────────┘         │  api/   │
        └───────────── new vectors from blind spots ───────────────┤ FastAPI │
                                                                  └─────────┘
```

Full detail in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## Tech stack

**Engine** Python 3.12 · numpy · scipy · scikit-learn · networkx. No GPU, no
external services, no proprietary dependencies. Scoring is single-digit
milliseconds.

**Prototype** Next.js 16 (App Router) · React 19 · Tailwind CSS 4 · TypeScript.
Charts are hand-rolled SVG — zero charting dependencies. Every page is
statically generated from `artifacts/`, so the site deploys as static files.

**Service** FastAPI · uvicorn, with server-sent events for the live arena.

**Optional** Claude (`ANTHROPIC_API_KEY` + `--llm`) enriches discovered attack
vectors. The pipeline is fully reproducible offline without it — the LLM
enriches, it is never load-bearing.
