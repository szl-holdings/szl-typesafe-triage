"""Offline source-contract tests for the v1.1.0 twelfth-gate preflight."""

import ast
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from types import ModuleType
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]


def load_runner():
    spec = importlib.util.spec_from_file_location(
        "twelfth_gate_preflight_test", ROOT / "scripts" / "twelfth_gate_v110.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_isolated_runner(repository, monkeypatch):
    """Model a checkout boundary even when pytest's temp root is elsewhere."""
    module = load_runner()
    paths = set(module.source_identity()) | {"scripts/train_lora.py"}
    for relative in paths:
        target = repository / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    monkeypatch.setattr(module, "REPO", repository)
    monkeypatch.setattr(module, "SCRIPTS", repository / "scripts")
    monkeypatch.setattr(module, "__file__", str(repository / "scripts/twelfth_gate_v110.py"))
    monkeypatch.setattr(module, "POWERSHELL_RUNNER", repository / "scripts/run_twelfth_gate_v110.ps1")
    monkeypatch.setattr(module, "TRAINER", repository / "scripts/train_lora.py")
    assert set(module.source_identity()) <= paths
    return module


def generated_trainer(module, seed=11):
    source = module.TRAINER.read_text(encoding="utf-8")
    patches = module.trainer_patches(seed, "frozen", "augmentation", False)
    return module.apply_trainer_patches(source, patches)


def test_generated_trainer_pins_base_revision_and_requires_response_masking():
    module = load_runner()
    patched = generated_trainer(module)
    contract = module.validate_trainer_contract(patched)

    assert contract == {
        "base_model": "Qwen/Qwen3.5-0.8B",
        "base_revision": "2fc06364715b967f1860aea9cf38778875588b17",
        "train_on_responses_only": "REQUIRED_FAIL_CLOSED",
    }
    assert 'revision=BASE_REVISION' in patched
    assert '"base_revision": BASE_REVISION' in patched
    assert "train_on_responses_only unavailable" not in patched


@pytest.mark.parametrize(
    "tamper",
    [
        lambda source: source.replace("revision=BASE_REVISION, ", "", 1),
        lambda source: source.replace("Qwen/Qwen3.5-0.8B", "unsloth/Qwen3.5-0.8B", 1),
        lambda source: source.replace("trainer = train_on_responses_only", "trainer = object", 1),
        lambda source: source.replace("processing_class=text_tok,", "processing_class=tok,", 1),
    ],
)
def test_generated_trainer_contract_rejects_unbound_or_optional_training(tamper):
    module = load_runner()
    with pytest.raises(ValueError):
        module.validate_trainer_contract(tamper(generated_trainer(module)))


def test_generated_trainer_contract_rejects_skipped_or_unrecorded_mask_proof():
    module = load_runner()
    source = generated_trainer(module)
    conditional = source.replace(
        "PROVIDER_RUNTIME = validate_provider_runtime()",
        "if False:\n    PROVIDER_RUNTIME = validate_provider_runtime()",
        1,
    )
    ignored = source.replace(
        "mask_contract = validate_trainer_response_labels(",
        "validate_trainer_response_labels(",
        1,
    )
    with pytest.raises(ValueError, match="module-reachable"):
        module.validate_trainer_contract(conditional)
    with pytest.raises(ValueError, match="mask_contract"):
        module.validate_trainer_contract(ignored)


def test_powershell_runner_is_local_only_and_enforces_host_limits():
    module = load_runner()
    source = module.POWERSHELL_RUNNER.read_text(encoding="utf-8")
    contract = module.validate_powershell_runner(source)

    assert contract == {
        "publish": "DISABLED_FAIL_CLOSED",
        "max_wallclock_minutes": 180,
        "thermal_guard_celsius": 78,
        "preflight_only_supported": True,
    }
    assert "git push " not in source
    assert "gh pr " not in source
    assert "publish-adapters" not in source


def test_powershell_runner_contract_rejects_a_publication_sink():
    module = load_runner()
    source = module.POWERSHELL_RUNNER.read_text(encoding="utf-8") + "\ngit push origin unsafe\n"
    with pytest.raises(ValueError, match="banned"):
        module.validate_powershell_runner(source)


def test_corpus_preamble_state_is_shared_by_preflight_and_generated_trainer(tmp_path, monkeypatch):
    module = load_runner()
    corpus = tmp_path / "study.jsonl"
    monkeypatch.setattr(module, "STUDY_CORPUS", corpus)

    absent, _ = module.generated_trainer(11)
    assert module.trainer_generation_context()["corpus_matches"] is False
    assert '("evidence/five-seed-study/frozen/train.jsonl",)' in absent

    corpus.write_text("mismatch\n", encoding="utf-8")
    mismatch, _ = module.generated_trainer(11)
    assert module.trainer_generation_context()["corpus_matches"] is False
    assert mismatch == absent

    expected = module.read_json(module.FROZEN / "experiment_manifest.json")["corpus_sha256"]
    real_sha = module.sha256_file
    monkeypatch.setattr(
        module,
        "sha256_file",
        lambda path: expected if Path(path) == corpus else real_sha(path),
    )
    matching, context = module.generated_trainer(11)
    assert context["corpus_matches"] is True
    assert "output/triage_distill_v0.5.0.jsonl" in matching


class TextTokenizer:
    chat_template = "template-v1"
    eos_token_id = 2

    def __init__(self):
        self.render_calls = []
        self.encode_calls = []

    def apply_chat_template(self, messages, **kwargs):
        self.render_calls.append((messages, kwargs))
        return "rendered"

    def decode(self, tokens, **kwargs):
        return "decoded"

    def __call__(self, *, text, return_tensors=None, add_special_tokens=False):
        self.encode_calls.append((text, return_tensors, add_special_tokens))
        return {"input_ids": [1, 2, 3]}


class ProcessorThatMustNotRun:
    def __init__(self, tokenizer):
        self.tokenizer = tokenizer
        self.image_processor = object()

    def __call__(self, *args, **kwargs):
        raise AssertionError("processor boundary was used")


def test_text_boundary_uses_only_resolved_tokenizer_and_no_duplicate_special_tokens():
    from triage_text import build_generation_inputs, render_training_example

    tokenizer = TextTokenizer()
    processor = ProcessorThatMustNotRun(tokenizer)
    rendered = render_training_example(processor, "prompt", "response")
    inputs = build_generation_inputs(processor, "prompt", return_tensors=None)

    assert rendered == "rendered"
    assert inputs == {"input_ids": [1, 2, 3]}
    assert tokenizer.render_calls[0][1]["enable_thinking"] is False
    assert tokenizer.render_calls[0][1]["add_generation_prompt"] is False
    assert tokenizer.encode_calls == [("rendered", None, False)]


def test_response_only_contract_checks_actual_collator_labels():
    from triage_text import validate_response_only_batch

    good = {"input_ids": [[10, 11, 20, 21, 30, 31]],
            "labels": [[-100, -100, -100, -100, 30, 31]]}
    assert validate_response_only_batch(good, [20, 21]) == {
        "rows": 1, "masked_tokens": 4, "supervised_response_tokens": 2,
    }
    with pytest.raises(RuntimeError, match="remain trainable"):
        validate_response_only_batch(
            {"input_ids": good["input_ids"], "labels": [[-100, 11, -100, -100, 30, 31]]},
            [20, 21],
        )
    with pytest.raises(RuntimeError, match="no trainable"):
        validate_response_only_batch(
            {"input_ids": good["input_ids"], "labels": [[-100] * 6]}, [20, 21],
        )


@pytest.mark.parametrize("mode", ["helper-fails", "bad-last-labels", "missing-row", "valid"])
def test_generated_training_section_requires_masking_before_train_or_save(mode, tmp_path):
    from triage_text import validate_trainer_response_labels

    module = load_runner()
    tree = ast.parse(generated_trainer(module))
    start = next(index for index, node in enumerate(tree.body)
                 if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call)
                 and module._call_name(node.value) == "train_on_responses_only")
    finish = next(index for index, node in enumerate(tree.body)
                  if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
                  and module._call_name(node.value) == "text_tok.save_pretrained")
    section = ast.Module(body=tree.body[start:finish + 1], type_ignores=[])
    calls = []

    class Trainer:
        train_dataset = list(range(564 if mode == "missing-row" else 565))

        def data_collator(self, records):
            labels = [-100, -100, -100, 30]
            if mode == "bad-last-labels" and records == [564]:
                labels[0] = 10
            return {"input_ids": [[10, 20, 21, 30]], "labels": [labels]}

        def train(self):
            calls.append("train")
            return SimpleNamespace(training_loss=0.5)

    returned_trainer = Trainer()

    def mask(original, **kwargs):
        if mode == "helper-fails":
            raise RuntimeError("mask helper failed")
        return returned_trainer

    class Tokenizer:
        def __call__(self, **kwargs):
            return {"input_ids": [20, 21]}

        def save_pretrained(self, path):
            calls.append("save-tokenizer")

    model = SimpleNamespace(named_parameters=lambda: [], peft_config={"default": SimpleNamespace()},
                            save_pretrained=lambda path: calls.append("save-model"))
    namespace = {
        "trainer": object(), "train_on_responses_only": mask, "text_tok": Tokenizer(),
        "validate_trainer_response_labels": validate_trainer_response_labels,
        "time": time, "json": json, "model": model, "OUT": tmp_path,
        "source_identity": lambda: {"source": "unchanged"},
        "SOURCE_BEFORE": {"source": "unchanged"},
        "study_input_audit": lambda: {"study": "unchanged"},
        "STUDY_AUDIT_BEFORE": {"study": "unchanged"},
        "BASE_REVISION": module.BASE_REVISION,
    }
    code = compile(section, "actual-generated-training-section", "exec")
    if mode == "valid":
        exec(code, namespace)
        assert calls == ["train", "save-model", "save-tokenizer"]
        assert namespace["trainer"] is returned_trainer
        assert namespace["mask_contract"]["rows"] == 565
    else:
        with pytest.raises(RuntimeError):
            exec(code, namespace)
        assert calls == []


