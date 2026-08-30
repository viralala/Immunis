"""The IMMUNIS Attack Atlas — 42 GenAI-era payment fraud vectors.

Scope note (see docs/RESPONSIBLE_USE.md): every entry describes the *observable
behaviour and telemetry signature* of an attack — what a defender can see and
model. Entries deliberately do not contain operational playbooks, tooling,
prompts or infrastructure. The kill chains are written at the altitude a fraud
strategy team uses to design controls, which is exactly the altitude the
simulator needs and well below the altitude an attacker would need.
"""

from __future__ import annotations

from .schema import AttackVector as V, Rail as R, Status as St, Surface as S

# ---------------------------------------------------------------------------
# A. Social engineering / authorised push payment (APP) fraud
#    The defining property: the transaction is technically perfect. Right
#    customer, right device, right credential, right geo. Every conventional
#    authorisation feature says "legitimate".
# ---------------------------------------------------------------------------

_SOCIAL = [
    V(
        id="AV-DIGITAL-ARREST",
        name="Coercion-authorised payment (\"digital arrest\")",
        family="Social engineering / APP",
        rails=(R.UPI_P2P, R.REMITTANCE),
        surface=S.AUTHORISATION,
        summary=(
            "Victim is held in a sustained impersonated-authority video/voice call and "
            "coerced into transferring funds to a 'verification' account. Generative "
            "video and voice make the impersonation persuasive; an LLM sustains a "
            "multi-hour interrogation script that adapts to the victim's objections."
        ),
        genai_uplift=5,
        detection_gap=5,
        impact=5,
        feasibility=4,
        scale_velocity=4,
        uplift_note=(
            "Pre-GenAI this required a fluent, confident human operator per victim and "
            "collapsed under improvised questions. An LLM runs the interrogation "
            "indefinitely, in the victim's own language and register, at ~zero marginal "
            "cost per victim, while synthetic video supplies the uniform and the office."
        ),
        kill_chain=(
            "Target selection from breached or scraped personal data",
            "Inbound contact impersonating law enforcement or a telecom regulator",
            "Sustained isolation: victim kept on a live call, told not to contact anyone",
            "Escalation to a 'verification transfer' framed as temporary and reversible",
            "Victim authorises the payment themselves on their own device",
            "Immediate layering through a mule chain within minutes of receipt",
        ),
        observable_signals=(
            "unusually long session with screen-share or call active during payment",
            "first-ever transfer to this beneficiary, created minutes before the payment",
            "transfer amount far above the customer's own historical p95",
            "abnormal hesitation and retry pattern during entry (coerced, not habitual)",
            "beneficiary account age measured in days with high fan-in",
            "sequence of escalating transfers within a single session window",
            "payment initiated outside the customer's normal circadian window",
        ),
        historical_analogue="Courier/CBI impersonation scams; IRS callback fraud",
        victim_profile="Senior citizens, first-generation digital users, students abroad",
        mitigations=(
            "Cross-modal detection: fuse in-session context (call/screen-share state) "
            "with the transaction",
            "Cooling-off and named-beneficiary confirmation for first-time high-value payees",
            "Beneficiary-side velocity and account-age gating at the receiving bank",
        ),
        status=St.SIMULATED,
        injector="digital_arrest",
    ),
    V(
        id="AV-VOICE-CLONE",
        name="Cloned-voice relative-in-distress / executive request",
        family="Social engineering / APP",
        rails=(R.UPI_P2P, R.CARD_CNP, R.REMITTANCE),
        surface=S.AUTHORISATION,
        summary=(
            "A few seconds of public audio is enough to clone a voice. The victim "
            "receives a call from a familiar voice requesting an urgent transfer, "
            "typically framed as an accident, arrest, or a confidential deal."
        ),
        genai_uplift=5,
        detection_gap=4,
        impact=4,
        feasibility=5,
        scale_velocity=4,
        uplift_note=(
            "Voice cloning moved from studio-grade to consumer-grade; the constraint is "
            "no longer the audio, it is the target list."
        ),
        kill_chain=(
            "Voice sample harvested from public media",
            "Relationship graph inferred from social profiles",
            "Urgent inbound call with a plausible, verifiable-sounding pretext",
            "Payment requested to a 'friend's' account to avoid name mismatch checks",
            "Rapid dispersal after receipt",
        ),
        observable_signals=(
            "new beneficiary with a name unrelated to any prior payee",
            "amount at or just under a step-up threshold",
            "compressed decision time between beneficiary creation and payment",
            "device and geo normal — only the payee and amount are anomalous",
        ),
        historical_analogue="Grandparent scam; classic BEC wire request",
        victim_profile="Parents of students abroad, finance staff in SMEs",
        mitigations=(
            "Out-of-band verification prompts on first payment to a new payee",
            "Payee-name-matching (confirmation of payee) at the network layer",
            "Family-designated 'safe word' controls in the issuer app",
        ),
        status=St.SIMULATED,
        injector="voice_clone",
    ),
    V(
        id="AV-ROMANCE-LLM",
        name="Persistent LLM romance / investment grooming (pig butchering)",
        family="Social engineering / APP",
        rails=(R.UPI_P2P, R.REMITTANCE, R.WALLET),
        surface=S.AUTHORISATION,
        summary=(
            "A long-horizon relationship is maintained by a language model across "
            "hundreds of targets simultaneously, culminating in escalating deposits "
            "into a fake trading platform that shows fabricated gains."
        ),
        genai_uplift=5,
        detection_gap=5,
        impact=5,
        feasibility=4,
        scale_velocity=5,
        uplift_note=(
            "The economics invert completely: the historical bottleneck was operator "
            "hours per victim over months. One model now sustains thousands of "
            "conversations with consistent persona memory."
        ),
        kill_chain=(
            "Broad-net contact across dating and messaging platforms",
            "Weeks of relationship building with consistent persona memory",
            "Introduction of a 'proven' investment opportunity",
            "Small initial deposit permitted to withdraw, building trust",
            "Escalating deposits; withdrawal blocked behind fabricated tax or fee demands",
        ),
        observable_signals=(
            "escalating transfer ladder to the same or rotating beneficiaries over weeks",
            "beneficiaries clustering into a single receiving community in the graph",
            "customer's savings-account drawdown pattern inverting",
            "new-to-customer merchant categories (crypto on-ramp, forex) appearing late",
        ),
        historical_analogue="Advance-fee fraud; boiler-room investment scams",
        victim_profile="Isolated adults 35-65, recently divorced or bereaved",
        mitigations=(
            "Longitudinal drawdown-pattern monitoring rather than per-transaction scoring",
            "Graph clustering of beneficiary communities across the portfolio",
            "Intervention prompts on repeat transfers to crypto on-ramps",
        ),
    ),
    V(
        id="AV-INVOICE-BEC",
        name="GenAI business email compromise / invoice redirection",
        family="Social engineering / APP",
        rails=(R.REMITTANCE, R.UPI_P2P),
        surface=S.AUTHORISATION,
        summary=(
            "Supplier correspondence is mimicked with correct house style, thread "
            "history and terminology, and banking details are changed on an otherwise "
            "genuine invoice at the moment of payment."
        ),
        genai_uplift=4,
        detection_gap=4,
        impact=5,
        feasibility=4,
        scale_velocity=3,
        uplift_note=(
            "The old tell was language: bad grammar, wrong register. That tell is gone, "
            "and thread-aware generation reproduces a supplier's exact phrasing."
        ),
        kill_chain=(
            "Compromise or spoof of a supplier mailbox",
            "Observation of a live invoice thread and payment cadence",
            "Banking-detail change introduced at the natural payment moment",
            "Funds received into a company-named mule account",
        ),
        observable_signals=(
            "known supplier relationship paying to a first-seen account number",
            "beneficiary bank/IFSC change on a recurring payment relationship",
            "payment amount consistent with history but destination novel",
            "beneficiary company registered within the last 90 days",
        ),
        historical_analogue="CEO fraud; mandate fraud",
        victim_profile="SME finance teams, procurement functions",
        mitigations=(
            "Bank-detail change verification workflow independent of email",
            "Confirmation-of-payee on corporate rails",
            "Supplier-relationship memory in the corporate banking risk model",
        ),
    ),
    V(
        id="AV-JOB-TASK-SCAM",
        name="Task-based job scam with escalating deposits",
        family="Social engineering / APP",
        rails=(R.UPI_P2P, R.WALLET),
        surface=S.AUTHORISATION,
        summary=(
            "Victims are recruited into a fake micro-task job, paid small genuine "
            "commissions, then required to deposit progressively larger 'task capital' "
            "to unlock higher-paying tasks."
        ),
        genai_uplift=4,
        detection_gap=4,
        impact=3,
        feasibility=5,
        scale_velocity=5,
        uplift_note=(
            "LLM handlers run thousands of recruit conversations and the fake task "
            "platform itself is generated, localised and re-skinned in hours."
        ),
        kill_chain=(
            "Mass recruitment via messaging platforms with a plausible brand",
            "Genuine small payouts to establish credibility",
            "Deposit requirement introduced and escalated",
            "Withdrawal blocked; further deposits demanded to 'release' balance",
        ),
        observable_signals=(
            "alternating small credits and larger debits with the same counterparty set",
            "ratio of outbound to inbound value degrading over successive cycles",
            "counterparty accounts shared across many unrelated customers",
            "young account age on the receiving side with extreme fan-in",
        ),
        historical_analogue="Ponzi recruitment; reshipping mule schemes",
        victim_profile="Students, gig workers, homemakers seeking part-time income",
        mitigations=(
            "Detect the credit-then-larger-debit oscillation at the customer level",
            "Portfolio-wide counterparty reuse detection",
            "In-app warnings on transfers to counterparties flagged by other customers",
        ),
    ),
    V(
        id="AV-KYC-REVERIFY",
        name="Synthetic bank re-KYC urgency lure",
        family="Social engineering / APP",
        rails=(R.UPI_P2P, R.CARD_CNP),
        surface=S.AUTHENTICATION,
        summary=(
            "A convincing replica of the issuer's own communication and app UI drives "
            "the victim to 'complete re-KYC before account freeze', harvesting "
            "credentials and a live OTP in the process."
        ),
        genai_uplift=4,
        detection_gap=3,
        impact=3,
        feasibility=5,
        scale_velocity=5,
        uplift_note=(
            "Pixel-accurate app clones and localised copy in a dozen Indian languages "
            "are now generated per campaign rather than per year."
        ),
        kill_chain=(
            "Mass SMS/WhatsApp distribution impersonating the issuer",
            "Victim lands on a cloned onboarding flow",
            "Credential and OTP harvested in real time",
            "Immediate session use before OTP expiry",
        ),
        observable_signals=(
            "authentication from an unseen device within seconds of an OTP issued for "
            "a different channel",
            "OTP consumed from a network path inconsistent with the issuing session",
            "burst of similar first-time logins across unrelated customers",
        ),
        historical_analogue="Classic phishing; vishing re-KYC calls",
        victim_profile="Broad retail base, skewing to lower digital literacy",
        mitigations=(
            "Bind OTP to the originating session/device rather than the customer",
            "Cross-customer campaign detection on landing-page fingerprints",
            "Number-agnostic in-app-only verification for KYC events",
        ),
    ),
    V(
        id="AV-VIDEO-DEEPFAKE-CALL",
        name="Live deepfake video-call approval",
        family="Social engineering / APP",
        rails=(R.REMITTANCE, R.UPI_P2P),
        surface=S.AUTHORISATION,
        summary=(
            "The 'verify by video call' control — introduced precisely to defeat email "
            "and voice fraud — is defeated by a real-time synthetic participant on the "
            "call, sometimes multiple synthetic colleagues at once."
        ),
        genai_uplift=5,
        detection_gap=5,
        impact=5,
        feasibility=3,
        scale_velocity=2,
        uplift_note=(
            "Real-time face and voice synthesis at call quality turns the strongest "
            "human verification control into an attack surface."
        ),
        kill_chain=(
            "Reconnaissance of the target organisation's approval hierarchy",
            "Scheduling of an urgent, confidential video meeting",
            "Synthetic participants present for approval",
            "Payment executed through the normal, fully-authorised channel",
        ),
        observable_signals=(
            "high-value payment approved outside the normal approval chain sequence",
            "approval timestamp clustering inside a single short meeting window",
            "beneficiary novel to the corporate relationship",
            "urgency and confidentiality flags in the payment memo field",
        ),
        historical_analogue="Executive impersonation wire fraud",
        victim_profile="Corporate treasury and finance approvers",
        mitigations=(
            "Structural controls (dual approval on separate channels) rather than "
            "perceptual controls",
            "Beneficiary allow-listing for high-value corporate payments",
            "Liveness challenge protocols for video approvals",
        ),
    ),
]

