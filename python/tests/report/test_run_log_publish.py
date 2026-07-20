"""Tests for immutable publication, durable retry, and write-through caching."""

from __future__ import annotations

import json
import threading
from collections.abc import Mapping
from pathlib import Path
from typing import cast

import pytest

from larch.report import run_log_publish
from larch.report.object_store import ObjectStoreError, ObjectStoreErrorKind, RemoteObject
from larch.report.storage_config import StorageRoot


class MemoryObjectStore:
    """Thread-safe create-only object store used by the publication contract tests."""

    def __init__(self, *, fail_uploads: int = 0) -> None:
        self.objects: dict[str, bytes] = {}
        self.fail_uploads = fail_uploads
        self.upload_calls = 0
        self.download_calls = 0
        self.metadata_calls = 0
        self._lock = threading.Lock()

    def upload_create(self, key: str, source: Path) -> RemoteObject:
        content: bytes = source.read_bytes()
        with self._lock:
            self.upload_calls += 1
            if self.fail_uploads > 0:
                self.fail_uploads -= 1
                raise ObjectStoreError(ObjectStoreErrorKind.TRANSPORT, "fake", "upload")
            if key in self.objects:
                raise ObjectStoreError(ObjectStoreErrorKind.ALREADY_EXISTS, "fake", "upload")
            self.objects[key] = content
        return RemoteObject(key, len(content), "etag", None)

    def download(self, key: str, destination: Path) -> None:
        with self._lock:
            self.download_calls += 1
            content: bytes = self.objects[key]
        _ = destination.write_bytes(content)

    def metadata(self, key: str) -> RemoteObject:
        with self._lock:
            self.metadata_calls += 1
            content: bytes = self.objects[key]
        return RemoteObject(key, len(content), "etag", None)


def _fixture(tmp_path: Path) -> tuple[Path, Path, Path, Path, StorageRoot]:
    repo: Path = tmp_path / "literal repo"
    staging: Path = tmp_path / "staging"
    cache_home: Path = tmp_path / "cache"
    state_home: Path = tmp_path / "state"
    repo.mkdir()
    staging.mkdir()
    nested: Path = staging / "nested"
    nested.mkdir()
    _ = (staging / "manifest.json").write_text('{"issue_number":7818}\n', encoding="utf-8")
    _ = (nested / "result.txt").write_text("published\n", encoding="utf-8")
    return repo, staging, cache_home, state_home, StorageRoot("s3", "bucket", "larch")


def _publish(
    *,
    repo: Path,
    staging: Path | None,
    cache_home: Path,
    state_home: Path,
    storage_root: StorageRoot,
    store: MemoryObjectStore,
) -> run_log_publish.PublicationResult:
    return run_log_publish.publish_run(
        request=run_log_publish.PublicationRequest(
            repo_root=repo,
            storage_root=storage_root,
            skill="implement",
            run_id="run-7818",
            staging_root=staging,
            cache_home=cache_home,
            state_home=state_home,
        ),
        store=store,
    )


def _paths(
    *,
    repo: Path,
    cache_home: Path,
    state_home: Path,
) -> run_log_publish.PublicationPaths:
    return run_log_publish.publication_paths(
        request=run_log_publish.PublicationRequest(
            repo_root=repo,
            storage_root=StorageRoot("s3", "bucket", "larch"),
            skill="implement",
            run_id="run-7818",
            staging_root=None,
            cache_home=cache_home,
            state_home=state_home,
        ),
    )


def _pending_metadata(paths: run_log_publish.PublicationPaths) -> Mapping[str, object]:
    return cast(
        "Mapping[str, object]",
        json.loads(paths.pending_metadata.read_text(encoding="utf-8")),
    )


