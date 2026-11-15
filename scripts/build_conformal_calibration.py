#!/usr/bin/env python3
# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""Build the conformal abstention calibration set from the typed triage corpus.

Population doctrine (honest): the typed corpus (build_corpus_typed.py) carries
ENGINE_DERIVED labels - the engine is the oracle BY DESIGN, and the corpus
supports exactly one claim: reproducing engine decisions. This builder takes
only rows the corpus marks state=MEASURED (confident auto-label regime), sets
gold = the typed template bucket, and lets conformal_abstain.py re-run the
engine over the raw input to attach engine_lambda / engine_axes / engine_label.

calibrate() then keeps only rows where the CURRENT engine reproduces the typed
intent. Rows the current policy routes differently are dropped, not trusted.

The resulting conformal threshold licenses lambda-typicality under the typed
corpus distribution - NOT real-traffic correctness. The exchangeability
condition in the policy receipt is the binding honesty clause.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "szl.conformal-calibration-set/v1"


def extract(path: Path, split: str) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        meta = rec.get("meta") or {}
        user = next((m["content"] for m in rec.get("messages", [])
                     if m.get("role") == "user"), None)
        if not user:
            continue
        if str(meta.get("state", "")).upper() != "MEASURED":
            continue  # confident auto-label regime only; REVIEW refusals excluded
        bucket = str(meta.get("bucket", "")).upper()
        if not bucket or bucket in ("ADVERSARIAL", "AMBIG"):
            continue  # typed-intent buckets only
        rows.append({
            "schema": SCHEMA,
            "input": user,
            "label": bucket,
            "gold_state": "MEASURED",
            "source_split": split,
            "source_file": path.name,
        })
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=ROOT / "out" / "conformal_calibration_set.jsonl")
    args = ap.parse_args()

    rows = []
    for name, split in (("train.jsonl", "typed-train"), ("heldout.jsonl", "typed-heldout")):
        p = ROOT / "corpus" / name
        rows.extend(extract(p, split))

    if len(rows) < 10:
        print(json.dumps({"refused": f"only {len(rows)} candidate rows; >= 10 required"}))
        return 2

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8", newline="\n") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    digest = hashlib.sha256(args.out.read_bytes()).hexdigest()
    print(json.dumps({
        "status": "BUILT",
        "out": str(args.out),
        "n_rows": len(rows),
        "sha256": digest,
        "schema": SCHEMA,
        "population": "typed corpus, state=MEASURED, gold=template bucket; engine re-run attaches scores",
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
