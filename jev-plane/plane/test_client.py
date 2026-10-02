"""The client fails closed and sends only a pinned model id, never a moving -latest alias.

Run: python -m pytest jev-plane/plane -ra
"""
from __future__ import annotations

import ast
import copy
import http.client
import json
import sys
import urllib.error
from email.message import Message
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
sys.path.insert(0, str(ROOT / "plane"))

import client  # noqa: E402
from client import evaluate, unavailable  # noqa: E402

PACKS = sorted((ROOT / "packs").glob("*.json"))
ORIGINAL_CLIENT_OPENER = client._client_opener
QUESTIONS = {
    "evidence_class": {
        "type": "choice", "instructions": "Classify labeled evidence only.",
        "criteria": {"MEASURED": "Measured.", "HOLD": "Hold.", "BLOCK": "Block."},
    },
    "claims_live": {"type": "noul", "instructions": "Does the text stamp LIVE?"},
    "overclaim_severity": {
        "type": "score", "instructions": "Severity.", "criteria": ["None.", "Hold.", "Block."],
    },
}
VALID_ANSWERS = {
    "evidence_class": {
        "type": "choice", "choice": "MEASURED", "confidence": 0.9,
        "probabilities": {"MEASURED": 0.9, "HOLD": 0.05, "BLOCK": 0.05},
    },
    "claims_live": {"type": "noul", "noul": 0.1},
    "overclaim_severity": {
        "type": "score", "score": 0.2, "confidence": 0.9,
        "legend": {"0": "None.", "1": "Hold.", "2": "Block."},
        "probabilities": {"0": 0.85, "1": 0.1, "2": 0.05},
    },
}


@pytest.fixture(autouse=True)
def offline_transport(monkeypatch):
    """Every client test fails if it accidentally reaches the real transport."""
    def refused(*args, **kwargs):
        raise AssertionError("client tests must never use real network transport")

    monkeypatch.setattr(client.urllib.request, "urlopen", refused)
    monkeypatch.setattr(client, "_client_opener", refused)


class FakeResponse:
    def __init__(self, raw=None, *, status=200, content_type="application/json", url=client.ENDPOINT):
        self.raw = raw if raw is not None else json.dumps({
            "model": client.MODEL, "answers": copy.deepcopy(VALID_ANSWERS),
            "usage": {"input_tokens": 10, "output_tokens": 3},
        }).encode("utf-8")
        self.status = status
        self.url = url
        self.headers = Message()
        if content_type is not None:
            self.headers["Content-Type"] = content_type
        self.read_sizes = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def geturl(self):
        return self.url

    def read(self, size):
        self.read_sizes.append(size)
        return self.raw[:size]


def mock_response(monkeypatch, response=None, *, error=None):
    seen = []

    class FakeOpener:
        def open(self, request, timeout):
            seen.append((request, timeout))
            if error is not None:
                raise error
            return response if response is not None else FakeResponse()

    monkeypatch.setattr(client, "_client_opener", lambda: FakeOpener())
    return seen


def evaluate_mock(monkeypatch, payload=None, *, response=None):
    if response is None:
        if payload is not None:
            payload = copy.deepcopy(payload)
            payload.setdefault("usage", {"input_tokens": 10, "output_tokens": 3})
        response = FakeResponse(json.dumps(payload if payload is not None else {
            "model": client.MODEL, "answers": copy.deepcopy(VALID_ANSWERS),
            "usage": {"input_tokens": 10, "output_tokens": 3},
        }, allow_nan=True).encode("utf-8"))
    mock_response(monkeypatch, response)
    return evaluate({"text": "MEASURED, not LIVE"}, copy.deepcopy(QUESTIONS), api_key="test-only-key")


def assert_closed(out, *, attempted=True, reason=None):
    assert out["reader_status"] == "UNAVAILABLE", out
    assert out["honesty"] == "UNAVAILABLE"
    assert out["answers"]["evidence_class"]["choice"] == "UNAVAILABLE"
    assert out["auto_merge"] is False
    assert out["jev_allow_alone"] is False
    assert out["signed"] is False
    assert out["transport_attempted"] is attempted
    assert out["state_left_host"] is attempted
    assert out["state_delivery"] == ("UNVERIFIED" if attempted else "NOT_ATTEMPTED")
    if reason is not None:
        assert out["reason"] == reason