# ---------------------------------------------------------------------------
# B. Authentication and session attacks
# ---------------------------------------------------------------------------

_AUTH = [
    V(
        id="AV-AITM-OTP",
        name="Real-time adversary-in-the-middle OTP relay",
        family="Authentication",
        rails=(R.CARD_CNP, R.UPI_P2M, R.WALLET),
        surface=S.AUTHENTICATION,
        summary=(
            "A reverse-proxy phishing surface relays the victim's credentials and "
            "one-time code to the genuine site in real time, capturing the resulting "
            "authenticated session and defeating OTP entirely."
        ),
        genai_uplift=4,
        detection_gap=4,
        impact=4,
        feasibility=4,
        scale_velocity=5,
        uplift_note=(
            "Generative tooling collapses the cost of building and localising a "
            "convincing, brand-accurate relay surface, and of writing the lure copy "
            "that drives traffic to it."
        ),
        kill_chain=(
            "Victim driven to a proxying surface that mirrors the genuine site",
            "Credentials and one-time code relayed live to the real service",
            "Authenticated session token captured",
            "Session used immediately from attacker infrastructure",
            "High-value transaction pushed inside the stolen session",
        ),
        observable_signals=(
            "session continuity break: device fingerprint changes mid-session",
            "impossible-travel velocity between authentication and transaction",
            "OTP latency far below or above the customer's habitual response time",
            "transaction within seconds of authentication on a new device",
            "absence of the customer's usual navigation path before checkout",
        ),
        historical_analogue="Man-in-the-browser trojans; session hijacking",
        victim_profile="Broad; concentrates on high-balance retail customers",
        mitigations=(
            "Phishing-resistant authentication (FIDO2/passkeys) with origin binding",
            "Device-binding continuity checks between auth and authorisation",
            "Session-anomaly features fed directly into the authorisation model",
        ),
        status=St.SIMULATED,
        injector="aitm_otp",
    ),
    V(
        id="AV-BIO-CLONE",
        name="Behavioural-biometric cloning",
        family="Authentication",
        rails=(R.CARD_CNP, R.UPI_P2M, R.WALLET),
        surface=S.AUTHENTICATION,
        summary=(
            "Passive behavioural authentication — typing cadence, swipe dynamics, "
            "navigation rhythm, hold pressure — is defeated by a model trained on "
            "captured interaction telemetry to reproduce the victim's motor signature."
        ),
        genai_uplift=5,
        detection_gap=5,
        impact=4,
        feasibility=3,
        scale_velocity=3,
        uplift_note=(
            "Behavioural biometrics were considered un-forgeable because they are "
            "involuntary. Sequence models learn them from a modest telemetry sample, "
            "turning the most trusted silent control into a false negative generator."
        ),
        kill_chain=(
            "Interaction telemetry captured from a compromised session or app clone",
            "Motor-signature model fitted to the victim's cadence",
            "Replay of synthesised interaction during an attacker-driven session",
            "Behavioural score passes; step-up is never triggered",
            "Transaction executes with the silent control fully satisfied",
        ),
        observable_signals=(
            "behavioural score suspiciously *close* to the customer's mean — real humans "
            "vary more than their model does",
            "variance collapse in inter-keystroke intervals across a session",
            "perfect behavioural match combined with novel device or network path",
            "absence of natural correction events (backspaces, mis-taps, scroll overshoot)",
        ),
        historical_analogue="Fingerprint spoofing; replay attacks on static biometrics",
        victim_profile="Customers of institutions relying on passive behavioural auth",
        mitigations=(
            "Score the *variance* of the behavioural signal, not only its centre",
            "Combine behavioural signals with challenge-response, never alone",
            "Treat an unnaturally perfect behavioural match as itself anomalous",
        ),
        status=St.SIMULATED,
        injector="bio_clone",
        notes="Held out of training in the zero-day evaluation.",
    ),
    V(
        id="AV-SIM-SWAP-ORCH",
        name="LLM-orchestrated SIM-swap social engineering",
        family="Authentication",
        rails=(R.UPI_P2P, R.CARD_CNP),
        surface=S.AUTHENTICATION,
        summary=(
            "Telecom retail and support staff are socially engineered into porting the "
            "victim's number, after which SMS-based authentication belongs to the "
            "attacker."
        ),
        genai_uplift=3,
        detection_gap=3,
        impact=5,
        feasibility=3,
        scale_velocity=3,
        uplift_note=(
            "Scripted, adaptive persuasion and synthetic supporting documents raise "
            "success rates against trained staff."
        ),
        kill_chain=(
            "Identity data assembled from breaches and public sources",
            "Port-out or replacement-SIM request supported by synthetic documents",
            "Victim's number active on attacker hardware",
            "Authentication resets across every SMS-bound financial account",
        ),
        observable_signals=(
            "SIM-change or port-out event immediately preceding credential reset",
            "device change plus SIM change within the same short window",
            "beneficiary additions clustered within hours of the port",
        ),
        historical_analogue="SIM swap; number porting fraud",
        victim_profile="High-net-worth and crypto-holding customers",
        mitigations=(
            "Consume telecom SIM-change signals directly in the risk model",
            "Mandatory cooling-off on beneficiary addition post SIM change",
            "Migrate away from SMS as an authentication factor",
        ),
    ),
    V(
        id="AV-PUSH-FATIGUE",
        name="Adaptive MFA push fatigue",
        family="Authentication",
        rails=(R.UPI_P2M, R.WALLET, R.CARD_CNP),
        surface=S.AUTHENTICATION,
        summary=(
            "Approval prompts are issued repeatedly, timed by a model to the victim's "
            "inferred inattention windows and paired with a spoofed support contact "
            "that explains the prompts away."
        ),
        genai_uplift=3,
        detection_gap=3,
        impact=3,
        feasibility=4,
        scale_velocity=4,
        uplift_note=(
            "Timing and pretext are optimised per victim rather than blasted uniformly."
        ),
        kill_chain=(
            "Valid credentials obtained from a prior breach",
            "Repeated authentication attempts generating approval prompts",
            "Timing tuned to late-night or high-distraction windows",
            "Spoofed support contact frames the prompts as routine",
            "One accidental approval yields a full session",
        ),
        observable_signals=(
            "high denied-prompt count preceding a single approval",
            "prompt approval latency inconsistent with the customer's baseline",
            "approval during the customer's usual sleep window",
        ),
        historical_analogue="MFA bombing on enterprise SSO",
        victim_profile="Broad retail; anyone with push-based approval",
        mitigations=(
            "Number-matching and rate-limited prompts",
            "Automatic lockout after N denials",
            "Score prompt-denial history as an authorisation feature",
        ),
    ),
    V(
        id="AV-VOICE-AUTH-BYPASS",
        name="Synthetic speech against voice-print IVR authentication",
        family="Authentication",
        rails=(R.CARD_CNP, R.UPI_P2P),
        surface=S.AUTHENTICATION,
        summary=(
            "Bank IVR and contact-centre voice-print authentication is satisfied by "
            "generated speech matching the enrolled voice-print."
        ),
        genai_uplift=5,
        detection_gap=4,
        impact=4,
        feasibility=4,
        scale_velocity=3,
        uplift_note=(
            "Voice-print enrolment was a differentiator for contact-centre security; "
            "synthesis quality has now overtaken most deployed liveness checks."
        ),
        kill_chain=(
            "Voice sample harvested from public or social audio",
            "Voice-print match produced for the IVR challenge",
            "Contact-centre agent performs account changes on the 'verified' caller",
            "Beneficiary or contact-detail changes enable subsequent transfers",
        ),
        observable_signals=(
            "account-detail changes originating from IVR/agent channel followed by "
            "immediate high-value movement",
            "call audio anomalies: absent room tone, unnatural prosody stability",
            "caller ID inconsistent with the registered number",
        ),
        historical_analogue="Contact-centre impersonation",
        victim_profile="Customers of banks with voice-print IVR",
        mitigations=(
            "Synthetic-speech liveness detection on the call leg",
            "Treat IVR-originated profile changes as elevated risk downstream",
            "Multi-factor confirmation for beneficiary changes regardless of channel",
        ),
    ),
    V(
        id="AV-SESSION-REPLAY",
        name="Session-token replay with fingerprint spoofing",
        family="Authentication",
        rails=(R.CARD_CNP, R.WALLET, R.AGENTIC),
        surface=S.AUTHENTICATION,
        summary=(
            "Stolen session tokens are replayed from infrastructure that reproduces the "
            "victim's device fingerprint, network characteristics and header order "
            "closely enough to satisfy device-recognition controls."
        ),
        genai_uplift=3,
        detection_gap=4,
        impact=4,
        feasibility=4,
        scale_velocity=4,
        uplift_note=(
            "Fingerprint reconstruction from captured telemetry is now an automated, "
            "generated artefact rather than a manual reverse-engineering exercise."
        ),
        kill_chain=(
            "Token and fingerprint telemetry exfiltrated from the victim's session",
            "Environment reconstructed to match the fingerprint",
            "Token replayed; device recognition passes",
            "Transactions executed as a recognised device",
        ),
        observable_signals=(
            "identical device fingerprint appearing from a distant network path",
            "concurrent sessions on the same fingerprint",
            "subtle entropy mismatch: fingerprint too stable across attribute changes",
            "no organic pre-transaction browsing behaviour",
        ),
        historical_analogue="Cookie theft; pass-the-cookie attacks",
        victim_profile="E-commerce and wallet users with long-lived sessions",
        mitigations=(
            "Token binding to a hardware-backed key",
            "Concurrent-session detection at the network level",
            "Short session lifetimes for payment-capable scopes",
        ),
    ),
]

