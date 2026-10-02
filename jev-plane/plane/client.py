#!/usr/bin/env python3
"""Fail-closed TypeSafe System One client. Jev never ALLOW-alone."""

from __future__ import annotations

import json
import http.client
import math
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ENDPOINT = "https://api.typesafe.ai/v1/systemone"
# Pinned to the repo's own pin (src/szl_triage/providers/jev.py PINNED_MODEL). A moving
# -latest alias silently changes answers under tuned thresholds, so it is refused below
# at every threshold. jev-latest is never a proof pin.
MODEL = "jev-1.13.0"
FORBIDDEN_MODELS = frozenset({"jev-latest", "latest", ""})
TIMEOUT_S = 20
MAX_REQUEST_BYTES = 256 * 1024
MAX_RESPONSE_BYTES = 256 * 1024
MAX_JSON_DEPTH = 32
MAX_JSON_NODES = 10_000
PROBABILITY_TOLERANCE = 1e-3  # Structural arithmetic tolerance, not calibration.
_FAILURE_CODES = frozenset({
    "CLIENT_UNAVAILABLE", "MODEL_REFUSED", "ENDPOINT_REFUSED", "PACK_REFUSED",
    "MISSING_API_KEY", "KEY_REFUSED", "QUESTIONS_INVALID", "REQUEST_INVALID",
    "REQUEST_TOO_LARGE", "TRANSPORT_UNAVAILABLE", "HTTP_ERROR", "RESPONSE_INVALID",
    "RESPONSE_TOO_LARGE", "RESPONSE_STATUS_REFUSED", "RESPONSE_MEDIA_TYPE_REFUSED",
    "RESPONSE_REDIRECT_REFUSED", "RESPONSE_MODEL_REFUSED", "ANSWERS_INVALID",
    "INPUT_INVALID", "INPUT_TOO_LARGE", "PACK_INVALID",
    "LIVE_CALL_NOT_REQUESTED", "LOCAL_GATE_READER_SKIPPED", "PACK_IDENTITY_MISMATCH",
    "INVALID_READER_ENVELOPE",
})