def repo_pin() -> str:
    """PINNED_MODEL from src/szl_triage/providers/jev.py, read without importing szl_triage."""
    source = REPO / "src" / "szl_triage" / "providers" / "jev.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "PINNED_MODEL" for t in node.targets
        ):
            return ast.literal_eval(node.value)
    raise AssertionError("PINNED_MODEL not found in providers/jev.py")


@pytest.fixture
def no_key(monkeypatch):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)


def test_missing_key_is_unavailable_never_pass(no_key):
    questions = {"claims_live": {"type": "noul", "instructions": "x"}}
    missing = evaluate({"text": "stamp LIVE"}, questions)
    assert missing["reader_status"] == "UNAVAILABLE", missing
    assert missing["honesty"] == "UNAVAILABLE"
    assert missing["answers"]["evidence_class"]["choice"] == "UNAVAILABLE"
    assert missing["auto_merge"] is False
    assert missing["jev_allow_alone"] is False


def test_unavailable_helper_is_unavailable():
    empty = unavailable("HTTP 401")
    assert empty["reader_status"] == "UNAVAILABLE"
    assert empty["jev_allow_alone"] is False


def test_client_model_is_the_repo_pin():
    assert repo_pin() == "jev-1.13.0"
    assert client.MODEL == repo_pin()
    assert unavailable("x")["model"] == repo_pin()


def test_all_five_packs_pin_the_repo_model():
    assert len(PACKS) == 5, PACKS
    for path in PACKS:
        pack = json.loads(path.read_text(encoding="utf-8"))
        assert pack["model"] == repo_pin(), path.name


@pytest.mark.parametrize("model", [
    "jev-latest", "JEV-LATEST", " jev-latest ", "latest", "", "jev-1.12.0",
    "jev-1.13.1", "JEV-1.13.0", " jev-1.13.0 ", None, [],
])
def test_unpinned_model_is_refused_before_any_call(model, monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "not-a-real-key")

    def no_network(*args, **kwargs):
        raise AssertionError("an unpinned model must be refused before any network call")

    monkeypatch.setattr(client.urllib.request, "urlopen", no_network)
    out = evaluate({"text": "x"}, {"q": {"type": "noul", "instructions": "x"}}, model=model)
    assert out["reader_status"] == "UNAVAILABLE", out
    assert out["jev_allow_alone"] is False
    assert_closed(out, attempted=False, reason="MODEL_REFUSED")


@pytest.mark.parametrize("endpoint", [
    "http://api.typesafe.ai/v1/systemone", "https://api.typesafe.ai/v1/systemone/",
    "https://api.typesafe.ai:443/v1/systemone", "https://example.invalid/v1/systemone",
    "https://api.typesafe.ai/v1/systemone?key=x", "https://user:password@api.typesafe.ai/v1/systemone",
    "file:///tmp/secret", "", None,
])
def test_endpoint_override_refused_before_transport(endpoint):
    out = evaluate({}, QUESTIONS, api_key="test-only-key", endpoint=endpoint)
    assert_closed(out, attempted=False, reason="ENDPOINT_REFUSED")


def test_valid_response_is_software_not_a_release_authority(monkeypatch):
    response = FakeResponse()
    seen = mock_response(monkeypatch, response)
    out = evaluate({"text": "MEASURED"}, QUESTIONS, api_key="test-only-key")
    assert out["reader_status"] == "SOFTWARE"
    assert out["answers"] == VALID_ANSWERS
    assert out["model"] == client.MODEL
    assert out["endpoint"] == client.ENDPOINT
    assert out["auto_merge"] is False and out["jev_allow_alone"] is False
    assert out["signed"] is False and out["calibration"] == "UNVERIFIED"
    assert out["transport_attempted"] is True and out["state_delivery"] == "UNVERIFIED"
    request, timeout = seen[0]
    assert request.full_url == client.ENDPOINT
    assert request.method == "POST" and timeout == client.TIMEOUT_S
    assert request.get_header("Accept-encoding") == "identity"
    assert json.loads(request.data)["model"] == client.MODEL
    assert response.read_sizes == [client.MAX_RESPONSE_BYTES + 1]


