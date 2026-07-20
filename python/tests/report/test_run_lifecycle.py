"""Tests for the universal per-skill run lifecycle."""

from __future__ import annotations

import json
import subprocess
import tarfile
import threading
from pathlib import Path

import pytest

from larch.report import run_lifecycle, run_log_manifest, run_log_publish, run_logs
from larch.report.object_store import ObjectStoreError, ObjectStoreErrorKind, RemoteObject
from larch.report.storage_config import StorageRoot


class MemoryObjectStore:
    """Minimal create-only store for lifecycle publication tests."""

    def __init__(self, *, fail_uploads: int = 0) -> None:
        self.objects: dict[str, bytes] = {}
        self.fail_uploads = fail_uploads
        self._lock = threading.Lock()

    def upload_create(self, key: str, source: Path) -> RemoteObject:
        content = source.read_bytes()
        with self._lock:
            if self.fail_uploads:
                self.fail_uploads -= 1
                raise ObjectStoreError(
                    ObjectStoreErrorKind.TRANSPORT, "fake", "upload"
                )
            if key in self.objects:
                raise ObjectStoreError(
                    ObjectStoreErrorKind.ALREADY_EXISTS, "fake", "upload"
                )
            self.objects[key] = content
        return RemoteObject(key, len(content), "etag", None)

    def download(self, key: str, destination: Path) -> None:
        _ = destination.write_bytes(self.objects[key])

    def metadata(self, key: str) -> RemoteObject:
        content = self.objects[key]
        return RemoteObject(key, len(content), "etag", None)


