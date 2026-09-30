"""Compatibility entry point for the six-criterion offline prediction audit.

The former implicit GPU gate ignored label accuracy in its PROMOTABLE verdict.
It is retired. Explicit prediction input and a new output path are required.
No model is loaded, no retained receipt is overwritten, and an audit pass never
grants release authority. Use challenge_eval.py for explicit model execution.
"""
from __future__ import annotations

from qualify_predictions import main


if __name__ == "__main__":
    raise SystemExit(main())