# ---------------------------------------------------------------------------
# C. Identity and onboarding
# ---------------------------------------------------------------------------

_IDENTITY = [
    V(
        id="AV-SYNTH-ID",
        name="Synthetic identity manufacture and credit bust-out",
        family="Identity / onboarding",
        rails=(R.CARD_CNP, R.CARD_CP, R.WALLET),
        surface=S.ONBOARDING,
        summary=(
            "A fabricated identity — real-looking but belonging to nobody — is nurtured "
            "with genuine small transactions and prompt repayment for months, until "
            "credit limits are large enough to draw down entirely and abandon."
        ),
        genai_uplift=4,
        detection_gap=5,
        impact=5,
        feasibility=3,
        scale_velocity=4,
        uplift_note=(
            "Generative models produce coherent identity backstories, supporting "
            "documents and, critically, *plausible transaction behaviour* during the "
            "nurture phase, so the account looks like a real thin-file customer."
        ),
        kill_chain=(
            "Identity assembled from partially real and partially fabricated attributes",
            "Onboarding at a thin-file-friendly institution",
            "Months of small, well-behaved, promptly-repaid activity",
            "Credit limits raised on demonstrated good behaviour",
            "Coordinated maximum drawdown across all lines, then abandonment",
        ),
        observable_signals=(
            "thin identity footprint: no long-lived cross-institution history",
            "behaviour statistically *too* well-behaved during nurture",
            "utilisation step-change from low and stable to near-limit within days",
            "shared device, address or contact attributes across many 'unrelated' identities",
            "cash-equivalent and high-liquidity MCC concentration at bust-out",
        ),
        historical_analogue="Classic bust-out fraud; Frankenstein identities",
        victim_profile="Issuers and lenders rather than consumers — no victim disputes it",
        mitigations=(
            "Cross-institution identity-footprint scoring at onboarding",
            "Monitor utilisation *acceleration*, not just level",
            "Entity resolution across device/address/contact graphs",
        ),
        status=St.SIMULATED,
        injector="synth_id",
    ),
    V(
        id="AV-DEEPFAKE-KYC",
        name="Deepfake and injection attacks on video KYC",
        family="Identity / onboarding",
        rails=(R.UPI_P2P, R.WALLET, R.CARD_CNP),
        surface=S.ONBOARDING,
        summary=(
            "Remote identity verification is defeated either by presenting a synthetic "
            "face to the camera or by injecting a synthetic video stream directly into "
            "the capture pipeline, bypassing the camera altogether."
        ),
        genai_uplift=5,
        detection_gap=4,
        impact=4,
        feasibility=4,
        scale_velocity=5,
        uplift_note=(
            "Face swapping now runs in real time on commodity hardware and passes "
            "most active-liveness challenges; injection attacks skip the physical "
            "channel that liveness checks assume exists."
        ),
        kill_chain=(
            "Identity documents assembled or forged",
            "Synthetic face rendered in real time to match the document",
            "Liveness challenge satisfied, or the capture pipeline bypassed entirely",
            "Account opened and immediately used as a receiving/mule account",
        ),
        observable_signals=(
            "capture-pipeline integrity anomalies (virtual camera, frame timing regularity)",
            "account moves to high fan-in receiving behaviour within days of opening",
            "onboarding device shared with previously flagged accounts",
            "document and selfie both novel with no historical footprint",
        ),
        historical_analogue="Photo-of-a-photo presentation attacks",
        victim_profile="Institutions and, downstream, every victim paying into the mule",
        mitigations=(
            "Injection-attack detection at the capture layer, not just liveness",
            "Post-onboarding behavioural gating for the first 30 days",
            "Device and network reuse detection across onboarding events",
        ),
        status=St.SIMULATED,
        injector="deepfake_kyc",
    ),
    V(
        id="AV-DOC-FORGE",
        name="Generative document forgery for underwriting",
        family="Identity / onboarding",
        rails=(R.CARD_CNP, R.WALLET),
        surface=S.ONBOARDING,
        summary=(
            "Bank statements, payslips, GST returns and utility bills are generated with "
            "internally consistent arithmetic, correct templates and plausible "
            "transaction histories, defeating manual and template-matching review."
        ),
        genai_uplift=5,
        detection_gap=4,
        impact=4,
        feasibility=5,
        scale_velocity=5,
        uplift_note=(
            "The historical defence was internal inconsistency — totals that did not "
            "add up, fonts that did not match. Generated documents are arithmetically "
            "self-consistent by construction."
        ),
        kill_chain=(
            "Target lender's document requirements enumerated",
            "Consistent synthetic financial history generated across all documents",
            "Application submitted with a coherent income and expenditure story",
            "Limit granted on fabricated capacity",
        ),
        observable_signals=(
            "document metadata and rendering artefacts inconsistent with issuing systems",
            "income claimed inconsistent with observed transactional inflow",
            "statement transaction distributions that are statistically too regular",
            "reuse of document structure across unrelated applications",
        ),
        historical_analogue="Photoshopped payslips; income inflation",
        victim_profile="Lenders and credit-issuing institutions",
        mitigations=(
            "Move to source-verified data (account aggregator / open banking) over documents",
            "Statistical forensics on statement distributions",
            "Cross-application document-structure fingerprinting",
        ),
    ),
    V(
        id="AV-MULE-RECRUIT",
        name="Industrialised mule recruitment and account farming",
        family="Identity / onboarding",
        rails=(R.UPI_P2P, R.WALLET),
        surface=S.ONBOARDING,
        summary=(
            "Willing and semi-witting account holders are recruited at scale through "
            "generated job and rental offers, producing a renewable inventory of "
            "genuine, KYC-clean accounts to receive fraud proceeds."
        ),
        genai_uplift=4,
        detection_gap=4,
        impact=4,
        feasibility=5,
        scale_velocity=5,
        uplift_note=(
            "Recruitment conversations, localisation and vetting are fully automated; "
            "mule supply stops being the constraint on every other attack in this atlas."
        ),
        kill_chain=(
            "Mass recruitment offers distributed across job and messaging platforms",
            "Recruits onboarded and paid a small fee per account",
            "Account credentials and devices controlled centrally",
            "Accounts rotated into receiving duty and burned after detection",
        ),
        observable_signals=(
            "dormant accounts activating simultaneously into receiving behaviour",
            "many accounts sharing device, IP range or app-install fingerprint",
            "balance held for minutes, never days",
            "recruit demographics clustering (young, low prior balance, same region)",
        ),
        historical_analogue="Money mule recruitment via classified ads",
        victim_profile="Recruits (who carry legal liability) and downstream victims",
        mitigations=(
            "Behavioural mule scoring on receiving accounts, not just sending",
            "Device-graph clustering across the onboarding population",
            "Dormancy-to-activity transition monitoring",
        ),
    ),
]