def test_real_opener_disables_proxy_forwarding_and_redirects(monkeypatch):
    # Building an opener performs no network request; inspect only its handlers.
    monkeypatch.setenv("HTTPS_PROXY", "https://example.invalid:1234")
    monkeypatch.setenv("HTTP_PROXY", "http://example.invalid:1234")
    handlers = []

    def builder(*values):
        handlers.extend(values)
        return object()

    monkeypatch.setattr(client.urllib.request, "build_opener", builder)
    # Exercise the real factory with an offline handler-builder spy.
    ORIGINAL_CLIENT_OPENER()
    assert isinstance(handlers[0], client.urllib.request.ProxyHandler)
    assert handlers[0].proxies == {}
    assert isinstance(handlers[1], client._NoRedirect)
    assert handlers[1].redirect_request(None, None, 302, "", {}, "https://example.invalid") is None


@pytest.mark.parametrize("status", [201, 204, 301, 302, 303, 307, 308, 400, 401, 500])
def test_non_200_response_never_reaches_answers(status, monkeypatch):
    response = FakeResponse(status=status)
    out = evaluate_mock(monkeypatch, response=response)
    assert_closed(out, reason="RESPONSE_STATUS_REFUSED")
    assert response.read_sizes == []


@pytest.mark.parametrize("media", [None, "text/html", "text/plain", "application/json; charset=latin-1",
                                        "application/problem+json", "application/json; bad=true"])
def test_unexpected_media_type_refused(media, monkeypatch):
    out = evaluate_mock(monkeypatch, response=FakeResponse(content_type=media))
    assert_closed(out, reason="RESPONSE_MEDIA_TYPE_REFUSED")


@pytest.mark.parametrize("media", ["application/json", "application/json; charset=utf-8",
                                        'Application/JSON; charset="UTF-8"'])
def test_json_utf8_media_type_accepted(media, monkeypatch):
    assert evaluate_mock(monkeypatch, response=FakeResponse(content_type=media))["reader_status"] == "SOFTWARE"


def test_duplicate_media_type_and_encoded_payload_refused(monkeypatch):
    response = FakeResponse()
    response.headers["Content-Type"] = "application/json"
    assert_closed(evaluate_mock(monkeypatch, response=response), reason="RESPONSE_MEDIA_TYPE_REFUSED")
    response = FakeResponse()
    response.headers["Content-Encoding"] = "gzip"
    assert_closed(evaluate_mock(monkeypatch, response=response), reason="RESPONSE_MEDIA_TYPE_REFUSED")


def test_changed_response_destination_refused(monkeypatch):
    out = evaluate_mock(monkeypatch, response=FakeResponse(url="https://example.invalid/redirect"))
    assert_closed(out, reason="RESPONSE_REDIRECT_REFUSED")


def test_errors_never_echo_token_state_or_provider_messages(monkeypatch):
    secret = "test-only-super-secret"
    for error in (
        urllib.error.URLError(f"Authorization: Bearer {secret}; private-intent"),
        urllib.error.HTTPError(f"https://example.invalid?key={secret}", 401, secret, {}, None),
        TimeoutError(secret), OSError(secret), UnicodeError(secret), ValueError(secret),
    ):
        mock_response(monkeypatch, error=error)
        out = evaluate({"private-intent": secret}, QUESTIONS, api_key=secret)
        assert_closed(out)
        raw = json.dumps(out)
        assert secret not in raw and "private-intent" not in raw
        assert "Authorization" not in raw and "example.invalid" not in raw


@pytest.mark.parametrize("raw", [
    b"", b"not JSON", b"null", b"[]", b"true", b"42", b'"object required"',
    b'{"model":"jev-1.13.0","answers":{},"answers":{}}',
    b'{"model":"jev-1.13.0","model":"jev-1.13.0","answers":{}}',
    b'{"model":"jev-1.13.0","answers":{"x":{"noul":0,"noul":1}}}',
    b'{"model":"jev-1.13.0","answers":{},"usage":{"value":NaN}}',
    b'{"model":"jev-1.13.0","answers":{},"usage":{"value":Infinity}}',
    b'{"model":"jev-1.13.0","answers":{},"usage":{"value":1e309}}',
    b'{"model":"jev-1.13.0","answers":{}} trailing', b'\xff',
])
def test_malformed_json_returns_unavailable_not_exception(raw, monkeypatch):
    assert_closed(evaluate_mock(monkeypatch, response=FakeResponse(raw)), reason="RESPONSE_INVALID")


