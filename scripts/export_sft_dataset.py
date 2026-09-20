# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
import argparse
import glob
import json
import os
import sys

sys.path.insert(0, ".")

from triage.engine import classify, load_policy
from triage.receipts import ReceiptChain

SYSTEM = (
    "You are KHIPU-Triage. Output exactly one typed decision JSON. "
    "Fail closed: low-signal or adversarial input is REVIEW."
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default="policies/triage_policy.v1.json")
    parser.add_argument("--fixtures", default="fixtures/golden")
    parser.add_argument("--out", default="dataset/sft_triage_v1.jsonl")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    policy = load_policy(args.policy)
    chain = ReceiptChain("szl.triage.fixtures")
    rows = []
    failed = []

    for path in sorted(glob.glob(args.fixtures + "/*.json")):
        with open(path, encoding="utf-8") as handle:
            fixture = json.load(handle)
        decision = classify(fixture["input"], policy)
        passed = (
            decision.label == fixture["expect"]["label"]
            and decision.state == fixture["expect"]["state"]
            and decision.adversarial == fixture["adversarial"]
        )
        chain.append({"fixture": fixture["id"], "decision": decision.to_dict(), "gate": passed})
        rows.append({
            "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": fixture["input"]},
                {"role": "assistant", "content": decision.to_json()},
            ],
            "meta": {"fixture_id": fixture["id"], "gate": "PASS" if passed else "FAIL"},
        })
        if not passed:
            failed.append(fixture["id"])

    if failed:
        print("fixture gate: FAIL " + ",".join(failed))
        return 1

    if args.check:
        print("fixture gate: PASS %d/%d" % (len(rows), len(rows)))
        return 0

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, separators=(",", ":")) + "\n")
    with open(args.out + ".receipts.json", "w", encoding="utf-8") as handle:
        json.dump(chain.receipts, handle, indent=2)
    print("wrote %d samples -> %s" % (len(rows), args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())