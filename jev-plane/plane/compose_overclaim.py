"""Overclaim pack compose branch. Jev never ALLOW-alone and never mints LIVE.

compose.py dispatches pack_id ending in overclaim_reader.v1 here. Fixtures
overclaim_live_stamp.json / overclaim_measured_ok.json / overclaim_unavailable.json
used to SystemExit as unknown packs.
"""

from __future__ import annotations

from typing import Any, Callable

PACK_ID = "szl.overclaim_reader.v1"
PACK_SUFFIX = "overclaim_reader.v1"
NOUL_BLOCK = 0.65
CONFIDENCE_HOLD = 0.55
KEYS = (
    "evidence_class",
    "claims_live",
    "invents_joules",
    "treats_hf_as_source",
    "lambda_as_theorem",
    "unsigned_as_live",
    "overclaim_severity",
)

Ge = Callable[[float | None, float], bool]
Fmt = Callable[[float | None], str]


def apply(
    *,
    klass: tuple[str, float] | None,
    live: float | None,
    joules: float | None,
    hub: float | None,
    lam: float | None,
    unsigned: float | None,
    sev: float | None,
    reasons: list[str],
    labels: list[str],
    ge: Ge,
    fmt: Fmt,
    noul_block: float = NOUL_BLOCK,
    high_score: float = 1.5,
    conf_hold: float = CONFIDENCE_HOLD,
    missing: bool = False,
) -> dict[str, Any]:
    """Mutate reasons/labels. Return flags for compose.py to merge."""
    block_publish = False
    block_merge = False
    escalate = False
    request_info = False

    overclaim = (
        ge(live, noul_block)
        or ge(joules, noul_block)
        or ge(hub, noul_block)
        or ge(lam, noul_block)
        or ge(unsigned, noul_block)
        or ge(sev, high_score)
        or (klass is not None and klass[0] == "BLOCK")
    )

    if klass is not None and klass[0] == "UNAVAILABLE":
        request_info = True

    # Positive risk remains a block even when the class or a sibling is unavailable.
    if overclaim:
        reader_class = "BLOCK"
        block_publish = True
        block_merge = True
        escalate = True
        reasons.append(
            f"overclaim live={fmt(live)} joules={fmt(joules)} hub={fmt(hub)} "
            f"lambda={fmt(lam)} unsigned={fmt(unsigned)} severity={fmt(sev)}"
        )
    elif missing or klass is None or klass[0] == "UNAVAILABLE":
        reader_class = "UNAVAILABLE"
        block_merge = True
        request_info = True
        reasons.append("second reader UNAVAILABLE; never PASS")
    elif klass[0] == "HOLD" or klass[1] < conf_hold:
        reader_class = "HOLD"
        block_merge = True
        escalate = True
        name = klass[0]
        conf = fmt(klass[1])
        reasons.append(f"class={name} confidence={conf}")
    elif klass[0] == "MEASURED":
        reader_class = "MEASURED"
        labels.append("class:MEASURED")
        labels.append("reader:MEASURED")
        reasons.append("second reader MEASURED; still not LIVE; still not auto-merge")
    else:
        reader_class = "HOLD"
        block_merge = True
        reasons.append(f"unrecognized class={klass[0]}")

    return {
        "block_publish": block_publish,
        "block_merge": block_merge,
        "escalate": escalate,
        "request_info": request_info,
        "reader_class": reader_class,
    }
