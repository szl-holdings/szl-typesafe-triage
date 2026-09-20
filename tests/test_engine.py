# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
import unittest
from pathlib import Path

from szl_triage import State, load_policy
from szl_triage.engine import classify, score

POLICY = load_policy(Path("policies/triage_policy.v2.json"))


class TestEngine(unittest.TestCase):
    def test_scores_bounded(self):
        scores, _, _ = score("crash crash error 500 bug broken regression", POLICY)
        for label, value in scores.items():
            self.assertGreaterEqual(value, 0.0, label)
            self.assertLessEqual(value, 1.0, label)

    def test_repeated_hits_capped(self):
        few, _, _ = score("crash crash", POLICY)
        many, _, _ = score("crash crash crash crash crash crash", POLICY)
        self.assertEqual(few["BUG"], many["BUG"])

    def test_lexicon_ceiling_is_review(self):
        """The engine's documented limitation, asserted as a test."""
        for text in (
            "the money thing looks wrong",
            "cannot get into my account anymore",
            "somebody else could read our private stuff",
        ):
            self.assertEqual(classify(text, POLICY).state, State.REVIEW, text)

    def test_single_strong_signal_classifies(self):
        self.assertEqual(classify("how do i rotate a key", POLICY).label, "SUPPORT")

    def test_weak_lone_signal_reviews(self):
        self.assertEqual(classify("help", POLICY).state, State.REVIEW)

    def test_rationale_always_explains(self):
        self.assertTrue(classify("anything at all", POLICY).rationale)

    def test_determinism(self):
        text = "refund for a duplicate payment"
        self.assertEqual(
            classify(text, POLICY).to_json(), classify(text, POLICY).to_json()
        )