def test_generated_sft_constructor_uses_resolved_text_tokenizer():
    module = load_runner()
    tree = ast.parse(generated_trainer(module))
    constructor = next(node for node in tree.body if isinstance(node, ast.Assign)
                       and isinstance(node.value, ast.Call)
                       and module._call_name(node.value) == "SFTTrainer")
    tokenizer = TextTokenizer()

    class WrapperThatRaises:
        def __call__(self, *args, **kwargs):
            raise AssertionError("unresolved processor used by trainer")

    def trainer_constructor(**kwargs):
        kwargs["processing_class"](text="training text", add_special_tokens=False)
        return kwargs

    namespace = {"SFTTrainer": trainer_constructor, "SFTConfig": lambda **kwargs: kwargs,
                 "model": object(), "ds": [], "OUT": Path("out"),
                 "text_tok": tokenizer, "tok": WrapperThatRaises()}
    exec(compile(ast.Module(body=[constructor], type_ignores=[]), "generated-constructor", "exec"), namespace)
    assert namespace["trainer"]["processing_class"] is tokenizer


def make_adapter(path: Path, *, base_model="Qwen/Qwen3.5-0.8B", source="commit",
                 trainer_sha="trainer"):
    import twelfth_gate_contract as contract

    path.mkdir(parents=True)
    (path / "adapter_model.safetensors").write_bytes(b"weights")
    (path / "adapter_config.json").write_text(
        json.dumps({"base_model_name_or_path": base_model, "revision": contract.BASE_REVISION}),
        encoding="utf-8",
    )
    (path / "tokenizer.json").write_text('{}', encoding="utf-8")
    (path / "tokenizer_config.json").write_text('{}', encoding="utf-8")
    binding = {
        "schema": "szl.twelfth-gate-adapter-binding/v1",
        "base_model": contract.BASE_MODEL,
        "base_revision": contract.BASE_REVISION,
        "source_commit": source,
        "trainer_sha256": trainer_sha,
        "provider_runtime": {"test": True},
        **contract.adapter_snapshot(path),
    }
    (path / contract.ADAPTER_BINDING).write_text(json.dumps(binding), encoding="utf-8")
    return binding


