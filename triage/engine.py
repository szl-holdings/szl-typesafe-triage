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
    scores = {}
    rationale = []

    for label, terms in policy["rules"].items():
        maximum = sum(float(item["weight"]) for item in terms)
        total = 0.0
        for item in terms:
            hits = lowered.count(item["term"].lower())
            if hits:
                total += float(item["weight"]) * min(hits, 2)
                rationale.append("%s: %s x%d" % (label, item["term"], hits))
        scores[label] = round(min(total / maximum, 1), 4) if maximum else 0.0

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