# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""Regression tests for this release workflow's pinning and existing gate.

Only local temporary fixtures are evaluated. No real receipts are regenerated,
no seal is created, and no model, network, publication or provider is invoked.
This checks the existing workflow layout, not arbitrary YAML or release quality.
"""
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "release_receipts.yml"
PINS = {
    "actions/checkout": "11d5960a326750d5838078e36cf38b85af677262",
    "actions/setup-python": "a26af69be951a213d495a4c3e4e4022e16d87065",
}


class ReleaseWorkflowContract(unittest.TestCase):
    def setUp(self):
        self.workflow = WORKFLOW.read_text(encoding="utf-8")

    def test_all_six_action_references_are_reviewed_immutable_pins(self):
        refs = re.findall(r"(?m)^\s*- uses:\s*([^\s#]+)", self.workflow)
        expected = [f"{name}@{sha}" for name, sha in PINS.items()] * 3
        self.assertCountEqual(refs, expected)
        for ref in refs:
            self.assertRegex(ref.rsplit("@", 1)[1], r"^[0-9a-f]{40}$")

    def test_all_three_verification_jobs_remain(self):
        jobs = re.findall(r"(?m)^  ([a-z][a-z-]+):$", self.workflow)
        self.assertCountEqual(jobs, ["verify-receipts", "verify-seal", "release-promotable"])
        self.assertEqual(self.workflow.count("run: python scripts/verify_release_receipts.py"), 1)
        self.assertEqual(self.workflow.count("run: python scripts/verify_seal.py"), 1)
        self.assertIn("on: [push, pull_request]", self.workflow)
        self.assertNotIn("continue-on-error:", self.workflow)
        self.assertNotIn("if:", self.workflow)
        self.assertNotIn("|| true", self.workflow)

    def test_seal_checkout_contains_full_ancestry(self):
        seal_job = self.workflow.split("  verify-seal:", 1)[1].split("  release-promotable:", 1)[0]
        self.assertRegex(
            seal_job,
            r"uses: actions/checkout@[0-9a-f]{40}[^\n]*\n\s+with:\n\s+fetch-depth: 0\b",
        )

    def _run_gate(self, raw):
        match = re.search(
            r"(?ms)^          python - <<'PY'\n(.*?)^          PY\s*$",
            self.workflow,
        )
        self.assertIsNotNone(match, "the existing inline promotion gate must remain")
        program = textwrap.dedent(match.group(1))
        with tempfile.TemporaryDirectory(prefix="szl-release-fixture-") as folder:
            root = Path(folder)
            (root / "out").mkdir()
            if raw is not None:
                (root / "out" / "release_gate.json").write_text(raw, encoding="utf-8")
            return subprocess.run(
                [sys.executable, "-I", "-c", program], cwd=root,
                capture_output=True, text=True, timeout=5, check=False,
            )

    def test_existing_promotable_verdict_positive_control(self):
        result = self._run_gate(json.dumps({"release_verdict": "PROMOTABLE", "stages": {}}))
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_blocked_unknown_and_missing_verdicts_remain_nonzero(self):
        for report in (
            {"release_verdict": "BLOCKED", "stages": {"fixture": {"verdict": "BLOCKED"}}},
            {"release_verdict": "UNKNOWN"},
            {"release_verdict": None},
            {},
        ):
            with self.subTest(report=report):
                self.assertNotEqual(self._run_gate(json.dumps(report)).returncode, 0)

    def test_absent_or_malformed_report_remains_nonzero(self):
        for raw in (None, "not-json", "[]", "null"):
            with self.subTest(raw=raw):
                self.assertNotEqual(self._run_gate(raw).returncode, 0)


if __name__ == "__main__":
    unittest.main()