# ---------------------------------------------------------------------------
# D. Card and rail exploitation
# ---------------------------------------------------------------------------

_RAIL = [
    V(
        id="AV-BIN-ENUM",
        name="Distributed BIN enumeration with humanised cadence",
        family="Card / rail exploitation",
        rails=(R.CARD_CNP,),
        surface=S.AUTHORISATION,
        summary=(
            "Card numbers, expiry dates and CVVs are validated by micro-authorisations "
            "spread across many low-friction merchants, with request timing, basket "
            "composition and browsing behaviour generated to look human."
        ),
        genai_uplift=4,
        detection_gap=3,
        impact=3,
        feasibility=5,
        scale_velocity=5,
        uplift_note=(
            "Velocity rules catch machine cadence. Generated traffic now carries "
            "human-plausible inter-arrival times, session paths and basket variety, "
            "which is precisely what those rules were keyed on."
        ),
        kill_chain=(
            "Candidate card numbers derived from a target BIN range",
            "Validation attempts distributed across many small merchants",
            "Timing and session behaviour humanised to defeat velocity rules",
            "Validated cards separated for resale or immediate cash-out",
        ),
        observable_signals=(
            "elevated decline-to-approval ratio concentrated in a BIN range",
            "many distinct PANs sharing a device, fingerprint or network segment",
            "micro-amount authorisations at merchants with no basket coherence",
            "the same merchant seeing an unusual PAN-diversity spike",
        ),
        historical_analogue="Card testing; enumeration attacks",
        victim_profile="Issuers, and the small merchants used as testing grounds",
        mitigations=(
            "Network-level BIN-range anomaly detection across acquirers",
            "PAN-diversity-per-device limits at the merchant",
            "Adaptive step-up on low-value authorisations from unfamiliar devices",
        ),
        status=St.SIMULATED,
        injector="bin_enum",
    ),
    V(
        id="AV-TOKEN-PROV",
        name="Token provisioning fraud (push provisioning to attacker wallet)",
        family="Card / rail exploitation",
        rails=(R.WALLET, R.CARD_CP),
        surface=S.AUTHENTICATION,
        summary=(
            "A stolen card is provisioned into the attacker's mobile wallet by "
            "satisfying the issuer's identification-and-verification step, converting a "
            "compromised number into a contactless credential with high approval rates."
        ),
        genai_uplift=3,
        detection_gap=4,
        impact=4,
        feasibility=4,
        scale_velocity=4,
        uplift_note=(
            "The verification step is often a call-centre or OTP interaction — exactly "
            "the surfaces that synthetic voice and real-time relay now defeat."
        ),
        kill_chain=(
            "Card credentials obtained from a prior compromise",
            "Provisioning requested into an attacker-controlled wallet",
            "Identification-and-verification step defeated via OTP relay or voice",
            "Token used at high-value, low-friction contactless acceptance",
        ),
        observable_signals=(
            "provisioning event followed within minutes by first token use",
            "token device and cardholder device inconsistent",
            "provisioning geo distant from the card's transaction history",
            "spend profile after provisioning bearing no resemblance to card history",
        ),
        historical_analogue="Apple Pay / wallet provisioning fraud waves",
        victim_profile="Cardholders; loss usually lands on the issuer",
        mitigations=(
            "Risk-based provisioning decisions with device-history checks",
            "Cooling-off between provisioning and first high-value token use",
            "Treat provisioning as a first-class risk event in the model",
        ),
        status=St.SIMULATED,
        injector="token_prov",
    ),
    V(
        id="AV-CNP-STUFF",
        name="Credential stuffing into card-not-present checkout",
        family="Card / rail exploitation",
        rails=(R.CARD_CNP, R.WALLET),
        surface=S.AUTHENTICATION,
        summary=(
            "Breached credential pairs are replayed across merchant accounts to reach "
            "stored payment instruments, then spent on resellable goods or gift cards."
        ),
        genai_uplift=3,
        detection_gap=3,
        impact=3,
        feasibility=5,
        scale_velocity=5,
        uplift_note=(
            "Automation is not new; what is new is generated session behaviour and "
            "CAPTCHA-resistant interaction that defeats bot-management heuristics."
        ),
        kill_chain=(
            "Credential lists replayed against merchant login surfaces",
            "Successful accounts triaged for stored cards and balances",
            "Shipping or delivery details changed to a controlled address",
            "High-liquidity goods purchased and resold",
        ),
        observable_signals=(
            "login success from a device never seen on the account",
            "shipping-address change immediately preceding checkout",
            "gift-card and high-resale-value MCC concentration",
            "account-takeover cluster across merchants sharing a credential breach",
        ),
        historical_analogue="Account takeover; card-on-file abuse",
        victim_profile="Consumers with reused passwords; merchants absorb chargebacks",
        mitigations=(
            "Device-reputation and address-change velocity features in checkout scoring",
            "Step-up when a stored instrument is used from a new device",
            "Credential-breach intelligence integrated into login risk",
        ),
    ),
    V(
        id="AV-QR-SWAP",
        name="QR tampering and collect-request abuse",
        family="Card / rail exploitation",
        rails=(R.UPI_P2M, R.UPI_P2P),
        surface=S.AUTHORISATION,
        summary=(
            "Static merchant QR codes are physically overlaid with an attacker's code, "
            "or victims are induced to approve an inbound collect request they believe "
            "is an incoming payment."
        ),
        genai_uplift=3,
        detection_gap=3,
        impact=3,
        feasibility=5,
        scale_velocity=4,
        uplift_note=(
            "Generated merchant branding, signage and support scripts make overlays and "
            "collect pretexts far more convincing and cheap to produce per location."
        ),
        kill_chain=(
            "Attacker QR overlaid at a physical merchant, or a collect request issued",
            "Payer believes they are paying the merchant or receiving funds",
            "Funds land in an attacker-controlled VPA",
            "Immediate onward layering",
        ),
        observable_signals=(
            "payments to a VPA at a merchant location with no acquiring relationship",
            "many distinct payers to a young VPA within a tight geographic radius",
            "collect requests approved by payers with no prior relationship to the payee",
            "merchant's own settlement volume dropping while footfall is unchanged",
        ),
        historical_analogue="Parking-meter QR fraud; payment-request phishing",
        victim_profile="Consumers at physical merchants; small merchants lose revenue",
        mitigations=(
            "Merchant-VPA geospatial consistency checks",
            "Friction and clearer intent language on inbound collect requests",
            "Payer-diversity-per-young-VPA monitoring",
        ),
        status=St.SIMULATED,
        injector="qr_swap",
    ),
    V(
        id="AV-RECURRING-ABUSE",
        name="Subscription and free-trial farming",
        family="Card / rail exploitation",
        rails=(R.CARD_CNP, R.WALLET),
        surface=S.AUTHORISATION,
        summary=(
            "Validated or synthetic card credentials are cycled through free trials and "
            "low-value recurring authorisations, monetising service access rather than "
            "cash and staying below every value-based control."
        ),
        genai_uplift=4,
        detection_gap=4,
        impact=2,
        feasibility=5,
        scale_velocity=5,
        uplift_note=(
            "Generated identities, emails and sign-up flows make each cycle "
            "indistinguishable from a genuine new customer, at unlimited volume."
        ),
        kill_chain=(
            "Large pools of validated or synthetic credentials assembled",
            "Trials opened across many services with generated identities",
            "Value extracted as service access or resold accounts",
            "Credentials rotated before recurring billing fails",
        ),
        observable_signals=(
            "many trial sign-ups sharing device, network or behavioural fingerprint",
            "abnormally uniform sign-up-to-cancellation intervals",
            "cards with no history other than trial authorisations",
            "email and identity attributes with zero prior footprint",
        ),
        historical_analogue="Promo abuse; trial farming",
        victim_profile="Subscription merchants and their acquirers",
        mitigations=(
            "Identity-footprint scoring at sign-up rather than at billing",
            "Device and behavioural clustering across the trial population",
            "Treat zero-history instruments as a distinct risk segment",
        ),
    ),
    V(
        id="AV-3DS-EXEMPT",
        name="Systematic exploitation of authentication exemptions",
        family="Card / rail exploitation",
        rails=(R.CARD_CNP, R.UPI_P2M),
        surface=S.AUTHORISATION,
        summary=(
            "Attack volume is deliberately shaped to sit inside low-value, recurring, "
            "trusted-beneficiary or transaction-risk-analysis exemptions so that "
            "step-up authentication is never invoked."
        ),
        genai_uplift=4,
        detection_gap=4,
        impact=3,
        feasibility=4,
        scale_velocity=4,
        uplift_note=(
            "An optimiser can learn the exemption boundary from decline feedback and "
            "shape every subsequent transaction to sit just inside it."
        ),
        kill_chain=(
            "Exemption thresholds inferred from observed step-up behaviour",
            "Transaction amounts and channels shaped to stay inside exemptions",
            "Cumulative value extracted through many exempt transactions",
            "Counters reset by rotating merchants and instruments",
        ),
        observable_signals=(
            "amount distribution with an unnatural spike just below a known threshold",
            "cumulative daily value high while every individual transaction is low",
            "exemption-eligible channel share far above the customer's baseline",
            "merchant rotation timed to cumulative-counter resets",
        ),
        historical_analogue="Structuring; smurfing adapted to authentication rules",
        victim_profile="Issuers operating threshold-based exemption policies",
        mitigations=(
            "Cumulative rather than per-transaction exemption counters",
            "Detect threshold-hugging amount distributions explicitly",
            "Randomised step-up sampling to break boundary inference",
        ),
    ),
    V(
        id="AV-CROSS-RAIL-HOP",
        name="Cross-rail laundering hop",
        family="Card / rail exploitation",
        rails=(R.CARD_CNP, R.WALLET, R.UPI_P2P, R.REMITTANCE),
        surface=S.SETTLEMENT,
        summary=(
            "Value is moved deliberately across rails — card to wallet to account to "
            "off-ramp — because each rail's monitoring sees only its own leg and no "
            "single institution observes the full chain."
        ),
        genai_uplift=3,
        detection_gap=5,
        impact=4,
        feasibility=4,
        scale_velocity=4,
        uplift_note=(
            "Route planning across rails, jurisdictions and thresholds is an "
            "optimisation problem that automation solves far better than a human."
        ),
        kill_chain=(
            "Funds enter on one rail from an unrelated predicate fraud",
            "Immediate hop to a second rail with different monitoring",
            "Aggregation and further hops through wallet or prepaid products",
            "Exit via an off-ramp with weak source-of-funds controls",
        ),
        observable_signals=(
            "instrument-to-instrument transfers with near-zero dwell time",
            "value preserved across hops minus a consistent fee margin",
            "rail changes at every hop with no economic rationale",
            "terminal hop into a high-liquidity or off-ramp category",
        ),
        historical_analogue="Layering in classical money laundering",
        victim_profile="The network as a whole; no single institution sees it",
        mitigations=(
            "Network-level cross-rail linkage — a natural role for a payment network",
            "Dwell-time features on received funds",
            "Shared typology intelligence between rails",
        ),
    ),
]

