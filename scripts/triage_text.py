"""One text-only rendering boundary for the triage study.

A multimodal processor can put a positional string in its image argument, and
its chat template can interpret string content as a sequence of media blocks.
Resolve the underlying text tokenizer *before* rendering or encoding. This
module deliberately imports no ML packages, so the boundary is testable without
loading weights, initializing CUDA, or contacting a model registry.
"""

from __future__ import annotations

import hashlib
import inspect
from collections.abc import Mapping
from typing import Any


_MEDIA_ATTRIBUTES = ("image_processor", "video_processor", "audio_processor", "feature_extractor")
_MEDIA_ARGUMENTS = {"image", "images", "video", "videos", "audio", "audios"}
_MEDIA_INPUTS = {
    "pixel_values", "pixel_values_videos", "image_grid_thw", "video_grid_thw",
    "input_features", "input_values", "audio_values",
}


def resolve_text_tokenizer(obj: Any) -> Any:
    """Unwrap tokenizer/text_tokenizer links; reject unsafe or ambiguous leaves.

    A processor wrapper may expose media capabilities, but the object actually
    used for rendering, encoding, special token IDs, and decoding must not. A
    cycle, divergent text children, or unresolved multimodal leaf is an error;
    no processor is invoked as a fallback.
    """
    seen: set[int] = set()
    current = obj
    for _ in range(32):
        identity = id(current)
        if identity in seen:
            raise RuntimeError("Text tokenizer resolution contains a cycle")
        seen.add(identity)

        children = [
            child for name in ("tokenizer", "text_tokenizer")
            if (child := getattr(current, name, None)) is not None
        ]
        if children:
            if any(child is not children[0] for child in children[1:]):
                raise RuntimeError("Ambiguous tokenizer and text_tokenizer children")
            current = children[0]
            continue

        media = [name for name in _MEDIA_ATTRIBUTES if hasattr(current, name)]
        if media:
            raise RuntimeError(f"Resolved text tokenizer exposes media processor: {', '.join(media)}")
        if not callable(current):
            raise RuntimeError("Resolved text tokenizer is not callable")
        for name in ("apply_chat_template", "decode"):
            if not callable(getattr(current, name, None)):
                raise RuntimeError(f"Resolved text tokenizer has no callable {name}")
        try:
            parameters = inspect.signature(current).parameters
        except (TypeError, ValueError) as exc:
            raise RuntimeError("Cannot verify the resolved text tokenizer call signature") from exc
        if _MEDIA_ARGUMENTS.intersection(parameters):
            raise RuntimeError("Resolved text tokenizer call signature still accepts media")
        text_parameter = parameters.get("text")
        accepts_text = text_parameter is not None and text_parameter.kind in {
            inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY,
        }
        accepts_keywords = any(
            parameter.kind == inspect.Parameter.VAR_KEYWORD
            for parameter in parameters.values()
        )
        if not accepts_text and not accepts_keywords:
            raise RuntimeError("Resolved text tokenizer cannot accept text by keyword")
        return current

    raise RuntimeError("Text tokenizer nesting exceeds the supported depth")


def _selected_chat_template(tokenizer: Any) -> str:
    selector = getattr(tokenizer, "get_chat_template", None)
    template = selector() if callable(selector) else getattr(tokenizer, "chat_template", None)
    if not isinstance(template, str) or not template:
        raise RuntimeError("Text tokenizer must select a nonempty string chat template")
    return template


def template_contract(obj: Any) -> dict[str, Any]:
    """Describe the exact selected template and fixed rendering mode for receipts.

    The digest identifies template source bytes, not a claim that a model obeyed
    the prompt or that an evaluation succeeded.
    """
    tokenizer = resolve_text_tokenizer(obj)
    template = _selected_chat_template(tokenizer)
    return {
        "schema": "szl.text-template-contract/v1",
        "mode": "text-only-nonthinking",
        "tokenizer_class": f"{type(tokenizer).__module__}.{type(tokenizer).__qualname__}",
        "chat_template_sha256": hashlib.sha256(template.encode("utf-8")).hexdigest(),
        "content_format": "string",
        "tokenize": False,
        "add_generation_prompt": True,
        "enable_thinking": False,
        "add_special_tokens": False,
    }


def render_prompt(obj: Any, prompt: str) -> str:
    """Render through the text tokenizer without retrying a different mode."""
    if not isinstance(prompt, str):
        raise TypeError("Text-only triage prompt must be a string")
    tokenizer = resolve_text_tokenizer(obj)
    rendered = tokenizer.apply_chat_template(
        [{"role": "user", "content": prompt}],
        chat_template=_selected_chat_template(tokenizer),
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=False,
    )
    if not isinstance(rendered, str) or not rendered:
        raise RuntimeError("Text tokenizer chat rendering did not return a nonempty string")
    return rendered


