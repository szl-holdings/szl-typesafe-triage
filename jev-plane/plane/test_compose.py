#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "plane" / "compose.py"


def run(fixture: str) -> dict:
    raw = (ROOT / "fixtures" / fixture).read_text(encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(COMPOSE)],
        input=raw,
        text=True,
        capture_output=True,
        check=True,
    )
    return json.loads(proc.stdout)


def main() -> int:
    honest = run("origin_honest_ok.json")["decision"]
    assert honest["action"] == "label", honest
    assert honest["block_publish"] is False

    drift = run("origin_count_drift.json")["decision"]
    assert drift["block_publish"] is True, drift
    assert drift["action"] == "block_publish"

    lora = run("hub_lora_candidate.json")["decision"]
    assert "hub:weights_candidate" in lora["labels"], lora
    assert lora["block_publish"] is False

    gate = run("github_11_12.json")["decision"]
    assert "governance" in gate["labels"], gate
    assert gate["block_merge"] is True
    assert gate["auto_merge"] is False

    refuse = run("router_refuse_gates.json")["decision"]
    assert refuse["refuse"] is True
    assert refuse["action"] == "refuse"
    assert refuse["jev_allow_alone"] is False

    print("ok: origin_ok, origin_drift, hub_lora, github_11_12, router_refuse")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
