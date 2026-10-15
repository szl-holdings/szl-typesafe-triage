# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""Run the actual local/public presentation servers for local browser fixtures.

The public startup binding is created from these local package bytes. It is
explicitly unsigned test metadata, not a publisher or live deployment receipt.
No provider, model, release writer, or external transport is invoked. The only
POST path is the existing deterministic decision endpoint with synthetic inputs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import threading

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from szl_triage import public_server, server  # noqa: E402


def git(*args: str) -> str:
    return subprocess.check_output(["git", "-C", str(ROOT), *args], timeout=5).decode().strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    revision = git("rev-parse", "HEAD")
    changed = git("status", "--porcelain", "--", "src", "scripts", "tests", "Dockerfile", "pyproject.toml", ".github/workflows/ci.yml", "docs/native-frontend-projection.json")
    sources = sorted((ROOT / "src/szl_triage").rglob("*.py"))
    sources.append(ROOT / "src/szl_triage/data/triage_policy.v3.json")
    files = {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources}
    binding = {"schema": public_server.BINDING_SCHEMA,
               "github_repository": public_server.GITHUB_REPOSITORY,
               "github_commit": "0" * 40 if changed else revision,
               "source_files": files}
    observations = {"schema": "szl.triage.local-browser-fixture/v1", "unsigned": True,
                    "source_revision": revision, "source_tree": git("rev-parse", "HEAD^{tree}"),
                    "local_changes": changed.splitlines(), "data_class": "LOCAL_DETERMINISTIC_SOFTWARE_FIXTURES",
                    "binding_is_publisher_authentication": False, "provider_mutations": 0,
                    "model_loaded": False, "live_verified": False, "package_sha256": files}
    runtimes = []
    started = []
    workers = []
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())

    def input_stop():
        sys.stdin.readline()
        stop.set()

    with tempfile.TemporaryDirectory(prefix="triage-native-binding-") as directory:
        binding_path = Path(directory) / "SOURCE_BINDING.json"
        binding_path.write_text(json.dumps(binding, indent=2) + "\n", encoding="utf-8")
        try:
            runtimes.append(server.make_server())
            runtimes.append(public_server.make_public_server(
                trusted_authorities=("szlholdings-szl-typesafe-triage.hf.space",), port=0,
                allow_loopback_probes=True, binding_path=binding_path,
            ))
            for runtime in runtimes:
                worker = threading.Thread(target=runtime.serve_forever, kwargs={"poll_interval": .01}, daemon=True)
                worker.start()
                workers.append(worker)
                started.append(runtime)
            observations["origins"] = [f"http://127.0.0.1:{runtime.server_port}" for runtime in runtimes]
            observations["source_binding"] = public_server.verify_source_binding(binding_path)
            (args.out / "fixture-source.json").write_text(json.dumps(observations, indent=2) + "\n", encoding="utf-8")
            print(json.dumps({"origins": observations["origins"]}), flush=True)
            threading.Thread(target=input_stop, daemon=True).start()
            stop.wait()
        finally:
            for runtime in runtimes:
                if runtime in started:
                    runtime.shutdown()
                runtime.server_close()
            for worker in workers:
                worker.join(timeout=5)
    assert not any(module in sys.modules for module in ("torch", "transformers", "peft"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
