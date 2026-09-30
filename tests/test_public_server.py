# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""Witness the public boundary, immutable content binding and local separation."""
import hashlib
import http.client
import json
from pathlib import Path
import shutil
import socket
import threading

import pytest

from szl_triage import public_server as public
from szl_triage import server as local

ROOT = Path(__file__).resolve().parents[1]
AUTHORITY = "szlholdings-szl-typesafe-triage.hf.space"
COMMIT = "1234567890abcdef1234567890abcdef12345678"


def write_binding(path, root=ROOT):
    sources = sorted((root / "src/szl_triage").rglob("*.py"))
    sources.append(root / "src/szl_triage/data/triage_policy.v3.json")
    value = {"schema": public.BINDING_SCHEMA, "github_repository": public.GITHUB_REPOSITORY,
             "github_commit": COMMIT,
             "source_files": {source.relative_to(root).as_posix():
                              hashlib.sha256(source.read_bytes()).hexdigest()
                              for source in sources}}
    path.write_text(json.dumps(value), encoding="utf-8")
    return value


@pytest.fixture
def binding(tmp_path):
    path = tmp_path / "SOURCE_BINDING.json"
    write_binding(path)
    return path


@pytest.fixture
def copied_source(tmp_path):
    root = tmp_path / "source"
    shutil.copytree(ROOT / "src/szl_triage", root / "src/szl_triage",
                    ignore=shutil.ignore_patterns("__pycache__"))
    path = root / "SOURCE_BINDING.json"
    write_binding(path, root)
    return root, path


@pytest.fixture
def running_public(binding):
    runtime = public.make_public_server(trusted_authorities=(AUTHORITY,), port=0,
                                        binding_path=binding, allow_loopback_probes=True)
    worker = threading.Thread(target=runtime.serve_forever,
                              kwargs={"poll_interval": 0.01}, daemon=True)
    worker.start()
    yield runtime
    runtime.shutdown()
    runtime.server_close()
    worker.join(timeout=5)
    assert not worker.is_alive()


def request(runtime, method="GET", path="/readyz", body=None, headers=None):
    connection = http.client.HTTPConnection("127.0.0.1", runtime.server_port, timeout=3)
    try:
        connection.request(method, path, body=body, headers={"Host": AUTHORITY, **(headers or {})})
        response = connection.getresponse()
        return response.status, dict(response.getheaders()), response.read()
    finally:
        connection.close()


def post(runtime, body=b'{"text":"invoice refund charged"}', headers=None):
    return request(runtime, "POST", "/v1/decide", body,
                   {"Content-Type": "application/json", **(headers or {})})


def test_source_bound_software_lab_is_explicit(running_public, binding):
    assert running_public.server_address[0] == "0.0.0.0"
    status, headers, body = request(running_public)
    ready = json.loads(body)
    assert status == 200 and ready["schema"] == public.RUNTIME_SCHEMA
    assert ready["mode"] == "DETERMINISTIC_SOFTWARE_LAB"
    assert ready["disposition"] == "HOLD" and ready["model_loaded"] is False
    assert ready["scope"] == "DETERMINISTIC_RULE_BASED_SOFTWARE_ONLY"
    assert ready["source_binding"]["github_commit"] == COMMIT
    assert ready["source_binding"]["verified"] is True
    assert ready["source_binding"]["manifest_sha256"] == hashlib.sha256(binding.read_bytes()).hexdigest()
    assert ready["source_binding"]["authenticity"] == "UNSIGNED_CONTENT_BINDING_ONLY"
    assert "qualification" not in ready
    assert headers["Cache-Control"] == "no-store"
    assert headers["Content-Security-Policy"] == "default-src 'none'; frame-ancestors 'none'"


def test_public_decision_has_source_binding_and_never_promotes_a_model(running_public):
    status, _, body = post(running_public, headers={"Origin": f"https://{AUTHORITY}"})
    envelope = json.loads(body)
    assert status == 200 and envelope["schema"] == public.ENVELOPE_SCHEMA
    assert envelope["decision"]["label"] == "BILLING"
    assert envelope["model_loaded"] is False and envelope["disposition"] == "HOLD"
    assert envelope["source_binding"]["github_commit"] == COMMIT
    assert "text" not in envelope
    digest = envelope.pop("envelope_sha256")
    assert digest == hashlib.sha256(local._canonical(envelope)).hexdigest()
    assert envelope["decision_sha256"] == hashlib.sha256(local._canonical(envelope["decision"])).hexdigest()


@pytest.mark.parametrize("headers", [
    {"Host": "attacker.example", "X-Forwarded-Host": AUTHORITY},
    {"Host": "attacker.example", "Forwarded": f"host={AUTHORITY};proto=https"},
    {"Host": f"{AUTHORITY}:443"}, {"Host": AUTHORITY.upper()},
    {"Origin": "https://attacker.example"}, {"Origin": "https://huggingface.co"},
    {"Origin": "https://a11oy.net"}, {"Origin": f"http://{AUTHORITY}"},
    {"Origin": f"https://{AUTHORITY}/"}, {"Origin": "null"},
])
def test_untrusted_host_or_cross_origin_never_reaches_the_engine(running_public, monkeypatch, headers):
    monkeypatch.setattr(local, "decide", lambda *args: pytest.fail("Untrusted request reached engine"))
    assert post(running_public, headers=headers)[0] == 403