# ---------------------------------------------------------------------------
# E. Merchant and acquiring side
# ---------------------------------------------------------------------------

_MERCHANT = [
    V(
        id="AV-FAKE-MERCH",
        name="Synthetic merchant onboarding for transaction laundering",
        family="Merchant / acquiring",
        rails=(R.CARD_CNP, R.UPI_P2M),
        surface=S.SETTLEMENT,
        summary=(
            "A fully-generated business — website, catalogue, reviews, incorporation "
            "documents, social presence — is onboarded by an acquirer and used to "
            "process transactions for goods that do not exist or are not permitted."
        ),
        genai_uplift=5,
        detection_gap=4,
        impact=4,
        feasibility=4,
        scale_velocity=5,
        uplift_note=(
            "Merchant due diligence leans heavily on 'does this business look real'. "
            "Generating an entire plausible commercial footprint is now hours of work."
        ),
        kill_chain=(
            "Complete synthetic business footprint generated",
            "Acquirer onboarding passed on documentary and web presence checks",
            "Genuine-looking low-value volume processed to build history",
            "Volume ramped sharply, then settlement drawn and entity abandoned",
        ),
        observable_signals=(
            "web and business footprint created entirely within a short window",
            "transaction mix statistically unlike the declared MCC's population",
            "customer base with no repeat purchasers",
            "sharp volume ramp shortly after reserve release",
            "refund and chargeback profile inconsistent with the stated business",
        ),
        historical_analogue="Bust-out merchants; transaction laundering",
        victim_profile="Acquirers, who carry the settlement exposure",
        mitigations=(
            "Behavioural merchant scoring post-onboarding, not just KYB at onboarding",
            "MCC-population conformance testing on transaction mix",
            "Dynamic reserve policy tied to volume acceleration",
        ),
        status=St.SIMULATED,
        injector="fake_merchant",
    ),
    V(
        id="AV-MERCH-COLLUDE",
        name="Collusive merchant bust-out",
        family="Merchant / acquiring",
        rails=(R.CARD_CNP, R.CARD_CP, R.UPI_P2M),
        surface=S.SETTLEMENT,
        summary=(
            "A genuine merchant with real history colludes to process a burst of "
            "fraudulent or fabricated transactions immediately before disappearing, "
            "leaving the acquirer with the chargebacks."
        ),
        genai_uplift=2,
        detection_gap=3,
        impact=5,
        feasibility=3,
        scale_velocity=2,
        uplift_note=(
            "GenAI mainly helps fabricate the supporting order and delivery evidence "
            "that delays chargeback resolution past the point of recovery."
        ),
        kill_chain=(
            "Legitimate merchant history established over months",
            "Sudden volume and ticket-size expansion",
            "Settlement drawn as rapidly as terms allow",
            "Entity ceases operating before chargebacks land",
        ),
        observable_signals=(
            "ticket-size and volume step-change against the merchant's own baseline",
            "shift in card-geography mix away from the historical customer base",
            "settlement acceleration requests",
            "delivery evidence that is uniform across disputes",
        ),
        historical_analogue="Merchant bust-out",
        victim_profile="Acquirers and the cardholders whose cards are used",
        mitigations=(
            "Merchant-level change-point detection on volume and ticket size",
            "Rolling-reserve policy responsive to behavioural change",
            "Evidence-similarity detection across dispute representments",
        ),
    ),
    V(
        id="AV-REFUND-ABUSE",
        name="Refund and return manipulation at scale",
        family="Merchant / acquiring",
        rails=(R.CARD_CNP, R.UPI_P2M),
        surface=S.DISPUTE,
        summary=(
            "Refund policies are exploited systematically — generated proof of damage, "
            "non-delivery claims, and coordinated returns — often as a service sold to "
            "consumers rather than by the fraudster directly."
        ),
        genai_uplift=5,
        detection_gap=4,
        impact=3,
        feasibility=5,
        scale_velocity=5,
        uplift_note=(
            "Fabricated photographic evidence and persuasive, policy-aware complaint "
            "narratives are generated per claim, defeating manual adjudication."
        ),
        kill_chain=(
            "Merchant refund policy and adjudication behaviour probed",
            "Claims filed with generated supporting evidence",
            "Refund granted; goods retained",
            "Method packaged and resold to other consumers",
        ),
        observable_signals=(
            "refund rate per customer far above the merchant's population",
            "claim narratives with high structural similarity across unrelated customers",
            "image evidence with generation artefacts or reused provenance",
            "refund requests clustering on high-value, easily-resold categories",
        ),
        historical_analogue="Return fraud; refund-as-a-service",
        victim_profile="Merchants, then consumers through tightened policies",
        mitigations=(
            "Customer-level refund propensity scoring across merchants",
            "Evidence provenance and similarity analysis",
            "Network-level sharing of abusive refund patterns",
        ),
    ),
    V(
        id="AV-FRIENDLY-FRAUD",
        name="Generated dispute narratives (first-party misuse)",
        family="Merchant / acquiring",
        rails=(R.CARD_CNP, R.CARD_CP),
        surface=S.DISPUTE,
        summary=(
            "Cardholders dispute genuine transactions using generated narratives tuned "
            "to the exact chargeback reason code most likely to succeed, industrialising "
            "what used to be an occasional, clumsy consumer behaviour."
        ),
        genai_uplift=5,
        detection_gap=4,
        impact=3,
        feasibility=5,
        scale_velocity=5,
        uplift_note=(
            "Reason-code selection and narrative construction used to require expertise. "
            "It is now a prompt, and the resulting text is more coherent than most "
            "genuine disputes."
        ),
        kill_chain=(
            "Genuine purchase completed and goods received",
            "Reason code selected for maximum success probability",
            "Dispute narrative generated to match that code's evidentiary standard",
            "Chargeback pursued; merchant representment often abandoned on cost",
        ),
        observable_signals=(
            "dispute rate per cardholder far above portfolio norms",
            "disputed transactions carrying strong device and behavioural continuity",
            "narrative similarity across a cardholder's disputes and across the portfolio",
            "delivery, session and geolocation evidence contradicting the claim",
        ),
        historical_analogue="Friendly fraud; chargeback abuse",
        victim_profile="Merchants primarily; issuers through dispute cost",
        mitigations=(
            "Attach device/session continuity evidence automatically to representments",
            "Cardholder-level dispute-propensity scoring",
            "Narrative-similarity clustering at the network level",
        ),
        status=St.SIMULATED,
        injector="friendly_fraud",
    ),
    V(
        id="AV-MCC-MISCODE",
        name="Merchant category miscoding to evade controls",
        family="Merchant / acquiring",
        rails=(R.CARD_CNP, R.UPI_P2M),
        surface=S.SETTLEMENT,
        summary=(
            "Transactions are submitted under a benign merchant category code so that "
            "issuer controls, spending restrictions and elevated scrutiny attached to "
            "the true category never engage."
        ),
        genai_uplift=2,
        detection_gap=4,
        impact=3,
        feasibility=4,
        scale_velocity=3,
        uplift_note=(
            "Modest GenAI uplift, but it pairs with synthetic-merchant onboarding to "
            "make the declared category impossible to falsify manually at scale."
        ),
        kill_chain=(
            "True business category identified as restricted or high-scrutiny",
            "Benign category declared at onboarding or via a payment facilitator",
            "Volume processed under the benign code",
            "Controls keyed to the true category never fire",
        ),
        observable_signals=(
            "transaction timing, ticket and geography distributions inconsistent with "
            "the declared MCC's population",
            "cardholder overlap with known high-risk category merchants",
            "refund and chargeback patterns typical of a different category",
        ),
        historical_analogue="MCC laundering; aggregator misuse",
        victim_profile="Issuers whose controls are silently bypassed",
        mitigations=(
            "MCC conformance scoring against population distributions",
            "Payment-facilitator sub-merchant transparency requirements",
            "Behavioural category inference independent of declared MCC",
        ),
    ),
    V(
        id="AV-TERMINAL-CLONE",
        name="Compromised soft-POS acceptance",
        family="Merchant / acquiring",
        rails=(R.CARD_CP, R.UPI_P2M),
        surface=S.AUTHORISATION,
        summary=(
            "Phone-as-terminal acceptance apps are cloned or repackaged so that a "
            "genuine-looking acceptance experience captures credentials or routes the "
            "payment to an attacker-controlled merchant."
        ),
        genai_uplift=3,
        detection_gap=4,
        impact=3,
        feasibility=3,
        scale_velocity=3,
        uplift_note=(
            "Repackaged app clones with correct branding are cheap to produce and "
            "localise, and soft-POS removes the physical tamper-evidence of hardware."
        ),
        kill_chain=(
            "Acceptance app cloned or repackaged",
            "Distributed to small merchants as an official-looking build",
            "Contactless credentials captured during genuine sales",
            "Credentials monetised on other rails",
        ),
        observable_signals=(
            "acceptance-app integrity attestation failures",
            "merchant terminal fingerprint changing without a registered device change",
            "cards later appearing in fraud clusters sharing one common acceptance point",
            "unusual proportion of read-then-declined interactions",
        ),
        historical_analogue="ATM skimming; POS malware",
        victim_profile="Small merchants and their customers",
        mitigations=(
            "Mandatory app attestation for soft-POS acceptance",
            "Common-point-of-purchase analytics at the network level",
            "Terminal-fingerprint change monitoring",
        ),
    ),
]