def test_adapter_binding_rejects_wrong_base_config_even_with_matching_snapshot(tmp_path):
    import twelfth_gate_contract as contract

    adapter = tmp_path / "adapter"
    make_adapter(adapter, base_model="wrong/base")
    with pytest.raises(ValueError, match="adapter_config.base_model_name_or_path"):
        contract.load_adapter_binding(adapter)


def test_provider_runtime_stays_blocked_without_independent_source_digest(monkeypatch):
    import twelfth_gate_contract as contract

    versions = {"unsloth": contract.UNSLOTH_VERSION, "unsloth_zoo": contract.UNSLOTH_ZOO_VERSION}
    monkeypatch.setattr(contract.importlib.metadata, "version", versions.__getitem__)
    monkeypatch.setattr(contract, "distribution_source_sha256", lambda name: "digest-" + name)
    monkeypatch.setattr(contract, "APPROVED_PROVIDER_DISTRIBUTION_SHA256", {})
    with pytest.raises(RuntimeError, match="has not been independently approved"):
        contract.validate_provider_runtime()


@pytest.mark.parametrize(
    "observed_name, observed_revision, passes",
    [
        ("Qwen/Qwen3.5-0.8B", "2fc06364715b967f1860aea9cf38778875588b17", True),
        ("Qwen/Qwen3.5-0.8B", None, False),
        ("Qwen/Qwen3.5-0.8B", "remapped", False),
        ("wrong/base", "2fc06364715b967f1860aea9cf38778875588b17", False),
    ],
)
def test_runtime_loader_passes_revision_and_rejects_missing_or_remapped_identity(
        observed_name, observed_revision, passes, monkeypatch):
    import train_eval_publish as runtime

    captured = {}

    class Model:
        config = SimpleNamespace(_name_or_path=observed_name, _commit_hash=observed_revision)

        def eval(self):
            return self

    class FastLanguageModel:
        @staticmethod
        def from_pretrained(**kwargs):
            captured.update(kwargs)
            return Model(), object()

        @staticmethod
        def for_inference(model):
            return model

    torch = ModuleType("torch")
    torch.bfloat16 = "bf16"
    unsloth = ModuleType("unsloth")
    unsloth.FastLanguageModel = FastLanguageModel
    monkeypatch.setitem(sys.modules, "torch", torch)
    monkeypatch.setitem(sys.modules, "unsloth", unsloth)
    monkeypatch.setattr(runtime, "validate_provider_runtime", lambda: {"approved": True})

    if passes:
        runtime.load_model("Qwen/Qwen3.5-0.8B")
        assert captured["revision"] == runtime.TWELFTH_GATE_BASE_REVISION
        assert captured["use_exact_model_name"] is True
        assert captured["local_files_only"] is True
        with pytest.raises(RuntimeError, match="unapproved model repository"):
            captured["on_model_resolved"]("unsloth/remapped-base")
    else:
        with pytest.raises(RuntimeError, match="loaded model"):
            runtime.load_model("Qwen/Qwen3.5-0.8B")


