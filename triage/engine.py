# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
import hashlib
import json
from dataclasses import asdict, dataclass


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_policy(path):
    with open(path, encoding="utf-8") as handle:
        policy = json.load(handle)
    required = {"name", "version", "labels", "rules", "min_confidence", "min_margin"}
    if not required <= set(policy):
        raise ValueError("invalid policy")
    return policy


def denominator(terms, mode):
    """Evidence baseline for a label.

    "sum"  (policy v1): every keyword in the label must fire. Unreachable for
                        real tickets -- a single strong signal could never
                        clear min_confidence. Retained unchanged so v1 stays
                        byte-for-byte reproducible.
    "top1" (policy v2): the strongest keyword in the label defines sufficient
                        evidence. One decisive signal can classify; weak lone
                        signals still fall to REVIEW.
    "top2":             two signals required. Measured too strict in practice
                        (see reports/calibration_v1_to_v2.md).
    """
    weights = sorted((float(t["weight"]) for t in terms), reverse=True)
    if mode == "top1":
        total = weights[0] if weights else 0.0
    elif mode == "top2":
        total = sum(weights[:2])
    else:
        total = sum(weights)
    return total if total > 0 else 1.0


@dataclass
class TriageDecision:
    decision_id: str
    label: str
    confidence: float
    state: str
    policy_name: str
    policy_version: str
    scores: dict
    adversarial: bool
    input_sha256: str
    rationale: list

    def to_dict(self):
        return asdict(self)

    def to_json(self):
        return canonical(self.to_dict())


def classify(text, policy):
    lowered = text.lower()
    mode = policy.get("normalization", "sum")
    scores = {}
    rationale = []

    for label, terms in policy["rules"].items():
        base = denominator(terms, mode)
        total = 0.0
        for item in terms:
            hits = lowered.count(item["term"].lower())
            if hits:
                total += float(item["weight"]) * min(hits, 2)
                rationale.append("%s: %s x%d" % (label, item["term"], hits))
        scores[label] = round(min(total / base, 1.0), 4)

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    leader, top = ranked[0]
    runner_up = ranked[1][1] if len(ranked) > 1 else 0.0

    injection = [p for p in policy.get("injection_phrases", []) if p.lower() in lowered]
    adversarial = bool(injection)
    confident = top >= policy["min_confidence"] and top - runner_up >= policy["min_margin"]

    if adversarial:
        label, state = "REVIEW", "REVIEW"
        rationale.append("adversarial pattern detected")
    elif confident:
        label, state = leader, "MEASURED"
    else:
        label, state = "REVIEW", "REVIEW"
        rationale.append("below confidence/margin gate")

    return TriageDecision(
        decision_id="szl.triage.v1/" + sha(text)[:16],
        label=label,
        confidence=top,
        state=state,
        policy_name=policy["name"],
        policy_version=policy["version"],
        scores=scores,
        adversarial=adversarial,
        input_sha256=sha(text),
        rationale=rationale,
    )