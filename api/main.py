"""IMMUNIS API — optional live service.

The web prototype reads baked artefacts and needs no backend, which is
deliberate: a judge should be able to open a static build and see everything.
This service is for the *live* demo — scoring a hypothetical transaction on
demand, streaming the arena, and re-running a simulation with different strain
parameters.

    uvicorn api.main:app --reload --port 8000

Then set NEXT_PUBLIC_API_URL=http://localhost:8000 for the web app.
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "engine"))

from immunis import __version__                                    # noqa: E402
from immunis.config import ARTIFACTS_DIR, Config                   # noqa: E402
from immunis.defend import (                                       # noqa: E402
    Detector, Explainer, apply_label_noise, apply_narrative_channel,
    build_features, evaluate, temporal_split,
)
from immunis.generate import REGISTRY, simulate                    # noqa: E402
from immunis.identify import build_extended_atlas, summary_stats   # noqa: E402
from immunis.redteam import make_context                           # noqa: E402
from immunis.loop import run_coevolution                           # noqa: E402

app = FastAPI(
    title="IMMUNIS",
    version=__version__,
    description="Adversarial immune system for payment networks.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Lazily-built engine state. The first scoring request pays for the model; every
# subsequent one is milliseconds.
# ---------------------------------------------------------------------------

class Engine:
    def __init__(self) -> None:
        self.ready = False
        self.building = False
        self.cfg: Config | None = None
        self.detector: Detector | None = None
        self.explainer: Explainer | None = None
        self.ledger = None
        self.fs: dict[str, Any] | None = None
        self.split = None
        self.built_at: float | None = None

    def build(self, profile: str = "fast", seed: int = 20260831) -> None:
        if self.building:
            return
        self.building = True
        try:
            cfg = Config.for_profile(profile, seed)
            ledger = simulate(cfg, verbose=False)
            eps = {e.episode_id: e.to_dict() for e in ledger.episodes}
            fs = build_features(ledger.transactions, ledger.world, eps)
            split = temporal_split(fs["meta"]["ts"], cfg.defend)
            apply_narrative_channel(fs["X"], fs["feature_names"],
                                    ledger.transactions, eps, split.train)
            y_obs = apply_label_noise(
                fs["y"], split.train | split.calib,
                missed_fraud=cfg.attacks.label_noise_missed_fraud,
                false_fraud=cfg.attacks.label_noise_false_fraud)
            zd = np.isin(fs["meta"]["vector_id"], list(cfg.attacks.zero_day_holdout))
            det = Detector(cfg=cfg.defend, costs=cfg.costs,
                           feature_names=fs["feature_names"],
                           categorical_idx=fs["categorical_idx"])
            det.fit(fs["X"], y_obs, split, exclude_train_mask=zd)
            det.choose_threshold(det.score(fs["X"][split.test]),
                                 fs["y"][split.test],
                                 fs["meta"]["amount"][split.test].astype(float))
            self.cfg, self.ledger, self.fs, self.split = cfg, ledger, fs, split
            self.detector = det
            self.explainer = Explainer(det, fs["X"][split.train], fs["feature_names"])
            self.built_at = time.time()
            self.ready = True
        finally:
            self.building = False


ENGINE = Engine()


def _artifact(name: str) -> Any:
    path = ARTIFACTS_DIR / name
    if not path.exists():
        raise HTTPException(404, f"{name} not found — run `python -m immunis.cli run`")
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Artefact endpoints — what the web app reads
# ---------------------------------------------------------------------------

@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "version": __version__,
        "model_ready": ENGINE.ready,
        "model_built_at": ENGINE.built_at,
        "artifacts": sorted(p.name for p in ARTIFACTS_DIR.glob("*.json")),
    }


@app.get("/atlas")
def atlas(discover: int = Query(10, ge=0, le=40)) -> dict:
    vectors = build_extended_atlas(top_k=discover)
    return {"stats": summary_stats(), "vectors": [v.to_dict() for v in vectors]}


@app.get("/artifacts/{name}")
def artifact(name: str) -> Any:
    if not name.replace("_", "").replace("-", "").isalnum():
        raise HTTPException(400, "bad artefact name")
    return _artifact(f"{name}.json")


# ---------------------------------------------------------------------------
# Live scoring
# ---------------------------------------------------------------------------

class ScoreRequest(BaseModel):
    """Score one hypothetical transaction against the live model.

    Only the fields you care about need to be supplied; anything omitted falls
    back to the population median, so a two-field request is valid.
    """
    amount: float = Field(25_000, ge=0)
    rail: str = "upi_p2p"
    is_new_beneficiary: bool = True
    beneficiary_age_days: float = 2.0
    screen_share: bool = False
    call_active: bool = False
    session_duration_s: float = 900.0
    amount_to_p95: float = 6.0
    device_is_emulator: bool = False
    device_customer_count: int = 1
    instrument_age_days: float = 400.0
    coercion_score: float = 0.0
    is_agentic: bool = False
    mandate_ceiling_to_typical: float = 0.0
    mandate_intent_match: bool = True
    typing_variance_ratio: float = 1.0
    cust_prior_disputes_90d: int = 0
    travel_speed_kmh: float = 0.0


@app.post("/score")
def score(req: ScoreRequest) -> dict:
    if not ENGINE.ready:
        ENGINE.build()
    if not ENGINE.ready or ENGINE.explainer is None or ENGINE.fs is None:
        raise HTTPException(503, "model still building — retry in a moment")

    names: list[str] = ENGINE.fs["feature_names"]
    x = ENGINE.explainer.median.astype(np.float32).copy()
    from immunis.defend.features import RAILS

    mapping: dict[str, float] = {
        "amount": req.amount,
        "log_amount": float(np.log1p(req.amount)),
        "cat_rail": float(RAILS.index(req.rail) if req.rail in RAILS else -1),
        "is_new_beneficiary": float(req.is_new_beneficiary),
        "benef_age_days": req.beneficiary_age_days,
        "screen_share": float(req.screen_share),
        "call_active": float(req.call_active),
        "session_duration_s": req.session_duration_s,
        "amount_to_p95": req.amount_to_p95,
        "device_is_emulator": float(req.device_is_emulator),
        "device_customer_count": float(req.device_customer_count),
        "instrument_age_days": req.instrument_age_days,
        "coercion_score": req.coercion_score,
        "has_episode": 1.0 if req.coercion_score > 0 else 0.0,
        "is_agentic": float(req.is_agentic),
        "mandate_ceiling_to_typical": req.mandate_ceiling_to_typical,
        "mandate_intent_match": float(req.mandate_intent_match),
        "typing_variance_ratio": req.typing_variance_ratio,
        "cust_prior_disputes_90d": float(req.cust_prior_disputes_90d),
        "travel_speed_kmh": req.travel_speed_kmh,
        "screen_share_and_new_benef": float(req.screen_share and req.is_new_beneficiary),
    }
    for k, v in mapping.items():
        if k in names:
            x[names.index(k)] = v

    t0 = time.perf_counter()
    out = ENGINE.explainer.explain(x, top_k=6)
    out["latency_ms"] = round((time.perf_counter() - t0) * 1000, 2)
    out["threshold"] = ENGINE.detector.budget_threshold if ENGINE.detector else None
    return out


# ---------------------------------------------------------------------------
# Simulation on demand
# ---------------------------------------------------------------------------

class SimulateRequest(BaseModel):
    profile: str = "fast"
    seed: int = 20260831
    injector: str | None = None
    params: dict[str, float] | None = None


@app.post("/simulate")
def run_simulation(req: SimulateRequest) -> dict:
    if req.injector and req.injector not in REGISTRY:
        raise HTTPException(400, f"unknown injector {req.injector}")
    cfg = Config.for_profile(req.profile, req.seed)
    overrides = {req.injector: req.params} if (req.injector and req.params) else None
    ledger = simulate(cfg, injector_keys=[req.injector] if req.injector else None,
                      param_overrides=overrides, verbose=False)
    return {"summary": ledger.summary()}


# ---------------------------------------------------------------------------
# Arena stream (server-sent events)
# ---------------------------------------------------------------------------

@app.get("/arena/stream")
async def arena_stream(profile: str = "fast") -> StreamingResponse:
    """Replay the recorded arena run as SSE, one generation at a time."""
    try:
        data = _artifact("arena.json")
    except HTTPException:
        raise

    async def gen():
        yield f"event: baseline\ndata: {json.dumps(data['baseline'])}\n\n"
        for g in data["generations"]:
            payload = {k: v for k, v in g.items() if k != "top_strains"}
            payload["top_strains"] = g.get("top_strains", [])[:3]
            yield f"event: generation\ndata: {json.dumps(payload)}\n\n"
            await asyncio.sleep(0.8)
        yield ("event: done\ndata: " + json.dumps({
            "time_to_immunity_generations": data.get("time_to_immunity_generations"),
            "delta": data.get("delta"),
        }) + "\n\n")

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.get("/stream/transactions")
def transaction_stream(limit: int = Query(200, ge=1, le=2000)) -> dict:
    data = _artifact("stream.json")
    return {"transactions": data["transactions"][:limit]}