def test_held_loader_uses_same_pinned_model_contract(monkeypatch):
    import five_seed_eval as held

    captured = {}

    class Model:
        config = SimpleNamespace(
            _name_or_path=held.BASE_MODEL,
            _commit_hash=held.BASE_REVISION,
        )

        def eval(self):
            return self

    class FastLanguageModel:
        @staticmethod
        def from_pretrained(**kwargs):
            captured.update(kwargs)
            return Model(), TextTokenizer()

        @staticmethod
        def for_inference(model):
            return model

    torch = ModuleType("torch")
    torch.bfloat16 = "bf16"
    unsloth = ModuleType("unsloth")
    unsloth.FastLanguageModel = FastLanguageModel
    monkeypatch.setitem(sys.modules, "torch", torch)
    monkeypatch.setitem(sys.modules, "unsloth", unsloth)
    monkeypatch.setattr(held, "validate_provider_runtime", lambda: {"approved": True})

    _, _, identity = held.load_target(None)
    assert captured["model_name"] == held.BASE_MODEL
    assert captured["revision"] == held.BASE_REVISION
    assert captured["use_exact_model_name"] is True
    assert identity["base_revision"] == held.BASE_REVISION


@pytest.mark.parametrize("loader_name", ["challenge", "held"])
@pytest.mark.parametrize("adapter_revision", ["valid", "wrong"])
def test_adapter_loading_pins_base_before_local_peft_attachment(
        loader_name, adapter_revision, tmp_path, monkeypatch):
    import five_seed_eval as held
    import train_eval_publish as runtime
    import twelfth_gate_contract as contract

    adapter = tmp_path / "adapter"
    make_adapter(adapter)
    calls = []

    class Model:
        config = SimpleNamespace(_name_or_path=contract.BASE_MODEL,
                                 _commit_hash=contract.BASE_REVISION)

        def eval(self):
            return self

    class FastLanguageModel:
        @staticmethod
        def from_pretrained(**kwargs):
            calls.append(("base", kwargs))
            return Model(), TextTokenizer()

        @staticmethod
        def for_inference(model):
            return model

    class PeftModel:
        @staticmethod
        def from_pretrained(model, path, **kwargs):
            calls.append(("adapter", path, kwargs))
            if adapter_revision == "wrong":
                model.config = SimpleNamespace(_name_or_path=contract.BASE_MODEL,
                                               _commit_hash="wrong")
            return model

    class AutoTokenizer:
        @staticmethod
        def from_pretrained(path, **kwargs):
            calls.append(("tokenizer", path, kwargs))
            return TextTokenizer()

    for name, attributes in {
        "torch": {"bfloat16": "bf16"},
        "unsloth": {"FastLanguageModel": FastLanguageModel},
        "peft": {"PeftModel": PeftModel},
        "transformers": {"AutoTokenizer": AutoTokenizer},
    }.items():
        mock = ModuleType(name)
        mock.__dict__.update(attributes)
        monkeypatch.setitem(sys.modules, name, mock)
    monkeypatch.setattr(runtime, "validate_provider_runtime", lambda: {"approved": True})
    monkeypatch.setattr(held, "validate_provider_runtime", lambda: {"approved": True})
    loader = runtime.load_model if loader_name == "challenge" else held.load_target
    if adapter_revision == "wrong":
        with pytest.raises(RuntimeError, match="loaded model revision"):
            loader(str(adapter))
    else:
        loader(str(adapter))
        assert [call[0] for call in calls] == ["base", "adapter", "tokenizer"]
        assert calls[0][1]["model_name"] == contract.BASE_MODEL
        assert calls[0][1]["revision"] == contract.BASE_REVISION
        assert calls[1][2]["local_files_only"] is True
        assert calls[2][2]["local_files_only"] is True


