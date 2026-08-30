"""IMMUNIS command line.

    python -m immunis.cli run              # full pipeline, demo profile
    python -m immunis.cli run --profile full --seed 7
    python -m immunis.cli atlas            # print the attack atlas
    python -m immunis.cli simulate         # generate a ledger only
    python -m immunis.cli score            # score one hypothetical transaction
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _utf8_stdout() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


BANNER = r"""
  ___ __  __ __  __ _   _ _  _ ___ ___
 |_ _|  \/  |  \/  | | | | \| |_ _/ __|   Adversarial Immune System
  | || |\/| | |\/| | |_| | .` || |\__ \   for Payment Networks
 |___|_|  |_|_|  |_|\___/|_|\_|___|___/   Mastercard Innovation Challenge 2026
"""


def cmd_run(args: argparse.Namespace) -> int:
    from .pipeline import run_pipeline

    print(BANNER)
    run_pipeline(
        profile=args.profile,
        seed=args.seed,
        out_dir=Path(args.out) if args.out else None,
        mirror_to_web=not args.no_web,
        skip_arena=args.no_arena,
        skip_ablations=args.no_ablations,
        discover_k=args.discover,
        use_llm=args.llm,
    )
    return 0


def cmd_atlas(args: argparse.Namespace) -> int:
    from .identify import build_extended_atlas, summary_stats

    vectors = build_extended_atlas(top_k=args.discover)
    if args.json:
        print(json.dumps([v.to_dict() for v in vectors], indent=2, ensure_ascii=False))
        return 0
    stats = summary_stats()
    print(f"\nATTACK ATLAS — {stats['total_vectors']} curated + "
          f"{len(vectors) - stats['total_vectors']} discovered\n")
    print(f"{'ID':<22}{'PRI':<10}{'SCORE':<8}{'RAILS':<28}NAME")
    print("-" * 118)
    for v in sorted(vectors, key=lambda x: -x.threat_score):
        rails = ",".join(r.value for r in v.rails)
        print(f"{v.id:<22}{v.priority:<10}{v.threat_score:<8}"
              f"{rails[:26]:<28}{v.name[:52]}")
    print()
    for k, val in stats.items():
        if isinstance(val, dict):
            print(f"{k}: " + ", ".join(f"{a}={b}" for a, b in val.items()))
        else:
            print(f"{k}: {val}")
    return 0


def cmd_simulate(args: argparse.Namespace) -> int:
    from .config import ARTIFACTS_DIR, Config
    from .generate import simulate
    from .util.io import write_json, write_ndjson_gz

    cfg = Config.for_profile(args.profile, args.seed)
    print(BANNER)
    ledger = simulate(cfg)
    out = Path(args.out) if args.out else ARTIFACTS_DIR
    write_json(out / "simulation.json",
               {"config": cfg.to_dict(), "summary": ledger.summary()})
    if args.dump_ledger:
        write_ndjson_gz(out / "ledger.ndjson.gz", ledger.transactions)
        write_ndjson_gz(out / "episodes.ndjson.gz",
                        (e.to_dict() for e in ledger.episodes))
        print(f"  wrote ledger + episodes to {out}")
    return 0


def cmd_score(args: argparse.Namespace) -> int:
    """Score a single hypothetical transaction against a freshly trained model."""
    import numpy as np

    from .config import Config
    from .defend import (Detector, Explainer, apply_narrative_channel,
                         build_features, temporal_split)
    from .generate import simulate

    cfg = Config.for_profile(args.profile, args.seed)
    ledger = simulate(cfg, verbose=False)
    episodes = {e.episode_id: e.to_dict() for e in ledger.episodes}
    fs = build_features(ledger.transactions, ledger.world, episodes)
    X, y, meta = fs["X"], fs["y"], fs["meta"]
    split = temporal_split(meta["ts"], cfg.defend)
    apply_narrative_channel(X, fs["feature_names"], ledger.transactions,
                            episodes, split.train)
    zd = np.isin(meta["vector_id"], list(cfg.attacks.zero_day_holdout))
    det = Detector(cfg=cfg.defend, costs=cfg.costs,
                   feature_names=fs["feature_names"],
                   categorical_idx=fs["categorical_idx"]).fit(
        X, y, split, exclude_train_mask=zd)
    det.choose_threshold(det.score(X[split.test]), y[split.test],
                         meta["amount"][split.test].astype(float))
    exp = Explainer(det, X[split.train], fs["feature_names"])

    row = int(args.row) if args.row is not None else int(
        np.flatnonzero(split.test & (y == 1))[0])
    print(json.dumps({"txn_id": str(meta["txn_id"][row]),
                      "vector_id": str(meta["vector_id"][row]) or None,
                      "amount": float(meta["amount"][row]),
                      **exp.explain(X[row], top_k=6)}, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="immunis", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--profile", default="demo",
                        choices=["fast", "demo", "full"])
    common.add_argument("--seed", type=int, default=20260831)
    common.add_argument("--out", default=None, help="artefact output directory")

    r = sub.add_parser("run", parents=[common], help="run the full pipeline")
    r.add_argument("--no-arena", action="store_true", help="skip co-evolution")
    r.add_argument("--no-ablations", action="store_true")
    r.add_argument("--no-web", action="store_true",
                   help="do not mirror artefacts into web/public/data")
    r.add_argument("--discover", type=int, default=10,
                   help="number of composite vectors to discover")
    r.add_argument("--llm", action="store_true",
                   help="enrich discovered vectors with Claude (needs ANTHROPIC_API_KEY)")
    r.set_defaults(func=cmd_run)

    a = sub.add_parser("atlas", help="print the attack atlas")
    a.add_argument("--json", action="store_true")
    a.add_argument("--discover", type=int, default=10)
    a.set_defaults(func=cmd_atlas)

    s = sub.add_parser("simulate", parents=[common], help="generate a ledger only")
    s.add_argument("--dump-ledger", action="store_true",
                   help="write the full ledger as gzipped NDJSON")
    s.set_defaults(func=cmd_simulate)

    sc = sub.add_parser("score", parents=[common],
                        help="score and explain one transaction")
    sc.add_argument("--row", default=None, help="row index (default: first test fraud)")
    sc.set_defaults(func=cmd_score)
    return p


def main(argv: list[str] | None = None) -> int:
    _utf8_stdout()
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
