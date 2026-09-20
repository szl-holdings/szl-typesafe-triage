# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""Command line surface.

    szl-triage decide  "text"        one decision, JSON on stdout
    szl-triage seal                  create the pre-registration seal
    szl-triage verify-seal           recompute the seal against the tree
    szl-triage verify-receipts FILE  offline receipt chain check

Every subcommand exits non-zero on failure so the whole thing is usable as a
CI gate without a wrapper script.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import subprocess
import sys
from pathlib import Path

from . import __version__
from .pipeline import decide
from .policy import load as load_policy
from .receipts import verify as verify_receipts
from .sealing import create as create_seal
from .sealing import verify as verify_seal

DEFAULT_POLICY = "policies/triage_policy.v2.json"
SEAL_PATH = "PROMOTION_SEAL.json"


def _git_commit() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        )
        return out.stdout.strip()
    except Exception:
        return "UNAVAILABLE"


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def cmd_decide(args: argparse.Namespace) -> int:
    policy = load_policy(args.policy)
    decision = decide(args.text, policy)
    print(json.dumps(decision.to_dict(), indent=2, sort_keys=True))
    return 0


def cmd_seal(args: argparse.Namespace) -> int:
    thresholds = json.loads(Path(args.thresholds).read_text(encoding="utf-8"))
    policy = load_policy(args.policy)
    seal = create_seal(
        thresholds=thresholds,
        eval_files=args.eval_file,
        policy_name=policy.name,
        policy_version=policy.version,
        base_model=args.base_model,
        source_commit=_git_commit(),
        sealed_at=_now(),
    )
    Path(SEAL_PATH).write_text(
        json.dumps(seal.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"sealed {len(seal.eval_digests)} evaluation file(s)")
    print(f"seal digest: {seal.seal_digest}")
    print(f"written to {SEAL_PATH} -- commit this BEFORE training")
    return 0


def cmd_verify_seal(args: argparse.Namespace) -> int:
    seal = json.loads(Path(args.seal).read_text(encoding="utf-8"))
    intact, findings = verify_seal(seal, repo_root=args.root)
    if intact:
        print(
            f"SEAL INTACT  digest {seal['seal_digest'][:16]}  sealed {seal['sealed_at']}"
        )
        return 0
    print("SEAL BROKEN -- any published result under this seal is void")
    for finding in findings:
        print(f"  - {finding}")
    return 1


def cmd_verify_receipts(args: argparse.Namespace) -> int:
    receipts = json.loads(Path(args.file).read_text(encoding="utf-8"))
    if verify_receipts(receipts, lane=args.lane):
        print(f"CHAIN INTACT  {len(receipts)} receipt(s)  lane {args.lane}")
        return 0
    print("CHAIN BROKEN")
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="szl-triage", description=__doc__)
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)

    d = sub.add_parser("decide", help="classify one input")
    d.add_argument("text")
    d.add_argument("--policy", default=DEFAULT_POLICY)
    d.set_defaults(func=cmd_decide)

    s = sub.add_parser("seal", help="create the pre-registration seal")
    s.add_argument("--thresholds", default="PROMOTION_THRESHOLDS.json")
    s.add_argument("--policy", default=DEFAULT_POLICY)
    s.add_argument("--base-model", default="Qwen/Qwen3.5-0.8B")
    s.add_argument("--eval-file", action="append", required=True)
    s.set_defaults(func=cmd_seal)

    v = sub.add_parser("verify-seal", help="recompute the seal")
    v.add_argument("--seal", default=SEAL_PATH)
    v.add_argument("--root", default=".")
    v.set_defaults(func=cmd_verify_seal)

    r = sub.add_parser("verify-receipts", help="offline receipt chain check")
    r.add_argument("file")
    r.add_argument("--lane", default="szl.triage")
    r.set_defaults(func=cmd_verify_receipts)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
