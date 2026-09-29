#!/usr/bin/env python3
"""Compose TypeSafe answers into estate actions. Jev does not ALLOW-alone.

Fail closed: a missing, NaN, infinite, non-numeric or out-of-range answer is UNAVAILABLE.
It never becomes 0.0, never yields a label, and moves reader_status off OK. A reader outage
neither opens nor closes a gate: it sets request_info (human review) and, for the router,
abstain (route to the deterministic path). Every output is advisory.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

THRESHOLDS = {
    "choice_confidence": 0.60,
    "claim_noul": 0.55,
    "secret_noul": 0.55,
    "overreach_noul": 0.55,
    "origin_confusion_noul": 0.55,
    "promotion_noul": 0.55,
    "unsafe_noul": 0.50,
    "ready_to_merge": 0.80,
    "high_score": 1.5,
}

AUTO_MERGE = False
AUTO_CLOSE = False
JEV_ALLOW_ALONE = False


def _node(answers: Any, key: str) -> dict[str, Any] | None:
    if not isinstance(answers, dict):
        return None
    node = answers.get(key)
    return node if isinstance(node, dict) else None


def _number(value: Any, lo: float | None = None, hi: float | None = None) -> float | None:
    """A finite number within [lo, hi], else None. Booleans and strings are not numbers."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        x = float(value)
    except OverflowError:
        return None
    if not math.isfinite(x):
        return None
    if (lo is not None and x < lo) or (hi is not None and x > hi):
        return None
    return x


def noul(answers: dict[str, Any] | None, key: str) -> float | None:
    node = _node(answers, key)
    return None if node is None else _number(node.get("noul"), 0.0, 1.0)


def choice_of(answers: dict[str, Any] | None, key: str) -> tuple[str, float] | None:
    node = _node(answers, key)
    if node is None:
        return None
    choice = node.get("choice")
    conf = _number(node.get("confidence"), 0.0, 1.0)
    if not isinstance(choice, str) or not choice.strip() or conf is None:
        return None
    return choice, conf


def score_of(answers: dict[str, Any] | None, key: str) -> float | None:
    node = _node(answers, key)
    return None if node is None else _number(node.get("score"))


READERS = {"choice": choice_of, "noul": noul, "score": score_of}


def _ge(value: float | None, threshold: float) -> bool:
    return value is not None and value >= threshold


def _lt(value: float | None, threshold: float) -> bool:
    return value is not None and value < threshold


def _fmt(value: float | None) -> str:
    return "UNAVAILABLE" if value is None else f"{value:.2f}"


