# Responsible use

This repository is a **defensive** research artefact for testing payment fraud detection against emerging attacks. Deliberate lines were drawn in its design to prioritize safety and responsible disclosure, and they are documented here rather than left implicit.

## No real data, ever

Every customer, merchant, device, account, transaction and conversation in this
repository is synthetic, generated from distributions. No real cardholder data,
no real merchant data, no scraped personal information and no production
transaction feed is used anywhere. There is no code path that reads one.

The population is synthesised from *statistics* — persona archetypes, ticket
distributions, circadian mixtures, geography weights — which is also how we
propose it works in production: an institution supplies distribution parameters,
never records.

## Threat intelligence, not a playbook

The Attack Atlas describes, for each vector:

- the **observable behaviour** — what the attack looks like from the outside,
- the **telemetry signature** — the specific signals a defender can compute,
- the **kill chain at strategy altitude** — the stages a fraud team needs in
  order to design controls,
- **mitigations**.

It deliberately does **not** contain: operational instructions, tooling,
prompts, scripts, infrastructure guidance, service providers, evasion recipes,
or anything that lowers the cost of running an attack for someone who wants to.

That line is the standard one in published fraud typology work, and it is drawn
where it is because the two audiences need different things. A defender needs to
know that a coercion payment shows up as *screen share active during a
first-ever transfer to a beneficiary created minutes earlier*. An attacker gains
nothing from that sentence they did not already know. The reverse — how to
actually run the campaign — is what we exclude.

The `attacks/` modules generate synthetic *telemetry patterns*: rows in a table
with plausible amounts, timings and graph structure. They contain no capability
to interact with any real payment system, no network code, and no ability to
touch anything outside the process.

## The red agent is sandboxed by construction

The evolutionary evader optimises against **our own detector, on our own
synthetic ledger, inside one Python process**. It has:

- no network access,
- no ability to submit anything to any payment rail,
- no interface to any system other than the in-memory model it was handed.

Its search space is eight bounded parameters of our own generators. It cannot
invent new attack code; it discovers parameterisations of typologies we already
documented. That is a deliberate limit on capability, not an implementation
shortcut.

## What we would not build

Some things are omitted on purpose, and would stay omitted in a production
version:

- **No voice, face or document synthesis.** Several atlas vectors depend on
  deepfake media. We model their *downstream payment signature* — session
  duration, beneficiary novelty, approval-chain anomalies — and never generate
  synthetic media of anyone.
- **No real persona targeting.** Victim selection operates on synthetic
  susceptibility attributes inside the simulation. Nothing profiles a real
  person or population.
- **No transferable evasion artefacts.** The mined evasions are feature vectors
  against our detector. They are training data for our model, not a portable
  bypass for anyone else's.

## Deployment guardrails

If this were operated at a payment network, three controls travel with it:

1. **Sandbox isolation.** The generator and red agent run in a pre-production
   environment with no route to authorisation systems, enforced at the network
   layer rather than by convention.
2. **Strain library access control.** Generated strains are threat-intel
   material. They go to participating institutions' fraud functions under the
   same handling as any typology alert, not into a public repository.
3. **Human review of discovered vectors.** The discovery agent proposes
   composites automatically. A fraud strategy team reviews them before they
   enter the strain library — both for plausibility and to catch anything that
   should not be written down at all.

## Dual-use, stated plainly

Any system that models attacks is dual-use. The reason to build this one is
that the attacker's side of the asymmetry has already been automated: GenAI
made novel payment fraud cheap to invent and cheap to run at scale. The
defender's side has not been. A defence that can only learn from losses it has
already taken is structurally one step behind an adversary that iterates in
hours.

The judgement here is that publishing *observable signatures and a defensive
methodology* moves the balance toward defenders, and that withholding it does
not slow down anyone who is already running these attacks. Where a detail would
help an attacker more than a defender, it is not in this repository.

## Reporting

If you believe something in this repository crosses the line described above,
please open an issue describing the concern. We will remove or rewrite rather
than argue the boundary.