def prepare_training_receipt(module, work: Path, monkeypatch):
    import twelfth_gate_contract as contract

    monkeypatch.setattr(module, "WORK", work)
    monkeypatch.setattr(module, "git_head", lambda: "commit")
    source, context = module.generated_trainer(11)
    trainer_sha = module.hashlib.sha256(source.encode("utf-8")).hexdigest()
    control = work / "control"
    control.mkdir(parents=True)
    (control / "train_seed-011.py").write_text(source, encoding="utf-8", newline="\n")
    adapter = work / "seed-011" / "adapter"
    binding = make_adapter(adapter, source="commit", trainer_sha=trainer_sha)
    binding.update({"source": module.source_identity(), "study_audit": module.study_input_audit(),
                    "model_identity": {"base_model": module.BASE_MODEL,
                                       "base_revision": module.BASE_REVISION}})
    (adapter / contract.ADAPTER_BINDING).write_text(json.dumps(binding), encoding="utf-8")
    receipt = {
        "state": "MEASURED", "binding_check": "PASS",
        "base_model": contract.BASE_MODEL, "base_revision": contract.BASE_REVISION,
        "commit": "commit", "binding": binding,
        "hyperparameters": {"seed": 11},
        "retrain": {"train_rows": module.RETRAIN_ROWS,
                    "frozen_train_sha256": context["frozen_sha256"],
                    "augmentation_sha256": context["augmentation_sha256"]},
        "response_only_mask": {"rows": module.RETRAIN_ROWS,
                               "masked_tokens": 5, "supervised_response_tokens": 3},
    }
    receipt_path = work / "seed-011" / "training_receipt.json"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    return receipt_path, binding


@pytest.mark.parametrize("tamper", ["revision", "seed", "corpus", "mask", "weights",
                                    "config", "tokenizer", "trainer", "source"])
def test_check_train_entrypoint_rejects_stale_receipt(tmp_path, monkeypatch, tamper):
    module = load_runner()
    receipt_path, _ = prepare_training_receipt(module, tmp_path, monkeypatch)
    assert module.cmd_check_train(SimpleNamespace(seed=11)) == 0
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    adapter = tmp_path / "seed-011" / "adapter"
    if tamper == "revision":
        receipt["base_revision"] = "stale"
    elif tamper == "seed":
        receipt["hyperparameters"]["seed"] = 23
    elif tamper == "corpus":
        receipt["retrain"]["augmentation_sha256"] = "stale"
    elif tamper == "mask":
        receipt["response_only_mask"]["rows"] = 1
    elif tamper == "weights":
        (adapter / "adapter_model.safetensors").write_bytes(b"replaced")
    elif tamper == "config":
        (adapter / "adapter_config.json").write_text('{}', encoding="utf-8")
    elif tamper == "tokenizer":
        (adapter / "tokenizer.json").write_text('{"changed":true}', encoding="utf-8")
    elif tamper == "trainer":
        (tmp_path / "control" / "train_seed-011.py").write_text("# replaced", encoding="utf-8")
    elif tamper == "source":
        monkeypatch.setattr(module, "git_head", lambda: "another-commit")
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    with pytest.raises(SystemExit):
        module.cmd_check_train(SimpleNamespace(seed=11))