def compose(pack_id: str, answers: dict[str, Any] | None) -> dict[str, Any]:
    reasons: list[str] = []
    escalate = False
    block_publish = False
    block_merge = False
    request_info = False
    refuse = False
    abstain = False
    labels: list[str] = []
    asked: list[str] = []
    unavailable: list[str] = []

    def read(key: str, kind: str) -> Any:
        asked.append(key)
        value = READERS[kind](answers, key)
        if value is None:
            unavailable.append(key)
            reasons.append(f"{key}=UNAVAILABLE")
        return value

    if pack_id.endswith("origin_claim.v1"):
        role = read("surface_role", "choice")
        over = read("claim_overreach", "noul")
        unbound = read("count_unbound", "noul")
        confuse = read("origin_confusion", "noul")
        sev = read("honesty_severity", "score")
        if role is not None and role[1] >= THRESHOLDS["choice_confidence"]:
            labels.append(f"origin:{role[0]}")
        if _ge(over, THRESHOLDS["overreach_noul"]) or _ge(sev, THRESHOLDS["high_score"]):
            block_publish = True
            escalate = True
            reasons.append(f"claim_overreach={_fmt(over)} severity={_fmt(sev)}")
        if _ge(unbound, THRESHOLDS["overreach_noul"]):
            block_publish = True
            reasons.append(f"count_unbound={_fmt(unbound)}")
        if _ge(confuse, THRESHOLDS["origin_confusion_noul"]):
            block_publish = True
            escalate = True
            reasons.append(f"origin_confusion={_fmt(confuse)}")

    elif pack_id.endswith("hub_card.v1"):
        klass = read("artifact_class", "choice")
        unsafe = read("unsafe_serialization", "noul")
        promo = read("promotion_language", "noul")
        dead = read("decommissioned_as_live", "noul")
        grade = read("evidence_grade", "score")
        if klass is not None and klass[1] >= THRESHOLDS["choice_confidence"]:
            labels.append(f"hub:{klass[0]}")
        if _ge(unsafe, THRESHOLDS["unsafe_noul"]):
            block_publish = True
            labels.append("quarantine")
            reasons.append(f"unsafe_serialization={_fmt(unsafe)}")
        if _ge(promo, THRESHOLDS["promotion_noul"]) or _ge(dead, THRESHOLDS["promotion_noul"]):
            block_publish = True
            escalate = True
            reasons.append(f"promotion={_fmt(promo)} decommissioned_as_live={_fmt(dead)}")
        if _ge(grade, THRESHOLDS["high_score"]):
            block_publish = True
            reasons.append(f"evidence_grade={_fmt(grade)}")

    elif pack_id.endswith("github_item.v1"):
        kind = read("kind", "choice")
        claim = read("claim_risk", "noul")
        secret = read("secret_risk", "noul")
        actionable = read("actionable", "noul")
        ready = read("ready_to_merge", "noul")
        urgency = read("urgency", "score")
        if kind is not None and kind[1] >= THRESHOLDS["choice_confidence"]:
            labels.append(kind[0])
        elif kind is not None:
            escalate = True
            reasons.append(f"kind confidence {kind[1]:.2f} below gate")
        if _ge(claim, THRESHOLDS["claim_noul"]):
            labels.append("governance")
            escalate = True
            reasons.append(f"claim_risk={_fmt(claim)}")
        if _ge(secret, THRESHOLDS["secret_noul"]):
            labels.append("security")
            escalate = True
            block_merge = True
            reasons.append(f"secret_risk={_fmt(secret)}")
        if _lt(actionable, 0.35):
            request_info = True
            labels.append("question")
            reasons.append(f"actionable={_fmt(actionable)}")
        if _lt(ready, THRESHOLDS["ready_to_merge"]):
            block_merge = True
            reasons.append(f"ready_to_merge={_fmt(ready)}")
        if _ge(urgency, THRESHOLDS["high_score"]):
            escalate = True
            reasons.append(f"urgency={_fmt(urgency)}")

    elif pack_id.endswith("router_intent.v1"):
        pick = read("handler", "choice")
        yuyay = read("needs_yuyay", "noul")
        stakes = read("stakes", "score")
        inject = read("prompt_injection", "noul")
        handler = pick[0] if pick is not None else None
        if _ge(inject, 0.55) or handler == "refuse":
            refuse = True
            escalate = True
            reasons.append(f"handler={handler} injection={_fmt(inject)}")
        if _ge(yuyay, 0.55) or handler == "measure_yuyay":
            labels.append("measure_yuyay")
            reasons.append(f"needs_yuyay={_fmt(yuyay)}")
        if _ge(stakes, THRESHOLDS["high_score"]) or handler == "human":
            escalate = True
            reasons.append(f"stakes={_fmt(stakes)} handler={handler}")
        if pick is not None and pick[1] < THRESHOLDS["choice_confidence"]:
            escalate = True
            reasons.append(f"handler confidence {pick[1]:.2f} below gate")
        # Any router input unavailable: route nothing on Jev's word; the deterministic path decides.
        abstain = bool(unavailable)
        if handler and not abstain:
            labels.append(f"handler:{handler}")

    else:
        raise SystemExit(f"unknown pack_id: {pack_id}")

    if not unavailable:
        reader_status = "OK"
    elif len(unavailable) == len(asked):
        reader_status = "UNAVAILABLE"
    else:
        reader_status = "DEGRADED"
    if unavailable:
        request_info = True

    action = "label"
    if request_info:
        action = "request_info"
    if abstain:
        action = "abstain"
    if block_merge:
        action = "hold"
    if block_publish:
        action = "block_publish"
    if refuse:
        action = "refuse"
    if escalate and action == "label":
        action = "escalate"

    seen: set[str] = set()
    uniq = []
    for label in labels:
        if label and label not in seen:
            seen.add(label)
            uniq.append(label)

    return {
        "pack_id": pack_id,
        "action": action,
        "labels": uniq,
        "reader_status": reader_status,
        "unavailable": unavailable,
        "escalate": escalate,
        "block_publish": block_publish,
        "block_merge": block_merge,
        "request_info": request_info,
        "refuse": refuse,
        "abstain": abstain,
        "advisory": True,
        "auto_merge": AUTO_MERGE,
        "auto_close": AUTO_CLOSE,
        "jev_allow_alone": JEV_ALLOW_ALONE,
        "reasons": reasons,
        "thresholds": THRESHOLDS,
    }


def main() -> int:
    payload = json.loads(sys.stdin.read())
    pack_id = payload["pack_id"]
    answers = payload.get("answers")
    decision = compose(pack_id, answers)
    out = {**payload, "decision": decision}
    sys.stdout.write(json.dumps(out, indent=2) + "\n")
    if path := payload.get("out"):
        Path(path).write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