@pytest.fixture
def lifecycle_fixture(tmp_path: Path) -> tuple[Path, dict[str, str], StorageRoot]:
    repo = tmp_path / "consumer"
    repo.mkdir()
    _ = subprocess.run(
        ["git", "init", "-q"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    environment = {
        "XDG_STATE_HOME": str(tmp_path / "state"),
        "XDG_CACHE_HOME": str(tmp_path / "cache"),
    }
    return repo, environment, StorageRoot("s3", "bucket", "larch")


def test_final_report_renderer_names_terminal_identity() -> None:
    report = run_lifecycle._render_final_report(  # pyright: ignore[reportPrivateUsage]  # Golden-test lint requires direct renderer coverage.
        skill="status", run_id="reference-success", outcome="success"
    )
    assert "Skill: `status`" in report
    assert "Run ID: `reference-success`" in report
    assert "Outcome: `success`" in report


@pytest.mark.parametrize("outcome", ["success", "failure", "cancelled", "early-return"])
def test_reference_skill_publishes_every_terminal_outcome(
    lifecycle_fixture: tuple[Path, dict[str, str], StorageRoot], outcome: str
) -> None:
    repo, environment, storage_root = lifecycle_fixture
    preflights: list[str] = []
    started = run_lifecycle.start_run(
        repo_root=repo,
        skill="status",
        run_id=f"reference-{outcome}",
        environ=environment,
        storage_root=storage_root,
        preflight=lambda root: preflights.append(root.uri),
    )

    terminal = run_lifecycle.finish_run(
        repo_root=repo,
        skill="status",
        run_id=started.run_id,
        outcome=outcome,
        environ=environment,
        storage_root=storage_root,
        store=MemoryObjectStore(),
    )

    assert preflights == [storage_root.uri]
    assert terminal.outcome == outcome
    assert not started.run_dir.exists()
    cache = terminal.publication.cache_dir
    manifest = json.loads((cache / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["skill"] == "status"
    assert manifest["run_id"] == started.run_id
    assert manifest["terminal_outcome"] == outcome
    assert (cache / run_lifecycle.UNIVERSAL_FINAL_REPORT).is_file()
    issues = (cache / run_lifecycle.UNIVERSAL_EXECUTION_ISSUES).read_text(
        encoding="utf-8"
    )
    assert run_lifecycle.UNIVERSAL_SESSION_TRANSCRIPT in issues


def test_nested_child_records_both_run_ids_without_merging_archives(
    lifecycle_fixture: tuple[Path, dict[str, str], StorageRoot]
) -> None:
    repo, environment, storage_root = lifecycle_fixture

    def preflight(_root: StorageRoot) -> None:
        return

    parent = run_lifecycle.start_run(
        repo_root=repo,
        skill="status",
        run_id="parent-run",
        environ=environment,
        storage_root=storage_root,
        preflight=preflight,
    )
    child = run_lifecycle.start_run(
        repo_root=repo,
        skill="cleanup",
        run_id="child-run",
        parent_skill=parent.skill,
        parent_run_id=parent.run_id,
        environ=environment,
        storage_root=storage_root,
        preflight=preflight,
    )
    store = MemoryObjectStore()

    child_terminal = run_lifecycle.finish_run(
        repo_root=repo,
        skill=child.skill,
        run_id=child.run_id,
        outcome="success",
        environ=environment,
        storage_root=storage_root,
        store=store,
    )
    parent_terminal = run_lifecycle.finish_run(
        repo_root=repo,
        skill=parent.skill,
        run_id=parent.run_id,
        outcome="success",
        environ=environment,
        storage_root=storage_root,
        store=store,
    )

    child_manifest = json.loads(
        (child_terminal.publication.cache_dir / "manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert child_manifest["run_id"] == child.run_id
    assert child_manifest["parent_skill"] == parent.skill
    assert child_manifest["parent_run_id"] == parent.run_id
    assert child_terminal.publication.remote_key != parent_terminal.publication.remote_key
    assert len(store.objects) == 2


def test_upload_failure_is_loud_and_retry_uses_durable_pending_archive(
    lifecycle_fixture: tuple[Path, dict[str, str], StorageRoot]
) -> None:
    repo, environment, storage_root = lifecycle_fixture
    started = run_lifecycle.start_run(
        repo_root=repo,
        skill="status",
        run_id="upload-failure",
        environ=environment,
        storage_root=storage_root,
        preflight=lambda _root: None,
    )
    store = MemoryObjectStore(fail_uploads=1)

    with pytest.raises(ObjectStoreError):
        _ = run_lifecycle.finish_run(
            repo_root=repo,
            skill=started.skill,
            run_id=started.run_id,
            outcome="failure",
            environ=environment,
            storage_root=storage_root,
            store=store,
        )

    paths = run_log_publish.publication_paths(
        request=run_log_publish.PublicationRequest(
            repo_root=repo,
            storage_root=storage_root,
            skill=started.skill,
            run_id=started.run_id,
            staging_root=None,
        ),
        environ=environment,
    )
    assert paths.pending_archive.is_file()
    assert started.run_dir.is_dir()

    retried = run_lifecycle.finish_run(
        repo_root=repo,
        skill=started.skill,
        run_id=started.run_id,
        outcome="failure",
        environ=environment,
        storage_root=storage_root,
        store=store,
    )
    assert retried.outcome == "failure"
    assert not paths.pending_dir.exists()


def test_parent_metadata_must_be_complete(
    lifecycle_fixture: tuple[Path, dict[str, str], StorageRoot]
) -> None:
    repo, environment, storage_root = lifecycle_fixture
    with pytest.raises(ValueError, match="provided together"):
        _ = run_lifecycle.start_run(
            repo_root=repo,
            skill="status",
            parent_skill="cleanup",
            environ=environment,
            storage_root=storage_root,
            preflight=lambda _root: None,
        )


def test_universal_artifacts_extend_existing_skill_requirements(
    lifecycle_fixture: tuple[Path, dict[str, str], StorageRoot]
) -> None:
    repo, environment, storage_root = lifecycle_fixture
    started = run_lifecycle.start_run(
        repo_root=repo,
        skill="implement",
        run_id="implement-adoption",
        environ=environment,
        storage_root=storage_root,
        preflight=lambda _root: None,
    )
    _ = (started.run_dir / "code-review-tally.json").write_text("{}\n", encoding="utf-8")
    manifest = run_log_manifest.Manifest.from_json(
        json.loads((started.run_dir / "manifest.json").read_text(encoding="utf-8"))
    )

    required = run_log_manifest.required_artifacts_for_run(
        run_dir=started.run_dir,
        skill="implement",
        manifest=manifest,
        repo_root=repo,
    )

    paths = {artifact.relative_path for artifact in required}
    assert run_lifecycle.UNIVERSAL_FINAL_REPORT in paths
    assert run_lifecycle.UNIVERSAL_SESSION_TRANSCRIPT in paths
    assert "review-findings-full.jsonl" in paths


def test_design_adopts_universal_ndjson_waiver_without_contract_fork(
    lifecycle_fixture: tuple[Path, dict[str, str], StorageRoot]
) -> None:
    repo, environment, storage_root = lifecycle_fixture
    started = run_lifecycle.start_run(
        repo_root=repo,
        skill="design",
        run_id="design-adoption",
        environ=environment,
        storage_root=storage_root,
        preflight=lambda _root: None,
    )

    terminal = run_lifecycle.finish_run(
        repo_root=repo,
        skill=started.skill,
        run_id=started.run_id,
        outcome="success",
        environ=environment,
        storage_root=storage_root,
        store=MemoryObjectStore(),
    )

    assert (terminal.publication.cache_dir / "execution-issues.ndjson").is_file()


def test_parent_identity_is_immutable_after_start(
    lifecycle_fixture: tuple[Path, dict[str, str], StorageRoot]
) -> None:
    repo, environment, storage_root = lifecycle_fixture
    started = run_lifecycle.start_run(
        repo_root=repo,
        skill="cleanup",
        run_id="immutable-parent",
        parent_skill="status",
        parent_run_id="parent-run",
        environ=environment,
        storage_root=storage_root,
        preflight=lambda _root: None,
    )

    with pytest.raises(ValueError, match="immutable-field:parent_run_id"):
        _ = run_logs.log_manifest_update(
            log_root=started.log_root,
            skill=started.skill,
            run_id=started.run_id,
            updates={"parent_run_id": "other-parent"},
        )


@pytest.mark.parametrize(
    "error",
    [
        run_log_publish.PublicationError("broken publication invariant"),
        tarfile.TarError("broken archive"),
    ],
)
def test_terminal_cli_converts_publication_exceptions_to_loud_failure(
    lifecycle_fixture: tuple[Path, dict[str, str], StorageRoot],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    error: Exception,
) -> None:
    repo, _environment, _storage_root = lifecycle_fixture

    def fail_finish(**_kwargs: object) -> run_lifecycle.LifecycleTerminal:
        raise error

    monkeypatch.setattr(run_lifecycle, "finish_run", fail_finish)

    rc = run_lifecycle.finalize_main(
        ["--repo-root", str(repo), "--skill", "status", "--run-id", "run-id"]
    )

    captured = capsys.readouterr()
    assert rc != 0
    assert captured.out == "LIFECYCLE_FLUSHED=false\n"
    assert "run lifecycle finalize failed" in captured.err