def prepare_held_receipt(module, work: Path, binding: dict):
    import twelfth_gate_contract as contract

    evaluation = work / "study" / "evaluation"
    evaluation.mkdir(parents=True)
    prediction = evaluation / "predictions-seed-011.jsonl"
    failure = evaluation / "failures-seed-011.jsonl"
    # Historical outputs are copied only into the unit-test fixture; no new
    # inference score is supplied or claimed by this source contract test.
    prediction.write_bytes((module.STUDY_EVAL / prediction.name).read_bytes())
    failure.write_bytes((module.STUDY_EVAL / failure.name).read_bytes())
    frozen = work / "study" / "frozen"
    frozen.mkdir()
    for name in ("train.jsonl", "held.jsonl", "experiment_manifest.json"):
        (frozen / name).write_bytes((module.FROZEN / name).read_bytes())
    source = {
        "scripts/" + name: module.sha256_file(module.SCRIPTS / name)
        for name in ("five_seed_eval.py", "train_eval_publish.py", "triage_text.py",
                     "twelfth_gate_contract.py")
    }
    source["src/szl_triage/study_evidence.py"] = module.sha256_file(
        module.REPO / "src" / "szl_triage" / "study_evidence.py")
    snapshot = contract.adapter_snapshot(work / "seed-011" / "adapter")
    template = {"schema": "test-template", "sha256": "template"}
    metrics = {**module.read_json(module.STUDY_EVAL / "metrics-seed-011.json"),
        "rows": module.HELD_ROWS,
        "base_model": module.BASE_MODEL,
        "base_revision": module.BASE_REVISION,
        "model_identity": {"base_model": module.BASE_MODEL,
                           "base_revision": module.BASE_REVISION},
        "source_commit": "commit",
        "trainer_sha256": binding["trainer_sha256"],
        "adapter_binding": binding,
        "adapter_snapshot": snapshot,
        "adapter_snapshot_after": snapshot,
        "evaluator_sha256": module.sha256_file(module.SCRIPTS / "five_seed_eval.py"),
        "source": source,
        "source_after": source,
        "held_manifest_sha256": module.sha256_file(module.FROZEN / "held.jsonl"),
        "held_manifest_sha256_after": module.sha256_file(module.FROZEN / "held.jsonl"),
        "template_contract": template,
        "template_contract_after": template,
        "predictions_sha256": module.sha256_file(prediction),
        "failures_sha256": module.sha256_file(failure),
    }
    path = evaluation / "metrics-seed-011.json"
    path.write_text(json.dumps(metrics), encoding="utf-8")
    return path


@pytest.mark.parametrize("tamper", ["source", "held", "predictions", "adapter", "template"])
def test_check_held_entrypoint_rejects_reused_unbound_metrics(tmp_path, monkeypatch, tamper):
    module = load_runner()
    _, binding = prepare_training_receipt(module, tmp_path, monkeypatch)
    metrics_path = prepare_held_receipt(module, tmp_path, binding)
    assert module.cmd_check_held(SimpleNamespace(seed=11)) == 0
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    if tamper == "source":
        metrics["source_commit"] = "stale"
    elif tamper == "held":
        metrics["held_manifest_sha256"] = "stale"
    elif tamper == "predictions":
        (metrics_path.parent / "predictions-seed-011.jsonl").write_text("changed\n", encoding="utf-8")
    elif tamper == "adapter":
        (tmp_path / "seed-011" / "adapter" / "adapter_model.safetensors").write_bytes(b"replaced")
    elif tamper == "template":
        metrics["template_contract_after"] = {"changed": True}
    metrics_path.write_text(json.dumps(metrics), encoding="utf-8")
    with pytest.raises(SystemExit):
        module.cmd_check_held(SimpleNamespace(seed=11))


@pytest.mark.parametrize("tamper", ["summary", "missing", "duplicate", "raw-rehashed", "flags", "failures"])
def test_check_held_replays_raw_outputs_despite_rebound_file_hashes(tmp_path, monkeypatch, tamper):
    module = load_runner()
    _, binding = prepare_training_receipt(module, tmp_path, monkeypatch)
    metrics_path = prepare_held_receipt(module, tmp_path, binding)
    assert module.cmd_check_held(SimpleNamespace(seed=11)) == 0
    metrics = module.read_json(metrics_path)
    prediction_path = metrics_path.parent / "predictions-seed-011.jsonl"
    failure_path = metrics_path.parent / "failures-seed-011.jsonl"
    predictions = module.read_jsonl(prediction_path)
    if tamper == "summary":
        metrics["joint_accuracy"] = 0.123
    elif tamper == "missing":
        predictions.pop()
    elif tamper == "duplicate":
        predictions[1] = predictions[0]
    elif tamper == "raw-rehashed":
        predictions[0]["raw_output"] = "{}"
    elif tamper == "flags":
        predictions[0]["joint_exact"] = not predictions[0]["joint_exact"]
    elif tamper == "failures":
        failure_path.write_text(json.dumps(predictions[0]) + "\n", encoding="utf-8")
    prediction_path.write_text(
        "\n".join(json.dumps(row) for row in predictions) + "\n", encoding="utf-8")
    metrics["predictions_sha256"] = module.sha256_file(prediction_path)
    metrics["failures_sha256"] = module.sha256_file(failure_path)
    metrics_path.write_text(json.dumps(metrics), encoding="utf-8")
    with pytest.raises(SystemExit):
        module.cmd_check_held(SimpleNamespace(seed=11))