def test_response_byte_and_structure_bounds(monkeypatch):
    out = evaluate_mock(monkeypatch, response=FakeResponse(b" " * (client.MAX_RESPONSE_BYTES + 2)))
    assert_closed(out, reason="RESPONSE_TOO_LARGE")
    raw = ('{"nest":' + '[' * (client.MAX_JSON_DEPTH + 2) + '0' + ']' * (client.MAX_JSON_DEPTH + 2) + '}').encode()
    assert_closed(evaluate_mock(monkeypatch, response=FakeResponse(raw)), reason="RESPONSE_INVALID")
    payload = {"model": client.MODEL, "answers": VALID_ANSWERS,
               "too_many_nodes": [0] * client.MAX_JSON_NODES}
    assert_closed(evaluate_mock(monkeypatch, payload), reason="RESPONSE_INVALID")


@pytest.mark.parametrize("model", [None, "jev-latest", "jev-1.12.0", "JEV-1.13.0", {}, []])
def test_wrong_or_missing_returned_model_is_unavailable(model, monkeypatch):
    payload = {"answers": VALID_ANSWERS}
    if model is not None:
        payload["model"] = model
    assert_closed(evaluate_mock(monkeypatch, payload), reason="RESPONSE_MODEL_REFUSED")


@pytest.mark.parametrize("answers", [None, [], {}, {"extra": {"type": "noul", "noul": 0.0}}])
def test_missing_or_unknown_answers_are_unavailable(answers, monkeypatch):
    assert_closed(evaluate_mock(monkeypatch, {"model": client.MODEL, "answers": answers}), reason="ANSWERS_INVALID")


@pytest.mark.parametrize("key", list(VALID_ANSWERS))
def test_missing_answer_never_defaults_to_zero(key, monkeypatch):
    answers = copy.deepcopy(VALID_ANSWERS)
    del answers[key]
    assert_closed(evaluate_mock(monkeypatch, {"model": client.MODEL, "answers": answers}), reason="ANSWERS_INVALID")


@pytest.mark.parametrize("key", list(VALID_ANSWERS))
@pytest.mark.parametrize("bad", [None, [], "wrong", {"type": "wrong"}, {"noul": 0.0}])
def test_answer_shape_and_type_are_required(key, bad, monkeypatch):
    answers = copy.deepcopy(VALID_ANSWERS)
    answers[key] = bad
    assert_closed(evaluate_mock(monkeypatch, {"model": client.MODEL, "answers": answers}), reason="ANSWERS_INVALID")


@pytest.mark.parametrize("value", [None, True, False, "0.1", [], {}, -0.001, 1.001])
@pytest.mark.parametrize("key,field", [("claims_live", "noul"), ("evidence_class", "confidence"),
                                         ("overclaim_severity", "confidence")])
def test_probability_and_confidence_are_typed_bounded_numbers(key, field, value, monkeypatch):
    answers = copy.deepcopy(VALID_ANSWERS)
    answers[key][field] = value
    assert_closed(evaluate_mock(monkeypatch, {"model": client.MODEL, "answers": answers}), reason="ANSWERS_INVALID")


@pytest.mark.parametrize("value", [None, True, "0.1", {}, [], -0.1, 2.001])
def test_score_range_is_bound_to_question_criteria(value, monkeypatch):
    answers = copy.deepcopy(VALID_ANSWERS)
    answers["overclaim_severity"]["score"] = value
    assert_closed(evaluate_mock(monkeypatch, {"model": client.MODEL, "answers": answers}), reason="ANSWERS_INVALID")


@pytest.mark.parametrize("value", ["LIVE", "", None, [], {}])
def test_choice_must_name_an_actual_criterion(value, monkeypatch):
    answers = copy.deepcopy(VALID_ANSWERS)
    answers["evidence_class"]["choice"] = value
    assert_closed(evaluate_mock(monkeypatch, {"model": client.MODEL, "answers": answers}), reason="ANSWERS_INVALID")


