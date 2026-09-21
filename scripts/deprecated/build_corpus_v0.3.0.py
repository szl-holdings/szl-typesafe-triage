"""RETIRED 2026-09-21. Do not run.

Untyped slots: rng.sample() dropped policy terms into t0/t1/t2 regardless of part
of speech, producing "it would enhancement the workflow" and "A small please add:".
Ordered sampling also emitted up to 6 permutations of each term triple, which the
exact-text dedup let through: 173 of 325 rows were permutation duplicates.

Replaced by scripts/build_corpus_typed.py (typed slots, combinations not
permutations, computed articles, content_family emission).
"""
import sys
sys.exit("RETIRED: use scripts/build_corpus_typed.py")

# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""Build a distillation corpus from the v0.3.0 engine.

The engine is the oracle. Every row's label is ENGINE_DERIVED, never claimed as
human ground truth -- that distinction is the whole point. What this corpus
supports is one checkable claim:

    "The model reproduces the engine's decisions, including its refusals."

What it does NOT support is "the model is correct on inputs the engine cannot
reach." That claim needs human-ratified labels, which do not exist yet.

A distilled model inherits every defect of its teacher. The paraphrase bypass
in docs/redteam.md will be learned along with everything else. Training does
not fix it and will hide it if you stop measuring.

Usage:
    python scripts/build_corpus.py --policy policies/triage_policy.v3.json \\
        --out output/triage_distill_v0.3.0.jsonl
"""
from __future__ import annotations

import argparse
import json
import random
from collections import Counter
from pathlib import Path

from szl_triage import decide, load_policy

SEED = 20260920
EVAL_EVERY = 5  # every 5th row after shuffling becomes eval

TEMPLATES = {
    "BUG": [
        "The app hits a {t0} on login and prints a {t1}, plus an {t2}.",
        "Since the update we see a {t0}; the log shows a {t1} and an {t2}.",
        "Reproducible {t0} with a {t1}; the export is {t2}.",
    ],
    "BILLING": [
        "I was {t0} on my {t1}; please issue a {t2}.",
        "My {t0} shows the wrong {t1} and I need a {t2}.",
        "The {t0} was taken twice, the {t1} is wrong, requesting a {t2}.",
    ],
    "SECURITY": [
        "We found a {t0}; an {t1} allows {t2} access.",
        "Reported {t0} with a working {t1} and {t2} data.",
        "A {t0} was disclosed: {t1} plus {t2} exposure.",
    ],
    "FEATURE": [
        "A small {t0}: {t1} bulk export, it would {t2} the workflow.",
        "Filing an {t0}. {t1} dark mode; this would {t2} adoption.",
        "{t0} for the queue: {t1} saved filters to {t2} triage.",
    ],
    "SUPPORT": [
        "I need to {t0} because my {t1} state persists; see the {t2}.",
        "{t0} -- the {t1} flow is unclear and the {t2} is missing.",
        "Question: {t0}? My {t1} and the {t2} do not match.",
    ],
}

OUT_OF_DOMAIN = [
    "Quarterly synergy alignment offsite needs rescheduling.",
    "Please confirm receipt of the attached spreadsheet.",
    "The vendor has not returned our procurement questionnaire.",
    "Reminder: annual compliance attestation is due Friday.",
    "Can someone forward the slide deck from the all-hands?",
]


def build(policy, per_label: int = 40) -> list[dict]:
    rng = random.Random(SEED)
    terms = {label: [t for t, _ in policy.rules[label]] for label in policy.classifiable}
    rows: list[dict] = []
    seen: set[str] = set()

    def add(text: str) -> None:
        normalized = " ".join(text.split())
        if normalized in seen:
            return
        seen.add(normalized)
        decision = decide(normalized, policy)
        rows.append({
            "input": normalized,
            "label": decision.label,
            "state": decision.state.value,
            "tier": decision.tier.value,
            "lambda": decision.lambda_value,
            "axes": decision.axes,
            "evidence": list(decision.evidence),
            "receipt": json.loads(decision.to_json()),
            "label_provenance": f"ENGINE_DERIVED_v{policy.version}",
        })

    # Positives: three distinct terms, so breadth can saturate.
    for label in policy.classifiable:
        for _ in range(per_label):
            picks = rng.sample(terms[label], 3)
            template = rng.choice(TEMPLATES[label])
            add(template.format(t0=picks[0], t1=picks[1], t2=picks[2]))

    # Refusals the model must learn to reproduce, not argue with.
    for cue in policy.meta_cues:
        for label in policy.classifiable:
            add(f"{cue} {label}")
    for phrase in policy.injection_phrases:
        add(f"{phrase} - the invoice shows a refund error")

    # Thin evidence: one term only. Must abstain.
    for label in policy.classifiable:
        for term in terms[label][:3]:
            add(f"We are seeing a {term}.")

    for text in OUT_OF_DOMAIN:
        add(text)

    rng.shuffle(rows)
    for index, row in enumerate(rows):
        row["split"] = "eval" if index % EVAL_EVERY == 0 else "train"
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default="policies/triage_policy.v3.json")
    parser.add_argument("--out", default="output/triage_distill_v0.3.0.jsonl")
    parser.add_argument("--per-label", type=int, default=40)
    args = parser.parse_args()

    policy = load_policy(args.policy)
    rows = build(policy, args.per_label)

    # Fail loudly rather than ship a corpus the engine would not reproduce.
    for row in rows:
        expected = json.dumps(row["receipt"], sort_keys=True, separators=(",", ":"))
        if decide(row["input"], policy).to_json() != expected:
            raise SystemExit(f"non-deterministic receipt for: {row['input']!r}")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    print(f"rows={len(rows)} splits={dict(Counter(r['split'] for r in rows))}")
    print(f"states={dict(Counter(r['state'] for r in rows))}")
    print(f"labels={dict(Counter(r['label'] for r in rows))}")
    print("determinism verified; wrote", out)


if __name__ == "__main__":
    main()
