# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""Real pipeline/receipt regressions; hashes are not signatures or authority."""
import copy

from szl_triage import ReceiptChain, decide, verify_receipts


def test_payload_digest_tampering_is_rejected(policy):
    chain = ReceiptChain()
    decide("crash traceback exception", policy, chain=chain)
    altered = copy.deepcopy(chain.receipts)
    digest = altered[0]["payload_hash"]
    altered[0]["payload_hash"] = ("0" if digest[0] != "0" else "1") + digest[1:]
    assert verify_receipts(altered, lane=chain.lane) is False
    assert verify_receipts(chain.receipts, lane=chain.lane) is True


def test_receipt_reordering_is_rejected(policy):
    chain = ReceiptChain()
    for text in ("crash traceback exception", "invoice refund overcharged"):
        decide(text, policy, chain=chain)
    assert verify_receipts(list(reversed(chain.receipts)), lane=chain.lane) is False
    assert verify_receipts(chain.receipts, lane=chain.lane) is True


def test_custom_lane_requires_the_matching_expected_lane(policy):
    chain = ReceiptChain(lane="szl.triage.fixture.custom")
    decide("crash traceback exception", policy, chain=chain)
    assert verify_receipts(chain.receipts, lane=chain.lane) is True
    assert verify_receipts(chain.receipts) is False
