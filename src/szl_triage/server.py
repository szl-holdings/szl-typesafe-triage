# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""Bounded loopback service for deterministic research; no model is loaded.

Envelopes bind their contents. They are unsigned and authenticate neither an
issuer nor execution, and do not establish model promotion.
"""
from __future__ import annotations

import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
from pathlib import Path
import re
import secrets
import socket
import threading
from typing import Any

from . import __version__, policy as policy_module
from .pipeline import decide

MODE = "DETERMINISTIC_LOCAL_RESEARCH"
ENVELOPE_SCHEMA = "szl.local-decision-envelope/v1"
MAX_BODY_BYTES = 65536
MAX_TEXT_CHARS = 8192
READ_TIMEOUT = 5.0
MAX_CONNECTIONS = 8
_HASH = re.compile(r"[0-9a-f]{64}\Z")


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(value: str) -> Any:
    raise ValueError("Non-finite JSON constant")


def _decode_json(data: bytes) -> Any:
    value = json.loads(data.decode("utf-8"), object_pairs_hook=_unique_object,
                       parse_constant=_reject_constant)
    _canonical(value)  # Reject numeric overflow and unpaired surrogates too.
    return value


def _implementation_identity() -> dict[str, str]:
    root = Path(__file__).resolve().parent
    files = {path.relative_to(root).as_posix(): _sha(path.read_bytes())
             for path in sorted(root.rglob("*.py"))}
    return {"package_version": __version__, "source_files_sha256": _sha(_canonical(files)),
            "binding": "PACKAGE_SOURCE_FILES_AT_STARTUP"}


def verify_envelope(value: Any) -> bool:
    """Check payload and envelope digests; never authenticate an issuer."""
    try:
        required = {"schema", "mode", "authenticity", "policy", "implementation",
                    "decision", "decision_sha256", "envelope_sha256"}
        if not isinstance(value, dict) or set(value) != required:
            return False
        if (value["schema"] != ENVELOPE_SCHEMA or value["mode"] != MODE
                or value["authenticity"] != "UNSIGNED_CONTENT_INTEGRITY_ONLY"
                or not isinstance(value["decision"], dict)):
            return False
        for key in ("decision_sha256", "envelope_sha256"):
            if not isinstance(value[key], str) or not _HASH.fullmatch(value[key]):
                return False
        policy, implementation = value["policy"], value["implementation"]
        if (not isinstance(policy, dict) or set(policy) != {"name", "version", "sha256"}
                or not all(isinstance(item, str) for item in policy.values())
                or not _HASH.fullmatch(policy["sha256"])
                or not isinstance(implementation, dict)
                or set(implementation) != {"package_version", "source_files_sha256", "binding"}
                or not all(isinstance(item, str) for item in implementation.values())
                or not _HASH.fullmatch(implementation["source_files_sha256"])
                or implementation["binding"] != "PACKAGE_SOURCE_FILES_AT_STARTUP"):
            return False
        payload = {key: item for key, item in value.items() if key != "envelope_sha256"}
        return (value["decision_sha256"] == _sha(_canonical(value["decision"]))
                and value["envelope_sha256"] == _sha(_canonical(payload)))
    except (TypeError, ValueError, RecursionError):
        return False


_LANDING_PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Local triage · SZL</title><style nonce="__NONCE__">
body{margin:0;background:#0c1422;color:#e5edf7;font:16px system-ui,sans-serif}
main{max-width:800px;margin:8vh auto;padding:24px}h1{font-size:42px;margin:16px 0}
.eyebrow{color:#7dd3fc;font-size:13px;letter-spacing:.12em}p{line-height:1.6;color:#b8c7db}
label{display:block;margin:30px 0 12px;font-weight:600}textarea{box-sizing:border-box;width:100%;min-height:150px;
border:1px solid #45607d;border-radius:12px;padding:16px;background:#172337;color:#f1f5f9;font:inherit;resize:vertical}
button{margin:16px 0;padding:12px 20px;border:0;border-radius:8px;background:#7dd3fc;color:#082f49;font:600 16px system-ui;cursor:pointer}
button:disabled{opacity:.6}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#172337;padding:20px;border-radius:12px;font-size:13px}
#identity{font-size:13px}#status{margin-left:12px;color:#b8c7db}small{display:block;color:#91a4bd;line-height:1.6}
</style></head><body><main><div class="eyebrow">SZL · DETERMINISTIC LOCAL RESEARCH</div>
<h1>Local triage</h1><p>Inspect how the rule-based engine classifies a report and where it refuses to decide.
It uses vocabulary and policy rules. No language model is loaded.</p><p id="identity">Loading policy identity…</p>
<label for="text">Report or error message</label><textarea id="text" maxlength="8192">charged twice on invoice INV-2041, want a refund</textarea>
<button id="submit" type="button">Run triage</button><span id="status" role="status"></span>
<pre id="result" aria-live="polite">Your decision and its content digests will appear here.</pre>
<small>Digests check that the returned contents agree. They are unsigned and do not establish model promotion or production readiness.</small>
</main><script nonce="__NONCE__">
const button=document.getElementById('submit'), status=document.getElementById('status'), result=document.getElementById('result');
fetch('/readyz').then(r=>r.json()).then(r=>{document.getElementById('identity').textContent='Policy '+r.policy.version+' · SHA-256 '+r.policy.sha256.slice(0,16);}).catch(()=>{document.getElementById('identity').textContent='Readiness unavailable';});
button.addEventListener('click',async()=>{button.disabled=true;status.textContent='Running…';try{
const response=await fetch('/v1/decide',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:document.getElementById('text').value})});
const body=await response.json();result.textContent=JSON.stringify(body,null,2);status.textContent=response.ok?body.decision.state:'Request rejected';
}catch(error){result.textContent='The local service could not be reached.';status.textContent='Unavailable';}finally{button.disabled=false;}});
</script></body></html>"""


