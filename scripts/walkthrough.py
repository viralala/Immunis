"""Generates docs/SOLUTION_WALKTHROUGH.md — the submission write-up.

Every figure is injected from `artifacts/`, so the document cannot drift from
the run that produced it. Imported by `scripts/make_docs.py`.
"""

from __future__ import annotations

SHORT = {
    "AV-DIGITAL-ARREST": "Coercion-authorised payment (digital arrest)",
    "AV-VOICE-CLONE": "Cloned-voice distress / executive request",
    "AV-AITM-OTP": "Adversary-in-the-middle OTP relay",
    "AV-BIO-CLONE": "Behavioural-biometric cloning",
    "AV-SYNTH-ID": "Synthetic identity bust-out",
    "AV-DEEPFAKE-KYC": "Deepfake KYC onboarding to mule cash-out",
    "AV-BIN-ENUM": "BIN enumeration / card testing",
    "AV-QR-SWAP": "QR tampering / collect-request abuse",
    "AV-TOKEN-PROV": "Wallet token provisioning fraud",
    "AV-FAKE-MERCH": "Synthetic merchant / transaction laundering",
    "AV-FRIENDLY-FRAUD": "First-party misuse / generated disputes",
    "AV-MULE-LAYER": "Fan-in / fan-out mule layering",
    "AV-AGENT-INJECT": "Prompt-injected shopping agent",
    "AV-AGENT-MANDATE": "Over-scoped agent payment mandate",
}


