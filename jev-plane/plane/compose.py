#!/usr/bin/env python3
"""Compose TypeSafe answers into estate actions. Jev does not ALLOW-alone."""

from __future__ import annotations

import json
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


def noul(answers: dict[str, Any], key: str) -> float:
    node = answers.get(key) or {}
    try:
        return float(node.get("noul") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def choice_of(answers: dict[str, Any], key: str) -> tuple[str | None, float]:
    node = answers.get(key) or {}
    try:
        conf = float(node.get("confidence") or 0.0)
    except (TypeError, ValueError):
        conf = 0.0
    return node.get("choice"), conf


def score_of(answers: dict[str, Any], key: str) -> float:
    node = answers.get(key) or {}
    try:
        return float(node.get("score") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def compose(pack_id: str, answers: dict[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    escalate = False
    block_publish = False
    block_merge = False
    request_info = False
    refuse = False
    labels: list[str] = []

    if pack_id.endswith("origin_claim.v1"):
        role, conf = choice_of(answers, "surface_role")
        over = noul(answers, "claim_overreach")
        unbound = noul(answers, "count_unbound")
        confuse = noul(answers, "origin_confusion")
        sev = score_of(answers, "honesty_severity")
        if conf >= THRESHOLDS["choice_confidence"] and role:
            labels.append(f"origin:{role}")
        if over >= THRESHOLDS["overreach_noul"] or sev >= THRESHOLDS["high_score"]:
            block_publish = True
            escalate = True
            reasons.append(f"claim_overreach={over:.2f} severity={sev:.2f}")
        if unbound >= THRESHOLDS["overreach_noul"]:
            block_publish = True
            reasons.append(f"count_unbound={unbound:.2f}")
        if confuse >= THRESHOLDS["origin_confusion_noul"]:
            block_publish = True
            escalate = True
            reasons.append(f"origin_confusion={confuse:.2f}")

    elif pack_id.endswith("hub_card.v1"):
        klass, conf = choice_of(answers, "artifact_class")
        unsafe = noul(answers, "unsafe_serialization")
        promo = noul(answers, "promotion_language")
        dead = noul(answers, "decommissioned_as_live")
        grade = score_of(answers, "evidence_grade")
        if conf >= THRESHOLDS["choice_confidence"] and klass:
            labels.append(f"hub:{klass}")
        if unsafe >= THRESHOLDS["unsafe_noul"]:
            block_publish = True
            labels.append("quarantine")
            reasons.append(f"unsafe_serialization={unsafe:.2f}")
        if promo >= THRESHOLDS["promotion_noul"] or dead >= THRESHOLDS["promotion_noul"]:
            block_publish = True
            escalate = True
            reasons.append(f"promotion={promo:.2f} decommissioned_as_live={dead:.2f}")
        if grade >= THRESHOLDS["high_score"]:
            block_publish = True
            reasons.append(f"evidence_grade={grade:.2f}")

    elif pack_id.endswith("github_item.v1"):
        kind, conf = choice_of(answers, "kind")
        claim = noul(answers, "claim_risk")
        secret = noul(answers, "secret_risk")
        actionable = noul(answers, "actionable")
        ready = noul(answers, "ready_to_merge")
        urgency = score_of(answers, "urgency")
        if conf >= THRESHOLDS["choice_confidence"] and kind:
            labels.append(kind)
        elif conf < THRESHOLDS["choice_confidence"]:
            escalate = True
            reasons.append(f"kind confidence {conf:.2f} below gate")
        if claim >= THRESHOLDS["claim_noul"]:
            labels.append("governance")
            escalate = True
            reasons.append(f"claim_risk={claim:.2f}")
        if secret >= THRESHOLDS["secret_noul"]:
            labels.append("security")
            escalate = True
            block_merge = True
            reasons.append(f"secret_risk={secret:.2f}")
        if actionable < 0.35:
            request_info = True
            labels.append("question")
            reasons.append(f"actionable={actionable:.2f}")
        if ready < THRESHOLDS["ready_to_merge"]:
            block_merge = True
            reasons.append(f"ready_to_merge={ready:.2f}")
        if urgency >= THRESHOLDS["high_score"]:
            escalate = True
            reasons.append(f"urgency={urgency:.2f}")

    elif pack_id.endswith("router_intent.v1"):
        handler, conf = choice_of(answers, "handler")
        yuyay = noul(answers, "needs_yuyay")
        stakes = score_of(answers, "stakes")
        inject = noul(answers, "prompt_injection")
        if inject >= 0.55 or handler == "refuse":
            refuse = True
            escalate = True
            reasons.append(f"handler={handler} injection={inject:.2f}")
        if yuyay >= 0.55 or handler == "measure_yuyay":
            labels.append("measure_yuyay")
            reasons.append(f"needs_yuyay={yuyay:.2f}")
        if stakes >= THRESHOLDS["high_score"] or handler == "human":
            escalate = True
            reasons.append(f"stakes={stakes:.2f} handler={handler}")
        if conf < THRESHOLDS["choice_confidence"]:
            escalate = True
            reasons.append(f"handler confidence {conf:.2f} below gate")
        if handler:
            labels.append(f"handler:{handler}")

    else:
        raise SystemExit(f"unknown pack_id: {pack_id}")

    action = "label"
    if request_info:
        action = "request_info"
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
        "escalate": escalate,
        "block_publish": block_publish,
        "block_merge": block_merge,
        "request_info": request_info,
        "refuse": refuse,
        "auto_merge": AUTO_MERGE,
        "auto_close": AUTO_CLOSE,
        "jev_allow_alone": JEV_ALLOW_ALONE,
        "reasons": reasons,
        "thresholds": THRESHOLDS,
    }


def main() -> int:
    payload = json.loads(sys.stdin.read())
    pack_id = payload["pack_id"]
    answers = payload["answers"]
    decision = compose(pack_id, answers)
    out = {**payload, "decision": decision}
    sys.stdout.write(json.dumps(out, indent=2) + "\n")
    if path := payload.get("out"):
        Path(path).write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
