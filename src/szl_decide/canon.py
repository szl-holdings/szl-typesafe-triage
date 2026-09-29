# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""Canonical bytes for hashed szl.decide.* objects (INVENTION §2.11).

Every float is written as the string ``"f64:<16 hex digits>"``: the IEEE-754
binary64 bits, big-endian, lowercase. Keys are sorted, separators are compact,
the output is UTF-8 and NaN / Infinity are refused. A Python engine and a JS
verifier therefore produce identical bytes without depending on float-to-text
formatting.

Only JSON-native values are accepted: dict (str keys), list, tuple, str, int,
float, bool and None. Anything else, including Enum members and dataclasses,
raises `CanonError`, so a caller states each field explicitly. Integers must be
within ±(2**53 - 1) so that JavaScript reads them exactly.

This form is scoped to szl.decide.* objects. The FF-01 vectors digest is a
different, plain form (floats as JSON numbers); see `spec/lambda_v1_vectors.SOURCE`.
"""
from __future__ import annotations

import hashlib
import json
import math
import struct
from enum import Enum
from typing import Any

MAX_SAFE_INT = 2 ** 53 - 1
_HEX = frozenset("0123456789abcdef")


class CanonError(ValueError):
    """A value that has no canonical form (NaN, ±Inf, an unsafe integer, a foreign type)."""


def encode_f64(x: float) -> str:
    """'f64:' + the 16 lowercase hex digits of the IEEE-754 binary64 bits (big-endian)."""
    return "f64:" + struct.pack(">d", float(x)).hex()


def decode_f64(text: str) -> float:
    """Inverse of encode_f64. Refuses anything but exactly 'f64:' + 16 lowercase hex digits."""
    if not isinstance(text, str) or len(text) != 20 or not text.startswith("f64:"):
        raise ValueError(f"not an f64 literal: {text!r}")
    digits = text[4:]
    if any(c not in _HEX for c in digits):
        raise ValueError(f"not an f64 literal: {text!r}")
    return struct.unpack(">d", bytes.fromhex(digits))[0]


def is_f64_literal(text: Any) -> bool:
    try:
        decode_f64(text)
    except ValueError:
        return False
    return True


def _prepare(obj: Any, path: str) -> Any:
    if isinstance(obj, Enum):
        raise CanonError(f"{path}: Enum member {obj!r}; pass its value explicitly")
    if obj is None or isinstance(obj, bool):
        return obj
    if isinstance(obj, int):
        if not -MAX_SAFE_INT <= obj <= MAX_SAFE_INT:
            raise CanonError(f"{path}: integer {obj} is outside ±(2**53 - 1)")
        return int(obj)
    if isinstance(obj, float):
        if not math.isfinite(obj):
            raise CanonError(f"{path}: {obj!r} is not finite")
        return encode_f64(obj)
    if isinstance(obj, str):
        return str(obj)
    if isinstance(obj, (list, tuple)):
        return [_prepare(v, f"{path}[{i}]") for i, v in enumerate(obj)]
    if isinstance(obj, dict):
        out = {}
        for key, value in obj.items():
            if isinstance(key, Enum) or not isinstance(key, str):
                raise CanonError(f"{path}: key {key!r} is not a plain string")
            out[str(key)] = _prepare(value, f"{path}.{key}")
        return out
    raise CanonError(f"{path}: {type(obj).__name__} has no canonical form")


def canonical_bytes(obj: Any) -> bytes:
    """Canonical JSON bytes: f64 floats, sorted keys, compact, UTF-8, no NaN/Infinity."""
    return json.dumps(_prepare(obj, "$"), sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    """Lowercase hex SHA-256 of bytes."""
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise TypeError(f"sha256_hex takes bytes, got {type(data).__name__}")
    return hashlib.sha256(bytes(data)).hexdigest()


def canonical_sha256(obj: Any) -> str:
    """sha256_hex(canonical_bytes(obj))."""
    return sha256_hex(canonical_bytes(obj))