# ---------------------------------------------------------------------------
# F. Money movement and laundering structure
# ---------------------------------------------------------------------------

_LAUNDER = [
    V(
        id="AV-MULE-LAYER",
        name="Fan-in / fan-out mule layering",
        family="Money movement",
        rails=(R.UPI_P2P, R.WALLET),
        surface=S.SETTLEMENT,
        summary=(
            "Proceeds are received by a first-layer mule and dispersed within minutes "
            "across a widening tree of accounts, with hop counts, amounts and timing "
            "chosen to stay under every per-account reporting and velocity threshold."
        ),
        genai_uplift=4,
        detection_gap=4,
        impact=5,
        feasibility=4,
        scale_velocity=5,
        uplift_note=(
            "Route and split optimisation against known thresholds is an automated "
            "planning problem; the structures produced are far less regular — and "
            "therefore far harder to rule-match — than hand-built ones."
        ),
        kill_chain=(
            "Proceeds land in a first-layer receiving account",
            "Split into multiple onward transfers within minutes",
            "Successive layers widen the tree and cross institutions",
            "Terminal accounts cash out via ATM, merchant purchase or off-ramp",
        ),
        observable_signals=(
            "pass-through ratio near 1.0 with dwell time in minutes",
            "in-degree and out-degree spiking simultaneously on a young account",
            "amount splits summing to the received value minus a small retained fee",
            "graph community with high internal density and no external economic activity",
            "balance never held overnight",
        ),
        historical_analogue="Smurfing; layering",
        victim_profile="Upstream fraud victims; institutions carry AML exposure",
        mitigations=(
            "Graph features (fan-in/out, pass-through ratio, community risk) in real time",
            "Cross-institution beneficiary intelligence at the network layer",
            "Hold periods on first-time high-value credits to young accounts",
        ),
        status=St.SIMULATED,
        injector="mule_layer",
    ),
    V(
        id="AV-SMURF-REMIT",
        name="Structured cross-border remittance smurfing",
        family="Money movement",
        rails=(R.REMITTANCE,),
        surface=S.SETTLEMENT,
        summary=(
            "Large sums are fragmented across many senders, corridors and providers, "
            "each transfer sitting below reporting thresholds and inside a plausible "
            "remittance narrative."
        ),
        genai_uplift=3,
        detection_gap=4,
        impact=4,
        feasibility=3,
        scale_velocity=3,
        uplift_note=(
            "Plausible purpose narratives and sender/beneficiary relationship stories "
            "are generated per transfer, defeating narrative-based review."
        ),
        kill_chain=(
            "Sender network assembled across providers and corridors",
            "Value fragmented below thresholds",
            "Transfers spaced to avoid aggregation windows",
            "Consolidation at the destination",
        ),
        observable_signals=(
            "many unrelated senders converging on a small beneficiary set",
            "amounts clustering just below reporting thresholds",
            "corridor mix inconsistent with any sender's profile",
            "purpose-of-transfer narratives with high structural similarity",
        ),
        historical_analogue="Hawala-style structuring; threshold avoidance",
        victim_profile="Financial institutions and regulators",
        mitigations=(
            "Beneficiary-side aggregation across providers",
            "Threshold-hugging distribution detection",
            "Narrative-similarity analysis on stated purposes",
        ),
    ),
    V(
        id="AV-P2P-PASSTHROUGH",
        name="Rapid P2P pass-through chains",
        family="Money movement",
        rails=(R.UPI_P2P,),
        surface=S.SETTLEMENT,
        summary=(
            "Chains of consumer accounts each hold funds for seconds, producing long "
            "hop sequences that no single institution sees end to end."
        ),
        genai_uplift=3,
        detection_gap=5,
        impact=4,
        feasibility=5,
        scale_velocity=5,
        uplift_note=(
            "Instant rails plus automated orchestration means the entire chain can "
            "complete before any batch monitoring process runs."
        ),
        kill_chain=(
            "Chain of consenting or compromised accounts prepared",
            "Funds relayed hop to hop within seconds",
            "Chain crosses institutions to break observability",
            "Exit at a terminal account or cash-out point",
        ),
        observable_signals=(
            "credit-to-debit interval measured in seconds",
            "sequential chains where each account has exactly one in and one out",
            "value decaying by a constant small percentage per hop",
            "chain accounts sharing device or onboarding attributes",
        ),
        historical_analogue="Wire chaining; rapid-movement typologies",
        victim_profile="The network; recovery becomes impossible within minutes",
        mitigations=(
            "Real-time dwell-time scoring on credits",
            "Network-level chain reconstruction across institutions",
            "Automated hold on onward transfer of a suspicious credit",
        ),
    ),
    V(
        id="AV-GIG-PAYOUT",
        name="Fabricated marketplace payout laundering",
        family="Money movement",
        rails=(R.UPI_P2M, R.WALLET),
        surface=S.SETTLEMENT,
        summary=(
            "Fake supply-side accounts on gig and marketplace platforms generate "
            "fabricated jobs, rides or sales, converting illicit funds into clean "
            "platform payouts with a documented commercial rationale."
        ),
        genai_uplift=4,
        detection_gap=4,
        impact=3,
        feasibility=4,
        scale_velocity=4,
        uplift_note=(
            "Generated reviews, chat logs, job descriptions and delivery evidence give "
            "each fabricated transaction a complete supporting narrative."
        ),
        kill_chain=(
            "Supply-side and demand-side accounts both controlled",
            "Fabricated transactions executed on the platform",
            "Platform payout issued to the supply-side account",
            "Funds now carry a legitimate payout provenance",
        ),
        observable_signals=(
            "buyer/seller pairs transacting exclusively with each other",
            "job or delivery telemetry inconsistent with the claimed service",
            "payout velocity inconsistent with platform-wide supply-side norms",
            "device or network overlap between both sides of the transaction",
        ),
        historical_analogue="Self-dealing marketplace fraud",
        victim_profile="Platforms and their payment partners",
        mitigations=(
            "Counterparty-exclusivity detection on platform graphs",
            "Service-delivery telemetry verification",
            "Payout-velocity anomaly scoring on the supply side",
        ),
    ),
]