@pytest.mark.parametrize("name,values", [
    ("Host", [AUTHORITY, AUTHORITY]),
    ("Origin", [f"https://{AUTHORITY}", f"https://{AUTHORITY}"]),
    ("Content-Length", ["1", "1"]),
    ("Content-Type", ["application/json", "application/json"]),
    ("X-Probe", ["one", "two"]),
])
def test_duplicate_headers_are_rejected(running_public, name, values):
    connection = http.client.HTTPConnection("127.0.0.1", running_public.server_port, timeout=3)
    try:
        connection.putrequest("POST", "/v1/decide", skip_host=True)
        if name != "Host":
            connection.putheader("Host", AUTHORITY)
        for value in values:
            connection.putheader(name, value)
        connection.endheaders()
        response = connection.getresponse()
        assert response.status == 400
        assert json.loads(response.read())["error"] == "duplicate_header"
    finally:
        connection.close()


def test_probe_authority_is_exact_to_bound_port_and_loopback_peer(running_public):
    for name in ("127.0.0.1", "localhost"):
        authority = f"{name}:{running_public.server_port}"
        assert request(running_public, headers={"Host": authority, "Origin": f"http://{authority}"})[0] == 200
        assert request(running_public, headers={"Host": f"{name}:7861"})[0] == 403
    handler = object.__new__(public._PublicHandler)
    handler.server = running_public
    handler.client_address = ("192.0.2.1", 1234)
    handler.headers = http.client.HTTPMessage()
    handler.headers["Host"] = f"127.0.0.1:{running_public.server_port}"
    responses = []
    handler._json = lambda code, payload: responses.append((code, payload))
    assert handler._trusted_request() is False
    assert responses == [(403, {"error": "host_not_allowed"})]


def test_loopback_probes_require_explicit_opt_in(binding):
    runtime = public.make_public_server(trusted_authorities=(AUTHORITY,), port=0, binding_path=binding)
    try:
        assert runtime.allow_loopback_probes is False
    finally:
        runtime.server_close()


@pytest.mark.parametrize("raw,expected", [
    (b'{"text":false}', 400), (b'{"text":"a","text":"b"}', 400),
    (b'{"text":NaN}', 400), (b'{"text":"\\ud800"}', 400),
    (b'[' * 2000 + b'0' + b']' * 2000, 400),
    (json.dumps({"text": "x" * (local.MAX_TEXT_CHARS + 1)}).encode(), 413),
    (b"x" * (local.MAX_BODY_BYTES + 1), 413),
], ids=['boolean-text', 'duplicate-text', 'nan', 'surrogate', 'deep-nesting',
        'oversized-text', 'oversized-body'])
def test_public_entry_point_retains_json_and_body_boundaries(running_public, monkeypatch, raw, expected):
    monkeypatch.setattr(local, "decide", lambda *args: pytest.fail("Invalid request reached engine"))
    assert post(running_public, body=raw)[0] == expected


def test_json_depth_scan_ignores_braces_and_escaped_quotes_inside_text():
    value = {'text': 'invoice "quoted" \\ ' + '[{' * 2000 + '}]' * 2000}
    assert local._decode_json(json.dumps(value).encode()) == value


def test_public_connection_slots_remain_bounded(running_public):
    sockets = []
    try:
        for _ in range(local.MAX_CONNECTIONS):
            connection = socket.create_connection(("127.0.0.1", running_public.server_port), timeout=3)
            connection.sendall(b"GET /readyz HTTP/1.1\r\n")
            sockets.append(connection)
        # Wait for all connections to enter the bounded worker pool, without
        # relying on a sleep or launching more unbounded workers.
        for _ in range(500):
            if running_public._slots._value == 0:
                break
            threading.Event().wait(0.002)
        assert running_public._slots._value == 0
        excess = socket.create_connection(("127.0.0.1", running_public.server_port), timeout=3)
        try:
            assert excess.recv(4096).startswith(b"HTTP/1.1 503 Service Unavailable\r\n")
        finally:
            excess.close()
    finally:
        for connection in sockets:
            connection.close()


def test_landing_page_preserves_nonce_csp_and_explicit_hold(running_public):
    status, headers, body = request(running_public, path="/")
    html = body.decode()
    assert status == 200 and "DETERMINISTIC SOFTWARE LAB · HOLD" in html
    assert "No language model is loaded" in html and "Model promotion remains HOLD" in html
    assert "script-src 'nonce-" in headers["Content-Security-Policy"]
    assert "frame-ancestors 'none'" in headers["Content-Security-Policy"]
    assert "unsafe-inline" not in headers["Content-Security-Policy"]
    assert "innerHTML" not in html and "__NONCE__" not in html