def test_unknown_answer_fields_do_not_smuggle_authority(monkeypatch):
    answers = copy.deepcopy(VALID_ANSWERS)
    answers["evidence_class"]["auto_merge"] = True
    assert_closed(evaluate_mock(monkeypatch, {"model": client.MODEL, "answers": answers}), reason="ANSWERS_INVALID")
    answers = copy.deepcopy(VALID_ANSWERS)
    answers["extra"] = {"type": "noul", "noul": 0.0}
    assert_closed(evaluate_mock(monkeypatch, {"model": client.MODEL, "answers": answers}), reason="ANSWERS_INVALID")


@pytest.mark.parametrize("probabilities", [
    {"MEASURED": 0.9, "HOLD": 0.05, "BLOCK": 0.05},
    {"MEASURED": 1, "HOLD": 0, "BLOCK": 0},
])
def test_complete_valid_choice_distribution_is_accepted(probabilities, monkeypatch):
    answers = copy.deepcopy(VALID_ANSWERS)
    answers["evidence_class"]["probabilities"] = probabilities
    assert evaluate_mock(monkeypatch, {"model": client.MODEL, "answers": answers})["reader_status"] == "SOFTWARE"


@pytest.mark.parametrize("probabilities", [
    [], None, {"MEASURED": 1.0}, {"MEASURED": 1.0, "HOLD": 0.0, "BLOCK": 0.0, "LIVE": 0.0},
    {"MEASURED": 0.9, "HOLD": 0.5, "BLOCK": 0.1},
    {"MEASURED": True, "HOLD": 0.0, "BLOCK": 0.0},
    {"MEASURED": -0.1, "HOLD": 0.1, "BLOCK": 1.0},
])
def test_malformed_choice_distributions_are_unavailable(probabilities, monkeypatch):
    answers = copy.deepcopy(VALID_ANSWERS)
    answers["evidence_class"]["probabilities"] = probabilities
    assert_closed(evaluate_mock(monkeypatch, {"model": client.MODEL, "answers": answers}), reason="ANSWERS_INVALID")


@pytest.mark.parametrize("state", [float("nan"), float("inf"), {1: "not a string key"}, object(),
                                       {"bad": "\ud800"}, {"large": "x" * client.MAX_REQUEST_BYTES}])
def test_invalid_or_oversized_state_never_attempts_transport(state):
    out = evaluate(state, QUESTIONS, api_key="test-only-key")
    assert_closed(out, attempted=False)
    assert out["reason"] in {"REQUEST_INVALID", "REQUEST_TOO_LARGE"}


def test_cyclic_and_deep_state_never_attempts_transport():
    cyclic = {}
    cyclic["self"] = cyclic
    assert_closed(evaluate(cyclic, QUESTIONS, api_key="test-only-key"), attempted=False, reason="REQUEST_INVALID")
    deep = {}
    for _ in range(client.MAX_JSON_DEPTH + 1):
        deep = {"nested": deep}
    assert_closed(evaluate(deep, QUESTIONS, api_key="test-only-key"), attempted=False, reason="REQUEST_INVALID")


@pytest.mark.parametrize("questions", [None, [], {}, {"q": []}, {"q": {"type": "unknown", "instructions": "x"}},
                                            {"q": {"type": "choice", "instructions": "x", "criteria": []}},
                                            {"q": {"type": "score", "instructions": "x", "criteria": {}}},
                                            {"q": {"type": "noul", "instructions": ""}}])
def test_invalid_questions_never_attempt_transport(questions):
    assert_closed(evaluate({}, questions, api_key="test-only-key"), attempted=False, reason="QUESTIONS_INVALID")


@pytest.mark.parametrize("key", [None, "", " \n", "bad\r\nAuthorization: injected", "x" * 4097, object()])
def test_missing_or_unsafe_key_never_attempts_transport(key, no_key):
    out = evaluate({}, QUESTIONS, api_key=key)
    assert_closed(out, attempted=False)
    assert out["reason"] in {"MISSING_API_KEY", "KEY_REFUSED"}


