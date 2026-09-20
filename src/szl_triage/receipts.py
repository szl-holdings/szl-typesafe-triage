# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""Hash-chained receipts.

Each receipt commits to the canonical bytes of its payload and to the hash of
its predecessor, so altering any earlier entry invalidates every later one.
`verify` is dependency-free and runs offline: a third party can check a chain
without this package, a key, or a network.

Signatures are reported as UNSIGNED_HONEST until a DSSE key is wired in. The
chain is never described as signed when it is not.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any

from .contracts import canonical

GENESIS = "0" * 64
SIGNATURE_UNSIGNED = "UNSIGNED_HONEST"


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _payload_hash(payload: Any) -> str:
    return _digest(canonical(payload).encode("utf-8"))


@dataclass
class ReceiptChain:
    """Append-only tamper-evident log."""

    lane: str = "szl.triage"
    receipts: list[dict[str, Any]] = field(default_factory=list)

    @property
    def head(self) -> str:
        return self.receipts[-1]["receipt_hash"] if self.receipts else GENESIS

    def append(self, payload: Any) -> dict[str, Any]:
        previous = self.head
        payload_hash = _payload_hash(payload)
        receipt = {
            "lane": self.lane,
            "seq": len(self.receipts),
            "prev_hash": previous,
            "payload_hash": payload_hash,
            "receipt_hash": _digest((previous + payload_hash).encode("ascii")),
            "signature": {"state": SIGNATURE_UNSIGNED, "algorithm": None},
        }
        self.receipts.append(receipt)
        return receipt


def verify(receipts: list[dict[str, Any]], lane: str = "szl.triage") -> bool:
    """Recompute the chain. False on any break, reorder, or edit."""
    previous = GENESIS
    for index, receipt in enumerate(receipts):
        if receipt.get("lane") != lane or receipt.get("seq") != index:
            return False
        if receipt.get("prev_hash") != previous:
            return False
        expected = _digest((previous + receipt["payload_hash"]).encode("ascii"))
        if expected != receipt.get("receipt_hash"):
            return False
        previous = receipt["receipt_hash"]
    return True
