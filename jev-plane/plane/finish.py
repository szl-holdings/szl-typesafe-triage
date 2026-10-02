#!/usr/bin/env python3
"""Offline-first, advisory successor to the supplied SZL frontier finish payload.

Code applies local gates before an optional semantic reader. No classification
authorizes a merge, publication, model promotion, signature or provider action.
An explicit --live sends the intent to TypeSafe; --selftest never uses network.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from client import ENDPOINT, MODEL, evaluate, load_pack, unavailable
from compose import compose

PACK_ID = "szl.overclaim_reader.v1"
PACK_PATH = Path(__file__).resolve().parents[1] / "packs" / "overclaim_reader.json"
RANK = {"MEASURED": 0, "UNAVAILABLE": 1, "HOLD": 2, "BLOCK": 3}
MAX_INTENT_BYTES = 65_536
QUESTION_KEYS = frozenset({
    "evidence_class", "claims_live", "invents_joules", "treats_hf_as_source",
    "lambda_as_theorem", "unsigned_as_live", "overclaim_severity",
})

_LIVE = re.compile(r"\b(stamp|mark|set|promote|is|are|now)\b.{0,64}\blive\b", re.I)
_NOT_LIVE = re.compile(r"\bnot\s+live\b", re.I)
_ENERGY = re.compile(r"\b\d+(?:\.\d+)?\s*(?:j|joules?|wh|watt-?hours?)\b", re.I)
_LAMBDA = re.compile(
    r"(?:\blambda\b|\bconjecture\s*1\b|Λ).{0,64}\b(proven|closed|solved|theorem)\b"
    r"|\b(proven|closed|solved)\b.{0,64}(?:\blambda\b|\bconjecture\s*1\b|Λ)", re.I,
)
_HUB = re.compile(
    r"\b(?:hf\s+publish|hugging\s*face\s+write|mint\s+space|push\s+to\s+(?:the\s+)?hub"
    r"|hf\s+as\s+source|hugging\s*face\s+(?:is\s+)?(?:canonical\s+)?source)\b", re.I,
)
_AUTHORITY = re.compile(r"\b(?:ato|customer\s+production\s+saas|new\s+flagship)\b", re.I)
_UNSIGNED = re.compile(
    r"\b(?:unsigned(?:-honest)?|hash-linked|absent\s+signer)\b.{0,64}"
    r"\b(?:live|ato|authorized|authorization|dsse-live)\b", re.I,
)


def local_gates(intent: str) -> dict[str, Any]:
    """Bounded lexical scanner, not a semantic proof or an action admission gate."""
    if not isinstance(intent, str) or not intent.strip():
        return {"class": "UNAVAILABLE", "reasons": ["EMPTY_OR_INVALID_INTENT"],
                "allowed": False, "owner": "code"}
    try:
        too_large = len(intent) > MAX_INTENT_BYTES or len(intent.encode("utf-8")) > MAX_INTENT_BYTES
    except UnicodeError:
        return {"class": "UNAVAILABLE", "reasons": ["INVALID_INTENT_ENCODING"],
                "allowed": False, "owner": "code"}
    if too_large:
        return {"class": "UNAVAILABLE", "reasons": ["INTENT_TOO_LARGE"],
                "allowed": False, "owner": "code"}
    # Remove only each honest negation, never the remaining sentence or intent.
    # Thus 'not LIVE; stamp domain LIVE' retains its affirmative LIVE stamp.
    text = _NOT_LIVE.sub("", re.sub(r"\s+", " ", intent))
    reasons = []
    for pattern, reason in (
        (_LIVE, "LIVE_STAMP"), (_ENERGY, "UNVERIFIED_ENERGY_QUANTITY"),
        (_LAMBDA, "LAMBDA_AS_THEOREM"), (_HUB, "HUB_WRITE_OR_SOURCE"),
        (_AUTHORITY, "CONSEQUENTIAL_AUTHORITY_CLAIM"),
        (_UNSIGNED, "UNSIGNED_AS_LIVE_AUTHORITY"),
    ):
        if pattern.search(text):
            reasons.append(reason)
    if reasons:
        klass = "BLOCK"
    elif re.search(r"\b(?:merge|publish|promote|write)\b", intent, re.I) and not re.search(
        r"\b(?:MEASURED|UNAVAILABLE|HOLD|sha|receipt)\b", intent
    ):
        klass, reasons = "HOLD", ["WRITE_WITHOUT_NAMED_EVIDENCE"]
    elif re.search(r"\bUNAVAILABLE\b", intent):
        klass, reasons = "UNAVAILABLE", ["UNAVAILABLE_MARKER"]
    elif re.search(r"\bMEASURED\b", intent):
        klass, reasons = "MEASURED", ["MARKER_ONLY_NOT_PROOF"]
    else:
        klass, reasons = "HOLD", ["NO_EVIDENCE_MARKER"]
    return {"class": klass, "reasons": reasons, "allowed": False, "owner": "code"}


def _digest(state: dict[str, Any]) -> str:
    raw = json.dumps(state, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def finish(intent: str, local_class: str | None = None, *, live: bool = False) -> dict[str, Any]:
    if not isinstance(live, bool):
        raise ValueError("live must be an explicit boolean")
    if local_class is not None and local_class not in RANK:
        raise ValueError("unrecognized operator class")
    local = local_gates(intent)
    if local_class is not None:
        local["class"] = max((local["class"], local_class), key=RANK.__getitem__)
        local["reasons"].append("OPERATOR_RESTRICTION:" + local_class)
    state = {
        "command_or_pr": {"text": intent if isinstance(intent, str) and not any(
            reason in {"EMPTY_OR_INVALID_INTENT", "INVALID_INTENT_ENCODING", "INTENT_TOO_LARGE"}
            for reason in local["reasons"]
        ) else ""},
        "local_class": local["class"],
        "measured": {},
        "policy": {"github_is_source": True, "reader_is_advisory": True,
                   "reachability_is_not_live": True},
    }
    if not live:
        reader = unavailable("LIVE_CALL_NOT_REQUESTED", PACK_ID)
    elif local["class"] in {"BLOCK", "UNAVAILABLE"}:
        reader = unavailable("LOCAL_GATE_READER_SKIPPED", PACK_ID)
    else:
        try:
            pack = load_pack(PACK_PATH)
            if not isinstance(pack, dict):
                raise ValueError("pack object required")
            questions = pack.get("questions")
            if (pack.get("pack_id") != PACK_ID or pack.get("model") != MODEL
                    or pack.get("endpoint") != ENDPOINT or not isinstance(questions, dict)
                    or set(questions) != QUESTION_KEYS):
                reader = unavailable("PACK_IDENTITY_MISMATCH", PACK_ID)
            else:
                reader = evaluate(state, questions, pack_id=PACK_ID)
        except (OSError, ValueError, TypeError, UnicodeError, RecursionError, OverflowError):
            reader = unavailable("PACK_INVALID", PACK_ID)
    if not isinstance(reader, dict):
        reader = unavailable("INVALID_READER_ENVELOPE", PACK_ID)
    elif reader.get("model") != MODEL or reader.get("pack_id") != PACK_ID:
        reader = unavailable("INVALID_READER_ENVELOPE", PACK_ID,
                             transport_attempted=reader.get("state_left_host") is not False)
    decision = compose(PACK_ID, reader.get("answers"))
    # An outage never looks clean, but any positive risk still wins over it.
    if reader.get("reader_status") != "SOFTWARE" and decision["reader_class"] != "BLOCK":
        decision.update(reader_class="UNAVAILABLE", block_merge=True, request_info=True, action="hold")
        decision["labels"] = []
    final = max((local["class"], decision["reader_class"]), key=RANK.__getitem__)
    clear = final == "MEASURED"
    return {
        "honesty": "SOFTWARE", "final_class": final, "allowed": False,
        "evidence_clear": clear, "evidence_clear_limit": "advisory text classification, not measured runtime proof",
        "local": local, "decision": decision,
        "reader": {"status": reader.get("reader_status"), "model": reader.get("model"),
                   "reason": reader.get("reason"), "state_digest": _digest(state),
                   "state_left_host": reader.get("state_left_host", False)},
        "not_claimed": ["LIVE", "ALL_DONE", "action authorization", "Hub write", "auto-merge",
                        "calibration", "model qualification", "signed receipt"],
    }


def selftest() -> int:
    cases = {
        "stamp": finish("Stamp a-11-oy.com LIVE")["final_class"] == "BLOCK",
        "mixed_stamp": finish("MEASURED, not LIVE; Stamp a-11-oy.com LIVE")["final_class"] == "BLOCK",
        "mixed_energy": finish("Energy UNAVAILABLE; attested 12.4 joules")["final_class"] == "BLOCK",
        "lambda": finish("MEASURED; Lambda is proven")["final_class"] == "BLOCK",
        "offline_unavailable": finish("MEASURED, not LIVE")["final_class"] == "UNAVAILABLE",
        "no_authority": all(not finish(text)["allowed"] for text in ("MEASURED", "UNAVAILABLE", "write", "stamp LIVE")),
        "no_data_sent": finish("MEASURED")["reader"]["state_left_host"] is False,
        "no_auto_merge": finish("MEASURED")["decision"]["auto_merge"] is False,
    }
    ok = all(cases.values())
    print(json.dumps({"ok": ok, "checks": len(cases), "failed": [name for name, value in cases.items() if not value],
                      "model": MODEL, "pack": PACK_ID, "network_calls": 0}, indent=2))
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selftest", action="store_true")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--intent", default="")
    source.add_argument("--intent-file", type=Path)
    parser.add_argument("--local-class", choices=sorted(RANK))
    parser.add_argument("--live", action="store_true", help="Explicitly send intent to the fixed TypeSafe endpoint; may incur API cost")
    args = parser.parse_args()
    if args.selftest:
        return selftest()
    try:
        if args.intent_file:
            with args.intent_file.open("rb") as stream:
                raw = stream.read(MAX_INTENT_BYTES + 1)
            if len(raw) > MAX_INTENT_BYTES:
                raise ValueError("intent size limit")
            intent = raw.decode("utf-8")
        else:
            intent = args.intent
        if not intent.strip():
            raise ValueError("empty intent")
        result = finish(intent, args.local_class, live=args.live)
    except (OSError, UnicodeError, ValueError):
        print(json.dumps({"honesty": "SOFTWARE", "final_class": "UNAVAILABLE", "allowed": False,
                          "error": "INVALID_INTENT_INPUT"}))
        return 2
    # The API retains its structured digest, but stdout must never carry user
    # intent or provider-controlled strings. Emit only literal allowlisted states.
    reported_class = "UNAVAILABLE"
    for klass in ("MEASURED", "UNAVAILABLE", "HOLD", "BLOCK"):
        if result.get("final_class") == klass:
            reported_class = klass
            break
    reported_reader = "UNAVAILABLE"
    for status in ("SOFTWARE", "UNAVAILABLE"):
        if result.get("reader", {}).get("status") == status:
            reported_reader = status
            break
    print(json.dumps({"honesty": "SOFTWARE", "final_class": reported_class,
                      "allowed": False, "reader_status": reported_reader,
                      "auto_merge": False, "jev_allow_alone": False}))
    return {"MEASURED": 0, "UNAVAILABLE": 2, "HOLD": 2, "BLOCK": 3}[reported_class]


if __name__ == "__main__":
    raise SystemExit(main())
