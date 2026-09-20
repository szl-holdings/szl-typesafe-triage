# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""Cryptographically sealed pre-registration.

A benchmark table is only evidence if the bar was set before the numbers
existed. Papers get this through registered reports; model releases almost
never do, and a README edited after the run is indistinguishable from one
written before it.

A seal commits, in a single digest, to:

* the promotion thresholds, canonicalized
* the SHA-256 of every evaluation file, by path
* the policy and its version
* the declared base model and the source commit

The seal is written and committed to version control *before training*. The
git timestamp anchors it in time; the digest anchors it in content. After the
evaluation runs, `verify` recomputes both. Loosening a threshold, editing a
held-out answer, or swapping an eval file changes the digest and the
published result is provably void.

This cannot stop a determined author from sealing twice and reporting the
kinder seal -- nothing short of a third-party timestamp can. It does make
silent, retroactive goalpost movement detectable by anyone with the
repository.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .contracts import canonical

SEAL_SCHEMA = "szl.triage.seal/v1"


def file_digest(path: str | Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


@dataclass(frozen=True)
class Seal:
    schema: str
    thresholds: dict[str, Any]
    eval_digests: dict[str, str]
    policy_name: str
    policy_version: str
    base_model: str
    source_commit: str
    sealed_at: str
    seal_digest: str = field(default="")

    def payload(self) -> dict[str, Any]:
        """Everything the digest commits to. Excludes the digest itself."""
        return {
            "schema": self.schema,
            "thresholds": self.thresholds,
            "eval_digests": self.eval_digests,
            "policy_name": self.policy_name,
            "policy_version": self.policy_version,
            "base_model": self.base_model,
            "source_commit": self.source_commit,
            "sealed_at": self.sealed_at,
        }

    def compute_digest(self) -> str:
        return hashlib.sha256(canonical(self.payload()).encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {**self.payload(), "seal_digest": self.seal_digest}


def create(
    thresholds: dict[str, Any],
    eval_files: list[str | Path],
    policy_name: str,
    policy_version: str,
    base_model: str,
    source_commit: str,
    sealed_at: str,
) -> Seal:
    """Build a seal. Raises if any declared evaluation file is missing."""
    digests: dict[str, str] = {}
    for path in sorted(str(p) for p in eval_files):
        if not Path(path).is_file():
            raise FileNotFoundError(f"cannot seal a missing evaluation file: {path}")
        digests[Path(path).as_posix()] = file_digest(path)

    unsealed = Seal(
        schema=SEAL_SCHEMA,
        thresholds=thresholds,
        eval_digests=digests,
        policy_name=policy_name,
        policy_version=policy_version,
        base_model=base_model,
        source_commit=source_commit,
        sealed_at=sealed_at,
    )
    return Seal(**{**unsealed.to_dict(), "seal_digest": unsealed.compute_digest()})


def verify(
    seal_dict: dict[str, Any], repo_root: str | Path = "."
) -> tuple[bool, list[str]]:
    """Recompute a seal against the working tree.

    Returns (intact, findings). `intact` is False if the digest does not
    reproduce or any evaluation file changed after sealing.
    """
    findings: list[str] = []
    stored = seal_dict.get("seal_digest", "")
    seal = Seal(**{k: v for k, v in seal_dict.items() if k != "seal_digest"})

    recomputed = seal.compute_digest()
    if recomputed != stored:
        findings.append(
            f"seal digest mismatch: stored {stored[:16]} recomputed {recomputed[:16]}"
        )

    root = Path(repo_root)
    for relative, expected in seal.eval_digests.items():
        target = root / relative
        if not target.is_file():
            findings.append(f"sealed evaluation file is missing: {relative}")
            continue
        actual = file_digest(target)
        if actual != expected:
            findings.append(
                f"sealed evaluation file changed: {relative} "
                f"expected {expected[:16]} found {actual[:16]}"
            )

    return (not findings), findings
