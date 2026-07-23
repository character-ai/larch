"""Tests for repository-scoped cloud run-log synchronization."""

from __future__ import annotations

import threading
import tarfile
import gzip
import hashlib
import io
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from larch.core import config
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


def _legacy_archive(entries: list[tuple[str, bytes, bytes]]) -> bytes:
    output = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=output, mtime=0) as compressed:
        with tarfile.open(
            fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT
        ) as archive:
            for name, content, kind in entries:
                info = tarfile.TarInfo(name)
                info.type = kind
                info.size = len(content)
                info.mode = 0o644
                info.mtime = 0
                info.uid = 0
                info.gid = 0
                info.uname = ""
                info.gname = ""
                archive.addfile(
                    info, io.BytesIO(content) if kind == tarfile.REGTYPE else None
                )
    return output.getvalue()


def _legacy_fixture(
    tmp_path: Path,
    *,
    run_id: str = "legacy-run",
    entries: list[tuple[str, bytes, bytes]] | None = None,
    archive_digest: str | None = None,
    archive_size: int | None = None,
    inventory_mutation: dict[str, object] | None = None,
) -> tuple[dict[str, bytes], str]:
    active_entries = entries or [
        (
            "manifest.json",
            b'{"issue_number":7886,"started_at":"2026-07-20T00:00:00Z"}\n',
            tarfile.REGTYPE,
        ),
        (
            "token-report.json",
            b'{"claude":{"totals":{"total":10}},"BUCKETS_claude":{"input":10}}\n',
            tarfile.REGTYPE,
        ),
    ]
    archive_bytes = _legacy_archive(active_entries)
    remote_key = f"run-logs/implement/{run_id}.tar.gz"
    object_key = f"larch/{remote_key}"
    source_files = [
        {
            "archive_member_path": name,
            "archive_object_key": object_key,
            "bytes": len(content),
            "git_oid": hashlib.sha1(content).hexdigest(),  # noqa: S324 - fixture models Git SHA-1 object IDs
            "mode": "100644",
            "path": f"larch-logs/implement/{run_id}/{name}",
            "sha256": hashlib.sha256(content).hexdigest(),
        }
        for name, content, kind in active_entries
        if kind == tarfile.REGTYPE and not name.startswith("../")
    ]
    archive_row: dict[str, object] = {
        "archive_bytes": len(archive_bytes) if archive_size is None else archive_size,
        "kind": "run",
        "member_count": len(source_files),
        "object_key": object_key,
        "run_id": run_id,
        "sha256": archive_digest or hashlib.sha256(archive_bytes).hexdigest(),
        "skill": "implement",
        "uncompressed_bytes": sum(int(row["bytes"]) for row in source_files),
    }
    inventory: dict[str, object] = {
        "archives": [archive_row],
        "schema": "larch-run-log-migration-inventory-v1",
        "source_commit": "a" * 40,
        "source_files": source_files,
        "storage_root": "s3://bucket/larch",
        "totals": {
            "archive_bytes": archive_row["archive_bytes"],
            "archive_objects": 1,
            "members": len(source_files),
            "run_directories": 1,
            "source_paths": len(source_files),
            "uncompressed_bytes": archive_row["uncompressed_bytes"],
        },
    }
    if inventory_mutation:
        inventory.update(inventory_mutation)
    inventory_bytes = (json.dumps(inventory, sort_keys=True) + "\n").encode()
    inventory_key = "migration/test-inventory.json"
    config_path = tmp_path / "repo" / "config.toml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    _ = config_path.write_text(
        "\n".join(
            [
                "[logs]",
                'uri = "s3://bucket/larch"',
                "",
                "[logs.legacy_migration]",
                'schema = "larch-run-log-migration-inventory-v1"',
                f'source_commit = "{"a" * 40}"',
                'storage_root = "s3://bucket/larch"',
                f'inventory_key = "{inventory_key}"',
                f'inventory_sha256 = "{hashlib.sha256(inventory_bytes).hexdigest()}"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    return {remote_key: archive_bytes, inventory_key: inventory_bytes}, remote_key


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


def test_legacy_cold_sync_verifies_extracts_and_warm_sync_lists_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    objects, remote_key = _legacy_fixture(tmp_path)
    store = MemoryObjectStore(objects)
    request = _request(
        repo=tmp_path / "repo",
        cache_home=tmp_path / "cache",
        state_home=tmp_path / "state",
    )
    calls = 0
    materialize = run_log_archive.materialize_legacy_run_archive

    def counted_materialize(**kwargs: object) -> object:
        nonlocal calls
        calls += 1
        return materialize(**kwargs)  # pyright: ignore[reportArgumentType] - forwards the exact production keyword contract

    monkeypatch.setattr(
        run_log_archive, "materialize_legacy_run_archive", counted_materialize
    )

    cold = run_log_sync.sync_repository_run_logs(request=request, store=store)
    run_dir = cold.corpus_root / "implement/legacy-run"

    assert cold.downloaded_count == 1
    assert calls == 1
    assert store.download_calls == [remote_key, "migration/test-inventory.json"]
    assert (run_dir / "manifest.json").is_file()
    assert (run_dir / "token-report.json").is_file()
    assert (run_dir / run_log_archive.ARCHIVE_MANIFEST_NAME).is_file()
    _ = run_log_archive.verify_materialized_run_directory(
        run_dir=run_dir,
        expected_skill="implement",
        expected_run_id="legacy-run",
    )

    warm = run_log_sync.sync_repository_run_logs(request=request, store=store)

    assert warm.present_count == 1
    assert warm.downloaded_count == 0
    assert calls == 1
    assert store.list_calls == ["run-logs/", "run-logs/"]
    assert store.download_calls == [remote_key, "migration/test-inventory.json"]


def test_mixed_legacy_and_versioned_archives_materialize_together(
    tmp_path: Path,
) -> None:
    objects, remote_key = _legacy_fixture(tmp_path)
    normal_key = "run-logs/design/normal-run.tar.gz"
    objects[normal_key] = _archive_bytes(
        tmp_path, skill="design", run_id="normal-run", content="normal\n"
    )
    store = MemoryObjectStore(objects)

    result = run_log_sync.sync_repository_run_logs(
        request=_request(
            repo=tmp_path / "repo",
            cache_home=tmp_path / "cache",
            state_home=tmp_path / "state",
        ),
        store=store,
    )

    assert result.downloaded_count == 2
    assert (result.corpus_root / "implement/legacy-run/token-report.json").is_file()
    assert (result.corpus_root / "design/normal-run/nested/result.txt").is_file()
    assert store.download_calls == [
        normal_key,
        remote_key,
        "migration/test-inventory.json",
    ]


@pytest.mark.parametrize(
    ("fixture_kwargs", "message"),
    [
        ({"archive_digest": "0" * 64}, "archive digest"),
        ({"archive_size": 1}, "archive size"),
        (
            {"inventory_mutation": {"source_commit": "b" * 40}},
            "source commit",
        ),
        (
            {"inventory_mutation": {"storage_root": "s3://other/larch"}},
            "storage root",
        ),
    ],
)
def test_legacy_sync_rejects_unpinned_or_inconsistent_inventory(
    tmp_path: Path,
    fixture_kwargs: dict[str, object],
    message: str,
) -> None:
    objects, _ = _legacy_fixture(tmp_path, **fixture_kwargs)  # pyright: ignore[reportArgumentType] - parametrized fixture keyword coverage
    store = MemoryObjectStore(objects)

    with pytest.raises(ValueError, match=message):
        _ = run_log_sync.sync_repository_run_logs(
            request=_request(
                repo=tmp_path / "repo",
                cache_home=tmp_path / "cache",
                state_home=tmp_path / "state",
            ),
            store=store,
        )


def test_legacy_sync_rejects_wrong_inventory_hash(tmp_path: Path) -> None:
    objects, _ = _legacy_fixture(tmp_path)
    objects["migration/test-inventory.json"] += b" "
    store = MemoryObjectStore(objects)

    with pytest.raises(ValueError, match="inventory digest"):
        _ = run_log_sync.sync_repository_run_logs(
            request=_request(
                repo=tmp_path / "repo",
                cache_home=tmp_path / "cache",
                state_home=tmp_path / "state",
            ),
            store=store,
        )


def test_manifestless_archive_without_exact_inventory_record_fails_closed(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    key = "run-logs/implement/unknown-run.tar.gz"
    store = MemoryObjectStore(
        {key: _legacy_archive([("manifest.json", b"{}\n", tarfile.REGTYPE)])}
    )

    with pytest.raises(run_log_sync.RunLogSyncError, match="descriptor"):
        _ = run_log_sync.sync_repository_run_logs(
            request=_request(
                repo=repo,
                cache_home=tmp_path / "cache",
                state_home=tmp_path / "state",
            ),
            store=store,
        )

    assert store.download_calls == [key]


def test_main_defaults_repo_root_to_cwd_discovery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Omitted ``--repo-root`` starts discovery from the invoking cwd (#7935)."""
    monkeypatch.chdir(tmp_path)
    rc = run_log_sync.main([])
    assert rc == config.EXIT_STORAGE_CONFIG
    captured = capsys.readouterr()
    assert "could not discover a Git repository root" in captured.err
