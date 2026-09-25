#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "plane"))

from client import evaluate, unavailable  # noqa: E402


def main() -> int:
    os.environ.pop("TYPESAFE_API_KEY", None)
    missing = evaluate({"text": "stamp LIVE"}, {"claims_live": {"type": "noul", "instructions": "x"}})
    assert missing["reader_status"] == "UNAVAILABLE", missing
    assert missing["honesty"] == "UNAVAILABLE"
    assert missing["answers"]["evidence_class"]["choice"] == "UNAVAILABLE"
    assert missing["auto_merge"] is False
    assert missing["jev_allow_alone"] is False

    empty = unavailable("HTTP 401")
    assert empty["reader_status"] == "UNAVAILABLE"
    print("ok: missing key UNAVAILABLE, no PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
