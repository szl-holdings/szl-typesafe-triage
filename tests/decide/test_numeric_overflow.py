"""Synthetic regressions for integers outside binary64's representable range."""
import dataclasses
import math
import unittest

from szl_decide import lam
from szl_decide.gate import Policy, PolicyError, ReasonClass, Seat, SeatReading, gate
from szl_decide.lattice import GO_I, Interval, IntervalError, Tri


class NumericOverflowTests(unittest.TestCase):
    def setUp(self):
        self.seat = Seat("s", "test", 0.5, 1.0, "test", "1", frozenset(),
                         "FREE_DETERMINISTIC", calibrated=True)
        self.policy = Policy((self.seat,), 0.8, "test", "test", "test")
        self.reading = SeatReading("s", GO_I, "OK", ReasonClass.NONE)

    def test_interval_constructor_reports_contract_error(self):
        for huge in (10**1000, -(10**1000)):
            for lo, hi in ((huge, 1), (0, huge)):
                with self.subTest(lo_is_huge=lo == huge, negative=huge < 0):
                    with self.assertRaises(IntervalError):
                        Interval(lo, hi)

    def test_forged_huge_endpoint_abstains(self):
        for field in ("lo", "hi"):
            for huge in (10**1000, -(10**1000)):
                iv = Interval(1, 1)
                object.__setattr__(iv, field, huge)
                r = dataclasses.replace(self.reading)
                object.__setattr__(r, "interval", iv)
                result = gate({"s": r}, self.policy)
                self.assertEqual((result.verdict, result.code), (Tri.ABSTAIN, "INVALID_READING"))

    def test_huge_policy_numbers_rejected_and_forged_values_abstain(self):
        for field, code in (("floor", "SEAT_INVALID"), ("weight", "SEAT_INVALID"),
                            ("alpha_council_bound", "POLICY_ALPHA_INVALID")):
            for huge in (10**1000, -(10**1000)):
                with self.subTest(field=field, negative=huge < 0):
                    original = self.policy if field == "alpha_council_bound" else self.seat
                    with self.assertRaises(PolicyError) as raised:
                        dataclasses.replace(original, **{field: huge})
                    self.assertEqual(raised.exception.code, code)
                    forged = dataclasses.replace(original)
                    object.__setattr__(forged, field, huge)
                    p = forged if field == "alpha_council_bound" else dataclasses.replace(self.policy)
                    if field != "alpha_council_bound":
                        object.__setattr__(p, "seats", (forged,))
                    result = gate({"s": self.reading}, p)
                    self.assertEqual((result.verdict, result.code), (Tri.ABSTAIN, code))

    def test_nan_comparison_retains_tie(self):
        self.assertEqual(lam.compare_log(math.nan, 0.0), lam.TIE)
        self.assertEqual(lam.compare_log(0.0, math.nan), lam.TIE)


if __name__ == "__main__":
    unittest.main()