def prepare_challenge_receipt(module, work: Path, binding: dict):
    import twelfth_gate_contract as contract

    challenge_eval, _ = module.import_study_modules()
    rows, corpus = challenge_eval.load_corpus(module.CHALLENGE)
    audit = module.study_input_audit(challenge_eval)
    source = module.source_identity()
    snapshot = contract.adapter_snapshot(work / "seed-011" / "adapter")
    template = {"schema": "test-template", "sha256": "template"}
    results = [challenge_eval.score_output(
        row, '{"label":"REVIEW","state":"REVIEW","evidence":[]}', 0.01, index)
        for index, row in enumerate(rows, 1)]
    receipt = {
        "schema": module.SCHEMA + "/challenge",
        "state": "EXECUTED",
        "seed": 11,
        "commit": "commit",
        "source": source,
        "source_after": source,
        "study_audit": audit,
        "study_audit_after": audit,
        "trainer_sha256": binding["trainer_sha256"],
        "adapter_binding": binding,
        "adapter_binding_after": binding,
        "adapter_snapshot": snapshot,
        "adapter_snapshot_after": snapshot,
        "corpus": corpus,
        "corpus_sha256_after": corpus["sha256"],
        "rows_completed": len(rows),
        "template_contract": template,
        "template_contract_after": template,
        "model_identity": {"base_model": module.BASE_MODEL,
                           "base_revision": module.BASE_REVISION},
        "results": results,
        "metrics": challenge_eval.aggregate_results(results),
    }
    target = work / "challenge" / "challenge-seed-011.json"
    target.parent.mkdir(parents=True)
    target.write_text(json.dumps(receipt), encoding="utf-8")
    return target


@pytest.mark.parametrize("tamper", ["corpus", "source", "audit", "adapter", "template"])
def test_check_challenge_entrypoint_rejects_reused_unbound_receipt(tmp_path, monkeypatch, tamper):
    module = load_runner()
    _, binding = prepare_training_receipt(module, tmp_path, monkeypatch)
    receipt_path = prepare_challenge_receipt(module, tmp_path, binding)
    assert module.cmd_check_challenge(SimpleNamespace(seed=11)) == 0
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if tamper == "corpus":
        receipt["corpus_sha256_after"] = "stale"
    elif tamper == "source":
        receipt["source_after"] = {"changed": True}
    elif tamper == "audit":
        receipt["study_audit_after"] = {"changed": True}
    elif tamper == "adapter":
        (tmp_path / "seed-011" / "adapter" / "adapter_model.safetensors").write_bytes(b"replaced")
    elif tamper == "template":
        receipt["template_contract_after"] = {"changed": True}
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    with pytest.raises(SystemExit):
        module.cmd_check_challenge(SimpleNamespace(seed=11))


@pytest.mark.parametrize("tamper", ["summary", "no-results", "missing", "duplicate", "raw", "flags"])
def test_check_challenge_recomputes_from_authoritative_rows(tmp_path, monkeypatch, tamper):
    module = load_runner()
    _, binding = prepare_training_receipt(module, tmp_path, monkeypatch)
    receipt_path = prepare_challenge_receipt(module, tmp_path, binding)
    assert module.cmd_check_challenge(SimpleNamespace(seed=11)) == 0
    receipt = module.read_json(receipt_path)
    if tamper == "summary":
        receipt["metrics"]["refusal_correct"] = 0
    elif tamper == "no-results":
        receipt.pop("results")
    elif tamper == "missing":
        receipt["results"].pop()
    elif tamper == "duplicate":
        receipt["results"][1] = receipt["results"][0]
    elif tamper == "raw":
        receipt["results"][0]["raw_output"] = "{}"
    elif tamper == "flags":
        receipt["results"][0]["joint_exact"] = not receipt["results"][0]["joint_exact"]
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    with pytest.raises(SystemExit):
        module.cmd_check_challenge(SimpleNamespace(seed=11))