class _ClientBoundaryError(ValueError):
    """A fixed failure code, never provider input or exception text."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never send credentials or state to a redirected destination, even same-host.
        return None


def _client_opener():
    # An operator's HTTP(S)_PROXY or a globally installed opener must not receive
    # authenticated requests. urllib's default HTTPS handler still verifies TLS.
    return urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())


def _client_number(value: Any, lower: float, upper: float) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value) and lower <= value <= upper
    except (OverflowError, TypeError, ValueError):
        return False


def _client_json_tree(value: Any) -> bool:
    """Bound structure before serialization and after parsing, without coercion."""
    stack = [(value, 0)]
    nodes = 0
    while stack:
        node, depth = stack.pop()
        nodes += 1
        if nodes > MAX_JSON_NODES or depth > MAX_JSON_DEPTH:
            return False
        if node is None or isinstance(node, (str, bool)):
            continue
        if isinstance(node, int):
            if node.bit_length() > 1024:
                return False
            continue
        if isinstance(node, float):
            if not math.isfinite(node):
                return False
            continue
        if isinstance(node, dict):
            if len(stack) + nodes + len(node) > MAX_JSON_NODES:
                return False
            if any(not isinstance(key, str) for key in node):
                return False
            stack.extend((item, depth + 1) for item in node.values())
        elif isinstance(node, list):
            if len(stack) + nodes + len(node) > MAX_JSON_NODES:
                return False
            stack.extend((item, depth + 1) for item in node)
        else:
            return False
        if len(stack) + nodes > MAX_JSON_NODES:
            return False
    return True


def _client_dump(value: Any) -> bytes:
    if not _client_json_tree(value):
        raise _ClientBoundaryError("REQUEST_INVALID")
    out = bytearray()
    encoder = json.JSONEncoder(ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    try:
        for chunk in encoder.iterencode(value):
            raw = chunk.encode("utf-8", errors="strict")
            if len(out) + len(raw) > MAX_REQUEST_BYTES:
                raise _ClientBoundaryError("REQUEST_TOO_LARGE")
            out.extend(raw)
    except _ClientBoundaryError:
        raise
    except (TypeError, ValueError, UnicodeError, RecursionError, OverflowError):
        raise _ClientBoundaryError("REQUEST_INVALID") from None
    return bytes(out)


def _client_pairs(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise _ClientBoundaryError("RESPONSE_INVALID")
        out[key] = value
    return out


def _client_constant(value):
    raise _ClientBoundaryError("RESPONSE_INVALID")


def _client_load(raw: bytes) -> dict[str, Any]:
    try:
        payload = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=_client_pairs,
            parse_constant=_client_constant,
        )
    except (ValueError, UnicodeError, RecursionError, OverflowError):
        raise _ClientBoundaryError("RESPONSE_INVALID") from None
    if not isinstance(payload, dict) or not _client_json_tree(payload):
        raise _ClientBoundaryError("RESPONSE_INVALID")
    return payload


def _client_questions(questions: Any) -> bool:
    if not isinstance(questions, dict) or not 1 <= len(questions) <= 128:
        return False
    for key, question in questions.items():
        if not isinstance(key, str) or not key or not isinstance(question, dict):
            return False
        kind = question.get("type")
        if kind not in ("choice", "noul", "score"):
            return False
        if not isinstance(question.get("instructions"), str) or not question["instructions"]:
            return False
        criteria = question.get("criteria")
        if kind == "choice":
            if not isinstance(criteria, dict) or not criteria:
                return False
            if any(not isinstance(k, str) or not k or not isinstance(v, str)
                   for k, v in criteria.items()):
                return False
        elif kind == "score":
            if (not isinstance(criteria, list) or not criteria
                    or any(not isinstance(item, str) for item in criteria)):
                return False
    return _client_json_tree(questions)


def _client_answers(answers: Any, questions: dict[str, Any]) -> bool:
    # Missing and unasked answers never become fabricated zero-risk answers.
    if not isinstance(answers, dict) or set(answers) != set(questions):
        return False
    for key, question in questions.items():
        answer = answers[key]
        kind = question["type"]
        if not isinstance(answer, dict) or answer.get("type") != kind:
            return False
        if kind == "choice":
            if set(answer) != {"type", "choice", "confidence", "probabilities"}:
                return False
            if (not isinstance(answer.get("choice"), str)
                    or answer["choice"] not in question["criteria"]):
                return False
            if not _client_number(answer.get("confidence"), 0.0, 1.0):
                return False
            expected = question["criteria"]
        elif kind == "noul":
            if set(answer) != {"type", "noul"}:
                return False
            if not _client_number(answer.get("noul"), 0.0, 1.0):
                return False
            continue
        else:
            if set(answer) != {"type", "score", "confidence", "legend", "probabilities"}:
                return False
            if not _client_number(answer.get("confidence"), 0.0, 1.0):
                return False
            if not _client_number(answer.get("score"), 0.0, float(len(question["criteria"]) - 1)):
                return False
            expected = {str(index): criterion for index, criterion in enumerate(question["criteria"])}
            if answer["legend"] != expected:
                return False
        if kind in ("choice", "score"):
            probabilities = answer["probabilities"]
            if not isinstance(probabilities, dict):
                return False
            if set(probabilities) != set(expected):
                return False
            if any(not _client_number(p, 0.0, 1.0) for p in probabilities.values()):
                return False
            if not math.isclose(sum(probabilities.values()), 1.0, rel_tol=0.0,
                                abs_tol=PROBABILITY_TOLERANCE):
                return False
            if kind == "choice" and probabilities[answer["choice"]] != max(probabilities.values()):
                return False
            if kind == "score" and not math.isclose(
                answer["score"], sum(int(label) * p for label, p in probabilities.items()),
                rel_tol=0.0, abs_tol=PROBABILITY_TOLERANCE,
            ):
                return False
    return True


def unavailable(
    reason: str,
    pack_id: str = "szl.overclaim_reader.v1",
    *,
    transport_attempted: bool = False,
) -> dict[str, Any]:
    return {
        "pack_id": pack_id if isinstance(pack_id, str) and re.fullmatch(
            r"szl\.[a-z0-9_.-]{1,100}", pack_id
        ) else "szl.overclaim_reader.v1",
        "model": MODEL,
        "endpoint": ENDPOINT,
        "reader_status": "UNAVAILABLE",
        "honesty": "UNAVAILABLE",
        "reason": reason if isinstance(reason, str) and reason in _FAILURE_CODES
        else "CLIENT_UNAVAILABLE",
        "answers": {
            "evidence_class": {
                "type": "choice",
                "choice": "UNAVAILABLE",
                "confidence": 0.0,
            }
        },
        "auto_merge": False,
        "jev_allow_alone": False,
        "transport_attempted": transport_attempted,
        # True is conservative: state may have left the host on an attempted
        # transport, even if no response was observed. Delivery is not certified.
        "state_left_host": transport_attempted,
        "state_delivery": "UNVERIFIED" if transport_attempted else "NOT_ATTEMPTED",
        "signed": False,
    }


def load_pack(path: Path) -> dict[str, Any]:
    with path.open("rb") as source:
        raw = source.read(MAX_REQUEST_BYTES + 1)
    if len(raw) > MAX_REQUEST_BYTES:
        raise _ClientBoundaryError("PACK_INVALID")
    return _client_load(raw)


def evaluate(
    state: Any,
    questions: dict[str, Any],
    *,
    pack_id: str = "szl.overclaim_reader.v1",
    api_key: str | None = None,
    endpoint: str = ENDPOINT,
    model: str = MODEL,
) -> dict[str, Any]:
    if model != MODEL:
        return unavailable("MODEL_REFUSED", pack_id)
    if endpoint != ENDPOINT:
        return unavailable("ENDPOINT_REFUSED", pack_id)
    if not isinstance(pack_id, str) or not re.fullmatch(r"szl\.[a-z0-9_.-]{1,100}", pack_id):
        return unavailable("PACK_REFUSED")
    supplied_key = api_key if api_key is not None else os.environ.get("TYPESAFE_API_KEY", "")
    if not isinstance(supplied_key, str):
        return unavailable("KEY_REFUSED", pack_id)
    key = supplied_key.strip()
    if not key:
        return unavailable("MISSING_API_KEY", pack_id)
    if len(key) > 4096 or any(ord(character) < 33 or ord(character) > 126 for character in key):
        return unavailable("KEY_REFUSED", pack_id)
    if not _client_questions(questions):
        return unavailable("QUESTIONS_INVALID", pack_id)

    try:
        body = _client_dump({"state": state, "model": MODEL, "questions": questions})
        # Validate against the exact question snapshot sent, not a caller-owned
        # dictionary that another thread could mutate while the request is in flight.
        sent_questions = _client_load(body)["questions"]
        req = urllib.request.Request(
            ENDPOINT,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Accept-Encoding": "identity",
            },
        )
        opener = _client_opener()
    except _ClientBoundaryError as exc:
        return unavailable(str(exc), pack_id)
    except (TypeError, ValueError, UnicodeError, OSError, RecursionError, OverflowError):
        return unavailable("REQUEST_INVALID", pack_id)
    try:
        with opener.open(req, timeout=TIMEOUT_S) as resp:
            if resp.geturl() != ENDPOINT:
                raise _ClientBoundaryError("RESPONSE_REDIRECT_REFUSED")
            if resp.status != 200:
                raise _ClientBoundaryError("RESPONSE_STATUS_REFUSED")
            media = resp.headers.get_all("Content-Type", [])
            if len(media) != 1 or not re.fullmatch(
                r"application/json(?:\s*;\s*charset\s*=\s*(?:utf-8|\"utf-8\"))?",
                media[0].strip(), flags=re.IGNORECASE,
            ):
                raise _ClientBoundaryError("RESPONSE_MEDIA_TYPE_REFUSED")
            encoding = resp.headers.get_all("Content-Encoding", [])
            if encoding and encoding != ["identity"]:
                raise _ClientBoundaryError("RESPONSE_MEDIA_TYPE_REFUSED")
            raw = resp.read(MAX_RESPONSE_BYTES + 1)
            if len(raw) > MAX_RESPONSE_BYTES:
                raise _ClientBoundaryError("RESPONSE_TOO_LARGE")
            payload = _client_load(raw)
    except _ClientBoundaryError as exc:
        return unavailable(str(exc), pack_id, transport_attempted=True)
    except urllib.error.HTTPError:
        return unavailable("HTTP_ERROR", pack_id, transport_attempted=True)
    except (urllib.error.URLError, http.client.HTTPException, TimeoutError, OSError, ValueError, TypeError,
            UnicodeError, RecursionError, OverflowError):
        return unavailable("TRANSPORT_UNAVAILABLE", pack_id, transport_attempted=True)
    if payload.get("model") != MODEL:
        return unavailable("RESPONSE_MODEL_REFUSED", pack_id, transport_attempted=True)
    if set(payload) != {"model", "answers", "usage"}:
        return unavailable("RESPONSE_INVALID", pack_id, transport_attempted=True)
    usage = payload["usage"]
    if (not isinstance(usage, dict) or set(usage) != {"input_tokens", "output_tokens"}
            or any(isinstance(count, bool) or not isinstance(count, int) or count < 0
                   for count in usage.values())):
        return unavailable("RESPONSE_INVALID", pack_id, transport_attempted=True)
    answers = payload.get("answers")
    if not _client_answers(answers, sent_questions):
        return unavailable("ANSWERS_INVALID", pack_id, transport_attempted=True)

    return {
        "pack_id": pack_id,
        "model": MODEL,
        "endpoint": ENDPOINT,
        "reader_status": "SOFTWARE",
        "honesty": "SOFTWARE",
        "answers": answers,
        "usage": usage,
        "auto_merge": False,
        "jev_allow_alone": False,
        "transport_attempted": True,
        "state_left_host": True,
        "state_delivery": "UNVERIFIED",
        "signed": False,
        "calibration": "UNVERIFIED",
        "determinism": "UNVERIFIED",
    }


def main() -> int:
    pack_path = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if pack_path is None:
        sys.stdout.write(json.dumps(unavailable("INPUT_INVALID"), indent=2) + "\n")
        return 2
    try:
        pack = load_pack(pack_path)
        raw_state = sys.stdin.read(MAX_REQUEST_BYTES + 1)
        if len(raw_state.encode("utf-8")) > MAX_REQUEST_BYTES:
            raise _ClientBoundaryError("INPUT_TOO_LARGE")
        state = _client_load((raw_state or "{}").encode("utf-8"))
        out = evaluate(
            state,
            pack.get("questions"),
            pack_id=pack.get("pack_id", "szl.overclaim_reader.v1"),
            endpoint=pack.get("endpoint", ENDPOINT),
            model=pack.get("model", MODEL),
        )
    except (OSError, ValueError, TypeError, UnicodeError, RecursionError, OverflowError):
        out = unavailable("INPUT_INVALID")
    sys.stdout.write(json.dumps(out, indent=2) + "\n")
    return 0 if out.get("reader_status") != "UNAVAILABLE" else 3


if __name__ == "__main__":
    raise SystemExit(main())
