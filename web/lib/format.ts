/** Pure formatting + label helpers.
 *
 * Deliberately separate from lib/data.ts: that module reads artefacts with
 * node:fs, so anything a client component imports has to live here or the
 * bundler tries to ship the filesystem to the browser.
 */


export function inr(n: number | null | undefined, compact = true): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  if (!compact) return "₹" + Math.round(n).toLocaleString("en-IN");
  const abs = Math.abs(n);
  if (abs >= 1e7) return "₹" + (n / 1e7).toFixed(2) + " Cr";
  if (abs >= 1e5) return "₹" + (n / 1e5).toFixed(2) + " L";
  if (abs >= 1e3) return "₹" + (n / 1e3).toFixed(1) + "K";
  return "₹" + n.toFixed(0);
}

export function pct(n: number | null | undefined, digits = 1): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  return (n * 100).toFixed(digits) + "%";
}

export function num(n: number | null | undefined, digits = 0): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  return n.toLocaleString("en-IN", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

export function ts(seconds: number): string {
  return new Date(seconds * 1000).toISOString().replace("T", " ").slice(0, 16);
}

export const RAIL_LABEL: Record<string, string> = {
  card_cp: "Card present",
  card_cnp: "Card not present",
  upi_p2p: "UPI P2P",
  upi_p2m: "UPI P2M",
  wallet: "Wallet / token",
  agentic: "Agentic commerce",
  remittance: "Cross-border",
};

export const SURFACE_LABEL: Record<string, string> = {
  onboarding: "Onboarding",
  authentication: "Authentication",
  authorisation: "Authorisation",
  settlement: "Settlement",
  dispute: "Dispute",
  model: "The model itself",
};

export const VECTOR_SHORT: Record<string, string> = {
  "AV-DIGITAL-ARREST": "Digital arrest",
  "AV-VOICE-CLONE": "Voice clone",
  "AV-AITM-OTP": "AiTM OTP relay",
  "AV-BIO-CLONE": "Biometric clone",
  "AV-SYNTH-ID": "Synthetic identity",
  "AV-DEEPFAKE-KYC": "Deepfake KYC",
  "AV-BIN-ENUM": "BIN enumeration",
  "AV-QR-SWAP": "QR swap",
  "AV-TOKEN-PROV": "Token provisioning",
  "AV-FAKE-MERCH": "Synthetic merchant",
  "AV-FRIENDLY-FRAUD": "First-party misuse",
  "AV-MULE-LAYER": "Mule layering",
  "AV-AGENT-INJECT": "Agent injection",
  "AV-AGENT-MANDATE": "Mandate abuse",
};

export function vectorShort(id: string | null | undefined): string {
  if (!id) return "—";
  return VECTOR_SHORT[id] ?? id.replace("AV-", "");
}
