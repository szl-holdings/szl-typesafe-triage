"""Fresh challenge control flow and scoring without GPU packages or weights."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import challenge_eval as challenge  # noqa: E402


def challenge_rows():
    rows = []
    for label in ("BUG", "BILLING", "SECURITY", "FEATURE", "SUPPORT", "REVIEW"):
        for index in range(12 if label == "REVIEW" else 6):
            rows.append({"input": f"Example {label} {index}", "label": label,
                         "state": "REVIEW" if label == "REVIEW" else "MEASURED",
                         "evidence": [], "split": "eval",
                         "probe_class": "STEERING" if label == "REVIEW" else "PARAPHRASE",
                         "label_provenance": "DECLARED_TEST_LABELS"})
    return rows


def write_rows(path, rows):
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


@pytest.fixture
def fake_run(tmp_path, monkeypatch):
    evidence = tmp_path / "evidence"
    (evidence / "frozen").mkdir(parents=True)
    artifact_root = tmp_path / "artifacts"
    adapter = artifact_root / "alternate" / "seed11"
    adapter.mkdir(parents=True)
    (adapter / "adapter_model.safetensors").write_bytes(b"indexed-weights")
    (adapter / "adapter_config.json").write_text("{}", encoding="utf-8")
    (adapter / "chat_template.jinja").write_text("original template", encoding="utf-8")
    index = [{"seed": 11, "local_path": "alternate/seed11",
              "adapter_sha256": challenge.digest(adapter / "adapter_model.safetensors")}]
    (evidence / "adapter-index.json").write_text(json.dumps(index), encoding="utf-8")
    write_rows(evidence / "frozen/train.jsonl", [{"row": {"input": "Train input"}}])
    write_rows(evidence / "frozen/held.jsonl", [{"prompt": "Held input"}])
    rows = challenge_rows()
    corpus = tmp_path / "corpus.jsonl"
    write_rows(corpus, rows)
    args = challenge.parser().parse_args([
        "--artifact-root", str(artifact_root), "--evidence", str(evidence),
        "--corpus", str(corpus), "--output", str(tmp_path / "fresh.json"), "--eager",
    ])
    audit = {"integrity_status": "PASS", "bundle_sha256": "unchanged-bundle",
             "promotion_status": "NOT_PROMOTABLE", "release_gate": {"status": "BLOCKED"}}
    monkeypatch.setattr(challenge, "audit", lambda _: copy.deepcopy(audit))
    monkeypatch.setattr(challenge, "evaluator_identity", lambda: {"head": "source-before"})
    monkeypatch.setattr(challenge, "template_contract", lambda _: {"mode": "text-only-nonthinking"})
    calls = []
    loaded = []
    model = SimpleNamespace(config=SimpleNamespace(_commit_hash="observed-base"))
    answers = {row["input"]: {"label": row["label"], "state": row["state"],
                              "evidence": [row["input"]] if row["state"] == "MEASURED" else []}
               for row in rows}

    def generate(model, tokenizer, prompt):
        calls.append(prompt)
        return json.dumps(answers[prompt]), 0.25

    def load(adapter, eager):
        loaded.append((str(adapter), eager))
        return model, object(), generate, {"device": "fake"}

    monkeypatch.setattr(challenge, "load_runtime", load)
    return SimpleNamespace(args=args, rows=rows, audit=audit, calls=calls, loaded=loaded,
                           adapter=adapter, answers=answers, generate=generate, load=load)


def test_complete_suite_uses_shared_runtime_and_retains_all_raw_outputs(fake_run):
    report = challenge.run_challenge(fake_run.args)
    assert fake_run.loaded == [(str(fake_run.adapter), True)]
    assert fake_run.calls == [row["input"] for row in fake_run.rows]
    assert report["state"] == "EXECUTED"
    assert report["rows_completed"] == 42
    assert report["metrics"]["joint_exact"] == 42
    assert report["metrics"]["refusal_correct"] == 12
    assert report["metrics"]["target_evidence_exact"] == 12
    assert report["metrics"]["missing_evidence_on_measured"] == 0
    assert report["metrics"]["nonempty_evidence_on_refusal"] == 0
    assert report["behavioral_failures_observed"] is False
    assert report["metrics"]["by_probe_class"] == {
        "PARAPHRASE": {"rows": 30, "joint_exact": 30},
        "STEERING": {"rows": 12, "joint_exact": 12},
    }
    assert all(row["raw_output"] and row["parsed"] for row in report["results"])
    assert report["promotion_status"] == "NOT_PROMOTABLE"
    assert report["release_status"] == "BLOCKED"
    assert report["prior_release_gate"] == {"status": "BLOCKED"}
    assert report["corpus"]["declared_label_provenance"] == {"DECLARED_TEST_LABELS": 42}
    assert report["corpus_sha256_after"] == report["corpus"]["sha256"]
    assert report["tokenizer_files_sha256_after"] == report["tokenizer_files_sha256"]
    assert report["base_revision_observed"] == "observed-base"
    assert report["overlap"]["exact_training_overlaps"] == 0
    assert not fake_run.args.output.exists(), "Only the CLI writes the final receipt"


def test_metrics_keep_silent_abstention_and_false_labels_separate(fake_run):
    refusal = fake_run.rows[-1]
    ordinary = fake_run.rows[0]
    predictions = [
        challenge.score_output(refusal, '{"label":"BUG","state":"MEASURED","evidence":[]}', .1, 1),
        challenge.score_output(refusal, 'not json', .1, 2),
        challenge.score_output(refusal, '{"label":"REVIEW","state":"MEASURED","evidence":[]}', .1, 3),
        challenge.score_output(ordinary, '{"label":"REVIEW","state":"REVIEW","evidence":[]}', .1, 4),
    ]
    metrics = challenge.aggregate_results(predictions)
    assert metrics["gold_refusals"] == metrics["refusal_failures"] == 3
    assert metrics["false_label_on_refusal"] == 1
    assert metrics["malformed_on_refusal"] == 2
    assert metrics["refusal_correct"] == 0
    assert metrics["evidence_grounding_rate"] is None
    assert metrics["joint_exact"] == 0


@pytest.mark.parametrize("raw", [
    '{"label":null,"state":"MEASURED","evidence":[]}',
    '{"label":"NOT_A_LABEL","state":"MEASURED","evidence":[]}',
    '{"label":"BUG","state":"UNKNOWN","evidence":[]}',
    '{"label":"BUG","label":"REVIEW","state":"MEASURED","evidence":[]}',
    '{"label":NaN,"state":"MEASURED","evidence":[]}',
    '{"label":"BUG","state":"MEASURED","evidence":[false]}',
])
def test_invalid_typed_outputs_are_not_credited(raw):
    result = challenge.score_output(challenge_rows()[0], raw, .1, 1)
    assert result["typed_json_valid"] is False
    assert result["joint_exact"] is False


def test_nonverbatim_evidence_is_counted_and_raw_output_preserved():
    raw = '{"label":"BUG","state":"MEASURED","evidence":["Example","example","invented"]}'
    result = challenge.score_output(challenge_rows()[0], raw, .1, 1)
    metrics = challenge.aggregate_results([result])
    assert result["raw_output"] == raw
    assert result["grounded_evidence_flags"] == [True, False, False]
    assert metrics["ungrounded_evidence_spans"] == 2
    assert metrics["evidence_grounding_rate"] == 1 / 3


@pytest.mark.parametrize("kind", ["missing_measured", "nonempty_refusal"])
def test_evidence_contract_violation_marks_fresh_run_behavior_failure(fake_run, kind):
    row = fake_run.rows[0] if kind == "missing_measured" else fake_run.rows[-1]
    fake_run.answers[row["input"]]["evidence"] = [] if kind == "missing_measured" else [row["input"]]
    report = challenge.run_challenge(fake_run.args)
    metric = "missing_evidence_on_measured" if kind == "missing_measured" else "nonempty_evidence_on_refusal"
    assert report["metrics"][metric] == 1
    assert report["metrics"]["joint_exact"] == 42
    assert report["metrics"]["ungrounded_evidence_spans"] == 0
    assert report["behavioral_failures_observed"] is True
    assert report["promotion_status"] == "NOT_PROMOTABLE"
    if kind == "nonempty_refusal":
        assert report["metrics"]["refusal_failures"] == 1


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity", "1e400", "-1e400"])
def test_nonfinite_extra_corpus_fields_are_rejected_before_model_load(fake_run, constant):
    lines = fake_run.args.corpus.read_text(encoding="utf-8").splitlines()
    lines[0] = lines[0][:-1] + ', "extra": {"nested": [' + constant + ']}}'
    fake_run.args.corpus.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Non-finite corpus number"):
        challenge.run_challenge(fake_run.args)
    assert fake_run.loaded == []


@pytest.mark.parametrize("mutation,error", [
    (lambda rows: rows.pop(), "all 42 rows"),
    (lambda rows: rows[1].update(input=rows[0]["input"]), "Duplicate challenge input"),
    (lambda rows: rows[0].update(label="REVIEW"), "target label/state"),
    (lambda rows: rows[0].update(evidence=["not present"]), "target evidence"),
    (lambda rows: rows[0].update(split="train"), "split/class/provenance"),
    (lambda rows: rows[0].update(label_provenance=""), "split/class/provenance"),
    (lambda rows: rows[0].update(probe_class="STEERING"), "class disagrees"),
    (lambda rows: rows[0].update(label="BILLING"), "strata"),
])
def test_invalid_corpus_is_rejected_before_model_load(fake_run, mutation, error):
    mutation(fake_run.rows)
    write_rows(fake_run.args.corpus, fake_run.rows)
    with pytest.raises(ValueError, match=error):
        challenge.run_challenge(fake_run.args)
    assert fake_run.loaded == []


def test_duplicate_corpus_fields_are_rejected(fake_run):
    data = fake_run.args.corpus.read_text(encoding="utf-8")
    fake_run.args.corpus.write_text(data.replace('"split": "eval"', '"split":"eval","split":"eval"', 1))
    with pytest.raises(ValueError, match="Duplicate corpus field"):
        challenge.run_challenge(fake_run.args)
    assert fake_run.loaded == []


@pytest.mark.parametrize("target", ["weights", "config", "tokenizer", "corpus", "source", "template", "audit"])
def test_changed_inputs_fail_after_inference_and_preserve_predictions(fake_run, monkeypatch, target):
    if target == "source":
        identities = iter([{"head": "before"}, {"head": "after"}])
        monkeypatch.setattr(challenge, "evaluator_identity", lambda: next(identities))
    elif target == "template":
        contracts = iter([{"mode": "before"}, {"mode": "after"}])
        monkeypatch.setattr(challenge, "template_contract", lambda _: next(contracts))
    elif target == "audit":
        reports = iter([fake_run.audit, {**fake_run.audit, "integrity_status": "FAIL"}])
        monkeypatch.setattr(challenge, "audit", lambda _: next(reports))
    else:
        path = {"weights": fake_run.adapter / "adapter_model.safetensors",
                "config": fake_run.adapter / "adapter_config.json",
                "tokenizer": fake_run.adapter / "chat_template.jinja",
                "corpus": fake_run.args.corpus}[target]

        def changing_load(adapter, eager):
            runtime = fake_run.load(adapter, eager)
            path.write_bytes(path.read_bytes() + b" ")
            return runtime

        monkeypatch.setattr(challenge, "load_runtime", changing_load)
    with pytest.raises(challenge.ChallengeExecutionError, match="changed during challenge") as error:
        challenge.run_challenge(fake_run.args)
    assert error.value.receipt["state"] == "FAILED"
    assert error.value.receipt["rows_completed"] == 42
    assert len(error.value.receipt["results"]) == 42
    assert "metrics" not in error.value.receipt


def test_runtime_failure_keeps_partial_raw_predictions(fake_run, monkeypatch):
    def broken_generate(model, tokenizer, prompt):
        if len(fake_run.calls) == 2:
            raise RuntimeError("synthetic runtime failure")
        return fake_run.generate(model, tokenizer, prompt)

    monkeypatch.setattr(challenge, "load_runtime", lambda *a: (object(), object(), broken_generate, {}))
    model = SimpleNamespace(config=SimpleNamespace(_commit_hash=None))
    monkeypatch.setattr(challenge, "load_runtime", lambda *a: (model, object(), broken_generate, {}))
    with pytest.raises(challenge.ChallengeExecutionError) as error:
        challenge.run_challenge(fake_run.args)
    receipt = error.value.receipt
    assert receipt["error"] == "synthetic runtime failure"
    assert receipt["rows_completed"] == 2
    assert len(receipt["results"]) == 2


def test_unindexed_adapter_never_loads(fake_run):
    (fake_run.adapter / "adapter_model.safetensors").write_bytes(b"different")
    with pytest.raises(ValueError, match="indexed weight"):
        challenge.run_challenge(fake_run.args)
    assert fake_run.loaded == []


def test_adapter_path_escape_is_rejected(fake_run):
    path = fake_run.args.evidence / "adapter-index.json"
    index = json.loads(path.read_text())
    index[0]["local_path"] = "../escaped-adapter"
    path.write_text(json.dumps(index))
    with pytest.raises(ValueError):
        challenge.run_challenge(fake_run.args)
    assert fake_run.loaded == []


def test_existing_output_is_never_overwritten(fake_run):
    fake_run.args.output.write_text("preserve", encoding="utf-8")
    with pytest.raises(FileExistsError):
        challenge.run_challenge(fake_run.args)
    assert fake_run.args.output.read_text() == "preserve"
    assert fake_run.loaded == []


@pytest.mark.parametrize("root_name", ["evidence", "artifact_root"])
def test_output_cannot_mutate_read_only_input_roots(fake_run, root_name, monkeypatch):
    fake_run.args.output = getattr(fake_run.args, root_name) / "new-receipt.json"
    monkeypatch.setattr(challenge, "parser", lambda: SimpleNamespace(parse_args=lambda _: fake_run.args))
    assert challenge.main([]) == 2
    assert not fake_run.args.output.exists()
    assert fake_run.loaded == []


def test_cli_writes_an_exclusive_complete_receipt(fake_run, monkeypatch):
    monkeypatch.setattr(challenge, "parser", lambda: SimpleNamespace(parse_args=lambda _: fake_run.args))
    assert challenge.main([]) == 0
    data = fake_run.args.output.read_bytes()
    assert json.loads(data)["state"] == "EXECUTED"
    assert challenge.main([]) == 2
    assert fake_run.args.output.read_bytes() == data
    assert len(fake_run.loaded) == 1


def test_cli_writes_failure_receipt_on_runtime_error(fake_run, monkeypatch):
    monkeypatch.setattr(challenge, "parser", lambda: SimpleNamespace(parse_args=lambda _: fake_run.args))

    def broken(*args):
        raise RuntimeError("GPU unavailable in synthetic test")

    monkeypatch.setattr(challenge, "load_runtime", broken)
    assert challenge.main([]) == 2
    report = json.loads(fake_run.args.output.read_text())
    assert report["schema"] == challenge.SCHEMA
    assert report["state"] == "FAILED"
    assert report["rows_completed"] == 0
    assert report["promotion_status"] == "NOT_PROMOTABLE"


def test_cli_help_never_loads_ml_or_writes_files(tmp_path):
    # Block packages in a fresh process while executing the actual CLI help path.
    script = """
