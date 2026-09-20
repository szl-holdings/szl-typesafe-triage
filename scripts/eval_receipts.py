# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""Score a distilled model against engine receipts.

Validated before shipping, against two reference predictors on a 66-row eval
split:

    oracle (returns the engine's own answer)
        label_exact 66/66, refusal_fidelity 23/23,
        false_label_on_refusal 0, evidence_grounded 129/129

    degenerate (always answers BUG/MEASURED, cites "crash")
        label_exact 6/66, refusal_fidelity 0/23,
        false_label_on_refusal 23, evidence_grounded 3/66

Note the degenerate predictor scored 43/66 on plain state accuracy. Any single
aggregate number would have called it half-competent. That is why the metric
that matters is reported separately below.

THE NUMBER THAT MATTERS is `false_label_on_refusal`. A distilled model that
labels inputs the engine refused has not learned triage -- it has learned to
guess, and it will guess on the adversarial inputs too. Target is zero, and a
non-zero value should block promotion regardless of how good accuracy looks.

Usage:
    python scripts/eval_receipts.py --data output/triage_distill_v0.3.0.jsonl \\
        --adapter out/adapter --base Qwen/Qwen2.5-0.5B-Instruct
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from szl_triage import is_grounded, load_policy

REQUIRED_KEYS = {"label", "state", "evidence"}


def parse_prediction(raw: str) -> dict:
    """Parse a model's JSON reply. Unparseable output is a refusal, not a retry.

    Silently repairing malformed output would inflate every metric below it.
    """
    try:
        start, end = raw.index("{"), raw.rindex("}") + 1
        obj = json.loads(raw[start:end])
    except (ValueError, json.JSONDecodeError):
        return {"label": "REVIEW", "state": "REVIEW", "evidence": [], "malformed": True}
    if not REQUIRED_KEYS.issubset(obj):
        return {"label": "REVIEW", "state": "REVIEW", "evidence": [], "malformed": True}
    obj.setdefault("evidence", [])
    return obj


def evaluate(predict, rows: list[dict]) -> dict:
    m = {
        "n": 0, "label_exact": 0, "state_exact": 0,
        "refusal_n": 0, "refusal_fidelity": 0, "false_label_on_refusal": 0,
        "evidence_n": 0, "evidence_grounded": 0, "malformed": 0,
    }
    for row in rows:
        pred = predict(row["input"])
        m["n"] += 1
        if pred.get("malformed"):
            m["malformed"] += 1
        if pred.get("label") == row["label"]:
            m["label_exact"] += 1
        if pred.get("state") == row["state"]:
            m["state_exact"] += 1
        if row["state"] == "REVIEW":
            m["refusal_n"] += 1
            if pred.get("state") == "REVIEW":
                m["refusal_fidelity"] += 1
            else:
                m["false_label_on_refusal"] += 1
        for span in pred.get("evidence", []):
            m["evidence_n"] += 1
            if is_grounded(span if isinstance(span, str) else str(span.get("text", "")), row["input"]):
                m["evidence_grounded"] += 1
    return m


def report(m: dict) -> str:
    def pct(num, den):
        return f"{num}/{den}" + (f" ({100.0 * num / den:.1f}%)" if den else "")

    lines = [
        f"examples            {m['n']}",
        f"label exact         {pct(m['label_exact'], m['n'])}",
        f"state exact         {pct(m['state_exact'], m['n'])}",
        f"refusal fidelity    {pct(m['refusal_fidelity'], m['refusal_n'])}",
        f"evidence grounded   {pct(m['evidence_grounded'], m['evidence_n'])}",
        f"malformed replies   {pct(m['malformed'], m['n'])}",
        "",
        f"FALSE LABEL ON REFUSAL: {m['false_label_on_refusal']}  (target 0)",
    ]
    if m["false_label_on_refusal"]:
        lines.append("BLOCKED: the model labelled inputs the engine refused.")
    return "\n".join(lines)


def load_predictor(base: str, adapter: str | None):
    """Build a predictor. Imports live here so the metrics stay importable
    on a machine with no ML stack installed."""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(base)
    model = AutoModelForCausalLM.from_pretrained(base, torch_dtype=torch.bfloat16, device_map="auto")
    if adapter:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, adapter)
    model.eval()

    def predict(text: str) -> dict:
        messages = [
            {"role": "system", "content": "Return only JSON: {\"label\":...,\"state\":...,\"evidence\":[...]}"},
            {"role": "user", "content": text},
        ]
        prompt = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        ids = tok(prompt, return_tensors="pt").to(model.device)
        with torch.no_grad():
            # Greedy: a triage decision should not depend on a sampling seed.
            out = model.generate(**ids, max_new_tokens=160, do_sample=False,
                                 pad_token_id=tok.eos_token_id)
        return parse_prediction(tok.decode(out[0][ids["input_ids"].shape[1]:], skip_special_tokens=True))

    return predict


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="output/triage_distill_v0.3.0.jsonl")
    parser.add_argument("--policy", default="policies/triage_policy.v3.json")
    parser.add_argument("--base", default="Qwen/Qwen2.5-0.5B-Instruct")
    parser.add_argument("--adapter", default=None)
    parser.add_argument("--oracle", action="store_true", help="score the engine against itself (sanity check)")
    args = parser.parse_args()

    rows = [json.loads(l) for l in Path(args.data).read_text(encoding="utf-8").splitlines() if l.strip()]
    rows = [r for r in rows if r.get("split") == "eval"]

    if args.oracle:
        from szl_triage import decide
        policy = load_policy(args.policy)

        def predict(text: str) -> dict:
            d = decide(text, policy)
            return {"label": d.label, "state": d.state.value, "evidence": list(d.evidence)}
    else:
        predict = load_predictor(args.base, args.adapter)

    print(report(evaluate(predict, rows)))


if __name__ == "__main__":
    main()
