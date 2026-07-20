"""Tests for repository-scoped cloud run-log synchronization."""

from __future__ import annotations

import threading
import tarfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from larch.report import run_log_archive, run_log_corpus, run_log_sync
from larch.report.object_store import RemoteObject
from larch.report.storage_config import StorageRoot


class MemoryObjectStore:
    """Thread-safe immutable archive store for sync contract tests."""

    def __init__(self, objects: dict[str, bytes]) -> None:
        self.objects = objects
        self.list_calls: list[str] = []
        self.download_calls: list[str] = []
        self.download_started: threading.Event | None = None
        self.release_download: threading.Event | None = None
        self._lock = threading.Lock()

    def list_objects(self, prefix: str = "") -> tuple[RemoteObject, ...]:
        with self._lock:
            self.list_calls.append(prefix)
            return tuple(
                RemoteObject(key, len(content), None, None)
                for key, content in sorted(self.objects.items())
                if key.startswith(prefix)
            )

    def download(self, key: str, destination: Path) -> None:
        with self._lock:
            self.download_calls.append(key)
            content: bytes = self.objects[key]
        if self.download_started is not None:
            self.download_started.set()
        if self.release_download is not None and not self.release_download.wait(
            timeout=5
        ):
            raise TimeoutError("test download release timed out")
        _ = destination.write_bytes(content)


def _archive_bytes(tmp_path: Path, *, skill: str, run_id: str, content: str) -> bytes:
    staging = tmp_path / f"staging-{skill}-{run_id}"
    staging.mkdir()
    _ = (staging / "manifest.json").write_text(
        '{"issue_number":7819,"started_at":"2026-07-20T00:00:00+00:00"}\n',
        encoding="utf-8",
    )
    nested = staging / "nested"
    nested.mkdir()
    _ = (nested / "result.txt").write_text(content, encoding="utf-8")
    created = run_log_archive.create_run_archive(
        staging_root=staging,
        output_dir=tmp_path / f"archives-{skill}-{run_id}",
        skill=skill,
        run_id=run_id,
    )
    return created.archive_path.read_bytes()


def _request(
    *,
    repo: Path,
    cache_home: Path,
    state_home: Path,
) -> run_log_sync.RunLogSyncRequest:
    return run_log_sync.RunLogSyncRequest(
        repo_root=repo,
        storage_root=StorageRoot("s3", "bucket", "larch"),
        cache_home=cache_home,
        state_home=state_home,
    )


