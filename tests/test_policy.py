# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
import json
import tempfile
import unittest
from pathlib import Path

from szl_triage import load_policy
from szl_triage.policy import PolicyError

POLICY = Path("policies/triage_policy.v2.json")


def mutate(**overrides):
    raw = json.loads(POLICY.read_text())
    raw.update(overrides)
    return raw


class TestPolicyValidation(unittest.TestCase):
    def _load(self, raw):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            json.dump(raw, fh)
            path = fh.name
        return load_policy(path)

    def test_loads(self):
        policy = load_policy(POLICY)
        self.assertEqual(policy.version, "v2")
        self.assertEqual(policy.normalization, "top1")

    def test_review_excluded_from_classifiable(self):
        self.assertNotIn("REVIEW", load_policy(POLICY).classifiable)

    def test_rejects_missing_keys(self):
        raw = mutate()
        del raw["min_margin"]
        with self.assertRaises(PolicyError):
            self._load(raw)

    def test_rejects_unknown_normalization(self):
        with self.assertRaises(PolicyError):
            self._load(mutate(normalization="mystery"))

    def test_rejects_missing_review_sink(self):
        with self.assertRaises(PolicyError):
            self._load(
                mutate(labels=["BUG", "FEATURE", "SUPPORT", "BILLING", "SECURITY"])
            )

    def test_rejects_out_of_range_weight(self):
        raw = mutate()
        raw["rules"]["BUG"][0]["weight"] = 4.2
        with self.assertRaises(PolicyError):
            self._load(raw)

    def test_rejects_out_of_range_threshold(self):
        with self.assertRaises(PolicyError):
            self._load(mutate(min_confidence=1.9))

    def test_top1_denominator_is_strongest_term(self):
        self.assertAlmostEqual(load_policy(POLICY).denominator("BUG"), 0.7)
