# Architecture

## Design principles

Four decisions shaped everything else.

**1 · Artefacts are the contract.** The engine writes plain JSON to
`artifacts/`; the web prototype reads it and nothing else. No figure on the site
is hand-entered, and the site can be deployed as static files with no backend.
It also means a judge can inspect any intermediate result with a text editor.

**2 · Causality is enforced, not assumed.** Features are computed in a single
streaming pass in timestamp order. There is no group-by over the full dataset
anywhere in the pipeline, and a test truncates the ledger and asserts the
surviving rows' features are byte-identical.

**3 · Difficulty is deliberate.** Every realism decision in the simulator makes
the detection problem *harder*: benign anomalies, missing telemetry, label
noise, cover traffic from mule identities, a genuine young-account cohort. A
synthetic benchmark that flatters its own model is worthless.

**4 · Determinism.** `(seed, profile)` determines a run completely. Each
stochastic component draws from a named substream derived from a Blake2b hash
of its name, so adding a component never shifts the numbers produced by an
existing one.

---

## Module map

```
engine/immunis/
├── config.py            Every knob that shapes a run, in one place
├── cli.py               run · atlas · simulate · score
├── pipeline.py          Orchestration; the only thing that writes artefacts
│
├── util/
│   ├── rng.py           Named, forkable, deterministic random substreams
│   ├── geo.py           India-weighted city set + haversine
│   └── io.py            JSON / NDJSON artefact writers
│
├── identify/            ── PILLAR 1
│   ├── schema.py        AttackVector dataclass; computed threat score
│   ├── atlas.py         42 curated vectors across 8 families
│   └── discovery.py     Composition-based discovery + optional LLM enrichment
│
├── generate/            ── PILLAR 2
│   ├── entities.py      MCCs, personas, devices, merchants, accounts
│   ├── population.py    World construction incl. new-account/new-merchant cohorts
│   ├── behaviour.py     Legitimate traffic, benign anomalies, cover traffic
│   ├── narrative.py     Scam and genuine conversation generation
│   ├── simulator.py     Orchestration, fraud budgeting, telemetry masking
│   └── attacks/
│       ├── base.py      Injector ABC, strain parameter space, world helpers
│       ├── social.py    AV-DIGITAL-ARREST · AV-VOICE-CLONE
│       ├── auth.py      AV-AITM-OTP · AV-BIO-CLONE
│       ├── identity.py  AV-SYNTH-ID · AV-DEEPFAKE-KYC
│       ├── rail.py      AV-BIN-ENUM · AV-QR-SWAP · AV-TOKEN-PROV
│       ├── merchant.py  AV-FAKE-MERCH · AV-FRIENDLY-FRAUD
│       ├── launder.py   AV-MULE-LAYER
│       └── agentic.py   AV-AGENT-INJECT · AV-AGENT-MANDATE
│
├── defend/              ── PILLAR 3
│   ├── features.py      ~110 causal features; the FORBIDDEN set
│   ├── narrative.py     Cross-modal text channel
│   ├── model.py         4-channel detector, rules, calibration, thresholds
│   ├── evaluate.py      Metrics incl. per-typology and benign-anomaly FPR
│   ├── explain.py       Ablation-based reason codes in log-odds space
│   └── stress.py        Targeted channel measurements
│
├── redteam/             ── THE LOOP
│   ├── constraints.py   Operating-cost model and per-family bounds
│   └── evader.py        Arena harness + evolutionary search
└── loop/
    └── coevolve.py      Generations, mining, retraining, Time-to-Immunity
```

---

## Data flow

```
Config(seed, profile)
   │
   ├─▶ build_world()            customers, merchants, devices, accounts
   │        │
   │        ├─▶ generate_legit()          ~205k legitimate transactions
   │        │      └ benign anomalies, travel windows, device upgrades
   │        │
   │        ├─▶ 14 × Injector.run()       ~3k fraudulent transactions
   │        │      └ + conversations + mule-graph edges
   │        │
   │        ├─▶ generate_cover_traffic()  ordinary activity from mule identities
   │        └─▶ _mask_telemetry()         label-independent missingness
   │
   ├─▶ build_features()          single causal pass → X (n × 110), y, meta
   │
   ├─▶ temporal_split()          train | calibrate | test, strictly in time order
   ├─▶ apply_narrative_channel() text model fitted on training episodes only
   ├─▶ apply_label_noise()       corrupt observed labels; ground truth preserved
   │
   ├─▶ Detector.fit()            GBM + isolation forest + rules + isotonic
   ├─▶ evaluate()                curves, per-typology, benign-anomaly FPR, cost
   ├─▶ ablations × 3             retrained from scratch per channel
   ├─▶ novelty_profile()         where each family sits vs the legitimate manifold
   ├─▶ narrative_stress_test()   targeted measurement, greed sweep
   │
   └─▶ run_coevolution()
            for each generation:
              Arena.run()        instantiate strains → warm ledger slice → score
              fitness            evasion − cost, subject to a value floor
              mine evasions      → hard negatives
              Detector.fit()     with extra=(X_mined, y, weights)
              re-score           immunity gained
              _measure()         frozen future slice, constant alert budget
              breed              elites + crossover + mutation + diversity
```

