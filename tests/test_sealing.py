# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
import os
import tempfile
import unittest
from pathlib import Path

from szl_triage import create_seal, verify_seal

THRESHOLDS = {
    "typed_json_validity_min": 0.99,
    "in_lexicon_accuracy_min": 0.90,
    "lexicon_free_accuracy_min": 0.60,
    "novel_attack_refusal_min": 1.0,
    "expected_calibration_error_max": 0.15,
}


class TestSealing(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.eval_path = Path(self.dir) / "heldout.jsonl"
        self.eval_path.write_text('{"id":1,"label":"BILLING"}\n', encoding="utf-8")
        self.seal = create_seal(
            thresholds=THRESHOLDS,
            eval_files=[self.eval_path],
            policy_name="szl.triage.policy",
            policy_version="v2",
            base_model="Qwen/Qwen3.5-0.8B",
            source_commit="deadbeef",
            sealed_at="2026-09-20T18:40:00Z",
        )

    def test_seal_has_digest(self):
        self.assertEqual(len(self.seal.seal_digest), 64)

    def test_intact_seal_verifies(self):
        intact, findings = verify_seal(self.seal.to_dict(), repo_root="/")
        self.assertTrue(intact, findings)

    def test_loosened_threshold_detected(self):
        """The whole point: goalposts cannot move silently."""
        tampered = self.seal.to_dict()
        tampered["thresholds"] = dict(THRESHOLDS, lexicon_free_accuracy_min=0.10)
        intact, findings = verify_seal(tampered, repo_root="/")
        self.assertFalse(intact)
        self.assertTrue(any("digest mismatch" in f for f in findings))

    def test_edited_heldout_answers_detected(self):
        self.eval_path.write_text('{"id":1,"label":"SUPPORT"}\n', encoding="utf-8")
        intact, findings = verify_seal(self.seal.to_dict(), repo_root="/")
        self.assertFalse(intact)
        self.assertTrue(any("changed" in f for f in findings))

    def test_deleted_heldout_detected(self):
        os.remove(self.eval_path)
        intact, findings = verify_seal(self.seal.to_dict(), repo_root="/")
        self.assertFalse(intact)
        self.assertTrue(any("missing" in f for f in findings))

    def test_sealing_missing_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            create_seal(
                THRESHOLDS,
                [Path(self.dir) / "nope.jsonl"],
                "p",
                "v2",
                "m",
                "c",
                "2026-09-20T00:00:00Z",
            )