def test_publish_uses_exact_key_and_promotes_staging_without_download(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, staging, cache_home, state_home, storage_root = _fixture(tmp_path)
    store = MemoryObjectStore()

    def unexpected_materialization(**_kwargs: object) -> object:
        raise AssertionError("the normal publication path must not decompress its archive")

    monkeypatch.setattr(run_log_publish, "materialize_run_archive", unexpected_materialization)
    result = _publish(
        repo=repo,
        staging=staging,
        cache_home=cache_home,
        state_home=state_home,
        storage_root=storage_root,
        store=store,
    )

    assert result.remote_key == "run-logs/implement/run-7818.tar.gz"
    assert result.remote_status is run_log_publish.RemotePublicationStatus.CREATED
    assert result.cache_status is run_log_publish.CachePublicationStatus.PROMOTED
    assert result.cache_dir == cache_home / "larch/run-logs/literal repo/implement/run-7818"
    assert (result.cache_dir / "nested/result.txt").read_text(encoding="utf-8") == "published\n"
    assert store.download_calls == 0
    assert not _paths(repo=repo, cache_home=cache_home, state_home=state_home).pending_dir.exists()


def test_failed_upload_retains_content_pinned_pending_archive_and_retry_metadata(
    tmp_path: Path,
) -> None:
    repo, staging, cache_home, state_home, storage_root = _fixture(tmp_path)
    store = MemoryObjectStore(fail_uploads=1)
    paths = _paths(repo=repo, cache_home=cache_home, state_home=state_home)

    with pytest.raises(ObjectStoreError) as failure:
        _ = _publish(
            repo=repo,
            staging=staging,
            cache_home=cache_home,
            state_home=state_home,
            storage_root=storage_root,
            store=store,
        )

    assert failure.value.kind is ObjectStoreErrorKind.TRANSPORT
    assert paths.pending_archive.is_file()
    metadata = _pending_metadata(paths)
    assert metadata["attempts"] == 1
    assert metadata["last_error"] == "object-upload-transport"
    assert metadata["remote_key"] == "run-logs/implement/run-7818.tar.gz"
    assert not paths.cache_dir.exists()

    result = _publish(
        repo=repo,
        staging=None,
        cache_home=cache_home,
        state_home=state_home,
        storage_root=storage_root,
        store=store,
    )

    assert result.remote_status is run_log_publish.RemotePublicationStatus.CREATED
    assert result.cache_status is run_log_publish.CachePublicationStatus.MATERIALIZED
    assert paths.cache_dir.is_dir()
    assert not paths.pending_dir.exists()


def test_matching_remote_collision_is_idempotent_but_different_content_fails(
    tmp_path: Path,
) -> None:
    repo, staging, cache_home, state_home, storage_root = _fixture(tmp_path)
    first_store = MemoryObjectStore(fail_uploads=1)
    paths = _paths(repo=repo, cache_home=cache_home, state_home=state_home)
    with pytest.raises(ObjectStoreError):
        _ = _publish(
            repo=repo,
            staging=staging,
            cache_home=cache_home,
            state_home=state_home,
            storage_root=storage_root,
            store=first_store,
        )
    archive_bytes: bytes = paths.pending_archive.read_bytes()
    first_store.objects["run-logs/implement/run-7818.tar.gz"] = archive_bytes

    matched = _publish(
        repo=repo,
        staging=staging,
        cache_home=cache_home,
        state_home=state_home,
        storage_root=storage_root,
        store=first_store,
    )

    assert matched.remote_status is run_log_publish.RemotePublicationStatus.MATCHED
    assert first_store.download_calls == 1
    assert not paths.pending_dir.exists()

    second_state: Path = tmp_path / "second-state"
    second_cache: Path = tmp_path / "second-cache"
    different_store = MemoryObjectStore(fail_uploads=1)
    with pytest.raises(ObjectStoreError):
        _ = _publish(
            repo=repo,
            staging=staging,
            cache_home=second_cache,
            state_home=second_state,
            storage_root=storage_root,
            store=different_store,
        )
    second_paths = _paths(repo=repo, cache_home=second_cache, state_home=second_state)
    different_store.objects["run-logs/implement/run-7818.tar.gz"] = (
        b"x" * second_paths.pending_archive.stat().st_size
    )
    with pytest.raises(run_log_publish.PublicationError, match="different content"):
        _ = _publish(
            repo=repo,
            staging=None,
            cache_home=second_cache,
            state_home=second_state,
            storage_root=storage_root,
            store=different_store,
        )
    assert second_paths.pending_archive.is_file()
    assert _pending_metadata(second_paths)["last_error"] == "publication-invariant"


def test_cache_failure_after_upload_retries_from_archive_without_overwrite(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, staging, cache_home, state_home, storage_root = _fixture(tmp_path)
    store = MemoryObjectStore()
    paths = _paths(repo=repo, cache_home=cache_home, state_home=state_home)
    original_promote = run_log_publish.promote_staging_run_directory

    def interrupted_promotion(**_kwargs: object) -> object:
        raise OSError("simulated cache promotion crash")

    monkeypatch.setattr(run_log_publish, "promote_staging_run_directory", interrupted_promotion)
    with pytest.raises(OSError, match="simulated cache promotion crash"):
        _ = _publish(
            repo=repo,
            staging=staging,
            cache_home=cache_home,
            state_home=state_home,
            storage_root=storage_root,
            store=store,
        )
    assert paths.pending_archive.is_file()
    assert len(store.objects) == 1

    monkeypatch.setattr(run_log_publish, "promote_staging_run_directory", original_promote)
    result = _publish(
        repo=repo,
        staging=None,
        cache_home=cache_home,
        state_home=state_home,
        storage_root=storage_root,
        store=store,
    )

    assert result.remote_status is run_log_publish.RemotePublicationStatus.MATCHED
    assert result.cache_status is run_log_publish.CachePublicationStatus.MATERIALIZED
    assert not paths.pending_dir.exists()


def test_crash_before_pending_retirement_reuses_remote_and_cache(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, staging, cache_home, state_home, storage_root = _fixture(tmp_path)
    store = MemoryObjectStore()
    paths = _paths(repo=repo, cache_home=cache_home, state_home=state_home)
    original_complete = run_log_publish._complete_pending  # pyright: ignore[reportPrivateUsage] - crash-window seam

    def interrupted_retirement(_paths: run_log_publish.PublicationPaths) -> None:
        raise OSError("simulated retirement crash")

    monkeypatch.setattr(run_log_publish, "_complete_pending", interrupted_retirement)
    with pytest.raises(OSError, match="simulated retirement crash"):
        _ = _publish(
            repo=repo,
            staging=staging,
            cache_home=cache_home,
            state_home=state_home,
            storage_root=storage_root,
            store=store,
        )
    assert paths.pending_archive.is_file()
    assert paths.cache_dir.is_dir()

    monkeypatch.setattr(run_log_publish, "_complete_pending", original_complete)
    result = _publish(
        repo=repo,
        staging=None,
        cache_home=cache_home,
        state_home=state_home,
        storage_root=storage_root,
        store=store,
    )

    assert result.remote_status is run_log_publish.RemotePublicationStatus.MATCHED
    assert result.cache_status is run_log_publish.CachePublicationStatus.PRESENT
    assert not paths.pending_dir.exists()


def test_concurrent_publications_converge_on_one_remote_and_one_valid_cache(
    tmp_path: Path,
) -> None:
    repo, staging, cache_home, state_home, storage_root = _fixture(tmp_path)
    store = MemoryObjectStore()
    results: list[run_log_publish.PublicationResult] = []
    failures: list[BaseException] = []

    def worker() -> None:
        try:
            results.append(
                _publish(
                    repo=repo,
                    staging=staging,
                    cache_home=cache_home,
                    state_home=state_home,
                    storage_root=storage_root,
                    store=store,
                )
            )
        except BaseException as exc:  # test thread must surface every failure
            failures.append(exc)

    threads: tuple[threading.Thread, ...] = tuple(threading.Thread(target=worker) for _ in range(2))
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert not failures
    assert len(results) == 2
    assert len(store.objects) == 1
    assert {result.remote_status for result in results} == {
        run_log_publish.RemotePublicationStatus.CREATED,
        run_log_publish.RemotePublicationStatus.MATCHED,
    }
    assert {result.cache_status for result in results} == {
        run_log_publish.CachePublicationStatus.PROMOTED,
        run_log_publish.CachePublicationStatus.PRESENT,
    }
    paths = _paths(repo=repo, cache_home=cache_home, state_home=state_home)
    assert paths.cache_dir.is_dir()
    assert not paths.pending_dir.exists()


def test_pending_identity_mismatch_fails_closed_and_preserves_archive(tmp_path: Path) -> None:
    repo, staging, cache_home, state_home, storage_root = _fixture(tmp_path)
    store = MemoryObjectStore(fail_uploads=1)
    paths = _paths(repo=repo, cache_home=cache_home, state_home=state_home)
    with pytest.raises(ObjectStoreError):
        _ = _publish(
            repo=repo,
            staging=staging,
            cache_home=cache_home,
            state_home=state_home,
            storage_root=storage_root,
            store=store,
        )

    changed_root = StorageRoot("s3", "other-bucket", "larch")
    with pytest.raises(run_log_publish.PublicationError, match="identity"):
        _ = _publish(
            repo=repo,
            staging=None,
            cache_home=cache_home,
            state_home=state_home,
            storage_root=changed_root,
            store=store,
        )

    assert paths.pending_archive.is_file()


def test_publish_cli_returns_nonzero_without_clean_success_on_terminal_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, _staging, _cache_home, _state_home, storage_root = _fixture(tmp_path)

    def fake_repo_root(_start: Path) -> Path:
        return repo

    def fake_storage_root(*, start: Path) -> StorageRoot:
        assert start == repo
        return storage_root

    def fail_publish(**_kwargs: object) -> run_log_publish.PublicationResult:
        raise ObjectStoreError(ObjectStoreErrorKind.TRANSPORT, "fake", "upload")

    monkeypatch.setattr(run_log_publish, "consumer_repo_root", fake_repo_root)
    monkeypatch.setattr(run_log_publish, "discover_storage_root", fake_storage_root)
    monkeypatch.setattr(run_log_publish, "publish_run", fail_publish)

    rc: int = run_log_publish.main(
        ["--repo-root", str(repo), "--skill", "implement", "--run-id", "run-7818"]
    )

    captured = capsys.readouterr()
    assert rc != 0
    assert captured.out == ""
    assert "publication failed" in captured.err
    assert "PUBLISH_OK=true" not in captured.err