---

## The strain parameter space

The contract between the generator and the red agent. Eight continuous knobs in
`[0, 1]`, exposed identically by every injector:

| Parameter | Meaning | Expensive when |
|---|---|---|
| `aggression` | share of available value extracted per event | — |
| `velocity` | how tightly events are packed in time | low (patience costs capital) |
| `device_hygiene` | 0 = emulator farm, 1 = clean attested handset | high |
| `spread` | distinct mules / merchants / cards used | high |
| `mimicry` | how closely the victim's own behaviour is imitated | high |
| `dwell` | how long value is held before onward movement | high |
| `stealth` | how hard amounts hug just under thresholds | high |
| `narrative_intensity` | how aggressive the social-engineering script is | low |

Per-family bounds keep evolution inside the typology: card testing without
velocity is not card testing, and a coercion script with zero narrative
intensity never gets the victim to press send.

---

## Leakage controls

Every one of these is enforced by a test.

| Risk | Control |
|---|---|
| Simulator internals as features | Explicit `FORBIDDEN` set — `susceptibility`, `vector_id`, `strain_id`, `campaign_id`, `benign_anomaly`, and the transaction's own `dispute_filed` |
| Look-ahead in aggregates | Single causal streaming pass; truncation test |
| Campaign bleed across the split | Temporal split, never random |
| Narrative channel fitted on its own test set | Episode split derived from the transaction split, never from the episode label |
| "Has a transcript" as a label proxy | Genuine conversations generated for legitimate payments, including urgent ones |
| "Young account" as a mule proxy | A real new-account cohort with no habitual payees |
| "Only ever did fraud" as an identity proxy | Cover traffic from every attacker-controlled identity |
| Nurture activity mislabelled | Synthetic-identity nurture transactions are labelled legitimate; only the bust-out is fraud |
| Missing telemetry correlating with the label | Masking applied independently of the label; test asserts the rates match within 12 points |

---

## Production mapping

| Prototype component | Production form |
|---|---|
| Population + behaviour simulator | Pre-prod sandbox seeded from de-identified portfolio statistics — no PII, since everything is synthesised from distributions |
| Attack injectors | A strain library, versioned like threat-intel signatures and shipped to participants |
| `build_features` | Causal, single-pass, streaming-safe — the same code shape runs on Flink/Kafka at authorisation time |
| `Detector` | Exportable GBM + rule layer; 2–5 ms scoring; deployable as a challenger behind the incumbent before promotion |
| Rule layer | Ships independently of the model when a typology lands mid-quarter |
| Arena | A scheduled CI job. Fraud defence becomes a build pipeline with a failing test, not a quarterly review |
| Reason codes | Attached to every alert for analyst and regulator consumption |
| Artefacts | The model-risk evidence pack: what was tried, what evaded, what residual risk remains |

---

## Performance

Measured on a laptop, `demo` profile (209k transactions), CPU only:

| Stage | Time |
|---|---|
| Atlas + discovery | < 0.1 s |
| Simulation | ~21 s |
| Feature engineering | ~24 s |
| Model fit (4 channels) | ~35 s |
| Ablations (3 retrains) | ~80 s |
| Arena (8 generations) | ~220 s |
| Artefacts + explanations | ~16 s |
| **Total** | **~7 min** |

Per-transaction scoring is single-digit milliseconds, including reason codes.

---

## Extending it

**A new attack vector** — add an `AttackVector` to `identify/atlas.py`. That
alone puts it in the atlas, the threat ranking and the web explorer.

**A new generator** — subclass `Injector`, implement `run()`, call `register()`.
Set `status=SIMULATED` and `injector=<key>` on the atlas entry. It is now
budgeted by the simulator, available to the red agent, and evaluated per-family
automatically.

**A new feature** — append to `FEATURE_NAMES` and populate it in the causal loop
in `build_features`. Add a `REASON_TEXT` entry so it can appear in reason codes.

**A new detection channel** — add it to `Detector.score`'s noisy-OR fusion and
register an ablation group in `pipeline.ABLATIONS` so its value gets measured
rather than assumed.
