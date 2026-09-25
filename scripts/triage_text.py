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