def test_unavailable_reason_is_a_fixed_code_not_exception_text():
    out = unavailable("Authorization: Bearer private-token; private state")
    assert out["reason"] == "CLIENT_UNAVAILABLE"
    assert "private" not in json.dumps(out)
    assert unavailable({"secret": "private-token"})["reason"] == "CLIENT_UNAVAILABLE"


@pytest.mark.parametrize("usage", [
    None, {}, [], {"input_tokens": 10}, {"input_tokens": 10, "output_tokens": -1},
    {"input_tokens": True, "output_tokens": 1}, {"input_tokens": 1.5, "output_tokens": 1},
    {"input_tokens": "10", "output_tokens": 1},
    {"input_tokens": 1, "output_tokens": 1, "secret": "never echo"},
])
def test_usage_requires_exact_nonnegative_integer_schema(usage, monkeypatch):
    payload = {"model": client.MODEL, "answers": VALID_ANSWERS, "usage": usage}
    assert_closed(evaluate_mock(monkeypatch, payload), reason="RESPONSE_INVALID")


def test_missing_usage_and_unexpected_response_keys_are_unavailable(monkeypatch):
    payload = {"model": client.MODEL, "answers": VALID_ANSWERS}
    assert_closed(evaluate_mock(monkeypatch, response=FakeResponse(json.dumps(payload).encode())), reason="RESPONSE_INVALID")
    payload["usage"] = {"input_tokens": 1, "output_tokens": 1}
    payload["auto_merge"] = True
    out = evaluate_mock(monkeypatch, payload)
    assert_closed(out, reason="RESPONSE_INVALID")


@pytest.mark.parametrize("key,field", [("evidence_class", "probabilities"), ("evidence_class", "confidence"),
                                         ("overclaim_severity", "probabilities"), ("overclaim_severity", "legend"),
                                         ("overclaim_severity", "confidence")])
def test_required_official_answer_fields_never_default(key, field, monkeypatch):
    answers = copy.deepcopy(VALID_ANSWERS)
    del answers[key][field]
    assert_closed(evaluate_mock(monkeypatch, {"model": client.MODEL, "answers": answers}), reason="ANSWERS_INVALID")


@pytest.mark.parametrize("legend", [None, [], {}, {"0": "Changed.", "1": "Hold.", "2": "Block."},
                                       {"1": "None.", "2": "Hold.", "3": "Block."}])
def test_score_legend_must_match_request_criteria_exactly(legend, monkeypatch):
    answers = copy.deepcopy(VALID_ANSWERS)
    answers["overclaim_severity"]["legend"] = legend
    assert_closed(evaluate_mock(monkeypatch, {"model": client.MODEL, "answers": answers}), reason="ANSWERS_INVALID")


@pytest.mark.parametrize("probabilities", [None, [], {}, {"0": 1.0}, {"0": 0.2, "1": 0.2, "2": 0.2},
                                              {"0": 0.8, "1": "0.1", "2": 0.1},
                                              {"0": 0.8, "1": True, "2": 0.1},
                                              {"0": 0.8, "1": 0.1, "2": 0.1, "3": 0.0}])
def test_score_probability_map_requires_complete_valid_distribution(probabilities, monkeypatch):
    answers = copy.deepcopy(VALID_ANSWERS)
    answers["overclaim_severity"]["probabilities"] = probabilities
    assert_closed(evaluate_mock(monkeypatch, {"model": client.MODEL, "answers": answers}), reason="ANSWERS_INVALID")


def test_reported_choice_must_be_a_probability_maximum(monkeypatch):
    answers = copy.deepcopy(VALID_ANSWERS)
    answers["evidence_class"]["choice"] = "HOLD"
    assert_closed(evaluate_mock(monkeypatch, {"model": client.MODEL, "answers": answers}), reason="ANSWERS_INVALID")
    answers["evidence_class"]["probabilities"] = {"MEASURED": 0.5, "HOLD": 0.5, "BLOCK": 0.0}
    assert evaluate_mock(monkeypatch, {"model": client.MODEL, "answers": answers})["reader_status"] == "SOFTWARE"


