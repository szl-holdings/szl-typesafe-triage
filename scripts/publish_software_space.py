"""Export canonical Git blobs and publish the deterministic research Space.

No model weights, working-tree files, tokens, or historical outputs enter this
publication. Dry export is the default; --publish is explicit operator action.
Uses the Hugging Face SDK's normal cached login without printing credentials.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess

REPOSITORY = 'szl-holdings/szl-typesafe-triage'
SPACE = 'SZLHOLDINGS/szl-typesafe-triage'
ROOT = Path(__file__).resolve().parents[1]
POLICY = 'src/szl_triage/data/triage_policy.v3.json'


def git(*args: str) -> bytes:
    return subprocess.check_output(['git', '-C', str(ROOT), *args], stderr=subprocess.PIPE)


def export(commit: str, destination: Path) -> dict:
    if not re.fullmatch('[0-9a-f]{40}', commit):
        raise ValueError('Full canonical commit required')
    # The exact commit must still be canonical main, not an unmerged local head.
    remote = git('ls-remote', 'https://github.com/' + REPOSITORY + '.git', 'refs/heads/main')
    if remote.decode().split()[0] != commit:
        raise ValueError('Source is not current canonical main')
    git('verify-commit', commit)
    names = git('ls-tree', '-r', '--name-only', commit).decode().splitlines()
    selected = [name for name in names if name.startswith('src/szl_triage/') and
                (name.endswith('.py') or name == POLICY)]
    selected += ['Dockerfile', 'pyproject.toml', 'README.md', 'LICENSE', 'docs/PROMOTION_PROGRAM.md']
    if POLICY not in selected or not selected or len(selected) != len(set(selected)):
        raise ValueError('Invalid source export set')
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=False)
    hashes = {}
    for name in selected:
        path = PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts:
            raise ValueError('Unsafe source path')
        content = git('cat-file', 'blob', f'{commit}:{name}')
        output = destination / name
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(content)
        if name.startswith('src/szl_triage/'):
            hashes[name] = hashlib.sha256(content).hexdigest()
    binding = {'schema': 'szl.triage-source-binding/v1', 'github_repository': REPOSITORY,
               'github_commit': commit, 'source_files': hashes}
    (destination/'SOURCE_BINDING.json').write_text(json.dumps(binding, indent=2)+'\n', encoding='utf-8')
    original = (destination/'README.md').read_bytes()
    (destination/'SOURCE_README.md').write_bytes(original)
    card = f'''---
title: TypeSafe Triage Lab
sdk: docker
app_port: 7860
license: apache-2.0
---

<p><a href="https://huggingface.co/spaces/SZLHOLDINGS/szl-command-lab"><img src="https://raw.githubusercontent.com/szl-holdings/.github/main/profile/assets/szl/logos/szl_mark_holographic.svg" alt="SZL Holdings" width="112" /></a></p>

# TypeSafe Triage Lab

Inspect a deterministic triage engine with source and policy bindings. The Space makes explicit decisions without loading a language model or adapter.

**Artifact:** Deterministic Python software lab · **Stage:** Software lab; learned-model promotion on hold

[Explore in Command Lab](https://huggingface.co/spaces/SZLHOLDINGS/szl-command-lab) · [Build](https://github.com/szl-holdings/szl-typesafe-triage) · [Evidence](https://github.com/szl-holdings/szl-typesafe-triage/blob/5a815b5e743e5d156ee4f875546ac4bda38a4341/docs/PROMOTION_PROGRAM.md)

## Before you use it

- Learned-model promotion remains HOLD / NOT\\_PROMOTABLE. A running service does not establish model accuracy or immunity to prompt injection.
- Decision content-integrity hashes are unsigned and do not authenticate an issuer.
- Experimental research modules do not participate in live decisions or confer release authority.

<details>
<summary>Technical details and original evidence</summary>

The retained source below is exact and may contain historical observations. Its dates, use restrictions, licenses and evidence boundaries continue to apply.

<!-- SZL-PRESERVED-TECHNICAL-BODY:START -->

# TypeSafe Triage Lab

This Space runs the deterministic Python triage engine. No language model or
adapter is loaded. Learned-model promotion remains **HOLD / NOT_PROMOTABLE**.
Literal evidence, schema validity and a running service do not establish model
accuracy or immunity to prompt injection.

Canonical source: [GitHub {commit}](https://github.com/{REPOSITORY}/tree/{commit}).
The startup verifier checks the deployed package and policy against
`SOURCE_BINDING.json`; `/readyz` reports the verified commit and exact binding.
`/v1/decide` performs real deterministic decisions with content-integrity hashes.
Those hashes are unsigned; they do not authenticate an issuer.

The experimental span-choice task, six-criterion evaluator and fixed-grid risk
audit are available as Python research modules. They do not participate in
live decisions and do not confer release authority. Read
`docs/PROMOTION_PROGRAM.md` and `SOURCE_README.md` for assumptions and limits.

<!-- SZL-PRESERVED-TECHNICAL-BODY:END -->

</details>
'''
    (destination/'README.md').write_text(card, encoding='utf-8')
    files = {p.relative_to(destination).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in destination.rglob('*') if p.is_file()}
    return {'github_repository': REPOSITORY, 'github_commit': commit, 'space': SPACE,
            'files': files, 'source_binding_sha256': files['SOURCE_BINDING.json'],
            'model_loaded': False, 'model_promotion': 'NOT_PROMOTABLE',
            'release_authorization': 'NONE'}


def publish(destination: Path, receipt: dict) -> dict:
    from huggingface_hub import CommitOperationAdd, HfApi, hf_hub_download
    from huggingface_hub.errors import RepositoryNotFoundError
    # Capture and verify only the declared immutable payload before any external
    # mutation. Do not let upload_folder re-enumerate a mutable export directory.
    destination = destination.resolve()
    expected = receipt['files']
    actual_names = {p.relative_to(destination).as_posix() for p in destination.rglob('*') if p.is_file()}
    if actual_names != set(expected):
        raise ValueError('Local publication output set mismatch')
    captured = {}
    for name, digest in expected.items():
        path = destination / name
        if path.is_symlink() or not path.resolve().is_relative_to(destination):
            raise ValueError('Publication source path is not contained')
        content = path.read_bytes()
        if hashlib.sha256(content).hexdigest() != digest:
            raise ValueError('Local publication bytes changed: ' + name)
        captured[name] = content
    current = git('ls-remote', 'https://github.com/' + REPOSITORY + '.git', 'refs/heads/main')
    if current.decode().split()[0] != receipt['github_commit']:
        raise ValueError('Canonical source changed before publication')
    api = HfApi()
    # Membership is checked by the provider on normal authenticated operations.
    try:
        info = api.repo_info(SPACE, repo_type='space')
    except RepositoryNotFoundError:
        api.create_repo(SPACE, repo_type='space', space_sdk='docker', private=False)
        info = api.repo_info(SPACE, repo_type='space')
    before = api.list_repo_files(SPACE, repo_type='space', revision=info.sha)
    managed = set(receipt['files'])
    extra = set(before) - managed - {'.gitattributes'}
    if extra:
        raise ValueError('Unmanaged existing Space files; refuse destructive publication: ' + ', '.join(sorted(extra)))
    operations = [CommitOperationAdd(path_in_repo=name, path_or_fileobj=content)
                  for name, content in captured.items()]
    receipt['parent_commit'] = info.sha
    result = api.create_commit(repo_id=SPACE, repo_type='space', operations=operations,
                               parent_commit=info.sha,
                               commit_message='Source-bound deterministic lab from ' + receipt['github_commit'])
    receipt['huggingface_commit'] = result.oid
    receipt['parent_commit'] = info.sha
    receipt['publication_status'] = 'UPLOADED_NOT_YET_VERIFIED'
    observed = api.repo_info(SPACE, repo_type='space', revision=result.oid)
    names = set(api.list_repo_files(SPACE, repo_type='space', revision=result.oid))
    if names - {'.gitattributes'} != managed:
        raise RuntimeError('Remote publication output set mismatch')
    actual = {}
    for name, expected in receipt['files'].items():
        # SDK cache avoids a second disposable copy; exact immutable revision.
        path = hf_hub_download(SPACE, name, repo_type='space', revision=result.oid)
        actual[name] = hashlib.sha256(Path(path).read_bytes()).hexdigest()
        if actual[name] != expected:
            raise RuntimeError('Remote byte mismatch: ' + name)
    return {**receipt, 'publication_status': 'BYTE_PARITY_VERIFIED', 'huggingface_commit': observed.sha,
            'parent_commit': info.sha, 'remote_files_sha256': actual,
            'runtime_status': 'NOT_YET_WITNESSED', 'release_authorization': 'SOFTWARE_LAB_ONLY'}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-commit', required=True)
    parser.add_argument('--export-dir', type=Path, required=True, help='New exclusive directory')
    parser.add_argument('--receipt', type=Path, required=True, help='New exclusive output path')
    parser.add_argument('--publish', action='store_true')
    args = parser.parse_args(argv)
    if args.receipt.exists():
        raise ValueError('Refuse receipt overwrite')
    with args.receipt.open('x', encoding='utf-8') as handle:
        receipt = {'github_commit': args.source_commit, 'space': SPACE,
                   'publication_status': 'NOT_STARTED', 'release_authorization': 'NONE'}
        try:
            receipt = export(args.source_commit, args.export_dir)
            receipt['publication_status'] = 'EXPORTED_ONLY'
            if args.publish:
                receipt = publish(args.export_dir, receipt)
        except Exception as exc:
            receipt['prior_publication_status'] = receipt['publication_status']
            receipt['publication_status'] = 'FAILED'
            receipt['error_type'] = type(exc).__name__
            raise
        finally:
            receipt['created_utc'] = datetime.now(timezone.utc).isoformat()
            json.dump(receipt, handle, indent=2, allow_nan=False)
            handle.write('\n')
    print(json.dumps({k:receipt[k] for k in ('github_commit','publication_status','space')}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
