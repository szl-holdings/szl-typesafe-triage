# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""szl.lambda/v1 in szl_decide: the vendored golden vectors, bit for bit (PT-L1),
joint multiplicativity and log-elasticity (PT-L2), and the incremental
accumulator against a scratch recompute (PT-L3).

`szl_decide.lam` ports `reference/szl_lambda_v1.py` from szl-lambda-gate with
the same algorithm (fsum of w*log x, exp), so it is held to exact f64 equality,
not to `value_tol`.
"""
from __future__ import annotations

import ast
import hashlib
import json
import math
import re
import sys
from importlib import resources
from pathlib import Path

import pytest

from szl_decide import canon, lam
from szl_decide.lam import LambdaContractError, LogAccumulator

from . import _gen

ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / "src" / "szl_decide"
SPEC = PKG / "spec"
VECTORS_PATH = SPEC / "lambda_v1_vectors.json"
SOURCE_PATH = SPEC / "lambda_v1_vectors.SOURCE"

#: FF-01 merge commit in szl-holdings/szl-lambda-gate (PR #53) and the digest its
#: spec records for the vectors: SHA-256 over canonical JSON bytes, so a CRLF
#: checkout does not change it.
UPSTREAM_SHA = "d3443b0539ad9fdbd407a0b0bf0454b416102089"
CANONICAL_SHA256 = "2a3fef3d17ca36142139fa6bd08b7f0e41526c749abc7cfd810b77cc50ab5d1f"

VECTORS = json.loads(VECTORS_PATH.read_text(encoding="utf-8"))["vectors"]


def _decode(value):
    """f64 strings become floats; any other JSON value is passed through unchanged."""
    if isinstance(value, str) and value.startswith("f64:"):
        return canon.decode_f64(value)
    if isinstance(value, list):
        return [_decode(v) for v in value]
    return value


def _plain_canonical_sha256(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False).encode("utf-8")).hexdigest()


# -------------------------------------------------------------- provenance --

def test_vendored_vectors_digest_matches_the_upstream_spec():
    raw = json.loads(VECTORS_PATH.read_text(encoding="utf-8"))
    assert _plain_canonical_sha256(raw) == CANONICAL_SHA256
    assert raw["schema"] == "szl.lambda/v1.vectors"
    assert len(raw["vectors"]) == 50


def test_source_file_names_the_upstream_commit_and_digest():
    text = SOURCE_PATH.read_text(encoding="utf-8")
    assert f"szl-holdings/szl-lambda-gate@{UPSTREAM_SHA}:spec/lambda_v1_vectors.json" in text
    assert f"canonical_sha256: {CANONICAL_SHA256}" in text


def test_vectors_ship_as_package_data():
    data = resources.files("szl_decide").joinpath("spec", "lambda_v1_vectors.json").read_bytes()
    assert _plain_canonical_sha256(json.loads(data.decode("utf-8"))) == CANONICAL_SHA256


def test_pyproject_adds_package_data_once_and_keeps_zero_dependencies():
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert text.count('szl_decide = ["spec/*.json", "plans/*.json"]') == 1
    section = text.split("[tool.setuptools.package-data]", 1)[1].split("\n[", 1)[0]
    assert 'szl_decide = ["spec/*.json", "plans/*.json"]' in section
    assert 'szl_triage = ["data/*.json"]' in section
    assert re.findall(r"(?m)^dependencies = .*$", text) == ["dependencies = []"]


# ------------------------------------------------------------- PT-L1 vectors --

@pytest.mark.parametrize("vec", VECTORS, ids=[v["id"] for v in VECTORS])
def test_lambda_w_matches_vector_bit_for_bit(vec):
    axes, weights = _decode(vec["axes"]), _decode(vec["weights"])
    expect = vec["expect"]
    if "error" in expect:
        with pytest.raises(LambdaContractError) as info:
            lam.lambda_w(axes, weights)
        assert info.value.code == expect["error"]
        with pytest.raises(LambdaContractError) as info:
            lam.log_lambda_w(axes, weights)
        assert info.value.code == expect["error"]
    else:
        value = lam.lambda_w(axes, weights)
        assert type(value) is float
        assert canon.encode_f64(value) == expect["value_f64"]


@pytest.mark.parametrize("vec", VECTORS, ids=[v["id"] for v in VECTORS])
def test_gate_v1_matches_vector_verdict_and_code(vec):
    axes, weights, tau = _decode(vec["axes"]), _decode(vec["weights"]), _decode(vec["tau"])
    assert lam.gate_v1(axes, weights, tau) == (vec["expect"]["verdict"], vec["expect"]["code"])


def test_every_error_code_and_verdict_is_exercised_by_the_vectors():
    errors = {v["expect"].get("error") for v in VECTORS} | {v["expect"]["code"] for v in VECTORS}
    for code in lam.ERROR_CODES:
        assert code in errors, code
    assert {v["expect"]["verdict"] for v in VECTORS} == set(lam.VERDICTS)


def test_contract_constants_match_the_spec():
    assert lam.SCHEMA == "szl.lambda/v1"
    assert lam.TIE_EPS == 1e-9
    assert lam.WEIGHT_SUM_TOL == 1e-12
    assert lam.ERROR_CODES == (
        "LAMBDA_TYPE_INVALID", "LAMBDA_EMPTY", "LAMBDA_LENGTH_MISMATCH",
        "LAMBDA_NONFINITE_AXIS", "LAMBDA_AXIS_OUT_OF_RANGE", "LAMBDA_NONFINITE_WEIGHT",
        "LAMBDA_WEIGHT_NONPOSITIVE", "LAMBDA_WEIGHT_SUM", "LAMBDA_TAU_INVALID")
    assert lam.VERDICTS == ("GO", "NO_GO", "ABSTAIN", "BLOCK")


def test_contract_error_is_a_value_error():
    with pytest.raises(ValueError):
        lam.lambda_w([], [])


def test_gate_v1_never_raises_on_garbage():
    for axes, weights, tau in [(None, None, None), ("ab", "ab", "x"), ([0.5], [1.0], []),
                               ([object()], [1.0], 0.5), ([0.5], [1.0], math.inf)]:
        verdict, code = lam.gate_v1(axes, weights, tau)
        assert verdict == "BLOCK" and code in lam.ERROR_CODES


def test_lambda_is_bitwise_invariant_under_permutation():
    r = _gen.rng(10)
    for i in range(2_000):
        k = r.randint(1, 8)
        xs = [r.random() for _ in range(k)]
        ws = _gen.weights(r, k)
        perm = list(range(k))
        r.shuffle(perm)
        a = lam.lambda_w(xs, ws)
        b = lam.lambda_w([xs[j] for j in perm], [ws[j] for j in perm])
        assert canon.encode_f64(a) == canon.encode_f64(b), i


def test_lam_does_not_import_the_torch_package_and_is_stdlib_only():
    stdlib = set(sys.stdlib_module_names)
    for path in sorted(PKG.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    continue  # intra-package
                names = [node.module or ""]
            else:
                continue
            for name in names:
                top = name.split(".")[0]
                assert top in stdlib or top == "szl_decide", f"{path.name} imports {name}"
                assert top not in ("szl_lambda_gate", "torch", "szl_triage"), path.name


# ---------------------------------------------- PT-L2 multiplicativity ----

def test_joint_multiplicativity():
    r = _gen.rng(11)
    for i in range(_gen.CASES):
        k = r.randint(1, 6)
        ws = _gen.weights(r, k)
        xs = [r.uniform(1e-6, 1.0) for _ in range(k)]
        ys = [r.uniform(1e-6, 1.0) for _ in range(k)]
        joint = lam.lambda_w([a * b for a, b in zip(xs, ys)], ws)
        assert abs(joint - lam.lambda_w(xs, ws) * lam.lambda_w(ys, ws)) <= 1e-12, i


def test_weights_are_identifiable_by_log_elasticity():
    r = _gen.rng(12)
    h = 1e-7
    for i in range(1_000):
        k = r.randint(1, 6)
        ws = _gen.weights(r, k)
        xs = [r.uniform(0.05, 0.95) for _ in range(k)]
        base = lam.log_lambda_w(xs, ws)
        for j in range(k):
            bumped = list(xs)
            bumped[j] = xs[j] * math.exp(h)
            elasticity = (lam.log_lambda_w(bumped, ws) - base) / h
            assert abs(elasticity - ws[j]) <= 1e-6, (i, j)


def test_zero_axis_is_a_veto_not_an_error():
    assert lam.lambda_w([0.0, 1.0], [0.5, 0.5]) == 0.0
    assert lam.log_lambda_w([0.0, 1.0], [0.5, 0.5]) == -math.inf


# --------------------------------------------------- PT-L3 accumulators ----

def test_accumulator_equals_scratch_recompute_bit_for_bit():
    r = _gen.rng(13)
    for i in range(_gen.CASES):
        k = r.randint(1, 8)
        ws = _gen.weights(r, k)
        xs = [0.0 if r.random() < 0.1 else r.random() for _ in range(k)]
        acc = LogAccumulator()
        order = list(range(k))
        r.shuffle(order)
        for j in order:
            acc.add(f"s{j}", xs[j], ws[j])
        scratch = lam.log_lambda_w(xs, ws)
        assert canon.encode_f64(acc.log_value()) == canon.encode_f64(scratch), i
        assert acc.zeros == sum(1 for x in xs if x == 0.0), i


def test_accumulator_counts_pending_axes_as_one():
    r = _gen.rng(14)
    for i in range(2_000):
        k = r.randint(2, 8)
        ws = _gen.weights(r, k)
        xs = [r.uniform(1e-6, 1.0) for _ in range(k)]
        done = r.randint(0, k)
        acc = LogAccumulator()
        for j in range(done):
            acc.add(f"s{j}", xs[j], ws[j])
        with_pending_at_one = xs[:done] + [1.0] * (k - done)
        assert acc.log_value() == lam.log_lambda_w(with_pending_at_one, ws), i


def test_accumulator_early_no_go_agrees_with_every_completion():
    # Pending seats can only contribute log 1 = 0, so once the partial upper
    # log-sum is below log tau (outside the band), every completion is NO_GO.
    r = _gen.rng(15)
    for i in range(_gen.CASES // 2):
        k = r.randint(2, 6)
        ws = _gen.weights(r, k)
        t = _gen.tau(r)
        done = r.randint(1, k - 1)
        xs = [r.random() for _ in range(done)]
        acc = LogAccumulator()
        for j, x in enumerate(xs):
            acc.add(f"s{j}", x, ws[j])
        early_no_go = acc.log_value() - math.log(t) < -lam.TIE_EPS
        if not early_no_go:
            continue
        for _ in range(5):
            completion = xs + [r.random() for _ in range(k - done)]
            assert lam.gate_v1(completion, ws, t)[0] == "NO_GO", i


def test_accumulator_refuses_contract_violations():
    acc = LogAccumulator()
    for x, w in [(math.nan, 0.5), (1.5, 0.5), (-0.1, 0.5), (0.5, 0.0), (0.5, math.inf),
                 (True, 0.5), (0.5, None)]:
        with pytest.raises(LambdaContractError):
            acc.add("a", x, w)
    acc.add("a", 0.5, 0.5)
    with pytest.raises(ValueError):
        acc.add("a", 0.5, 0.5)
    empty = LogAccumulator()
    assert empty.log_value() == 0.0 and empty.zeros == 0


# ------------------------------------------- canonical numbers (§2.11) ----

def test_f64_literals_round_trip_every_vector_float():
    for vec in VECTORS:
        for field in ("axes", "weights"):
            values = vec[field] if isinstance(vec[field], list) else []
            for text in values:
                if isinstance(text, str) and text.startswith("f64:"):
                    assert canon.encode_f64(canon.decode_f64(text)) == text
    assert canon.encode_f64(0.8) == "f64:3fe999999999999a"
    assert canon.encode_f64(-0.0) == "f64:8000000000000000"
    assert canon.encode_f64(0.0) == "f64:0000000000000000"


@pytest.mark.parametrize("text", ["f64:3FE999999999999A", "f64:3fe99999999999", "3fe999999999999a",
                                  "f64:3fe999999999999g", "f64:3fe999999999999a ", 0.8, None])
def test_decode_f64_refuses_anything_but_the_exact_form(text):
    with pytest.raises(ValueError):
        canon.decode_f64(text)
    assert canon.is_f64_literal(text) is False


def test_canonical_bytes_exact_form():
    obj = {"b": 1, "a": [0.5, True, None, "Λ", (2, -0.0)], "c": {"z": 0.1, "y": "x"}}
    assert canon.canonical_bytes(obj) == (
        '{"a":["f64:3fe0000000000000",true,null,"Λ",[2,"f64:8000000000000000"]],'
        '"b":1,"c":{"y":"x","z":"f64:3fb999999999999a"}}').encode("utf-8")
    assert canon.canonical_sha256(obj) == hashlib.sha256(canon.canonical_bytes(obj)).hexdigest()


def test_canonical_bytes_sorts_keys_by_code_point_and_is_insertion_order_free():
    a = {"b": 1, "a": 2, "B": 3, "é": 4}
    b = dict(reversed(list(a.items())))
    assert canon.canonical_bytes(a) == canon.canonical_bytes(b)
    assert canon.canonical_bytes(a).startswith(b'{"B":3,"a":2,"b":1')


def test_float_subclasses_are_encoded_as_floats():
    class F(float):
        pass
    assert canon.canonical_bytes([F(0.8)]) == b'["f64:3fe999999999999a"]'


@pytest.mark.parametrize("bad", [
    math.nan, math.inf, -math.inf, [1.0, math.nan], {"x": math.inf},
    2 ** 53, -(2 ** 53), {1: "a"}, {("a",): 1}, {"a"}, b"bytes", object(),
    lam, _gen.rng(0),
])
def test_canonical_bytes_refuses_values_without_a_canonical_form(bad):
    with pytest.raises(canon.CanonError):
        canon.canonical_bytes(bad)


def test_canonical_bytes_refuses_enums_and_dataclasses():
    from szl_decide.gate import ReasonClass
    from szl_decide.lattice import GO_I, Tri
    for bad in (Tri.GO, ReasonClass.NONE, {"k": Tri.ABSTAIN}, {ReasonClass.NONE: 1}, GO_I):
        with pytest.raises(canon.CanonError):
            canon.canonical_bytes(bad)
    assert canon.canonical_bytes(2 ** 53 - 1) == b"9007199254740991"


def test_sha256_hex_takes_bytes_only():
    assert canon.sha256_hex(b"") == hashlib.sha256(b"").hexdigest()
    with pytest.raises(TypeError):
        canon.sha256_hex("text")  # type: ignore[arg-type]
