"""Artifact IO.

The engine writes plain JSON (and gzipped NDJSON for ledgers) so that the web
prototype can consume artefacts with zero backend, and so that a judge can
inspect any intermediate result with a text editor.
"""

from __future__ import annotations

import dataclasses
import gzip
import json
import math
from pathlib import Path
from typing import Any, Iterable, Iterator

import numpy as np


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def jsonable(obj: Any) -> Any:
    """Convert numpy / dataclass / set structures into JSON-safe values."""
    if obj is None or isinstance(obj, (str, bool, int)):
        return obj
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return round(obj, 6)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        v = float(obj)
        return None if (math.isnan(v) or math.isinf(v)) else round(v, 6)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, np.ndarray):
        return [jsonable(v) for v in obj.tolist()]
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return jsonable(dataclasses.asdict(obj))
    if isinstance(obj, dict):
        return {str(k): jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set, frozenset)):
        return [jsonable(v) for v in obj]
    if hasattr(obj, "to_dict"):
        return jsonable(obj.to_dict())
    return str(obj)


def write_json(path: Path, payload: Any, *, indent: int | None = 2) -> Path:
    ensure_dir(path.parent)
    path.write_text(
        json.dumps(jsonable(payload), indent=indent, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_ndjson_gz(path: Path, rows: Iterable[dict]) -> Path:
    ensure_dir(path.parent)
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(jsonable(row), ensure_ascii=False))
            fh.write("\n")
    return path


def read_ndjson_gz(path: Path) -> Iterator[dict]:
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


def write_csv(path: Path, rows: list[dict], columns: list[str] | None = None) -> Path:
    import csv

    ensure_dir(path.parent)
    if not rows:
        path.write_text("", encoding="utf-8")
        return path
    cols = columns or list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({c: jsonable(row.get(c)) for c in cols})
    return path