# ---------------------------------------------------------------------------
# G. Agentic commerce — the 2026-native rail with no fraud history to train on
# ---------------------------------------------------------------------------

_AGENTIC = [
    V(
        id="AV-AGENT-INJECT",
        name="Prompt-injected shopping agent",
        family="Agentic commerce",
        rails=(R.AGENTIC, R.CARD_CNP),
        surface=S.AUTHORISATION,
        summary=(
            "An autonomous shopping agent acting for a consumer encounters attacker-"
            "controlled content on a merchant page that redirects its purchasing goal — "
            "different item, different merchant, different amount — while the consumer's "
            "credential and mandate remain entirely genuine."
        ),
        genai_uplift=5,
        detection_gap=5,
        impact=4,
        feasibility=4,
        scale_velocity=5,
        uplift_note=(
            "This vector does not exist without generative AI. The agent is the victim, "
            "the payment credential is valid, and no existing fraud model has ever seen "
            "a labelled example."
        ),
        kill_chain=(
            "Consumer delegates a purchase to an autonomous agent",
            "Agent traverses attacker-influenced merchant content",
            "Agent's objective is redirected by injected instructions",
            "Purchase completed at an attacker-benefiting merchant under a valid mandate",
            "Consumer discovers the divergence only at reconciliation",
        ),
        observable_signals=(
            "purchase category divergent from the stated mandate intent",
            "agent session traversing an unusually long or unusual merchant path",
            "merchant novel to both the consumer and the agent platform",
            "amount at the mandate ceiling rather than at a natural price point",
            "time-to-decision far shorter than the agent's normal comparison behaviour",
        ),
        historical_analogue="Malvertising redirects; supply-chain content injection",
        victim_profile="Early adopters of agentic checkout",
        mitigations=(
            "Mandate-intent conformance checking at authorisation",
            "Agent-path attestation and merchant allow-listing",
            "Treat the mandate as a constraint the network enforces, not advice",
        ),
        status=St.SIMULATED,
        injector="agent_inject",
    ),
    V(
        id="AV-AGENT-MANDATE",
        name="Over-scoped or manipulated agent payment mandate",
        family="Agentic commerce",
        rails=(R.AGENTIC, R.WALLET),
        surface=S.AUTHORISATION,
        summary=(
            "The consumer is induced to grant an agent a payment mandate far broader "
            "than they understand — higher ceiling, longer validity, wider merchant "
            "scope — which is then drawn down in full."
        ),
        genai_uplift=5,
        detection_gap=5,
        impact=4,
        feasibility=4,
        scale_velocity=4,
        uplift_note=(
            "Consent interfaces for agent mandates are new, inconsistent and poorly "
            "understood; persuasive generated framing does the rest."
        ),
        kill_chain=(
            "Consumer onboards an agent with an over-broad mandate",
            "Mandate scope obscured by persuasive consent framing",
            "Drawdown begins within the technically-authorised envelope",
            "Full ceiling consumed across merchants before the consumer notices",
        ),
        observable_signals=(
            "mandate ceiling far above the consumer's own historical spend distribution",
            "drawdown rate approaching the ceiling within the first mandate period",
            "merchant scope breadth inconsistent with the stated purpose",
            "no human confirmation events anywhere in the mandate's lifetime",
            "mandate created and first used within an unusually short window",
        ),
        historical_analogue="Over-permissive OAuth scopes; recurring-mandate abuse",
        victim_profile="Consumers adopting agent-initiated payments",
        mitigations=(
            "Network-enforced mandate ceilings benchmarked against the consumer's history",
            "Progressive trust: small initial ceilings that grow with observed behaviour",
            "Mandatory human confirmation above a spend-distribution percentile",
        ),
        status=St.SIMULATED,
        injector="agent_mandate",
        notes="Held out of training in the zero-day evaluation.",
    ),
    V(
        id="AV-AGENT-REPLAY",
        name="Agent credential and mandate-token replay",
        family="Agentic commerce",
        rails=(R.AGENTIC, R.WALLET, R.CARD_CNP),
        surface=S.AUTHENTICATION,
        summary=(
            "Agent-held payment tokens and mandate credentials are exfiltrated and "
            "replayed from other infrastructure, since machine credentials lack the "
            "device-binding and behavioural context that protect human sessions."
        ),
        genai_uplift=3,
        detection_gap=5,
        impact=4,
        feasibility=4,
        scale_velocity=4,
        uplift_note=(
            "Agent credentials are held by software, not people, so every human-centric "
            "control — device recognition, behavioural biometrics, step-up — is absent "
            "by design."
        ),
        kill_chain=(
            "Agent runtime or credential store compromised",
            "Mandate token and agent identity exfiltrated",
            "Token replayed from unrelated infrastructure",
            "Payments executed inside the mandate's authorised envelope",
        ),
        observable_signals=(
            "same agent identity presenting from divergent infrastructure signatures",
            "agent request cadence inconsistent with the platform's known runtime",
            "mandate used outside the consumer's timezone or activity pattern",
            "concurrent use of one mandate from multiple origins",
        ),
        historical_analogue="API key theft; OAuth token replay",
        victim_profile="Agent platforms and their users",
        mitigations=(
            "Hardware-backed agent identity with proof-of-possession",
            "Per-request attestation of the agent runtime",
            "Concurrency and origin-consistency checks on mandate use",
        ),
    ),
    V(
        id="AV-AGENT-SPOOF",
        name="Rogue agent impersonating a trusted agent identity",
        family="Agentic commerce",
        rails=(R.AGENTIC,),
        surface=S.AUTHENTICATION,
        summary=(
            "An attacker-operated agent presents the identity of a trusted, "
            "network-registered agent platform to obtain the preferential acceptance "
            "and reduced friction that identity carries."
        ),
        genai_uplift=4,
        detection_gap=5,
        impact=4,
        feasibility=3,
        scale_velocity=4,
        uplift_note=(
            "Agent identity registries are nascent; trust is being extended faster than "
            "it is being verified."
        ),
        kill_chain=(
            "Trusted agent platform identity observed and reproduced",
            "Rogue agent presents that identity at checkout",
            "Merchant applies reduced friction for the trusted agent",
            "Fraudulent purchases complete with elevated approval rates",
        ),
        observable_signals=(
            "agent identity presenting from an unregistered infrastructure origin",
            "behavioural profile diverging from the genuine agent's known patterns",
            "absence of valid platform attestation for the claimed identity",
            "sudden approval-rate and volume shift on a known agent identity",
        ),
        historical_analogue="User-agent spoofing; bot allow-list abuse",
        victim_profile="Merchants and consumers relying on agent trust signals",
        mitigations=(
            "Cryptographic agent identity with network-verified attestation",
            "Behavioural baselining per registered agent platform",
            "Never grant friction reduction on an unattested identity claim",
        ),
    ),
    V(
        id="AV-AGENT-COLLUDE",
        name="Merchant-side manipulation of agent decision-making",
        family="Agentic commerce",
        rails=(R.AGENTIC, R.CARD_CNP),
        surface=S.AUTHORISATION,
        summary=(
            "Merchants structure content specifically to manipulate autonomous buying "
            "agents — hidden directives, comparison poisoning, synthetic scarcity — "
            "extracting above-market prices from a buyer who never sees the page."
        ),
        genai_uplift=5,
        detection_gap=5,
        impact=3,
        feasibility=5,
        scale_velocity=5,
        uplift_note=(
            "Agent-targeted content optimisation is the next SEO, and it operates on "
            "a buyer with no human sanity check in the loop."
        ),
        kill_chain=(
            "Merchant content engineered for agent consumption",
            "Agent's comparison and ranking behaviour manipulated",
            "Agent selects the merchant and completes the purchase",
            "Consumer pays above market with a fully valid authorisation",
        ),
        observable_signals=(
            "price paid persistently above the market distribution for the item",
            "agent selection concentrating on merchants with anomalous content patterns",
            "comparison phase truncated relative to the agent's baseline behaviour",
            "post-purchase dispute and return rates elevated for that merchant",
        ),
        historical_analogue="SEO poisoning; dark-pattern pricing",
        victim_profile="Consumers delegating purchase decisions",
        mitigations=(
            "Price-conformance checking against market distributions at authorisation",
            "Agent content-integrity signals shared at the network level",
            "Merchant reputation weighted by agent-mediated dispute outcomes",
        ),
    ),
]