def test_hf_iframe_permission_is_explicit_and_exact(binding):
    runtime = public.make_public_server(trusted_authorities=(AUTHORITY,), port=0,
                                        binding_path=binding, frame_ancestor="https://huggingface.co")
    try:
        assert runtime.frame_ancestors == "https://huggingface.co"
    finally:
        runtime.server_close()


@pytest.mark.parametrize("field,value", [
    ("schema", False), ("github_repository", False), ("github_commit", False),
    ("github_commit", "main"), ("github_commit", "A" * 40),
    ("source_files", False), ("source_files", []), ("source_files", {}),
])
def test_invalid_binding_identity_and_false_values_fail_before_binding(binding, monkeypatch, field, value):
    manifest = json.loads(binding.read_text())
    manifest[field] = value
    binding.write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(local, "_LocalServer", lambda *args, **kwargs: pytest.fail("Unverified source bound a socket"))
    with pytest.raises(ValueError):
        public.make_public_server(trusted_authorities=(AUTHORITY,), binding_path=binding)


@pytest.mark.parametrize("relative", ["../escape.py", "/escape.py", "C:\\escape.py",
                                     "src\\szl_triage\\server.py", "src/./szl_triage/server.py",
                                     "src/szl_triage/../server.py", "", "."])
def test_manifest_paths_cannot_escape_or_use_aliases(copied_source, relative):
    root, binding = copied_source
    manifest = json.loads(binding.read_text())
    manifest["source_files"][relative] = "0" * 64
    binding.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="path"):
        public.verify_source_binding(binding, root)


@pytest.mark.parametrize("drift", ["changed", "extra", "missing", "policy", "false_digest"])
def test_source_and_policy_drift_are_rejected(copied_source, drift):
    root, binding = copied_source
    source = root / "src/szl_triage/server.py"
    if drift == "changed":
        source.write_text("# changed\n", encoding="utf-8")
    elif drift == "extra":
        (root / "src/szl_triage/undeclared.py").write_text("# extra\n", encoding="utf-8")
    elif drift == "missing":
        source.unlink()
    elif drift == "policy":
        (root / "src/szl_triage/data/triage_policy.v3.json").write_text("{}", encoding="utf-8")
    else:
        manifest = json.loads(binding.read_text())
        manifest["source_files"]["src/szl_triage/server.py"] = False
        binding.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError):
        public.verify_source_binding(binding, root)


@pytest.mark.parametrize("authorities", [(), AUTHORITY, (AUTHORITY, AUTHORITY),
    ("*.hf.space",), ("https://example.com",), ("example.com/path",),
    ("EXAMPLE.COM",), ("example.com:0",), ("example.com:65536",),
    ("example.com:0443",), ("127.0.0.1",), (False,)])
def test_public_authority_configuration_is_explicit(authorities, binding):
    with pytest.raises(ValueError):
        public.make_public_server(trusted_authorities=authorities, binding_path=binding)


@pytest.mark.parametrize("option,value", [("port", False), ("port", -1), ("port", 65536),
    ("allow_loopback_probes", 1), ("allow_loopback_probes", "false"),
    ("frame_ancestor", "*"), ("frame_ancestor", "https://attacker.example"),
    ("frame_ancestor", False)])
def test_invalid_public_options_fail_before_binding(binding, option, value):
    with pytest.raises(ValueError):
        public.make_public_server(trusted_authorities=(AUTHORITY,), binding_path=binding, **{option: value})


def test_missing_binding_never_binds_a_socket(tmp_path, monkeypatch):
    monkeypatch.setattr(local, "_LocalServer", lambda *args, **kwargs: pytest.fail("Missing source bound a socket"))
    with pytest.raises(ValueError):
        public.make_public_server(trusted_authorities=(AUTHORITY,), binding_path=tmp_path / "absent.json")


def test_duplicate_manifest_fields_are_rejected(binding):
    binding.write_text('{"schema":"first","schema":"second"}', encoding="utf-8")
    with pytest.raises(ValueError, match="Duplicate"):
        public.make_public_server(trusted_authorities=(AUTHORITY,), binding_path=binding)


def test_docker_copies_source_only_and_has_explicit_public_command():
    source = (ROOT / "Dockerfile").read_text()
    copies = [line for line in source.splitlines() if line.startswith("COPY ")]
    assert copies == ["COPY src/szl_triage/*.py /app/src/szl_triage/",
                      "COPY src/szl_triage/providers/*.py /app/src/szl_triage/providers/",
                      "COPY src/szl_triage/data/triage_policy.v3.json /app/src/szl_triage/data/triage_policy.v3.json",
                      "COPY SOURCE_BINDING.json /app/SOURCE_BINDING.json"]
    assert 'CMD ["python", "-m", "szl_triage.public_server"]' in source
    assert "USER 1000:1000" in source and "EXPOSE 7860" in source


def test_local_default_remains_loopback():
    runtime = local.make_server()
    try:
        assert runtime.server_address[0] == "127.0.0.1"
        assert runtime.identity["mode"] == "DETERMINISTIC_LOCAL_RESEARCH"
        assert "source_binding" not in runtime.identity
    finally:
        runtime.server_close()