class _LocalServer(ThreadingHTTPServer):
    daemon_threads = True
    block_on_close = False
    allow_reuse_address = False

    def __init__(self, policy: policy_module.Policy, policy_sha256: str, port: int):
        self.policy = policy
        self.policy_sha256 = policy_sha256
        self.identity = {"mode": MODE,
                         "policy": {"name": policy.name, "version": policy.version, "sha256": policy_sha256},
                         "implementation": _implementation_identity(), "model_loaded": False}
        self._slots = threading.BoundedSemaphore(MAX_CONNECTIONS)
        super().__init__(("127.0.0.1", port), _Handler)

    def get_request(self):
        connection, address = super().get_request()
        connection.settimeout(READ_TIMEOUT)
        return connection, address

    def process_request(self, request, client_address):
        if not self._slots.acquire(blocking=False):
            try:
                request.sendall(b"HTTP/1.1 503 Service Unavailable\r\nContent-Length: 0\r\nConnection: close\r\n\r\n")
            except OSError:
                pass
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self._slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._slots.release()

    def handle_error(self, request, client_address):
        pass  # Do not write request data or tracebacks to a persistent log.


class _Handler(BaseHTTPRequestHandler):
    server: _LocalServer
    protocol_version = "HTTP/1.1"
    server_version = "SZLLocal/1"
    sys_version = ""

    def log_message(self, format, *args):
        pass

    def _reply(self, status: int, body: bytes, content_type: str = "application/json; charset=utf-8",
               csp: str | None = None) -> None:
        self.close_connection = True
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", csp or "default-src 'none'; frame-ancestors 'none'")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, status: int, value: Any) -> None:
        self._reply(status, _canonical(value))

    def send_error(self, code, message=None, explain=None):
        self._json(code, {"error": "invalid_http_request", "status": code})

    def _trusted_request(self) -> bool:
        authority = f"127.0.0.1:{self.server.server_port}"
        if self.headers.get_all("Host", []) != [authority]:
            self._json(403, {"error": "host_not_allowed"})
            return False
        origins = self.headers.get_all("Origin", [])
        if origins and origins != [f"http://{authority}"]:
            self._json(403, {"error": "origin_not_allowed"})
            return False
        return True

    def do_GET(self):
        if not self._trusted_request():
            return
        if self.path == "/healthz":
            self._json(200, {"status": "UP", "mode": MODE})
        elif self.path == "/readyz":
            self._json(200, {"status": "READY", **self.server.identity})
        elif self.path == "/":
            nonce = secrets.token_urlsafe(18)
            csp = (f"default-src 'none'; script-src 'nonce-{nonce}'; style-src 'nonce-{nonce}'; "
                   "connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
            self._reply(200, _LANDING_PAGE.replace("__NONCE__", nonce).encode("utf-8"),
                        "text/html; charset=utf-8", csp)
        else:
            self._json(404, {"error": "not_found"})

    def do_POST(self):
        if not self._trusted_request():
            return
        if self.path != "/v1/decide":
            self._json(404, {"error": "not_found"})
            return
        if self.headers.get_all("Transfer-Encoding"):
            self._json(400, {"error": "transfer_encoding_not_supported"})
            return
        lengths = self.headers.get_all("Content-Length", [])
        if not lengths:
            self._json(411, {"error": "content_length_required"})
            return
        if len(lengths) != 1 or not re.fullmatch(r"[0-9]{1,10}", lengths[0]):
            self._json(400, {"error": "invalid_content_length"})
            return
        length = int(lengths[0])
        if length > MAX_BODY_BYTES:
            self._json(413, {"error": "body_too_large"})
            return
        types = self.headers.get_all("Content-Type", [])
        if (len(types) != 1 or not re.fullmatch(r"application/json(?:\s*;\s*charset=utf-8)?", types[0], re.I)
                or self.headers.get_all("Content-Encoding")):
            self._json(415, {"error": "application_json_required"})
            return
        try:
            raw = self.rfile.read(length)
            if len(raw) != length:
                raise ValueError("Incomplete body")
            data = _decode_json(raw)
            if (not isinstance(data, dict) or set(data) != {"text"}
                    or not isinstance(data["text"], str) or not data["text"].strip()):
                raise ValueError("Expected nonempty text")
            if len(data["text"]) > MAX_TEXT_CHARS:
                self._json(413, {"error": "text_too_large"})
                return
        except (socket.timeout, TimeoutError):
            self._json(408, {"error": "request_timeout"})
            return
        except (ValueError, RecursionError):
            self._json(400, {"error": "invalid_json_or_text"})
            return
        try:
            decision = decide(data["text"], self.server.policy).to_dict()
            envelope = {"schema": ENVELOPE_SCHEMA, "mode": MODE,
                        "authenticity": "UNSIGNED_CONTENT_INTEGRITY_ONLY",
                        "policy": self.server.identity["policy"],
                        "implementation": self.server.identity["implementation"],
                        "decision": decision, "decision_sha256": _sha(_canonical(decision))}
            envelope["envelope_sha256"] = _sha(_canonical(envelope))
        except Exception:
            self._json(500, {"error": "decision_failed"})
            return
        self._json(200, envelope)


def make_server(policy_path: str | Path | None = None, port: int = 0) -> _LocalServer:
    """Bind loopback after loading and identifying one immutable policy snapshot."""
    if type(port) is not int or not 0 <= port <= 65535:
        raise ValueError("Port must be an integer between 0 and 65535")
    path = Path(policy_path) if policy_path is not None else policy_module.default_policy_path()
    before = path.read_bytes()
    _decode_json(before)
    policy = policy_module.load(path)
    if not all(math.isfinite(weight) and weight > 0 for weight in policy.axis_weights.values()):
        raise ValueError("Policy axis weights must be finite and positive")
    if path.read_bytes() != before:
        raise RuntimeError("Policy changed while loading; server was not started")
    return _LocalServer(policy, _sha(before), port)


def serve(policy_path: str | Path | None = None, port: int = 8765) -> int:
    """Serve until interrupted, without external exposure or evidence writes."""
    server = make_server(policy_path, port)
    print(json.dumps({"url": f"http://127.0.0.1:{server.server_port}", **server.identity}), flush=True)
    try:
        server.serve_forever(poll_interval=0.2)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0