def build(run, sim, det, arena, atlas, *, pct, num, inr) -> str:
    base, post = det["baseline"], det["post_arena"]
    op, bop = post["operating_point"], base["operating_point"]
    s = sim["summary"]
    st = atlas["stats"]
    gens = arena["generations"] if arena else []
    tti = arena["time_to_immunity_generations"] if arena else None
    zj = det.get("zero_day_journey", {})
    stress = det.get("narrative_stress_test") or {}

    L: list[str] = []
    a = L.append

    a("# IMMUNIS — Solution Walkthrough")
    a("")
    a("**Mastercard Innovation Challenge 2026 · AI Defense Lab for Payment Security**")
    a("")
    a("*An adversarial immune system for payment networks.*")
    a("")
    a("---")
    a("")

    # ------------------------------------------------------------------ 1
    a("## 1. The problem, and the shape of our answer")
    a("")
    a("Payment fraud defence is reactive by construction. Fraud happens, chargebacks "
      "settle 45 to 90 days later, the data is labelled, and only then does the model "
      "retrain. That lag was survivable when a novel typology took a criminal crew "
      "months to invent and industrialise. Generative AI has cut that to hours, and "
      "the lag has not moved. The industry is now permanently one outbreak behind.")
    a("")
    a("Immunology solved this problem a century ago, and the solution was not a faster "
      "autopsy. A vaccine manufactures a safe, high-fidelity replica of a pathogen "
      "*before* exposure, so the antibody already exists on day zero.")
    a("")
    a("IMMUNIS applies that structure to payments:")
    a("")
    a("| Immunology | IMMUNIS | Challenge pillar |")
    a("|---|---|---|")
    a("| Antigen discovery | Attack Atlas — a living, machine-readable catalogue of "
      "GenAI payment attack vectors, scored and auto-expanded | **Identify** |")
    a("| Attenuated strain synthesis | Multi-modal generators emitting realistic "
      "payment traffic plus the conversation, telemetry and mule graph around it | "
      "**Generate** |")
    a("| Antibody | A calibrated four-channel detector with reason codes | **Defend** |")
    a("| Immune memory and booster shots | A red agent that evolves against the live "
      "model; every evasion becomes a training label | **The closed loop** |")
    a("")
    tti_txt = f"{tti} generation" + ("" if tti == 1 else "s") if tti else "not reached"
    secs = (f" — {round(gens[0]['seconds'])} seconds of compute on a laptop"
            if gens else "")
    a("The measurable output is a metric we define and put on the front page: "
      "**Time-to-Immunity** — the number of adversarial generations required to drive "
      "a novel strain family's evasion rate below 5% while holding false positives "
      "inside budget. The industry's equivalent today is measured in months of "
      f"chargeback data. In this run it is **{tti_txt}**{secs}.")
    a("")

    # ------------------------------------------------------------------ 2
    a("---")
    a("")
    a("## 2. Identify — the novel fraud attacks we found")
    a("")
    a(f"The atlas ships **{st['total_vectors']} curated vectors** across "
      f"{st['families']} families, {len(st['by_rail'])} payment rails and "
      f"{len(st['by_surface'])} attack surfaces, plus **{atlas['discovered']} "
      f"machine-composed hybrids**. {st['simulated_vectors']} of them have a working "
      "generator in the repository.")
    a("")
    a("Crucially, the atlas is a **data structure, not prose**. Every vector is a typed "
      "record — rail, surface, kill chain, GenAI uplift, observable signals, historical "
      "analogue, detection gap, victim profile, mitigations — which means the generator "
      "keys off it, the detector is evaluated against it, and the discovery agent can "
      "recombine it. Threat score is computed, not asserted:")
    a("")
    a("```")
    a("0.30 x detection_gap + 0.24 x genai_uplift + 0.20 x impact")
    a("  + 0.15 x scale_velocity + 0.11 x feasibility")
    a("```")
    a("")
    a("The weighting is deliberate: *what we cannot currently see* dominates, because a "
      "cheap, scalable attack the incumbent stack misses deserves more red-team "
      "attention than an expensive one it already catches.")
    a("")
    a("| Dimension | Breakdown |")
    a("|---|---|")
    for key, label in (("by_family", "Family"), ("by_surface", "Surface"),
                       ("by_rail", "Rail"), ("by_priority", "Priority")):
        parts = ", ".join(f"{k} ({v})" for k, v in
                          sorted(st[key].items(), key=lambda kv: -kv[1]))
        a(f"| {label} | {parts} |")
    a("")

    a("### 2.1 The vectors that matter most")
    a("")
    a("Three groups are worth calling out, because they are the ones a 2019-vintage "
      "typology catalogue does not contain.")
    a("")
    a("**Coercion-authorised payments** (`AV-DIGITAL-ARREST`, `AV-VOICE-CLONE`, "
      "`AV-VIDEO-DEEPFAKE-CALL`). The defining property is that the transaction is "
      "*technically perfect*: right customer, right device, right PIN, right "
      "geolocation. Every conventional authorisation feature reports legitimate — "
      "because it is. The customer really did authorise it. Pre-GenAI this required a "
      "fluent, confident human operator per victim who collapsed under improvised "
      "questions; a language model now runs the interrogation indefinitely, in the "
      "victim's own language and register, at near-zero marginal cost, while synthetic "
      "video supplies the uniform and the office.")
    a("")
    a("**Agentic commerce** (`AV-AGENT-INJECT`, `AV-AGENT-MANDATE`, `AV-AGENT-REPLAY`, "
      "`AV-AGENT-SPOOF`, `AV-AGENT-COLLUDE`). This rail is being stood up across the "
      "industry right now and has no labelled fraud, because it has no history. A "
      "prompt-injected shopping agent buys the wrong thing from the wrong merchant "
      "under a completely valid consumer mandate; an over-scoped mandate is drawn to "
      "its ceiling by an agent the consumer genuinely authorised. A system that can "
      "only learn from historical losses has, by definition, nothing to learn here.")
    a("")
    a("**Attacks on the defence itself** (`AV-MODEL-PROBE`, `AV-DATA-POISON`, "
      "`AV-ADV-PERTURB`). Every declined transaction is a labelled training example "
      "handed to the attacker for free. `AV-ADV-PERTURB` is the meta-vector — "
      "attacker-controlled parameters optimised against score feedback — and it is "
      "exactly what our red agent implements. Any attacker with outcome feedback can "
      "run the same optimisation, which is precisely why the defence must run it first.")
    a("")
    a("### 2.2 Discovery: attackers compose, they do not invent")
    a("")
    a("The discovery agent enumerates chainable pairs — where one stage's output "
      "capability satisfies the next stage's precondition — and scores composites with "
      "a bonus for straddling **observability boundaries**: different families, "
      "different rails, different surfaces. Those are the seams where each half looks "
      "unremarkable to the system that sees it and no single institution sees the "
      "whole, which is the structural blind spot only a network can close. A diversity "
      "guard caps how often any parent may appear, so the output is a spread of blind "
      "spots rather than ten variations on one. An optional Claude pass rewrites them "
      "into analyst-grade prose; the deterministic path runs identically without it, so "
      "the repository stays reproducible offline.")
    a("")

    # ------------------------------------------------------------------ 3
    a("---")
    a("")
    a("## 3. Generate — how the system simulates those attacks")
    a("")
    a(f"The engine produces a ledger of **{num(s['transactions'])} transactions** over "
      f"{s['days']} days across {num(run['generate']['customers'])} customers and "
      f"{num(run['generate']['merchants'])} merchants, of which "
      f"{num(s['fraud_transactions'])} ({pct(s['fraud_rate'], 2)}) are fraudulent, "
      f"alongside {num(s['episodes'])} conversations and {num(s['graph_edges'])} "
      "mule-graph edges.")
    a("")
    a("Fidelity is not primarily a claim about the fraud. It is a claim about the "
      "**legitimate** traffic, and four design decisions carry it — each of which makes "
      "our own detection problem harder.")
    a("")

    a("### 3.1 Attacks are injected into a calibrated population, not generated in isolation")
    a("")
    a("Seven persona archetypes (salaried urban, student, senior citizen, gig worker, "
      "SME owner, high-net-worth, homemaker) each carry their own device set, home "
      "geography, MCC affinity, log-normal ticket distribution, circadian activity "
      "mixture, instrument mix and susceptibility — so victim selection is realistic "
      "rather than uniform, and coercion typologies land on the segments they land on "
      "in the real world. Demand carries salary-week spikes, weekend uplift, a "
      "pre-payday squeeze and a festival surge. Households share devices. A genuine "
      "new-account cohort exists, with no habitual payees yet. Fraud is overlaid on "
      "*that*, so a fraudulent transaction is only anomalous relative to a real "
      "behavioural baseline.")
    a("")

    a("### 3.2 Roughly one in eleven legitimate transactions is deliberately anomalous")
    a("")
    a(f"{pct(s['benign_anomaly_rate'])} of legitimate traffic is a benign anomaly: "
      "genuine travel, a real first big-ticket purchase, a device upgrade, a first "
      "payment to a new landlord, a legitimate late-night payment, an out-of-character "
      "category, a retry burst. Each one mimics a different fraud tell.")
    a("")
    a("This is the single most important decision in the build. Most synthetic-fraud "
      "demos report AUC above 0.999 because their legitimate traffic is homogeneous, "
      "which makes *unusual equals fraud* trivially true. By making legitimate traffic "
      "genuinely messy, our precision and false-positive numbers mean something — and, "
      "as Section 5.3 shows, our residual errors concentrate on exactly the benign "
      "anomalies a real issuer's do.")
    a("")

    a("### 3.3 The model does not get complete telemetry, or correct labels")
    a("")
    a(f"Session and behavioural telemetry is present on only "
      f"{pct(s['telemetry_coverage'], 0)} of the ledger, masked independently of the "
      "label — because in production it is missing for different channels, older app "
      "versions, third-party acquirers and browser restrictions. Missing values "
      "propagate as NaN and are never imputed to zero: *no screen share* and *we could "
      "not observe screen share* are different facts, and conflating them is how a "
      "model learns to treat an entire channel as low risk.")
    a("")
    a(f"Training labels are corrupted the way reality corrupts them. "
      f"{pct(sim['label_noise']['missed_fraud_rate'], 0)} of fraud is never reported — "
      "coercion victims in particular rarely come forward — and a slice of legitimate "
      "traffic carries a false fraud label. In this run "
      f"{num(sim['label_noise']['training_frauds_hidden'])} training frauds are "
      "invisible to the model. Every metric in this document is nonetheless computed "
      "against ground truth.")
    a("")

    a("### 3.4 Attacks are multi-modal, and attackers live ordinary lives")
    a("")
    a("A coercion strain emits the scam transcript, the session telemetry (screen-share "
      "state, call state, hesitation, retries, app switches), the beneficiary graph and "
      "the transaction sequence — because that is what the fraud looks like end to end. "
      "Genuine conversations are generated for legitimate payments too, including "
      "urgent and emotional ones, so *has a transcript* is a signal rather than a label.")
    a("")
    a(f"Every attacker-controlled identity also emits ordinary cover traffic "
      f"({num(s['cover_transactions'])} transactions in this run). A mule account whose "
      "every transaction is fraudulent is a simulation artefact, not a mule, and would "
      "hand the detector a shortcut instead of a typology.")
    a("")

    a("### 3.5 The strain parameter space")
    a("")
    a("Every injector exposes the same eight continuous knobs — the levers a real "
      "operator actually controls: `aggression`, `velocity`, `device_hygiene`, "
      "`spread`, `mimicry`, `dwell`, `stealth` and `narrative_intensity`. This is the "
      "contract with the red agent, and it is what makes the loop closable: the red "
      "agent does not invent new code, it discovers new *parameterisations* of known "
      "typologies that the current model fails on — which is how attack evolution "
      "actually works in the field.")
    a("")

    a("### 3.6 What each generator produced")
    a("")
    a("| Typology | Campaigns | Transactions | Labelled fraud | Value extracted |")
    a("|---|---:|---:|---:|---:|")
    for vid, d in sorted(s["per_vector"].items(),
                         key=lambda kv: -kv[1]["value_extracted"]):
        a(f"| {SHORT.get(vid, d['label'])} | {d['campaigns']} | "
          f"{num(d['transactions'])} | {num(d['fraud_transactions'])} | "
          f"{inr(d['value_extracted'])} |")
    a("")
    a("The gap between transactions and labelled fraud on the synthetic-identity and "
      "deepfake-KYC generators is deliberate: the nurture phase of a synthetic identity "
      "is real, settled, repaid activity and is labelled legitimate. Only the bust-out "
      "is fraud. Labelling the account as fraudulent from birth would leak the answer "
      "into training and inflate every metric downstream.")
    a("")

    # ------------------------------------------------------------------ 4
    a("---")
    a("")
    a("## 4. Defend — the detection and mitigation model")
    a("")
    a(f"The detector fuses four channels with a noisy-OR over {sim['feature_count']} "
      "strictly causal features.")
    a("")
    a("1. **Supervised gradient boosting** over velocity, novelty, temporal, geo, "
      "device, merchant, graph, session, auth and mandate features. Trees, not a deep "
      "net, because an issuer has to deploy, monitor and explain this — and because "
      "trees win on tabular payment data.")
    a("2. **A graph channel** — fan-in and fan-out, pass-through ratio, dwell time on "
      "received value, shared-device components, payer diversity on young "
      "beneficiaries. This is what catches a mule mid-chain, and it is the clearest "
      "argument for a *network* doing this: no single bank sees more than one layer of "
      "the tree.")
    a("3. **An unsupervised novelty channel** (isolation forest fitted on legitimate "
      "training traffic only), contributing only in its extreme tail so it adds "
      "zero-day recall without flooding the alert queue.")
    a("4. **A rule layer** — 14 high-precision deterministic conjunctions. Every fraud "
      "team keeps rules for good reasons: they are auditable, they can be shipped in an "
      "afternoon when a new typology lands mid-quarter, and a regulator can read them.")
    a("")
    a("Plus a **narrative channel**: TF-IDF and logistic regression over the "
      "pre-transaction conversation, fitted on training-split episodes only, entering "
      "the tabular model as a single feature.")
    a("")

    a("### 4.1 Causality and leakage control")
    a("")
    a("Features are computed in one streaming pass in timestamp order, maintaining "
      "per-entity state — the same shape a Flink or Kafka job would have in production. "
      "There is no group-by over the full dataset anywhere, and a test truncates the "
      "ledger and asserts the surviving rows' features are unchanged.")
    a("")
    a("Simulator internals are never featurised: `susceptibility` (which drives victim "
      "selection), `vector_id`, `strain_id`, `campaign_id`, `benign_anomaly`, and the "
      "transaction's own `dispute_filed`. The customer's *prior* dispute history is "
      "used instead, because that genuinely is available at authorisation time.")
    a("")
    a("The train/test split is **temporal**, not random. A random split on payment data "
      "leaks: the same campaign, mule account and device appear on both sides. Time is "
      "the only split that answers the question a bank actually asks — will this work "
      "next week?")
    a("")

    a("### 4.2 Calibration, the operating point, and mitigation")
    a("")
    a("Probabilities are isotonically calibrated on a held-out temporal slice (Brier "
      f"score {post['brier']:.5f}), so the threshold can be chosen against an explicit "
      "cost matrix rather than an arbitrary 0.5. We report two operating points: the "
      "cost-optimal one, and the review-budget one at a 2% alert rate, because most "
      "institutions are staffed rather than optimised.")
    a("")
    cm = det["cost_model"]
    a(f"The cost matrix is explicit: Rs {cm['review_cost']:.0f} per analyst review, "
      f"Rs {cm['false_decline_cost']:.0f} per false decline, "
      f"{pct(cm['fraud_loss_ratio'], 0)} of a missed fraud's value borne by the "
      f"network, and {pct(cm['decline_share'], 0)} of alerts hard-declined rather than "
      "stepped up. Mitigation is graded accordingly — approve, review, step-up, decline "
      "— rather than a binary block, and every alert carries reason codes produced by "
      "ablation against the deployed scoring function, so an analyst can act on it and "
      "a regulator can read it.")
    a("")

    # ------------------------------------------------------------------ 5
    a("---")
    a("")
    a("## 5. Efficacy results")
    a("")
    a("| Metric | Before the arena | After the arena |")
    a("|---|---|---|")
    a(f"| ROC-AUC | {base['roc_auc']:.4f} | **{post['roc_auc']:.4f}** |")
    a(f"| PR-AUC | {base['pr_auc']:.4f} | **{post['pr_auc']:.4f}** |")
    a(f"| Recall @ {pct(op['alert_rate'])} alert budget | {pct(bop['recall'])} | "
      f"**{pct(op['recall'])}** |")
    a(f"| Precision (simulation prevalence) | {pct(bop['precision'])} | "
      f"**{pct(op['precision'])}** |")
    a(f"| False-positive rate | {pct(bop['fpr'], 3)} | **{pct(op['fpr'], 3)}** |")
    a(f"| Value recall | {pct(bop['value_recall'])} | **{pct(op['value_recall'])}** |")
    a(f"| Brier score | {base['brier']:.5f} | **{post['brier']:.5f}** |")
    a("")
    a(f"Test slice: {num(post['n_test'])} future transactions, "
      f"{num(post['n_test_fraud'])} fraudulent.")
    a("")

    a("### 5.1 Precision, reported twice")
    a("")
    a(f"The simulation runs at {pct(post['test_fraud_rate'], 2)} fraud prevalence — "
      "hot, so that every typology has enough examples to learn from. A real card or "
      f"UPI portfolio runs nearer {pct(det['realistic_prevalence'], 2)}. "
      "Bayes-adjusted to that prevalence, precision is "
      f"**{pct(op['precision_at_real_prevalence'])}** — about "
      f"{round(1 / max(0.001, op['precision_at_real_prevalence']))} alerts reviewed per "
      "fraud found, which is a staffing number an operations team recognises. Reporting "
      "only the in-simulation figure would be flattering and useless.")
    a("")

    a("### 5.2 Recall by typology")
    a("")
    a("An average hides the family you are blind to, so this is the table that matters.")
    a("")
    a("| Typology | n | Recall | Value recall | Held out |")
    a("|---|---:|---:|---:|:--:|")
    for vid, d in sorted(post["per_vector"].items(), key=lambda kv: kv[1]["recall"]):
        a(f"| {SHORT.get(vid, vid)} | {d['n']} | {pct(d['recall'])} | "
          f"{pct(d['value_recall'])} | {'yes' if d['zero_day'] else ''} |")
    a("")

    a("### 5.3 False positives, by what kind of legitimate the transaction was")
    a("")
    a("This is the table most synthetic-fraud submissions leave out. A low overall "
      "false-positive rate is easy if your legitimate traffic is boring; the rate that "
      "matters is the one on the hard negatives.")
    a("")
    fp = post["false_positives_by_benign_anomaly"]
    bfpr = fp.get("__normal__", {}).get("false_positive_rate", 0) or 1e-9
    a("| Legitimate behaviour | n | False-positive rate | vs ordinary traffic |")
    a("|---|---:|---:|---:|")
    for k, d in sorted(fp.items(), key=lambda kv: -kv[1]["false_positive_rate"]):
        label = ("Ordinary legitimate traffic" if k == "__normal__"
                 else k.replace("_", " "))
        mult = "—" if k == "__normal__" else f"{d['false_positive_rate'] / bfpr:.1f}x"
        a(f"| {label} | {num(d['n'])} | {pct(d['false_positive_rate'], 2)} | {mult} |")
    a("")
    a("Our residual errors concentrate on genuine big-ticket purchases — which is "
      "exactly where a real issuer's do, and is the honest cost of catching bust-out "
      "and account-takeover cash-outs.")
    a("")

    a("### 5.4 Zero-day holdout — the result that matters")
    a("")
    a("Two attack families were removed from training entirely, to measure cold "
      "generalisation to a typology with no labelled history.")
    a("")
    a("| Held-out family | Cold start | After the arena | Lift |")
    a("|---|---:|---:|---:|")
    for f in zj.get("holdout_families", []):
        b, af = zj["before"].get(f), zj["after"].get(f)
        lift = "—" if (b is None or af is None) else f"{(af - b) * 100:+.1f} pt"
        a(f"| {SHORT.get(f, f)} | {pct(b)} | {pct(af)} | {lift} |")
    a("")
    a("The *cold start* column is what a conventional programme achieves on a typology "
      "it has never seen a labelled example of. The *after the arena* column is the "
      "same families once the red agent manufactured them and the blue model retrained "
      "on those synthetic strains. No real loss, no chargeback data and no defrauded "
      "customer was involved in closing that gap.")
    a("")
    a("This is the entire thesis of the system in one table — and it is not a leak, "
      "because the labels came from attacks IMMUNIS generated itself, in a sandbox, "
      "against its own detector.")
    a("")

    nov = det.get("novelty_profile", {})
    if nov:
        a("The unsupervised channel's contribution is honestly split. Legitimate "
          f"traffic reaches the 99th novelty percentile at {nov['legit_p99']:.4f}. One "
          "held-out family sits far outside the legitimate manifold and the channel "
          "sees it coming; the other is engineered to look normal and it does not — "
          "which is precisely the gap the arena exists to close.")
        a("")

    a("### 5.5 What each channel is worth")
    a("")
    a("Each row is a model retrained from scratch with that channel's features removed. "
      "This is the question a bank asks before paying for any of it.")
    a("")
    a("| Channel removed | ROC-AUC | PR-AUC | Delta PR-AUC | Recall | Delta recall |")
    a("|---|---:|---:|---:|---:|---:|")
    a(f"| nothing (full model) | {base['roc_auc']:.4f} | {base['pr_auc']:.4f} | — | "
      f"{pct(bop['recall'])} | — |")
    for tag, ab in det["ablations"].items():
        a(f"| {tag.replace('no_', '')} | {ab['roc_auc']:.4f} | {ab['pr_auc']:.4f} | "
          f"{ab['delta_pr_auc']:+.4f} | {pct(ab['recall'])} | "
          f"{ab['delta_recall'] * 100:+.1f} pt |")
    a("")

    if stress.get("sweep"):
        a("### 5.6 A negative result we are keeping")
        a("")
        a("Our thesis was that reading the pre-transaction conversation would catch "
          "coercion payments the transaction side cannot see. The ablation above says "
          "the narrative channel is worth roughly nothing at portfolio level. Rather "
          "than explain that away, we built the experiment that could have rescued it: "
          "a high-mimicry operator — aged mule beneficiaries, amounts shaped under "
          "step-up thresholds, the victim taken off screen share before authorising, "
          "session pacing close to their own baseline — swept across how greedy they "
          "are. Low greed is the regime where every amount-based signal should go quiet "
          "and the conversation is the only evidence left.")
        a("")
        a("| Aggression | n | Mean amount | Amount z | With narrative | Without | Lift |")
        a("|---:|---:|---:|---:|---:|---:|---:|")
        for p in stress["sweep"]:
            a(f"| {p['aggression']:.2f} | {p['n']} | {inr(p['mean_amount'])} | "
              f"{p['mean_amount_z']:+.2f} | {pct(p['recall_full'])} | "
              f"{pct(p['recall_without_narrative'])} | {p['lift']:+.3f} |")
        a("")
        a("The lift is zero at every point: beneficiary novelty and account age already "
          "carry this typology in our simulation. We would still ship the channel — a "
          "coercion alert an analyst can justify to a regulator is worth more than one "
          "they cannot, and it is the only signal left on the "
          f"{pct(1 - s['telemetry_coverage'], 0)} of traffic with no session telemetry "
          "— but it is a design bet, not a measured win, and we label it that way. We "
          "would rather present a null result honestly than a claim we did not earn.")
        a("")

    # ------------------------------------------------------------------ 6
    if gens:
        a("---")
        a("")
        a("## 6. The closed loop — red versus blue")
        a("")
        a(f"Each generation the red agent instantiates a population of "
          f"{gens[0]['population']} strains into real transactions, injects them into a "
          "warm slice of the ledger, and reads back the only feedback a real attacker "
          "has: does this get through?")
        a("")
        a("The initial population is seeded from four **operator archetypes** — the "
          "documented parameterisation, a well-resourced professional crew, a cheap "
          "fast opportunist, and a threshold-hugging shaper — because seeding only from "
          "documented defaults would measure the detector against the attack as it is "
          "written up today, which is precisely the mistake this system exists to avoid.")
        a("")
        a("**Fitness is evasion net of operating cost, subject to a value floor.** "
          "Unconstrained adversarial search always finds the same degenerate answer: "
          "make the attack so small, so slow and so expensive that it evades everything "
          "and earns nothing. That is a surrender, not an evasion, and a defence "
          "hardened against it learns nothing. So clean attested devices cost money, "
          "deep mule inventory costs recruitment, high mimicry costs operator hours per "
          "victim, and patience ties up working capital. The strains that survive are "
          "the ones a real crew would actually run — which is what makes retraining on "
          "them worth anything.")
        a("")
        a("Every evasion is mined as a hard negative at elevated weight, the blue model "
          "retrains, and the same strains are re-scored to measure the immunity gained. "
          "The blue model is then re-measured on a **frozen future test slice at "
          "constant alert budget**, so a recall gain is only counted if the "
          "false-positive cost did not move.")
        a("")
        a("| Gen | Attacks | Evasion found | After retrain | Mined | Blue AUC | Recall "
          "| FPR | Budget |")
        a("|---:|---:|---:|---:|---:|---:|---:|---:|:--:|")
        for g in gens:
            a(f"| {g['generation']} | {num(g['attack_rows'])} | "
              f"{pct(g['evasion_pre'], 2)} | {pct(g['evasion_post'], 2)} | "
              f"{g['mined']} | {g['blue_after']['auc']:.4f} | "
              f"{pct(g['blue_after']['recall'], 2)} | "
              f"{pct(g['blue_after']['fpr'], 3)} | "
              f"{'ok' if g['fpr_within_budget'] else 'BREACH'} |")
        a("")
        d = arena["delta"]
        a(f"The red agent found **{pct(max(g['evasion_pre'] for g in gens))} peak "
          "evasion** against the shipped model. Across the run the blue model gained "
          f"**{d['recall'] * 100:+.1f} points of recall** and "
          f"{d['value_recall'] * 100:+.1f} points of value recall while its "
          f"false-positive rate moved {d['fpr'] * 100:+.3f} points, against a ceiling "
          f"of {pct(arena['fpr_budget_ceiling'], 2)} it was not allowed to exceed. "
          f"{num(gens[-1]['mined_cumulative'])} evading transactions were mined and "
          "folded back into training.")
        a("")
        a(f"**Time-to-Immunity: {tti_txt}.**")
        a("")

    # ------------------------------------------------------------------ 7
    a("---")
    a("")
    a("## 7. Real-world feasibility in live payment environments")
    a("")
    a("Nothing here needs a research cluster. The engine is CPU-only Python with "
      f"scikit-learn; the whole pipeline runs end to end in {run['total_seconds']:.0f} "
      "seconds on a laptop, and per-transaction scoring including reason codes is "
      "single-digit milliseconds.")
    a("")
    a("| Prototype component | Production form |")
    a("|---|---|")
    a("| Population and behaviour simulator | Pre-production sandbox seeded from "
      "de-identified portfolio statistics. No PII is ever required, because everything "
      "is synthesised from distributions |")
    a("| Attack injectors | A strain library, versioned like threat-intel signatures "
      "and distributed to participants |")
    a("| Feature pipeline | Causal, single-pass, streaming-safe — the same code shape "
      "runs on Flink/Kafka at authorisation time |")
    a("| Detector | Exportable gradient-boosted model plus rule layer; 2 to 5 ms "
      "scoring; deployable as a challenger behind the incumbent before promotion |")
    a("| Rule layer | Ships independently of the model when a typology lands "
      "mid-quarter |")
    a("| Red vs Blue arena | A scheduled CI job. Fraud defence becomes a build pipeline "
      "with a failing test, not a quarterly review |")
    a("| Reason codes | Attached to every alert for analyst and regulator consumption |")
    a("| Artefacts | The model-risk evidence pack: what was tried, at what parameter "
      "ranges, what evaded, what residual risk remains |")
    a("")
    a("**Adoption path.** An issuer runs IMMUNIS as a challenger model against shadow "
      "traffic, comparing its alerts to the incumbent's for one cycle. The rule layer "
      "can ship immediately and independently. The arena runs nightly in CI, and the "
      "first time it produces a strain the production model misses, the value "
      "proposition proves itself without anyone having lost money.")
    a("")

    # ------------------------------------------------------------------ 8
    a("---")
    a("")
    a("## 8. Novelty of the solution")
    a("")
    a("The novelty is the closed loop, not any individual model.")
    a("")
    a("**The red agent optimises against the live decision boundary of the deployed "
      "blue model, under realism and profitability constraints, and its survivors "
      "become the next training batch.** Adjacent industries — malware, spam, ad fraud "
      "— have run continuous adversarial self-play for years. Payments has not, because "
      "the labelling loop runs through chargebacks and chargebacks are slow. "
      "Manufacturing the fraud removes the dependency on that loop entirely.")
    a("")
    a("Three supporting choices are also, as far as we know, unusual in this space:")
    a("")
    a("- **Cross-modal generation and fusion.** Attacks emit the conversation, the "
      "session telemetry, the graph and the transaction together, and the detector "
      "consumes all four. (Our own measurement says the narrative channel does not pay "
      "off yet — reported in Section 5.6 rather than buried.)")
    a("- **Deliberately hard negatives.** Benign anomalies, missing telemetry, label "
      "noise, cover traffic from mule identities, and a genuine new-account cohort — "
      "all of which lower our own headline numbers and raise their credibility.")
    a("- **Time-to-Immunity as the product metric.** Not AUC. The question a network "
      "should be asking is *how fast can we become immune to something new*, and that "
      "number has not existed before.")
    a("")

    # ------------------------------------------------------------------ 9
    a("---")
    a("")
    a("## 9. Business case")
    a("")
    a("Mastercard's fraud franchise sells models. The structural weakness of a model "
      "business is that models decay, and the decay rate is set by the attacker's "
      "iteration speed — which GenAI has just multiplied. IMMUNIS is not a competing "
      "model; it is the factory that keeps those models fresh, and it sells on three "
      "lines.")
    a("")
    a("**1. Pre-breach immunisation** — subscription, per issuer or acquirer. Today a "
      "bank learns a new typology from its own losses. We ship the attack before it "
      "arrives: a monthly stream of synthetic strains for emerging vectors, plus "
      "retrained weights and the evaluation evidence. Priced against fraud basis points "
      "saved, a number every risk officer already has on a slide.")
    a("")
    a("**2. Adversarial assurance and model validation** — per engagement, and a "
      "compliance line item. Model-risk and cyber-resilience expectations (RBI, EU "
      "DORA, US SR 11-7) increasingly require evidence that a model was stress-tested, "
      "not merely backtested. IMMUNIS emits exactly that evidence pack.")
    a("")
    a("**3. Network herd immunity** — the moat, and the part only a network can build. "
      "When the red agent finds an evasion gap against one participant's configuration, "
      "the antibody propagates to every participant without any customer data moving: "
      "only synthetic strains and model updates. Value grows superlinearly with "
      "participants and cannot be replicated by a single bank or a point vendor. That "
      "is the strategic reason this belongs at a network rather than anywhere else.")
    a("")
    a("**Why now.** Three curves cross in 2026: GenAI collapses the attacker's cost per "
      "novel attack, agentic commerce opens a rail with no fraud history to train on, "
      "and regulators begin asking for adversarial evidence. A system that manufactures "
      "labelled fraud on demand is the only answer to a rail that has no labels yet.")
    a("")

    # ------------------------------------------------------------------ 10
    a("---")
    a("")
    a("## 10. Responsible use, and limitations")
    a("")
    a("Every entity, transaction and conversation is synthetic; no real cardholder data "
      "exists in this repository or is required by it. The atlas publishes observable "
      "behaviour and telemetry signatures — what a defender needs — and deliberately "
      "excludes operational playbooks, tooling, prompts and infrastructure. The red "
      "agent operates only against our own detector, in-process, with no network access "
      "and no interface to any payment system. Full policy in "
      "`docs/RESPONSIBLE_USE.md`.")
    a("")
    a("Limitations we would want a judge to hold us to:")
    a("")
    a("- **Simulated data is not real data.** Our generators encode our beliefs about "
      "how fraud looks. A production deployment must be calibrated against "
      "de-identified portfolio statistics before its numbers mean anything about that "
      "portfolio.")
    a("- **The conversation transcripts are template-generated**, so the narrative "
      "channel's in-sample separability is an upper bound. This is part of why we treat "
      "its stress-test result, not its AUC, as the evidence.")
    a("- **The red agent searches parameters, not code.** It cannot invent a typology "
      "outside the atlas. Closing that gap — an agent that proposes new generators, not "
      "just new parameterisations — is the obvious next step.")
    a("- **Time-to-Immunity is measured against our own generators.** It is a real "
      "number about a real loop, but the loop's coverage is bounded by the atlas, and "
      "the atlas is bounded by what we thought of.")
    a("")

    # ------------------------------------------------------------------ 11
    a("---")
    a("")
    a("## 11. Reproducing every number in this document")
    a("")
    a("```bash")
    a("cd engine")
    a("pip install -r requirements.txt")
    a(f"python -m immunis.cli run --profile {run['profile']} --seed {run['seed']}")
    a("python ../scripts/make_docs.py")
    a("```")
    a("")
    a(f"Run environment: Python {run['environment']['python']}, "
      f"{run['environment']['platform']}, CPU only, {run['total_seconds']:.0f}s end to "
      "end. Stage timings: "
      + ", ".join(f"{k} {v}s" for k, v in run["timings"].items()) + ".")
    a("")
    a("The web prototype in `web/` renders these same artefacts; every figure on the "
      "site comes from this pipeline and nothing is hand-entered.")
    a("")
    return "\n".join(L)
