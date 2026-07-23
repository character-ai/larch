"""Repository-scoped synchronization of immutable cloud run archives."""

from __future__ import annotations

import argparse
import os
import shutil
import stat
import sys
import tarfile
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol

from larch.core import config, repo_roots
from larch.report import run_log_archive, run_log_migration, run_log_publish, storage_config
from larch.report.object_store import ObjectStoreError, RemoteObject, object_store_for
from larch.report.storage_config import StorageConfigurationError, StorageRoot

_REMOTE_PREFIX = "run-logs/"
_ARCHIVE_SUFFIX = ".tar.gz"
_ARCHIVE_KEY_PARTS = 2


class RunLogSyncError(RuntimeError):
    """A remote inventory or local cache synchronization invariant failed."""


class SyncObjectStore(Protocol):
    """Provider-neutral object operations required by synchronization."""

    def list_objects(self, prefix: str = "") -> tuple[RemoteObject, ...]: ...

    def download(self, key: str, destination: Path) -> None: ...


class CacheSyncStatus(StrEnum):
    """How one remote archive reached its validated local postcondition."""

    PRESENT = "present"
    DOWNLOADED = "downloaded"
    REPAIRED = "repaired"


@dataclass(frozen=True)
class RunLogSyncRequest:
    """Immutable inputs for one repository-scoped synchronization."""

    repo_root: Path
    storage_root: StorageRoot
    cache_home: Path | None = None
    state_home: Path | None = None


@dataclass(frozen=True)
class RemoteRunArchive:
    """Validated identity and listing metadata for one remote run archive."""

    remote_key: str
    skill: str
    run_id: str
    size: int


@dataclass(frozen=True)
class SyncedRun:
    """Validated local result for one remote run archive."""

    remote_key: str
    cache_dir: Path
    status: CacheSyncStatus


@dataclass(frozen=True)
class RepositorySyncResult:
    """Complete repository cache result returned after one remote listing."""

    corpus_root: Path
    runs: tuple[SyncedRun, ...]

    @property
    def listed_count(self) -> int:
        return len(self.runs)

    @property
    def present_count(self) -> int:
        return sum(run.status is CacheSyncStatus.PRESENT for run in self.runs)

    @property
    def downloaded_count(self) -> int:
        return sum(run.status is not CacheSyncStatus.PRESENT for run in self.runs)

    @property
    def repaired_count(self) -> int:
        return sum(run.status is CacheSyncStatus.REPAIRED for run in self.runs)


class _LegacyMigrationLoader:
    """Lazily download a repository-scoped migration inventory at most once."""

    def __init__(self, *, request: RunLogSyncRequest, store: SyncObjectStore, temporary_dir: Path) -> None:
        self._request = request
        self._store = store
        self._temporary_dir = temporary_dir
        self._attempted = False
        self._inventory: run_log_migration.LegacyMigrationInventory | None = None

    def archive_for(self, remote_key: str) -> run_log_archive.LegacyRunArchive:
        if not self._attempted:
            self._attempted = True
            try:
                descriptor = storage_config.load_legacy_migration_descriptor(
                    repo_root=self._request.repo_root, storage_root=self._request.storage_root,
                )
            except StorageConfigurationError as exc:
                raise RunLogSyncError("legacy migration descriptor is invalid") from exc
            if descriptor is None:
                raise RunLogSyncError(
                    "manifest-less run archive is not recognized by a repository migration descriptor"
                )
            self._inventory = run_log_migration.download_and_parse_inventory(
                store=self._store, descriptor=descriptor, storage_root=self._request.storage_root,
                temporary_dir=self._temporary_dir,
            )
        if self._inventory is None:
            raise RunLogSyncError("legacy migration inventory is unavailable")
        record: run_log_archive.LegacyRunArchive | None = self._inventory.archive_for(remote_key)
        if record is None:
            raise RunLogSyncError(
                "manifest-less run archive is not recognized by the pinned migration inventory"
            )
        return record


def _remote_run_archive(remote: RemoteObject) -> RemoteRunArchive:
    if not remote.key.startswith(_REMOTE_PREFIX):
        raise RunLogSyncError(
            f"listed object is outside {_REMOTE_PREFIX}: {remote.key!r}"
        )
    relative: str = remote.key.removeprefix(_REMOTE_PREFIX)
    parts: list[str] = relative.split("/")
    if len(parts) != _ARCHIVE_KEY_PARTS or not parts[1].endswith(_ARCHIVE_SUFFIX):
        raise RunLogSyncError(f"invalid run archive key: {remote.key!r}")
    try:
        skill: str = run_log_publish.validated_component(
            parts[0], label="remote skill", slug=True
        )
        run_id: str = run_log_publish.validated_component(
            parts[1].removesuffix(_ARCHIVE_SUFFIX),
            label="remote run-id",
            slug=True,
        )
    except ValueError as exc:
        raise RunLogSyncError(f"invalid run archive key: {remote.key!r}") from exc
    if isinstance(remote.size, bool) or remote.size <= 0:
        raise RunLogSyncError(f"run archive has invalid size: {remote.key!r}")
    return RemoteRunArchive(remote.key, skill, run_id, remote.size)