import importlib.abc
import runpy
import sys
class RejectML(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'torch', 'transformers', 'unsloth', 'peft'}:
            raise AssertionError('ML import attempted: ' + fullname)
sys.meta_path.insert(0, RejectML())
target = sys.argv[1]
sys.argv = [target, '--help']
runpy.run_path(target, run_name='__main__')
"""
    result = subprocess.run([sys.executable, "-I", "-c", script, str(ROOT / "scripts/challenge_eval.py")],
                            cwd=tmp_path, capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
    assert "--corpus" in result.stdout
    assert "--limit" not in result.stdout
    assert list(tmp_path.iterdir()) == []


def test_repository_challenge_is_complete_and_declared_provenance_is_preserved():
    rows, description = challenge.load_corpus(ROOT / "policies/redteam_probes.verified.jsonl")
    assert len(rows) == 42
    assert description["probe_classes"] == {"PARAPHRASE": 30, "STEERING": 12}
    assert description["declared_label_provenance"] == {"HUMAN_RATIFIED_2026-09-21": 42}
    assert description["label_provenance_verification"] == "FILE_DECLARATION_ONLY_NOT_INDEPENDENTLY_VERIFIED"


def test_exact_overlap_is_reported_without_claiming_semantic_independence(fake_run):
    write_rows(fake_run.args.evidence / "frozen/train.jsonl", [{"row": {"input": fake_run.rows[0]["input"]}}])
    report = challenge.overlap_report(fake_run.rows, fake_run.args.evidence)
    assert report["exact_training_overlaps"] == 1
    assert report["semantic_independence"] == "NOT_ESTABLISHED"
