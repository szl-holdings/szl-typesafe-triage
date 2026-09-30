"""Compatibility entry point for retained release-receipt integrity verification.

This command never implicitly trains or loads a GPU model, deletes a previous
stage receipt, or rewrites release history. A zero exit means recorded evidence
is internally consistent; a valid BLOCKED receipt remains NOT_PROMOTABLE.
Performance is audited separately by gate.py / qualify_predictions.py against
all six sealed criteria. Neither offline audit confers release authority.
"""
from __future__ import annotations

from verify_release_receipts import main


if __name__ == "__main__":
    raise SystemExit(main())