def _validated_inventory(
    objects: tuple[RemoteObject, ...],
) -> tuple[RemoteRunArchive, ...]:
    archives: list[RemoteRunArchive] = []
    remote_keys: set[str] = set()
    local_names: dict[tuple[str, str], str] = {}
    for remote in objects:
        archive: RemoteRunArchive = _remote_run_archive(remote)
        if archive.remote_key in remote_keys:
            raise RunLogSyncError(
                f"duplicate run archive listing: {archive.remote_key!r}"
            )
        remote_keys.add(archive.remote_key)
        local_key: tuple[str, str] = (
            archive.skill.casefold(),
            archive.run_id.casefold(),
        )
        previous: str | None = local_names.get(local_key)
        if previous is not None:
            raise RunLogSyncError(
                f"run archive names collide in the local cache: {previous!r} and {archive.remote_key!r}"
            )
        local_names[local_key] = archive.remote_key
        archives.append(archive)
    return tuple(sorted(archives, key=lambda archive: archive.remote_key))


def _remove_entry(path: Path) -> None:
    try:
        mode: int = path.lstat().st_mode
    except FileNotFoundError:
        return
    if stat.S_ISDIR(mode):
        shutil.rmtree(path)
    else:
        path.unlink()


def _remove_interrupted_entries(parent: Path, *, run_id: str) -> None:
    for suffix in ("download-*", "invalid-*", "materialize-*", "promote-*"):
        for path in parent.glob(f".{run_id}.{suffix}"):
            _remove_entry(path)


def _existing_cache_is_valid(cache_dir: Path, *, archive: RemoteRunArchive) -> bool:
    try:
        entry: os.stat_result = cache_dir.lstat()
    except FileNotFoundError:
        return False
    if stat.S_ISLNK(entry.st_mode) or not stat.S_ISDIR(entry.st_mode):
        return False
    try:
        _ = run_log_archive.verify_materialized_run_directory(
            run_dir=cache_dir,
            expected_skill=archive.skill,
            expected_run_id=archive.run_id,
        )
    except (FileNotFoundError, RuntimeError, TypeError, ValueError):
        return False
    return True


def _download_and_materialize(
    *,
    store: SyncObjectStore,
    archive: RemoteRunArchive,
    cache_dir: Path,
    migration: _LegacyMigrationLoader,
) -> None:
    with tempfile.NamedTemporaryFile(
        dir=cache_dir.parent,
        prefix=f".{archive.run_id}.download-",
        suffix=_ARCHIVE_SUFFIX,
        delete=False,
    ) as handle:
        archive_path: Path = Path(handle.name)
    try:
        store.download(archive.remote_key, archive_path)
        entry: os.stat_result = archive_path.stat(follow_symlinks=False)
        if not stat.S_ISREG(entry.st_mode) or entry.st_size != archive.size:
            raise RunLogSyncError(
                f"downloaded archive does not match listed size: {archive.remote_key!r}"
            )
        try:
            _ = run_log_archive.materialize_run_archive(
                archive_path=archive_path, run_dir=cache_dir,
                expected_skill=archive.skill, expected_run_id=archive.run_id,
            )
        except run_log_archive.MissingArchiveManifestError:
            legacy: run_log_archive.LegacyRunArchive = migration.archive_for(archive.remote_key)
            _ = run_log_archive.materialize_legacy_run_archive(
                archive_path=archive_path, run_dir=cache_dir,
                expected_skill=archive.skill, expected_run_id=archive.run_id, legacy=legacy,
            )
    finally:
        archive_path.unlink(missing_ok=True)