def test_reported_score_must_match_probability_weighted_mean(monkeypatch):
    answers = copy.deepcopy(VALID_ANSWERS)
    answers["overclaim_severity"]["score"] = 1.9
    assert_closed(evaluate_mock(monkeypatch, {"model": client.MODEL, "answers": answers}), reason="ANSWERS_INVALID")


def test_structural_probability_tolerance_is_not_calibration(monkeypatch):
    answers = copy.deepcopy(VALID_ANSWERS)
    answers["evidence_class"]["probabilities"] = {"MEASURED": 0.9, "HOLD": 0.05, "BLOCK": 0.0495}
    answers["overclaim_severity"]["score"] = 0.2005
    out = evaluate_mock(monkeypatch, {"model": client.MODEL, "answers": answers})
    assert out["reader_status"] == "SOFTWARE"
    assert out["calibration"] == "UNVERIFIED"
    answers["overclaim_severity"]["score"] = 0.202
    assert_closed(evaluate_mock(monkeypatch, {"model": client.MODEL, "answers": answers}), reason="ANSWERS_INVALID")


def test_noul_schema_refuses_unasked_confidence_and_distribution(monkeypatch):
    for field, value in [("confidence", 0.99), ("probabilities", {"true": 0.1, "false": 0.9})]:
        answers = copy.deepcopy(VALID_ANSWERS)
        answers["claims_live"][field] = value
        assert_closed(evaluate_mock(monkeypatch, {"model": client.MODEL, "answers": answers}), reason="ANSWERS_INVALID")


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_answer_values_are_unavailable_at_json_boundary(value, monkeypatch):
    answers = copy.deepcopy(VALID_ANSWERS)
    answers["claims_live"]["noul"] = value
    assert_closed(evaluate_mock(monkeypatch, {"model": client.MODEL, "answers": answers}), reason="RESPONSE_INVALID")


def test_response_is_bound_to_sent_question_snapshot(monkeypatch):
    questions = copy.deepcopy(QUESTIONS)
    answers = copy.deepcopy(VALID_ANSWERS)
    del answers["claims_live"]

    class MutatingOpener:
        def open(self, request, timeout):
            assert "claims_live" in json.loads(request.data)["questions"]
            del questions["claims_live"]
            return FakeResponse(json.dumps({
                "model": client.MODEL, "answers": answers,
                "usage": {"input_tokens": 1, "output_tokens": 1},
            }).encode())

    monkeypatch.setattr(client, "_client_opener", lambda: MutatingOpener())
    out = evaluate({}, questions, api_key="test-only-key")
    assert_closed(out, reason="ANSWERS_INVALID")


@pytest.mark.parametrize("usage", [
    {"input": 10, "output": 3},
    {"input": 10, "output_tokens": 3},
    {"input_tokens": 10, "output": 3},
    {"input_tokens": 10, "output_tokens": 3, "input": 10, "output": 3},
])
def test_obsolete_short_usage_keys_are_not_official_schema(usage, monkeypatch):
    payload = {"model": client.MODEL, "answers": VALID_ANSWERS, "usage": usage}
    assert_closed(evaluate_mock(monkeypatch, payload), reason="RESPONSE_INVALID")


@pytest.mark.parametrize("code", [
    "LIVE_CALL_NOT_REQUESTED", "LOCAL_GATE_READER_SKIPPED", "PACK_IDENTITY_MISMATCH",
    "INVALID_READER_ENVELOPE", "PACK_INVALID",
])
def test_reviewed_finish_boundary_failure_codes_remain_fixed(code):
    out = unavailable(code)
    assert_closed(out, attempted=False, reason=code)


@pytest.mark.parametrize("error", [
    http.client.HTTPException("Authorization: Bearer test-private-token"),
    http.client.BadStatusLine("private-state test-private-token"),
    http.client.IncompleteRead(b"private-state test-private-token", 999),
    http.client.RemoteDisconnected("private-state test-private-token"),
])
def test_http_parser_failures_are_sanitized_unavailable(error, monkeypatch):
    mock_response(monkeypatch, error=error)
    out = evaluate({"text": "private-state"}, QUESTIONS, api_key="test-private-token")
    assert_closed(out, reason="TRANSPORT_UNAVAILABLE")
    assert "test-private-token" not in json.dumps(out)
    assert "private-state" not in json.dumps(out)
