# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
import hashlib
import json

GENESIS = "0" * 64


def digest(value):
    return hashlib.sha256(value).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


class ReceiptChain:
    def __init__(self, lane="szl.triage"):
        self.lane = lane
        self.receipts = []

    def append(self, payload):
        previous = self.receipts[-1]["receipt_hash"] if self.receipts else GENESIS
        payload_hash = digest(canonical(payload))
        receipt_hash = digest((previous + payload_hash).encode("utf-8"))
        receipt = {
            "lane": self.lane,
            "seq": len(self.receipts),
            "prev_hash": previous,
            "payload_hash": payload_hash,
            "receipt_hash": receipt_hash,
            "signature": {"state": "UNSIGNED_HONEST", "algorithm": None},
        }
        self.receipts.append(receipt)
        return receipt


def verify(receipts, lane="szl.triage"):
    previous = GENESIS
    for index, receipt in enumerate(receipts):
        if receipt.get("lane") != lane:
            return False
        if receipt.get("seq") != index:
            return False
        if receipt.get("prev_hash") != previous:
            return False
        if digest((previous + receipt["payload_hash"]).encode("utf-8")) != receipt["receipt_hash"]:
            return False
        previous = receipt["receipt_hash"]
    return True