def _sync_archive(
    *,
    request: RunLogSyncRequest,
    archive: RemoteRunArchive,
    store: SyncObjectStore,
    environ: Mapping[str, str] | None,
    migration: _LegacyMigrationLoader,
) -> SyncedRun:
    paths: run_log_publish.PublicationPaths = run_log_publish.publication_paths(
        request=run_log_publish.PublicationRequest(
            repo_root=request.repo_root,
            storage_root=request.storage_root,
            skill=archive.skill,
            run_id=archive.run_id,
            staging_root=None,
            cache_home=request.cache_home,
            state_home=request.state_home,
        ),
        environ=environ,
    )
    with run_log_publish.publication_lock(paths.lock_file):
        parent: Path = run_log_publish.ensure_concurrent_directory(
            paths.cache_dir.parent
        )
        _remove_interrupted_entries(parent, run_id=archive.run_id)
        if _existing_cache_is_valid(paths.cache_dir, archive=archive):
            return SyncedRun(
                archive.remote_key, paths.cache_dir, CacheSyncStatus.PRESENT
            )

        had_invalid_entry: bool = (
            paths.cache_dir.exists() or paths.cache_dir.is_symlink()
        )
        quarantine: Path | None = None
        if had_invalid_entry:
            quarantine = parent / (
                f".{archive.run_id}.invalid-{os.getpid()}-{os.urandom(4).hex()}"
            )
            _ = paths.cache_dir.rename(quarantine)
        try:
            _download_and_materialize(
                store=store,
                archive=archive,
                cache_dir=paths.cache_dir,
                migration=migration,
            )
        except (
            EOFError,
            ObjectStoreError,
            OSError,
            RunLogSyncError,
            RuntimeError,
            tarfile.TarError,
            TypeError,
            ValueError,
        ):
            if paths.cache_dir.exists() or paths.cache_dir.is_symlink():
                _remove_entry(paths.cache_dir)
            if quarantine is not None and (
                quarantine.exists() or quarantine.is_symlink()
            ):
                _ = quarantine.rename(paths.cache_dir)
            raise
        if quarantine is not None:
            _remove_entry(quarantine)
        status: CacheSyncStatus = (
            CacheSyncStatus.REPAIRED
            if had_invalid_entry
            else CacheSyncStatus.DOWNLOADED
        )
        return SyncedRun(archive.remote_key, paths.cache_dir, status)


def sync_repository_run_logs(
    *,
    request: RunLogSyncRequest,
    store: SyncObjectStore | None = None,
    environ: Mapping[str, str] | None = None,
) -> RepositorySyncResult:
    """List remote archives once and materialize every missing repository run."""
    active_store: SyncObjectStore = (
        object_store_for(request.storage_root, environ=environ)
        if store is None
        else store
    )
    inventory: tuple[RemoteRunArchive, ...] = _validated_inventory(
        active_store.list_objects(_REMOTE_PREFIX)
    )
    corpus_root: Path = run_log_publish.repository_cache_root(
        repo_root=request.repo_root,
        cache_home=request.cache_home,
        environ=environ,
    )
    _ = run_log_publish.ensure_concurrent_directory(corpus_root)
    migration = _LegacyMigrationLoader(
        request=request, store=active_store, temporary_dir=corpus_root,
    )
    runs: tuple[SyncedRun, ...] = tuple(
        _sync_archive(
            request=request,
            archive=archive,
            store=active_store,
            environ=environ,
            migration=migration,
        )
        for archive in inventory
    )
    return RepositorySyncResult(corpus_root=corpus_root, runs=runs)


def main(argv: Sequence[str]) -> int:
    """Synchronize one repository cache and emit its machine envelope."""
    parser = argparse.ArgumentParser(prog="cli.py run-log sync")
    _ = parser.add_argument("--repo-root", default=".")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else config.EXIT_USAGE
    try:
        requested_root: Path = Path(args.repo_root)
        repo_root: Path | None = repo_roots.consumer_repo_root(requested_root)
        if repo_root is None:
            raise StorageConfigurationError(
                f"could not discover a Git repository root from {requested_root}"
            )
        storage_root: StorageRoot = storage_config.discover_storage_root(
            start=repo_root
        )
        result: RepositorySyncResult = sync_repository_run_logs(
            request=RunLogSyncRequest(
                repo_root=repo_root,
                storage_root=storage_root,
            )
        )
    except StorageConfigurationError as exc:
        print(f"run-log sync failed: {exc}", file=sys.stderr)
        return config.EXIT_STORAGE_CONFIG
    except (
        EOFError,
        ObjectStoreError,
        OSError,
        RunLogSyncError,
        RuntimeError,
        tarfile.TarError,
        TypeError,
        ValueError,
    ) as exc:
        print(f"run-log sync failed: {exc}", file=sys.stderr)
        return config.EXIT_INTERNAL_ERROR
    print(f"CORPUS_ROOT={result.corpus_root}")
    print(f"LISTED_ARCHIVES={result.listed_count}")
    print(f"PRESENT_RUNS={result.present_count}")
    print(f"DOWNLOADED_RUNS={result.downloaded_count}")
    print(f"REPAIRED_RUNS={result.repaired_count}")
    print("SYNC_OK=true")
    return config.EXIT_OK
