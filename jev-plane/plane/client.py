#!/usr/bin/env python3
"""Fail-closed TypeSafe System One client. Jev never ALLOW-alone."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ENDPOINT = "https://api.typesafe.ai/v1/systemone"
MODEL = "jev-latest"
TIMEOUT_S = 20


def unavailable(reason: str, pack_id: str = "szl.overclaim_reader.v1") -> dict[str, Any]:
    return {
        "pack_id": pack_id,
        "model": MODEL,
        "endpoint": ENDPOINT,
        "reader_status": "UNAVAILABLE",
        "honesty": "UNAVAILABLE",
        "reason": reason,
        "answers": {
            "evidence_class": {
                "type": "choice",
                "choice": "UNAVAILABLE",
                "confidence": 0.0,
            }
        },
        "auto_merge": False,
        "jev_allow_alone": False,
    }


def load_pack(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate(
    state: Any,
    questions: dict[str, Any],
    *,
    pack_id: str = "szl.overclaim_reader.v1",
    api_key: str | None = None,
    endpoint: str = ENDPOINT,
    model: str = MODEL,
) -> dict[str, Any]:
    key = (api_key if api_key is not None else os.environ.get("TYPESAFE_API_KEY", "")).strip()
    if not key:
        return unavailable("TYPESAFE_API_KEY missing", pack_id)

    body = json.dumps({"state": state, "model": model, "questions": questions}).encode("utf-8")
    req = urllib.request.Request(
        endpoint,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
            raw = resp.read().decode("utf-8")
            payload = json.loads(raw)
    except urllib.error.HTTPError as exc:
        return unavailable(f"HTTP {exc.code}", pack_id)
    except urllib.error.URLError as exc:
        return unavailable(f"URL error: {exc.reason}", pack_id)
    except (TimeoutError, json.JSONDecodeError, OSError) as exc:
        return unavailable(f"{type(exc).__name__}", pack_id)

    answers = payload.get("answers")
    if not isinstance(answers, dict) or not answers:
        return unavailable("empty answers", pack_id)

    return {
        "pack_id": pack_id,
        "model": payload.get("model") or model,
        "endpoint": endpoint,
        "reader_status": "SOFTWARE",
        "honesty": "SOFTWARE",
        "answers": answers,
        "usage": payload.get("usage") or {},
        "auto_merge": False,
        "jev_allow_alone": False,
    }


def main() -> int:
    pack_path = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if pack_path is None:
        sys.stdout.write(json.dumps(unavailable("no pack path"), indent=2) + "\n")
        return 2
    pack = load_pack(pack_path)
    state = json.loads(sys.stdin.read() or "{}")
    out = evaluate(
        state,
        pack["questions"],
        pack_id=str(pack.get("pack_id") or "szl.overclaim_reader.v1"),
        endpoint=str(pack.get("endpoint") or ENDPOINT),
        model=str(pack.get("model") or MODEL),
    )
    sys.stdout.write(json.dumps(out, indent=2) + "\n")
    return 0 if out.get("reader_status") != "UNAVAILABLE" else 3


if __name__ == "__main__":
    raise SystemExit(main())