@pytest.mark.parametrize("stage", ["held", "challenge"])
@pytest.mark.parametrize("tamper", ["summary", "missing", "duplicate", "raw", "flags"])
def test_seed_row_cannot_accept_forged_summary_metrics(tmp_path, monkeypatch, stage, tamper):
    module = load_isolated_runner(tmp_path, monkeypatch)
    _, binding = prepare_training_receipt(module, tmp_path, monkeypatch)
    held_path = prepare_held_receipt(module, tmp_path, binding)
    challenge_path = prepare_challenge_receipt(module, tmp_path, binding)
    assert module.seed_row(11, module.thresholds())["status"] != "INCOMPLETE"
    path = held_path if stage == "held" else challenge_path
    value = module.read_json(path)
    if stage == "held":
        prediction_path = path.parent / "predictions-seed-011.jsonl"
        predictions = module.read_jsonl(prediction_path)
        if tamper == "summary":
            value["joint_accuracy"] = 0.123
        elif tamper == "missing":
            predictions.pop()
        elif tamper == "duplicate":
            predictions[1] = predictions[0]
        elif tamper == "raw":
            predictions[0]["raw_output"] = "{}"
        elif tamper == "flags":
            predictions[0]["joint_exact"] = not predictions[0]["joint_exact"]
        prediction_path.write_text(
            "\n".join(json.dumps(row) for row in predictions) + "\n", encoding="utf-8")
        value["predictions_sha256"] = module.sha256_file(prediction_path)
    else:
        if tamper == "summary":
            value["metrics"]["refusal_correct"] = 0
        elif tamper == "missing":
            value["results"].pop()
        elif tamper == "duplicate":
            value["results"][1] = value["results"][0]
        elif tamper == "raw":
            value["results"][0]["raw_output"] = "{}"
        elif tamper == "flags":
            value["results"][0]["joint_exact"] = not value["results"][0]["joint_exact"]
    path.write_text(json.dumps(value), encoding="utf-8")
    row = module.seed_row(11, module.thresholds())
    assert row["status"] == "INCOMPLETE"
    assert "binding validation failed" in row["reason"]


def test_challenge_entrypoint_fails_if_study_audit_changes_during_run(tmp_path, monkeypatch):
    module = load_isolated_runner(tmp_path, monkeypatch)
    prepare_training_receipt(module, tmp_path, monkeypatch)
    real_challenge, _ = module.import_study_modules()
    rows, corpus = real_challenge.load_corpus(module.CHALLENGE)
    model = SimpleNamespace(config=SimpleNamespace(
        _name_or_path=module.BASE_MODEL, _commit_hash=module.BASE_REVISION))

    fake = SimpleNamespace(
        load_corpus=lambda path: (rows, corpus),
        load_runtime=lambda adapter, eager: (
            model, object(), lambda m, t, p: ('{"label":"REVIEW","state":"REVIEW","evidence":[]}', 0.01),
            {"test": True},
        ),
        score_output=real_challenge.score_output,
        aggregate_results=real_challenge.aggregate_results,
    )
    audit = module.study_input_audit()
    audits = iter((audit, audit, {**audit, "nonce": "changed"}))
    monkeypatch.setattr(module, "import_study_modules", lambda: (
        fake, lambda tokenizer: {"schema": "template"}))
    monkeypatch.setattr(module, "study_input_audit", lambda challenge=None: next(audits))

    assert module.cmd_challenge(SimpleNamespace(seed=11)) == 2
    receipt = json.loads(
        (tmp_path / "challenge" / "challenge-seed-011.json").read_text(encoding="utf-8")
    )
    assert receipt["state"] == "FAILED"
    assert "changed during challenge" in receipt["error"]


def test_fresh_offline_preflight_denies_model_stack_imports(tmp_path):
    sitecustomize = tmp_path / "sitecustomize.py"
    sitecustomize.write_text(
        "import builtins\n"
        "real = builtins.__import__\n"
        "def guarded(name, *args, **kwargs):\n"
        "    if name.split('.')[0] in {'torch','unsloth','transformers','peft'}:\n"
        "        raise AssertionError('model stack import denied: ' + name)\n"
        "    return real(name, *args, **kwargs)\n"
        "builtins.__import__ = guarded\n",
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        [str(tmp_path), str(ROOT / "scripts"), str(ROOT / "src")]
    )
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "twelfth_gate_v110.py"),
         "preflight", "--skip-gpu"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PREFLIGHT_OK" in result.stdout


def test_offline_preflight_binds_inputs_and_never_imports_model_stack(tmp_path, monkeypatch):
    module = load_runner()
    monkeypatch.setattr(module, "WORK", tmp_path / "preflight-output")

    assert module.cmd_preflight(SimpleNamespace(skip_gpu=True)) == 0
    receipt = json.loads((module.WORK / "preflight.json").read_text(encoding="utf-8"))
    assert receipt["gpu"] == "SKIPPED_BY_FLAG"
    assert receipt["challenge"]["probe_classes"] == {"PARAPHRASE": 30, "STEERING": 12}
    assert receipt["challenge"]["criterion"].startswith("12 steering refusals gated")
    assert receipt["trainer"]["contract"]["base_revision"] == module.BASE_REVISION
    assert receipt["runner"]["contract"]["publish"] == "DISABLED_FAIL_CLOSED"
    assert receipt["provider_runtime"] == "UNQUALIFIED_SOURCE_DIGEST_APPROVAL_REQUIRED"
    assert receipt["study_input_audit"]["integrity_status"] == "PASS"
    assert set(receipt["trainer"]["generated_sha256"]) == {
        "seed-011", "seed-023", "seed-037", "seed-053", "seed-071"
    }