def render_training_example(obj: Any, prompt: str, response: str) -> str:
    """Render one complete text-only training exchange in the fixed mode."""
    if not isinstance(prompt, str) or not isinstance(response, str):
        raise TypeError("Training prompt and response must be strings")
    tokenizer = resolve_text_tokenizer(obj)
    rendered = tokenizer.apply_chat_template(
        [{"role": "user", "content": prompt}, {"role": "assistant", "content": response}],
        chat_template=_selected_chat_template(tokenizer),
        tokenize=False,
        add_generation_prompt=False,
        enable_thinking=False,
    )
    if not isinstance(rendered, str) or not rendered:
        raise RuntimeError("Text tokenizer training render did not return a nonempty string")
    return rendered


def _plain_tokens(value: Any) -> list[int]:
    tolist = getattr(value, "tolist", None)
    value = tolist() if callable(tolist) else value
    if not isinstance(value, list) or any(not isinstance(item, int) for item in value):
        raise RuntimeError("Response-only label contract requires integer token lists")
    return value


def _subsequence_offsets(values: list[int], needle: list[int]) -> list[int]:
    if not needle:
        raise RuntimeError("Response marker tokenization is empty")
    return [index for index in range(len(values) - len(needle) + 1)
            if values[index:index + len(needle)] == needle]


def validate_response_only_batch(batch: Mapping[str, Any], response_marker_ids: Any) -> dict[str, int]:
    """Prove final collator labels mask users and train assistant responses.

    This checks the actual batch returned by the trainer's data collator after
    ``train_on_responses_only``. Merely calling the helper is insufficient.
    """
    if not isinstance(batch, Mapping) or "input_ids" not in batch or "labels" not in batch:
        raise RuntimeError("Response-only collator batch must contain input_ids and labels")
    input_rows = getattr(batch["input_ids"], "tolist", lambda: batch["input_ids"])()
    label_rows = getattr(batch["labels"], "tolist", lambda: batch["labels"])()
    marker = _plain_tokens(response_marker_ids)
    if not isinstance(input_rows, list) or not isinstance(label_rows, list) \
            or len(input_rows) != len(label_rows) or not input_rows:
        raise RuntimeError("Response-only collator batch dimensions are invalid")
    supervised = masked = 0
    for input_row, label_row in zip(input_rows, label_rows):
        inputs, labels = _plain_tokens(input_row), _plain_tokens(label_row)
        if len(inputs) != len(labels):
            raise RuntimeError("Response-only labels do not align with input_ids")
        offsets = _subsequence_offsets(inputs, marker)
        if len(offsets) != 1:
            raise RuntimeError("Expected exactly one assistant response marker in each example")
        response_start = offsets[0] + len(marker)
        if any(label != -100 for label in labels[:response_start]):
            raise RuntimeError("User or response-marker tokens remain trainable")
        trainable = [(token, label) for token, label in zip(inputs[response_start:], labels[response_start:])
                     if label != -100]
        if not trainable:
            raise RuntimeError("Assistant response has no trainable labels")
        if any(token != label for token, label in trainable):
            raise RuntimeError("Trainable response labels differ from their input tokens")
        supervised += len(trainable)
        masked += sum(label == -100 for label in labels)
    return {"rows": len(input_rows), "masked_tokens": masked,
            "supervised_response_tokens": supervised}


def validate_trainer_response_labels(
    trainer: Any, response_marker_ids: Any, *, expected_rows: int,
) -> dict[str, int]:
    """Verify final collator labels for every prepared training example."""
    dataset = trainer.train_dataset
    if len(dataset) != expected_rows:
        raise RuntimeError("Prepared training dataset must have {} rows; found {}".format(
            expected_rows, len(dataset)))
    totals = {"rows": 0, "masked_tokens": 0, "supervised_response_tokens": 0}
    for index in range(len(dataset)):
        observed = validate_response_only_batch(
            trainer.data_collator([dataset[index]]), response_marker_ids,
        )
        for key in totals:
            totals[key] += observed[key]
    return totals


def _validate_inputs(inputs: Any) -> None:
    if not isinstance(inputs, Mapping) or "input_ids" not in inputs:
        raise RuntimeError("Text tokenizer must return a mapping containing input_ids")
    if _MEDIA_INPUTS.intersection(inputs):
        raise RuntimeError("Text tokenizer returned multimodal generation inputs")


def build_generation_inputs(
    obj: Any, prompt: str, device: Any = None, *, return_tensors: str | None = "pt",
) -> Mapping[str, Any]:
    """Render once, encode via keyword text, and move BatchEncoding or dict data.

    Chat templates already contain their special tokens. Encoding must not add
    another BOS/EOS layer, and a template TypeError must never trigger a second
    render that silently drops the nonthinking request.
    """
    tokenizer = resolve_text_tokenizer(obj)
    rendered = render_prompt(tokenizer, prompt)
    inputs = tokenizer(
        text=rendered,
        return_tensors=return_tensors,
        add_special_tokens=False,
    )
    _validate_inputs(inputs)
    if device is None:
        return inputs
    move = getattr(inputs, "to", None)
    if callable(move):
        inputs = move(device)
    else:
        inputs = {
            key: value.to(device) if callable(getattr(value, "to", None)) else value
            for key, value in inputs.items()
        }
    _validate_inputs(inputs)
    return inputs
