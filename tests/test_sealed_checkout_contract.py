# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""Historical seal bytes must reproduce without changing the seal or other rules."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEGACY_CRLF = (
    "out/axis_collision.json", "out/despace_effect.json", "out/engine_only_probe.json",
    "out/gate_report_bf16_in_domain.json", "out/gate_report_bf16_red_team.json",
    "out/gate_report_int4_in_domain.json", "out/gate_report_int4_red_team.json",
    "out/lambda_sweep.json", "out/quant_refusal_curve.json", "out/quant_significance.json",
    "output/triage_distill_split_v0.4.0.jsonl", "policies/redteam_probes.verified.jsonl",
)


def test_exact_legacy_overrides_preserve_generic_and_lfs_rules():
    rules = [line for line in (ROOT / ".gitattributes").read_text().splitlines()
             if line and not line.startswith("#")]
    assert rules[:3] == ["* text=auto eol=lf", "*.ps1 text eol=crlf", "*.jsonl text eol=lf"]
    for suffix in ("safetensors", "bin", "gguf", "pt"):
        assert f"*.{suffix} filter=lfs diff=lfs merge=lfs -text" in rules
    for suffix in ("json", "md", "py"):
        assert f"*.{suffix} text eol=lf" in rules
    assert rules[-12:] == [f"{path} text eol=crlf" for path in LEGACY_CRLF]


def test_all_thirteen_artifacts_match_unchanged_historical_seal():
    seal = json.loads((ROOT / "out/release_seal.json").read_text())
    assert seal["seal_digest"] == "0eb47b29121ffd0a531a7cf74e61b989f67a84624a28014de6d09e70dd51dafd"
    assert set(seal["eval_digests"]) == {*LEGACY_CRLF, "policies/triage_policy.v3.json"}
    for name, expected in seal["eval_digests"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name