# ---------------------------------------------------------------------------
# H. Attacks on the defence itself
#    The category most fraud programmes have no coverage for at all.
# ---------------------------------------------------------------------------

_MODEL = [
    V(
        id="AV-MODEL-PROBE",
        name="Decision-boundary probing of the fraud model",
        family="Attacks on the defence",
        rails=(R.CARD_CNP, R.UPI_P2M, R.WALLET),
        surface=S.MODEL,
        summary=(
            "Approve/decline/step-up outcomes are treated as an oracle: many small, "
            "cheap transactions are used to map where the model's decision boundary "
            "sits, so that subsequent real attacks are shaped to stay inside it."
        ),
        genai_uplift=4,
        detection_gap=5,
        impact=4,
        feasibility=4,
        scale_velocity=4,
        uplift_note=(
            "Every declined transaction is a labelled training example handed to the "
            "attacker for free. Automation turns that feedback into a usable surrogate "
            "model of the defence."
        ),
        kill_chain=(
            "Low-value transactions issued across a controlled parameter space",
            "Outcomes recorded as labels for a surrogate model",
            "Surrogate model identifies the decision boundary",
            "Real attacks shaped to sit inside the approval region",
        ),
        observable_signals=(
            "systematic parameter sweeps across amount, time, merchant and channel",
            "unusual concentration of near-threshold scores from one entity cluster",
            "decline-then-adjust-then-retry patterns with monotonic parameter movement",
            "coverage of the feature space that no genuine customer would produce",
        ),
        historical_analogue="Model extraction attacks; card testing generalised",
        victim_profile="The issuer's model itself",
        mitigations=(
            "Randomised decision noise near the boundary to poison surrogate learning",
            "Detect systematic parameter sweeps at the entity-cluster level",
            "Limit the information content of decline responses",
        ),
    ),
    V(
        id="AV-DATA-POISON",
        name="Feedback-loop poisoning via coordinated disputes",
        family="Attacks on the defence",
        rails=(R.CARD_CNP, R.CARD_CP),
        surface=S.MODEL,
        summary=(
            "Coordinated false fraud claims on legitimate transaction patterns corrupt "
            "the label supply the detector retrains on, deliberately raising false "
            "positives on benign behaviour and forcing thresholds down."
        ),
        genai_uplift=4,
        detection_gap=5,
        impact=4,
        feasibility=3,
        scale_velocity=3,
        uplift_note=(
            "Filing thousands of individually plausible disputes used to be infeasible. "
            "It is now a generation task, and the labels flow straight into retraining."
        ),
        kill_chain=(
            "Benign transaction pattern chosen as the poisoning target",
            "Coordinated fraud claims filed against that pattern",
            "Labels enter the retraining set as confirmed fraud",
            "Model degrades on the poisoned region; thresholds loosen elsewhere",
        ),
        observable_signals=(
            "dispute clusters concentrated on a narrow, coherent feature region",
            "claimants sharing device, onboarding or network attributes",
            "confirmed-fraud rate rising without a corresponding loss pattern",
            "label distribution shifting faster than transaction distribution",
        ),
        historical_analogue="Training-data poisoning in spam and content models",
        victim_profile="The detection model and every customer it subsequently scores",
        mitigations=(
            "Provenance weighting and anomaly screening on training labels",
            "Robust loss functions resistant to label noise",
            "Hold-out canaries to detect targeted degradation",
        ),
    ),
    V(
        id="AV-ADV-PERTURB",
        name="Adversarial feature perturbation under realism constraints",
        family="Attacks on the defence",
        rails=(R.CARD_CNP, R.UPI_P2P, R.WALLET),
        surface=S.MODEL,
        summary=(
            "Attack parameters that the attacker fully controls — amount, timing, "
            "merchant selection, device hygiene, beneficiary count, session pacing — are "
            "optimised to minimise the model's score while keeping the attack profitable."
        ),
        genai_uplift=5,
        detection_gap=5,
        impact=5,
        feasibility=4,
        scale_velocity=5,
        uplift_note=(
            "This is the meta-vector, and it is exactly what the IMMUNIS red agent "
            "implements. Any attacker with score feedback can run the same optimisation, "
            "which is precisely why the defence must run it first."
        ),
        kill_chain=(
            "Controllable attack parameters enumerated",
            "Score or outcome feedback obtained from the target",
            "Parameters optimised for minimum score subject to a value floor",
            "Optimised strain deployed at scale until the model is retrained",
        ),
        observable_signals=(
            "population of attacks clustering just below the operating threshold",
            "score distribution of confirmed fraud shifting downward over time",
            "attack parameters converging across otherwise unrelated incidents",
            "detection recall decaying while transaction distributions are stable",
        ),
        historical_analogue="Adversarial examples in vision and malware classifiers",
        victim_profile="Every model in the network simultaneously",
        mitigations=(
            "Continuous adversarial self-play — retrain on your own evasions",
            "Ensemble and rule diversity so no single boundary can be optimised against",
            "Monitor the score distribution of confirmed fraud as a drift alarm",
        ),
        status=St.SIMULATED,
        injector="__redteam__",
        notes="Implemented as the red agent in redteam/evader.py rather than as a "
              "standalone injector.",
    ),
]

# ---------------------------------------------------------------------------

ATLAS: list[V] = [*_SOCIAL, *_AUTH, *_IDENTITY, *_RAIL, *_MERCHANT, *_LAUNDER,
                  *_AGENTIC, *_MODEL]

ATLAS_BY_ID: dict[str, V] = {v.id: v for v in ATLAS}

SIMULATED_IDS: list[str] = [
    v.id for v in ATLAS if v.status is St.SIMULATED and v.injector != "__redteam__"
]


def families() -> list[str]:
    seen: list[str] = []
    for v in ATLAS:
        if v.family not in seen:
            seen.append(v.family)
    return seen


def get(vector_id: str) -> V:
    try:
        return ATLAS_BY_ID[vector_id]
    except KeyError:
        raise KeyError(f"unknown attack vector {vector_id!r}") from None


def summary_stats() -> dict:
    from collections import Counter

    rail_counter: Counter[str] = Counter()
    for v in ATLAS:
        for r in v.rails:
            rail_counter[r.value] += 1
    return {
        "total_vectors": len(ATLAS),
        "simulated_vectors": len(SIMULATED_IDS),
        "families": len(families()),
        "by_family": dict(Counter(v.family for v in ATLAS)),
        "by_surface": dict(Counter(v.surface.value for v in ATLAS)),
        "by_rail": dict(rail_counter),
        "by_priority": dict(Counter(v.priority for v in ATLAS)),
        "mean_threat_score": round(sum(v.threat_score for v in ATLAS) / len(ATLAS), 1),
    }
