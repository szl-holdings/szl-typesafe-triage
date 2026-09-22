# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""Bind this legacy checkout-byte repair to the unchanged historical seal.

These are integrity checks, not model evaluation or release approval. A new
measured evidence set needs a reviewed successor, not rewritten legacy hashes.
"""
import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
LEGACY_CRLF = (
    "out/axis_collision.json",
    "out/despace_effect.json",
    "out/engine_only_probe.json",
    "out/gate_report_bf16_in_domain.json",
    "out/gate_report_bf16_red_team.json",
    "out/gate_report_int4_in_domain.json",
    "out/gate_report_int4_red_team.json",
    "out/lambda_sweep.json",
    "out/quant_refusal_curve.json",
    "out/quant_significance.json",
    "output/triage_distill_split_v0.4.0.jsonl",
    "policies/redteam_probes.verified.jsonl",
)
UNCHANGED_SEAL = "0eb47b29121ffd0a531a7cf74e61b989f67a84624a28014de6d09e70dd51dafd"


class SealedCheckoutContract(unittest.TestCase):
    def test_overrides_are_exact_and_keep_default_lf_policy(self):
        lines = (ROOT / ".gitattributes").read_text(encoding="utf-8").splitlines()
        rules = [line.strip() for line in lines if line.strip() and not line.lstrip().startswith("#")]
        self.assertEqual(rules[:3], ["* text=auto eol=lf", "*.ps1 text eol=crlf", "*.jsonl text eol=lf"])
        self.assertCountEqual(rules[3:], [f"{path} text eol=crlf" for path in LEGACY_CRLF])

    def test_all_thirteen_artifacts_match_the_unchanged_historical_seal(self):
        seal = json.loads((ROOT / "out/release_seal.json").read_text(encoding="utf-8"))
        self.assertEqual(seal["seal_digest"], UNCHANGED_SEAL)
        self.assertEqual(set(seal["eval_digests"]), {*LEGACY_CRLF, "policies/triage_policy.v3.json"})
        for name, expected in seal["eval_digests"].items():
            with self.subTest(artifact=name):
                actual = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                self.assertEqual(actual, expected, "checkout bytes must match; never normalize inside the verifier")


if __name__ == "__main__":
    unittest.main()
