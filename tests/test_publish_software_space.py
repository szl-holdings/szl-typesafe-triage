# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""Witness software-only publication boundaries without Git or provider access."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]
COMMIT = 'a' * 40
PARENT = 'b' * 40
UPLOADED = 'c' * 40


@pytest.fixture
def publisher():
    spec = importlib.util.spec_from_file_location(
        'test_software_publisher', ROOT / 'scripts/publish_software_space.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def canonical_git(publisher, monkeypatch):
    blobs = {
        'src/szl_triage/__init__.py': b'# exact canonical package bytes\n',
        publisher.POLICY: b'{"labels":["REVIEW"]}\n',
        'Dockerfile': b'FROM python:3.12-slim\n',
        'pyproject.toml': b'[project]\nname="szl-triage"\n',
        'README.md': b'# Retained canonical source README\n',
        'LICENSE': b'Apache-2.0\n',
        'docs/PROMOTION_PROGRAM.md': b'# Promotion program\nHOLD\n',
        'out/model.safetensors': b'never publish model bytes',
        'out/release_gate.json': b'never publish historical proof bytes',
    }
    state = SimpleNamespace(blobs=blobs, calls=[], main=COMMIT)

    def git(*args):
        state.calls.append(args)
        if args[0] == 'ls-remote':
            assert args[1:] == (
                'https://github.com/' + publisher.REPOSITORY + '.git', 'refs/heads/main')
            return (state.main + '\trefs/heads/main\n').encode()
        if args == ('verify-commit', COMMIT):
            return b''
        if args == ('ls-tree', '-r', '--name-only', COMMIT):
            return ('\n'.join(sorted(blobs)) + '\n').encode()
        if args[:2] == ('cat-file', 'blob'):
            commit, name = args[2].split(':', 1)
            assert commit == COMMIT
            return blobs[name]
        raise AssertionError('Unexpected Git operation: ' + repr(args))

    monkeypatch.setattr(publisher, 'git', git)
    return state


@pytest.fixture
def provider(monkeypatch, tmp_path):
    """Install a strict in-memory SDK double, including immutable readback."""
    sdk = ModuleType('huggingface_hub')
    errors = ModuleType('huggingface_hub.errors')

    class RepositoryNotFoundError(Exception):
        pass

    class CommitOperationAdd:
        def __init__(self, *, path_in_repo, path_or_fileobj):
            assert isinstance(path_or_fileobj, bytes)
            self.path_in_repo = path_in_repo
            self.path_or_fileobj = path_or_fileobj

    class API:
        def __init__(self):
            self.calls = []
            self.mutations = []
            self.before = {'.gitattributes'}
            self.uploaded = {}
            self.operations = []
            self.on_first_read = None
            self.failure_phase = None
            self.first_read = True

        def repo_info(self, space, *, repo_type, revision=None):
            self.calls.append(('repo_info', space, repo_type, revision))
            assert repo_type == 'space'
            if self.first_read:
                self.first_read = False
                if self.on_first_read:
                    self.on_first_read()
            if revision is not None:
                assert revision == UPLOADED
                if self.failure_phase == 'readback':
                    raise RuntimeError('Synthetic verification failure')
                return SimpleNamespace(sha=UPLOADED)
            return SimpleNamespace(sha=PARENT)

        def list_repo_files(self, space, *, repo_type, revision):
            self.calls.append(('list_repo_files', space, repo_type, revision))
            assert repo_type == 'space'
            if revision == PARENT:
                return sorted(self.before)
            assert revision == UPLOADED
            return sorted(set(self.uploaded) | {'.gitattributes'})

        def create_repo(self, *args, **kwargs):
            self.mutations.append(('create_repo', args, kwargs))
            raise AssertionError('Existing fake Space must not be recreated')

        def upload_folder(self, **kwargs):
            raise AssertionError('Mutable-directory publication is forbidden')

        def create_commit(self, *, repo_id, repo_type, operations, parent_commit, commit_message):
            assert repo_type == 'space' and parent_commit == PARENT
            assert COMMIT in commit_message
            self.mutations.append(('create_commit', repo_id, parent_commit))
            self.operations = operations
            assert all(type(operation) is CommitOperationAdd for operation in operations)
            if self.failure_phase == 'upload':
                raise RuntimeError('Synthetic upload failure')
            self.uploaded = {operation.path_in_repo: operation.path_or_fileobj
                             for operation in operations}
            return SimpleNamespace(oid=UPLOADED)

    api = API()

    def download(space, name, *, repo_type, revision):
        api.calls.append(('download', space, name, repo_type, revision))
        assert repo_type == 'space' and revision == UPLOADED
        cache = tmp_path / 'mock-provider-cache' / name
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_bytes(api.uploaded[name])
        return str(cache)

    sdk.HfApi = lambda: api
    sdk.CommitOperationAdd = CommitOperationAdd
    sdk.hf_hub_download = download
    errors.RepositoryNotFoundError = RepositoryNotFoundError
    monkeypatch.setitem(sys.modules, 'huggingface_hub', sdk)
    monkeypatch.setitem(sys.modules, 'huggingface_hub.errors', errors)
    return api


def test_export_uses_only_canonical_software_blobs(publisher, canonical_git, tmp_path):
    destination = tmp_path / 'new-export'
    receipt = publisher.export(COMMIT, destination)
    source = 'src/szl_triage/__init__.py'
    assert (destination / source).read_bytes() == canonical_git.blobs[source]
    assert (destination / 'SOURCE_README.md').read_bytes() == canonical_git.blobs['README.md']
    assert not any(name.startswith('out/') for name in receipt['files'])
    binding = json.loads((destination / 'SOURCE_BINDING.json').read_text())
    assert binding['github_commit'] == COMMIT
    assert binding['source_files'][source] == hashlib.sha256(canonical_git.blobs[source]).hexdigest()
    assert canonical_git.calls.index(('verify-commit', COMMIT)) < next(
        index for index, call in enumerate(canonical_git.calls) if call[0] == 'cat-file')
    assert receipt['model_loaded'] is False
    assert receipt['model_promotion'] == 'NOT_PROMOTABLE'
    assert receipt['release_authorization'] == 'NONE'
    assert 'No language model or' in (destination / 'README.md').read_text()


@pytest.mark.parametrize('drift', ['extra', 'changed', 'missing'])
def test_local_payload_drift_is_rejected_before_provider_access(
        publisher, canonical_git, provider, tmp_path, drift):
    destination = tmp_path / 'new-export'
    receipt = publisher.export(COMMIT, destination)
    if drift == 'extra':
        (destination / 'model.safetensors').write_bytes(b'forbidden model bytes')
    elif drift == 'changed':
        (destination / 'Dockerfile').write_bytes(b'changed working-directory content')
    else:
        (destination / 'LICENSE').unlink()
    with pytest.raises(ValueError, match='Local publication'):
        publisher.publish(destination, receipt)
    assert provider.calls == []
    assert provider.mutations == []


def test_publication_uploads_captured_bytes_and_only_enumerated_adds(
        publisher, canonical_git, provider, tmp_path):
    destination = tmp_path / 'new-export'
    receipt = publisher.export(COMMIT, destination)
    original = {name: (destination / name).read_bytes() for name in receipt['files']}

    def contaminate_after_capture():
        (destination / 'Dockerfile').write_bytes(b'changed after validated capture')
        (destination / 'model.safetensors').write_bytes(b'never send this extra file')

    provider.on_first_read = contaminate_after_capture
    result = publisher.publish(destination, receipt)
    assert provider.uploaded == original
    assert len(provider.operations) == len(original)
    assert provider.mutations == [('create_commit', publisher.SPACE, PARENT)]
    assert result['publication_status'] == 'BYTE_PARITY_VERIFIED'
    assert result['remote_files_sha256'] == receipt['files']
    assert result['huggingface_commit'] == UPLOADED and result['parent_commit'] == PARENT
    assert result['runtime_status'] == 'NOT_YET_WITNESSED'
    assert result['release_authorization'] == 'SOFTWARE_LAB_ONLY'
    assert result['model_loaded'] is False and result['model_promotion'] == 'NOT_PROMOTABLE'
    assert {call[2] for call in provider.calls if call[0] == 'download'} == set(original)


def test_existing_remote_model_or_proof_files_are_never_deleted(
        publisher, canonical_git, provider, tmp_path):
    destination = tmp_path / 'new-export'
    receipt = publisher.export(COMMIT, destination)
    provider.before |= {'adapter_model.safetensors', 'out/release_gate.json'}
    with pytest.raises(ValueError, match='Unmanaged existing Space files'):
        publisher.publish(destination, receipt)
    assert provider.mutations == []
    assert provider.before == {'.gitattributes', 'adapter_model.safetensors', 'out/release_gate.json'}


@pytest.mark.parametrize('phase', ['export', 'publish'])
def test_wrong_canonical_main_refuses_source_before_provider_mutation(
        publisher, canonical_git, provider, tmp_path, phase):
    destination = tmp_path / 'new-export'
    receipt = None
    if phase == 'publish':
        receipt = publisher.export(COMMIT, destination)
    canonical_git.main = 'd' * 40
    with pytest.raises(ValueError, match='canonical|Canonical'):
        if phase == 'export':
            publisher.export(COMMIT, destination)
        else:
            assert receipt is not None
            publisher.publish(destination, receipt)
    if phase == 'export':
        assert not destination.exists()
    assert provider.calls == [] and provider.mutations == []


@pytest.mark.parametrize('failure_phase', ['upload', 'readback'])
def test_failed_main_retains_publication_state_and_known_commit_identity(
        publisher, canonical_git, provider, tmp_path, failure_phase):
    output = tmp_path / 'new-receipt.json'
    provider.failure_phase = failure_phase
    with pytest.raises(RuntimeError, match='Synthetic'):
        publisher.main(['--source-commit', COMMIT, '--export-dir', str(tmp_path / 'new-export'),
                        '--receipt', str(output), '--publish'])
    retained = json.loads(output.read_text())
    assert retained['publication_status'] == 'FAILED'
    assert retained['parent_commit'] == PARENT
    assert retained['error_type'] == 'RuntimeError'
    assert retained['created_utc']
    assert retained['release_authorization'] == 'NONE'
    assert retained['model_loaded'] is False and retained['model_promotion'] == 'NOT_PROMOTABLE'
    if failure_phase == 'readback':
        assert retained['prior_publication_status'] == 'UPLOADED_NOT_YET_VERIFIED'
        assert retained['huggingface_commit'] == UPLOADED
    else:
        assert retained['prior_publication_status'] == 'EXPORTED_ONLY'
        assert 'huggingface_commit' not in retained


def test_existing_export_directory_and_files_are_not_overwritten(
        publisher, canonical_git, tmp_path):
    destination = tmp_path / 'retained-export'
    destination.mkdir()
    retained = destination / 'README.md'
    retained.write_bytes(b'retained witness')
    with pytest.raises(FileExistsError):
        publisher.export(COMMIT, destination)
    assert retained.read_bytes() == b'retained witness'
    assert list(destination.iterdir()) == [retained]
    assert not any(call[0] == 'cat-file' for call in canonical_git.calls)


@pytest.mark.parametrize('raced_precheck', [False, True])
def test_existing_receipt_is_not_overwritten_even_if_existence_check_races(
        publisher, canonical_git, monkeypatch, tmp_path, raced_precheck):
    output = tmp_path / 'retained-receipt.json'
    output.write_bytes(b'retained witness')
    if raced_precheck:
        real_exists = Path.exists
        monkeypatch.setattr(Path, 'exists', lambda path: False if path == output else real_exists(path))
    expected_error = FileExistsError if raced_precheck else ValueError
    with pytest.raises(expected_error):
        publisher.main(['--source-commit', COMMIT, '--export-dir', str(tmp_path / 'new-export'),
                        '--receipt', str(output), '--publish'])
    assert output.read_bytes() == b'retained witness'
    assert not (tmp_path / 'new-export').exists()
    assert canonical_git.calls == []
