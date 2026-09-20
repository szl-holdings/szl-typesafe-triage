# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
import unittest

from szl_triage import is_grounded, ungrounded_spans


class TestGrounding(unittest.TestCase):
    SOURCE = "Customer was charged   TWICE on invoice INV-2041 and wants a refund"

    def test_exact_span(self):
        self.assertTrue(is_grounded("invoice INV-2041", self.SOURCE))

    def test_case_insensitive(self):
        self.assertTrue(is_grounded("charged twice", self.SOURCE))

    def test_whitespace_collapsed(self):
        self.assertTrue(is_grounded("charged twice on invoice", self.SOURCE))

    def test_paraphrase_rejected(self):
        self.assertFalse(is_grounded("billed two times", self.SOURCE))

    def test_invention_rejected(self):
        self.assertFalse(is_grounded("customer threatened legal action", self.SOURCE))

    def test_trivially_short_span_rejected(self):
        self.assertFalse(is_grounded("a", self.SOURCE))

    def test_reports_only_ungrounded(self):
        bad = ungrounded_spans(("charged twice", "made up entirely"), self.SOURCE)
        self.assertEqual(bad, ["made up entirely"])
