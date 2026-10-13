# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""Native byte identity, nonce closure, and real package publication inclusion."""
import hashlib
from html.parser import HTMLParser
import importlib.util
import json
from pathlib import Path
import re

import pytest

from szl_triage import native_assets, presentation, public_server, server

ROOT = Path(__file__).resolve().parents[1]


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.elements = []

    def handle_starttag(self, tag, attrs):
        assert len(attrs) == len({key for key, _ in attrs}), f"Duplicate attributes on {tag}"
        self.elements.append((tag, dict(attrs)))


@pytest.mark.parametrize("public", [False, True])
def test_native_page_preserves_exact_art_and_nonce_closed_assets(public):
    html = presentation.render_landing(public=public)
    page = Page()
    page.feed(html)
    assert html.count(native_assets.ORBIT_SVG) == 1
    assert html.count(native_assets.TOKEN_CSS) == 1
    assert len(html.encode("utf-8")) < 65536
    assert set(re.findall(r"__[A-Z_]+__", html)) == {"__NONCE__"}
    assert html.count('nonce="__NONCE__"') == 2
    assert [attrs["nonce"] for tag, attrs in page.elements if tag in {"style", "script"}] == ["__NONCE__", "__NONCE__"]
    assert not [(tag, attrs) for tag, attrs in page.elements if "src" in attrs or tag in {"iframe", "img", "link"}]
    assert not [(tag, attrs) for tag, attrs in page.elements if "style" in attrs or any(key.startswith("on") for key in attrs)]
    ids = [attrs["id"] for _, attrs in page.elements if "id" in attrs]
    assert len(ids) == len(set(ids))
    assert sum(tag == "h1" for tag, _ in page.elements) == 1
    for _, attrs in page.elements:
        if attrs.get("href", "").startswith("#"):
            assert attrs["href"][1:] in ids
    buttons = [attrs for tag, attrs in page.elements if tag == "button"]
    assert "disabled" in next(attrs for attrs in buttons if attrs.get("id") == "submit")
    assert "hidden" in next(attrs for attrs in buttons if attrs.get("id") == "theme")
    assert "Model promotion remains HOLD" in html if public else "not a published GitHub source attestation" in html
    assert "innerHTML" not in html and "localStorage" not in html and "sessionStorage" not in html
    assert 'No language model is loaded.' in html


def test_entry_points_select_presentation_explicitly_without_string_rewrites():
    assert server._LANDING_PAGE == presentation.render_landing()
    assert public_server._LANDING_PAGE == presentation.render_landing(public=True)
    assert "local._LANDING_PAGE" not in (ROOT / "src/szl_triage/public_server.py").read_text()
    with pytest.raises(TypeError):
        presentation.render_landing(public="public")


def test_qualified_source_bytes_and_complete_manifest_are_unchanged():
    projection = json.loads(native_assets.PROJECTION_JSON)
    assert native_assets.PROJECTION_JSON == (ROOT / "docs/native-frontend-projection.json").read_text()
    assert projection["unsigned"] is True
    expected = {
        "TOKEN_CSS": "81f7c9baeef0b435e6e3f9d0c4e0d70e40fa17df5d1f30697f623cd3ef5f8eab",
        "SOURCE_MANIFEST": "967a77235227f1d75852fb61873e46336e67403cbc0e7e12b141e31c83fbd93d",
        "ORBIT_SVG": "6e2b7d72a3af3d9602b79de41df0194ede6496a9661f057108ec224c0efc92e6",
    }
    assert {row["constant"] for row in projection["assets"]} == set(expected)
    for row in projection["assets"]:
        data = getattr(native_assets, row["constant"]).encode("utf-8")
        assert hashlib.sha256(data).hexdigest() == row["sha256"] == expected[row["constant"]]
        assert len(data) == row["bytes"]
    upstream = json.loads(native_assets.SOURCE_MANIFEST)
    assert upstream["source_commit"] == projection["token_source_commit"]
    assert upstream["sha256"]["szl-tokens.css"] == expected["TOKEN_CSS"]


def test_actual_python_export_includes_native_modules_and_tamper_fails(tmp_path, monkeypatch):
    """Use current package bytes with explicitly synthetic Git authorization.

    No provider or actual canonical-source qualification occurs in this fixture.
    Canonical-main and signature qualification remain required at publication;
    this test witnesses the real export set and byte closure, not that authority.
    """
    spec = importlib.util.spec_from_file_location("native_fixture_publisher", ROOT / "scripts/publish_software_space.py")
    publisher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(publisher)
    commit = "a" * 40
    names = [path.relative_to(ROOT).as_posix() for path in (ROOT / "src/szl_triage").rglob("*.py")]
    names += [publisher.POLICY, "Dockerfile", "pyproject.toml", "README.md", "LICENSE", "docs/PROMOTION_PROGRAM.md"]
    blobs = {name: (ROOT / name).read_bytes() for name in names}

    def git(*args):
        if args[0] == "ls-remote":
            return (commit + "\trefs/heads/main\n").encode()
        if args == ("verify-commit", commit):
            return b""
        if args == ("ls-tree", "-r", "--name-only", commit):
            return ("\n".join(sorted(blobs)) + "\n").encode()
        if args[:2] == ("cat-file", "blob"):
            revision, name = args[2].split(":", 1)
            assert revision == commit
            return blobs[name]
        raise AssertionError("Unexpected Git operation")

    monkeypatch.setattr(publisher, "git", git)
    output = tmp_path / "synthetic-package-export"
    publisher.export(commit, output)
    binding_path = output / "SOURCE_BINDING.json"
    assert binding_path.stat().st_size < public_server.MAX_BINDING_BYTES
    bound = public_server.verify_source_binding(binding_path, output)
    assert bound["verified"] is True and bound["authenticity"] == "UNSIGNED_CONTENT_BINDING_ONLY"
    for name in ("native_assets.py", "presentation.py"):
        relative = "src/szl_triage/" + name
        assert (output / relative).read_bytes() == blobs[relative]
    assert (output / "SOURCE_README.md").read_bytes() == blobs["README.md"]
    assert "COPY src/szl_triage/*.py /app/src/szl_triage/" in blobs["Dockerfile"].decode()
    card = (output / "README.md").read_text()
    assert 'suite/szl-icon-32.svg" alt="SZL Holdings" width="40" height="40"' in card
    assert "HOLD / NOT_PROMOTABLE" in card and bound["github_commit"] == commit
    (output / "src/szl_triage/native_assets.py").write_text("# tampered native projection\n")
    with pytest.raises(ValueError, match="byte mismatch"):
        public_server.verify_source_binding(binding_path, output)
