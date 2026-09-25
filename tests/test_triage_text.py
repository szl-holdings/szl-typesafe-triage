"""Text boundary regressions run without transformers, torch, or model weights."""

from __future__ import annotations

import hashlib
import importlib.util
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


_SPEC = importlib.util.spec_from_file_location(
    "triage_text", Path(__file__).resolve().parents[1] / "scripts" / "triage_text.py",
)
assert _SPEC is not None and _SPEC.loader is not None
triage_text = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(triage_text)


class Tensor:
    def __init__(self, tokens):
        self.tokens = tokens
        self.device = None

    def to(self, device):
        self.device = device
        return self


class BatchEncoding(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.moves = []

    def to(self, device):
        self.moves.append(device)
        for value in self.values():
            if hasattr(value, "to"):
                value.to(device)
        return self


class TextTokenizer:
    chat_template = "<bos>{{ messages[0].content }}<assistant><think></think>"
    eos_token_id = 2

    def __init__(self, batch=False):
        self.batch = batch
        self.render_calls = []
        self.encode_calls = []
        self.decode_calls = []

    def apply_chat_template(self, messages, **kwargs):
        self.render_calls.append((messages, kwargs))
        return "<bos>" + messages[0]["content"] + "<assistant><think></think>"

    def __call__(self, *, text, return_tensors, add_special_tokens):
        self.encode_calls.append((text, return_tensors, add_special_tokens))
        # Simulate the additional BOS a normal tokenizer would add by default.
        tokens = ([1] if add_special_tokens else []) + [1, 10, 11]
        result = {"input_ids": Tensor(tokens), "attention_mask": Tensor([1] * len(tokens))}
        return BatchEncoding(result) if self.batch else result

    def decode(self, tokens, **kwargs):
        self.decode_calls.append((tokens, kwargs))
        return "reply"


class Processor:
    image_processor = object()

    def __init__(self, tokenizer, attribute="tokenizer"):
        setattr(self, attribute, tokenizer)
        self.image_calls = 0
        self.render_calls = 0

    def __call__(self, images=None, text=None, videos=None, **kwargs):
        self.image_calls += 1
        raise AssertionError("Processor image path was invoked")

    def apply_chat_template(self, *args, **kwargs):
        self.render_calls += 1
        raise AssertionError("Processor template was invoked")

    def decode(self, *args, **kwargs):
        raise AssertionError("Processor decode was invoked")


@pytest.mark.parametrize("attribute", ["tokenizer", "text_tokenizer"])
@pytest.mark.parametrize("batch", [False, True])
def test_entire_prompt_path_uses_text_tokenizer(attribute, batch):
    tokenizer = TextTokenizer(batch=batch)
    processor = Processor(tokenizer, attribute)
    inputs = triage_text.build_generation_inputs(processor, "triage me", "cpu")

    assert processor.image_calls == processor.render_calls == 0
    assert tokenizer.render_calls == [(
        [{"role": "user", "content": "triage me"}],
        {"chat_template": tokenizer.chat_template, "tokenize": False,
         "add_generation_prompt": True, "enable_thinking": False},
    )]
    assert tokenizer.encode_calls == [("<bos>triage me<assistant><think></think>", "pt", False)]
    assert inputs["input_ids"].tokens.count(1) == 1
    assert all(value.device == "cpu" for value in inputs.values())
    if batch:
        assert inputs.moves == ["cpu"]
    resolved = triage_text.resolve_text_tokenizer(processor)
    assert resolved.eos_token_id == 2
    assert resolved.decode([20], skip_special_tokens=True) == "reply"
    assert tokenizer.decode_calls == [([20], {"skip_special_tokens": True})]


def test_nested_processors_resolve_to_safe_text_leaf():
    tokenizer = TextTokenizer()
    wrapper = Processor(Processor(tokenizer, "text_tokenizer"))
    assert triage_text.resolve_text_tokenizer(wrapper) is tokenizer


def test_same_child_aliases_are_unambiguous():
    tokenizer = TextTokenizer()
    wrapper = SimpleNamespace(tokenizer=tokenizer, text_tokenizer=tokenizer)
    assert triage_text.resolve_text_tokenizer(wrapper) is tokenizer


def test_nested_unresolved_multimodal_processor_is_refused():
    unsafe_leaf = Processor(None)
    with pytest.raises(RuntimeError, match="media processor"):
        triage_text.build_generation_inputs(Processor(unsafe_leaf), "hello")
    assert unsafe_leaf.image_calls == unsafe_leaf.render_calls == 0


@pytest.mark.parametrize("cycle_length", [1, 2, 3])
def test_cycles_are_refused(cycle_length):
    nodes = [SimpleNamespace() for _ in range(cycle_length)]
    for index, node in enumerate(nodes):
        node.tokenizer = nodes[(index + 1) % cycle_length]
    with pytest.raises(RuntimeError, match="cycle"):
        triage_text.resolve_text_tokenizer(nodes[0])


def test_distinct_children_are_refused():
    wrapper = SimpleNamespace(tokenizer=TextTokenizer(), text_tokenizer=TextTokenizer())
    with pytest.raises(RuntimeError, match="Ambiguous"):
        triage_text.resolve_text_tokenizer(wrapper)


def test_media_call_signature_without_media_attribute_is_refused():
    class HiddenProcessor(TextTokenizer):
        def __call__(self, images=None, text=None, **kwargs):
            raise AssertionError("Must not invoke multimodal signature")

    with pytest.raises(RuntimeError, match="signature still accepts media"):
        triage_text.build_generation_inputs(HiddenProcessor(), "hello")


def test_template_typeerror_does_not_retry_without_nonthinking_mode():
    class BrokenTemplate(TextTokenizer):
        def apply_chat_template(self, messages, **kwargs):
            self.render_calls.append((messages, kwargs))
            raise TypeError("template rejected enable_thinking")

    tokenizer = BrokenTemplate()
    with pytest.raises(TypeError, match="rejected enable_thinking"):
        triage_text.build_generation_inputs(Processor(tokenizer), "hello")
    assert len(tokenizer.render_calls) == 1
    assert tokenizer.render_calls[0][1]["enable_thinking"] is False
    assert tokenizer.encode_calls == []


@pytest.mark.parametrize("prompt", [None, 1, [{"type": "text", "text": "hello"}]])
def test_nonstring_prompt_is_refused(prompt):
    tokenizer = TextTokenizer()
    with pytest.raises(TypeError, match="must be a string"):
        triage_text.build_generation_inputs(tokenizer, prompt)
    assert tokenizer.render_calls == tokenizer.encode_calls == []


def test_template_contract_hashes_selected_template_and_records_fixed_mode():
    class MultipleTemplates(TextTokenizer):
        chat_template = {"default": "plain chat", "tool_use": "tools"}

        def get_chat_template(self):
            return self.chat_template["default"]

    tokenizer = MultipleTemplates()
    contract = triage_text.template_contract(Processor(tokenizer))
    triage_text.render_prompt(tokenizer, "hello")
    assert contract["chat_template_sha256"] == hashlib.sha256(b"plain chat").hexdigest()
    assert tokenizer.render_calls[0][1]["chat_template"] == "plain chat"
    assert contract["mode"] == "text-only-nonthinking"
    assert contract["enable_thinking"] is contract["add_special_tokens"] is False


@pytest.mark.parametrize("template", [None, "", {"unknown": "value"}])
def test_missing_or_unselected_template_is_refused(template):
    tokenizer = TextTokenizer()
    tokenizer.chat_template = template
    with pytest.raises(RuntimeError, match="nonempty string chat template"):
        triage_text.render_prompt(tokenizer, "hello")
    assert tokenizer.render_calls == []


@pytest.mark.parametrize("rendered", [None, "", {"input_ids": [1]}, ["hello"]])
def test_nonstring_or_empty_render_is_refused(rendered):
    tokenizer = TextTokenizer()
    tokenizer.apply_chat_template = lambda *args, **kwargs: rendered
    with pytest.raises(RuntimeError, match="did not return a nonempty string"):
        triage_text.build_generation_inputs(tokenizer, "hello")
    assert tokenizer.encode_calls == []


def test_no_device_preserves_encoding_without_moving():
    tokenizer = TextTokenizer(batch=True)
    inputs = triage_text.build_generation_inputs(tokenizer, "hello")
    assert inputs.moves == []
    assert inputs["input_ids"].device is None


def test_dict_move_preserves_nontensor_values():
    class MetadataTokenizer(TextTokenizer):
        def __call__(self, **kwargs):
            inputs = super().__call__(**kwargs)
            inputs["metadata"] = 3
            return inputs

    inputs = triage_text.build_generation_inputs(MetadataTokenizer(), "hello", "cpu")
    assert inputs["metadata"] == 3
    assert inputs["input_ids"].device == "cpu"


@pytest.mark.parametrize("encoded", [None, [1, 2], {}, {"input_ids": [1], "pixel_values": []}])
def test_invalid_or_multimodal_encodings_are_refused(encoded):
    class BadEncoding(TextTokenizer):
        def __call__(self, **kwargs):
            return encoded

    with pytest.raises(RuntimeError, match="mapping containing input_ids|multimodal"):
        triage_text.build_generation_inputs(BadEncoding(), "hello")


def test_invalid_batch_move_result_is_refused():
    class BrokenBatch(BatchEncoding):
        def to(self, device):
            return None

    class BrokenTokenizer(TextTokenizer):
        def __call__(self, **kwargs):
            return BrokenBatch(super().__call__(**kwargs))

    with pytest.raises(RuntimeError, match="mapping containing input_ids"):
        triage_text.build_generation_inputs(BrokenTokenizer(), "hello", "cpu")


def test_boundary_import_does_not_load_ml_packages():
    # A fresh process keeps this independent of other tests' imported packages.
    script = """
import importlib.abc
import importlib.util
import sys
class RejectML(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'torch', 'transformers', 'unsloth', 'peft'}:
            raise AssertionError('ML import attempted: ' + fullname)
sys.meta_path.insert(0, RejectML())
spec = importlib.util.spec_from_file_location('triage_text', sys.argv[1])
spec.loader.exec_module(importlib.util.module_from_spec(spec))
"""
    result = subprocess.run(
        [sys.executable, "-I", "-c", script, str(Path(triage_text.__file__))],
        capture_output=True, text=True, timeout=15,
    )
    assert result.returncode == 0, result.stderr
