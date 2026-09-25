"""The generated Hub card must retain scope boundaries and valid examples.

Compile only the two pure renderer functions: importing the historical study
script creates study directories and is unnecessary for a documentation test.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path


def generated_card():
    source = Path(__file__).resolve().parents[1] / "scripts/train_eval_publish.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    functions = [node for node in tree.body
                 if isinstance(node, ast.FunctionDef)
                 and node.name in {"percentage", "build_model_card"}]
    assert len(functions) == 2
    namespace = {
        "BASE_MODEL": "unsloth/Qwen3.5-0.8B",
        "HF_REPO": "SZLHOLDINGS/szl-triage-qwen3.5-0.8b-lora-study5",
        "RUN1_TAG": "triage-lora-run1",
        "STUDY_TAG": "triage-lora-study5-measured-20260922-111314",
    }
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(source), "exec"), namespace)
    # Deliberately non-perfect sample metrics ensure the card renders its inputs
    # instead of manufacturing a perfect result while documenting the boundary.
    metrics = [{"name": name, "strict_json_rate": 0.5, "joint_accuracy": 0.25,
                "failure_rows": 7}
               for name in ["base", "seed-011", "seed-023", "seed-037", "seed-053", "seed-071"]]
    aggregate = {"five_seed_summary": {"joint_accuracy": {"mean": 0.25, "sample_std": 0.125}}}
    return namespace["build_model_card"](metrics, aggregate, [])


def test_python_examples_are_syntactically_valid():
    card = generated_card()
    for index, snippet in enumerate(re.findall(r"```python\s*\n(.*?)```", card, re.DOTALL)):
        compile(snippet, f"generated-model-card-example-{index}", "exec")


def test_historical_gate_does_not_promote_the_later_study():
    card = generated_card()
    assert "[gate_report.json](./gate_report.json)" in card
    assert "66-row" in card and "113-row" in card
    assert "earlier 66-row gate with verdict `PROMOTABLE`" in card
    assert "not promotion of this later five-seed, 113-row study" in card
    assert "**BLOCKED — 11/12**" in card
    assert "**NOT_PROMOTABLE**" in card


def test_inference_documentation_does_not_claim_a_new_run():
    card = generated_card()
    assert "Inline inference example withdrawn" in card
    assert "No fresh inference was performed for this card correction" in card
    assert "scripts/train_eval_publish.py" in card
    assert "training, evaluation, and publication" in card
    assert 'output[inputs["input_ids"].shape:],[3]' not in card


def test_rendering_preserves_supplied_metrics():
    card = generated_card()
    assert "| base | 50.0% | N/A | N/A | 25.0% | N/A | N/A | 7 |" in card
    assert "**25.0%**" in card
    assert "**12.5%**" in card