def test_cold_then_warm_sync_lists_once_per_call_and_downloads_each_run_once(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "literal repo"
    repo.mkdir()
    cache_home = tmp_path / "cache"
    state_home = tmp_path / "state"
    objects = {
        "run-logs/design/design-run.tar.gz": _archive_bytes(
            tmp_path, skill="design", run_id="design-run", content="design\n"
        ),
        "run-logs/implement/implement-run.tar.gz": _archive_bytes(
            tmp_path, skill="implement", run_id="implement-run", content="implement\n"
        ),
    }
    store = MemoryObjectStore(objects)
    request = _request(repo=repo, cache_home=cache_home, state_home=state_home)

    cold = run_log_sync.sync_repository_run_logs(request=request, store=store)

    assert cold.corpus_root == cache_home / "larch/run-logs/literal repo"
    assert cold.listed_count == 2
    assert cold.downloaded_count == 2
    assert cold.present_count == 0
    assert cold.repaired_count == 0
    assert store.list_calls == ["run-logs/"]
    assert store.download_calls == sorted(objects)
    assert (cold.corpus_root / "implement/implement-run/nested/result.txt").read_text(
        encoding="utf-8"
    ) == "implement\n"

    warm = run_log_sync.sync_repository_run_logs(request=request, store=store)

    assert warm.listed_count == 2
    assert warm.downloaded_count == 0
    assert warm.present_count == 2
    assert warm.repaired_count == 0
    assert store.list_calls == ["run-logs/", "run-logs/"]
    assert store.download_calls == sorted(objects)


def test_shared_corpus_api_syncs_once_then_supports_multiple_local_read_waves(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    cache_home = tmp_path / "cache"
    state_home = tmp_path / "state"
    store = MemoryObjectStore(
        {
            "run-logs/implement/run-wave.tar.gz": _archive_bytes(
                tmp_path,
                skill="implement",
                run_id="run-wave",
                content="wave\n",
            )
        }
    )

    corpus_root = run_log_corpus.synchronized_run_log_root(
        request=_request(repo=repo, cache_home=cache_home, state_home=state_home),
        store=store,
    )

    first_wave = run_log_corpus.run_dirs(corpus_root / "implement")
    second_wave = run_log_corpus.safe_child_run_dirs(corpus_root / "implement")
    assert [path.name for path in first_wave] == ["run-wave"]
    assert [path.name for path in second_wave] == ["run-wave"]
    assert store.list_calls == ["run-logs/"]
    assert store.download_calls == ["run-logs/implement/run-wave.tar.gz"]


def test_invalid_cache_and_interrupted_materialization_are_repaired(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    cache_home = tmp_path / "cache"
    state_home = tmp_path / "state"
    key = "run-logs/review/run-repair.tar.gz"
    store = MemoryObjectStore(
        {
            key: _archive_bytes(
                tmp_path, skill="review", run_id="run-repair", content="clean\n"
            )
        }
    )
    request = _request(repo=repo, cache_home=cache_home, state_home=state_home)
    first = run_log_sync.sync_repository_run_logs(request=request, store=store)
    run_dir = first.corpus_root / "review/run-repair"
    _ = (run_dir / "nested/result.txt").write_text("corrupt\n", encoding="utf-8")
    interrupted = run_dir.parent / ".run-repair.materialize-interrupted"
    interrupted.mkdir()
    _ = (interrupted / "partial").write_text("partial", encoding="utf-8")

    repaired = run_log_sync.sync_repository_run_logs(request=request, store=store)

    assert repaired.repaired_count == 1
    assert repaired.downloaded_count == 1
    assert (run_dir / "nested/result.txt").read_text(encoding="utf-8") == "clean\n"
    assert not interrupted.exists()
    assert store.download_calls == [key, key]


def test_unverifiable_cache_fails_without_replacement_or_download(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    cache_home = tmp_path / "cache"
    state_home = tmp_path / "state"
    key = "run-logs/review/run-unreadable.tar.gz"
    store = MemoryObjectStore(
        {
            key: _archive_bytes(
                tmp_path,
                skill="review",
                run_id="run-unreadable",
                content="valid\n",
            )
        }
    )
    request = _request(repo=repo, cache_home=cache_home, state_home=state_home)
    first = run_log_sync.sync_repository_run_logs(request=request, store=store)
    run_dir = first.corpus_root / "review/run-unreadable"

    def unreadable_cache(**_kwargs: object) -> object:
        raise PermissionError("temporarily unreadable")

    monkeypatch.setattr(
        run_log_archive,
        "verify_materialized_run_directory",
        unreadable_cache,
    )
    with pytest.raises(PermissionError, match="temporarily unreadable"):
        _ = run_log_sync.sync_repository_run_logs(request=request, store=store)

    assert (run_dir / "nested/result.txt").read_text(encoding="utf-8") == "valid\n"
    assert store.download_calls == [key]


def test_failed_repair_restores_invalid_entry_and_removes_download_temporary(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    cache_home = tmp_path / "cache"
    state_home = tmp_path / "state"
    key = "run-logs/review/run-broken.tar.gz"
    store = MemoryObjectStore({key: b"not-an-archive"})
    request = _request(repo=repo, cache_home=cache_home, state_home=state_home)
    run_dir = cache_home / "larch/run-logs/repo/review/run-broken"
    run_dir.mkdir(parents=True)
    _ = (run_dir / "partial.txt").write_text("preserve for retry\n", encoding="utf-8")

    with pytest.raises((tarfile.ReadError, run_log_sync.RunLogSyncError)):
        _ = run_log_sync.sync_repository_run_logs(request=request, store=store)

    assert (run_dir / "partial.txt").read_text(
        encoding="utf-8"
    ) == "preserve for retry\n"
    assert not list(run_dir.parent.glob(".run-broken.download-*"))
    assert not list(run_dir.parent.glob(".run-broken.invalid-*"))


@pytest.mark.parametrize(
    "key",
    [
        "run-logs/run.tar.gz",
        "run-logs/implement/nested/run.tar.gz",
        "run-logs/implement/run.zip",
        "run-logs/bad skill/run.tar.gz",
    ],
)
def test_invalid_remote_inventory_fails_before_download(
    tmp_path: Path, key: str
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    store = MemoryObjectStore({key: b"archive"})

    with pytest.raises(run_log_sync.RunLogSyncError):
        _ = run_log_sync.sync_repository_run_logs(
            request=_request(
                repo=repo,
                cache_home=tmp_path / "cache",
                state_home=tmp_path / "state",
            ),
            store=store,
        )

    assert not store.download_calls


def test_case_colliding_remote_names_fail_before_download(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    store = MemoryObjectStore(
        {
            "run-logs/review/Run-A.tar.gz": b"first",
            "run-logs/REVIEW/run-a.tar.gz": b"second",
        }
    )

    with pytest.raises(run_log_sync.RunLogSyncError, match="collide"):
        _ = run_log_sync.sync_repository_run_logs(
            request=_request(
                repo=repo,
                cache_home=tmp_path / "cache",
                state_home=tmp_path / "state",
            ),
            store=store,
        )

    assert not store.download_calls


def test_concurrent_syncs_share_the_publication_lock_and_download_once(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    key = "run-logs/implement/run-concurrent.tar.gz"
    store = MemoryObjectStore(
        {
            key: _archive_bytes(
                tmp_path,
                skill="implement",
                run_id="run-concurrent",
                content="concurrent\n",
            )
        }
    )
    store.download_started = threading.Event()
    store.release_download = threading.Event()
    request = _request(
        repo=repo,
        cache_home=tmp_path / "cache",
        state_home=tmp_path / "state",
    )

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(
            run_log_sync.sync_repository_run_logs, request=request, store=store
        )
        assert store.download_started.wait(timeout=5)
        second = pool.submit(
            run_log_sync.sync_repository_run_logs, request=request, store=store
        )
        store.release_download.set()
        results = (first.result(timeout=5), second.result(timeout=5))

    assert sorted(result.downloaded_count for result in results) == [0, 1]
    assert store.download_calls == [key]
    assert store.list_calls == ["run-logs/", "run-logs/"]
