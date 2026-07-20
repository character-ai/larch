"""Append-only run archive publication with durable retry and cache promotion."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import shutil
import stat
import sys
import tarfile
import tempfile
from collections.abc import Generator, Mapping, Sequence
from contextlib import contextmanager, suppress
from dataclasses import asdict, dataclass, replace
from enum import StrEnum
from pathlib import Path
from typing import Final, Protocol, cast

from larch import io as larch_io
from larch.core import config, repo_roots
from larch.report import run_log_archive, storage_config
from larch.report.object_store import (
    ObjectStoreError,
    ObjectStoreErrorKind,
    RemoteObject,
    object_store_for,
)
from larch.report.run_log_archive import RunArchiveMaterializationResult
from larch.report.run_log_batch import validate_run_id_slug
from larch.report.storage_config import StorageConfigurationError, StorageRoot

_PENDING_SCHEMA_VERSION: Final = 1
_PENDING_ARCHIVE_NAME: Final = "archive.tar.gz"
_PENDING_METADATA_NAME: Final = "retry.json"
_ENV_XDG_CACHE_HOME: Final = "XDG_CACHE_HOME"
_ENV_XDG_STATE_HOME: Final = "XDG_STATE_HOME"
_CHUNK_SIZE: Final = 1024 * 1024
_ASCII_CONTROL_BOUND: Final = 32
_ASCII_DELETE: Final = 127
_SHA256_HEX_LENGTH: Final = 64
_PENDING_KEYS: Final = frozenset(
    {
        "archive_sha256",
        "archive_size",
        "attempts",
        "last_error",
        "manifest_sha256",
        "remote_key",
        "repo_name",
        "run_id",
        "schema_version",
        "skill",
        "storage_uri",
    }
)


class PublicationError(RuntimeError):
    """A publication or durable retry invariant failed."""


class RemotePublicationStatus(StrEnum):
    """How the immutable remote object reached its postcondition."""

    CREATED = "created"
    MATCHED = "matched"


class CachePublicationStatus(StrEnum):
    """How the verified unpacked cache reached its postcondition."""

    PROMOTED = "promoted"
    MATERIALIZED = "materialized"
    PRESENT = "present"


class ObjectStore(Protocol):
    """Provider-neutral operations required by publication."""

    def upload_create(self, key: str, source: Path) -> RemoteObject: ...

    def download(self, key: str, destination: Path) -> None: ...

    def metadata(self, key: str) -> RemoteObject: ...


@dataclass(frozen=True)
class PublicationPaths:
    """All local paths owned by one repository/skill/run publication."""

    pending_dir: Path
    pending_archive: Path
    pending_metadata: Path
    cache_dir: Path
    lock_file: Path


@dataclass(frozen=True)
class PublicationRequest:
    """Immutable caller inputs for one run publication attempt."""

    repo_root: Path
    storage_root: StorageRoot
    skill: str
    run_id: str
    staging_root: Path | None
    cache_home: Path | None = None
    state_home: Path | None = None


@dataclass(frozen=True)
class PendingPublication:
    """Content-pinned durable retry record for one immutable object."""

    schema_version: int
    storage_uri: str
    repo_name: str
    skill: str
    run_id: str
    remote_key: str
    archive_sha256: str
    archive_size: int
    manifest_sha256: str
    attempts: int
    last_error: str


@dataclass(frozen=True)
class PublicationResult:
    """Verified remote and local postconditions for a published run."""

    remote_key: str
    archive_sha256: str
    cache_dir: Path
    remote_status: RemotePublicationStatus
    cache_status: CachePublicationStatus


def validated_component(value: str, *, label: str, slug: bool) -> str:
    invalid_literal: bool = (
        not value
        or value in {".", ".."}
        or "/" in value
        or "\\" in value
        or any(
            ord(character) < _ASCII_CONTROL_BOUND or ord(character) == _ASCII_DELETE
            for character in value
        )
    )
    if invalid_literal or (slug and not validate_run_id_slug(value)):
        raise ValueError(f"invalid {label}: {value!r}")
    return value


def xdg_home(
    *,
    environ: Mapping[str, str],
    variable: str,
    fallback: Path,
) -> Path:
    configured: str = environ.get(variable, "")
    selected: Path = Path(configured) if configured else fallback
    if not selected.is_absolute():
        raise ValueError(f"{variable} must be an absolute path")
    return selected


def repository_cache_root(
    *,
    repo_root: Path,
    cache_home: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> Path:
    """Return the literal per-repository root for unpacked run archives."""
    root: Path = larch_io.validate_trusted_directory(repo_root)
    repo_name: str = validated_component(root.name, label="repository name", slug=False)
    environment: Mapping[str, str] = os.environ if environ is None else environ
    resolved_cache_home: Path = cache_home or xdg_home(
        environ=environment,
        variable=_ENV_XDG_CACHE_HOME,
        fallback=Path.home() / ".cache",
    )
    if not resolved_cache_home.is_absolute():
        raise ValueError("publication cache home must be an absolute path")
    return resolved_cache_home / "larch" / "run-logs" / repo_name


def publication_paths(
    *,
    request: PublicationRequest,
    environ: Mapping[str, str] | None = None,
) -> PublicationPaths:
    """Resolve the literal repository cache path and durable retry path."""
    root: Path = larch_io.validate_trusted_directory(request.repo_root)
    repo_name: str = validated_component(root.name, label="repository name", slug=False)
    skill_name: str = validated_component(request.skill, label="skill", slug=True)
    run_name: str = validated_component(request.run_id, label="run-id", slug=True)
    environment: Mapping[str, str] = os.environ if environ is None else environ
    cache_root: Path = repository_cache_root(
        repo_root=root,
        cache_home=request.cache_home,
        environ=environment,
    )
    resolved_state_home: Path = request.state_home or xdg_home(
        environ=environment,
        variable=_ENV_XDG_STATE_HOME,
        fallback=Path.home() / ".local" / "state",
    )
    if not resolved_state_home.is_absolute():
        raise ValueError("publication state home must be an absolute path")
    cache_dir: Path = cache_root / skill_name / run_name
    pending_dir: Path = (
        resolved_state_home
        / "larch"
        / "run-log-pending"
        / repo_name
        / skill_name
        / run_name
    )
    lock_file: Path = (
        resolved_state_home
        / "larch"
        / "run-log-locks"
        / repo_name
        / skill_name
        / f"{run_name}.lock"
    )
    return PublicationPaths(
        pending_dir=pending_dir,
        pending_archive=pending_dir / _PENDING_ARCHIVE_NAME,
        pending_metadata=pending_dir / _PENDING_METADATA_NAME,
        cache_dir=cache_dir,
        lock_file=lock_file,
    )


def ensure_concurrent_directory(path: Path) -> Path:
    """Create a trusted directory while tolerating a same-path creator race."""
    directory: Path = path if path.is_absolute() else Path.cwd() / path
    try:
        return larch_io.validate_trusted_directory(directory)
    except OSError:
        pass
    if directory == directory.parent:
        raise OSError(f"cannot create trusted publication directory: {directory}")
    _ = ensure_concurrent_directory(directory.parent)
    with suppress(FileExistsError):
        directory.mkdir(mode=0o700)
    return larch_io.validate_trusted_directory(directory)


@contextmanager
def publication_lock(path: Path) -> Generator[None, None, None]:
    """Hold the blocking advisory lock shared by all operations for one run."""
    parent: Path = ensure_concurrent_directory(path.parent)
    lock_path: Path = parent / path.name
    if lock_path.is_symlink():
        raise OSError(f"refusing symlinked publication lock: {lock_path}")
    flags: int = os.O_RDWR | os.O_CREAT
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor: int = os.open(lock_path, flags, 0o600)
    try:
        opened: os.stat_result = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode):
            raise OSError(f"publication lock is not a regular file: {lock_path}")
        os.fchmod(descriptor, 0o600)
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        with suppress(OSError):
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def _sha256_regular_file(path: Path, *, root: Path) -> tuple[str, int]:
    trusted_root: Path = larch_io.validate_trusted_directory(root)
    if path.parent != trusted_root:
        raise OSError(f"publication archive is outside its trusted directory: {path}")
    entry: os.stat_result = path.stat(follow_symlinks=False)
    if not stat.S_ISREG(entry.st_mode):
        raise OSError(f"publication archive is not a regular file: {path}")
    flags: int = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor: int = os.open(path, flags)
    digest = hashlib.sha256()
    with os.fdopen(descriptor, "rb") as handle:
        opened: os.stat_result = os.fstat(handle.fileno())
        if (opened.st_dev, opened.st_ino, opened.st_size) != (
            entry.st_dev,
            entry.st_ino,
            entry.st_size,
        ):
            raise OSError(f"publication archive changed while opening: {path}")
        while chunk := handle.read(_CHUNK_SIZE):
            digest.update(chunk)
    current: os.stat_result = path.stat(follow_symlinks=False)
    if (current.st_dev, current.st_ino, current.st_size, current.st_mtime_ns) != (
        entry.st_dev,
        entry.st_ino,
        entry.st_size,
        entry.st_mtime_ns,
    ):
        raise OSError(f"publication archive changed while reading: {path}")
    return digest.hexdigest(), entry.st_size


def _fsync_directory(path: Path) -> None:
    directory: Path = larch_io.validate_trusted_directory(path)
    flags: int = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor: int = os.open(directory, flags)
    try:
        opened: os.stat_result = os.fstat(descriptor)
        if not stat.S_ISDIR(opened.st_mode):
            raise OSError(f"publication directory changed while opening: {directory}")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _metadata_text(pending: PendingPublication) -> str:
    return json.dumps(asdict(pending), ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def _write_pending_metadata(paths: PublicationPaths, pending: PendingPublication) -> None:
    larch_io.trusted_atomic_write(
        paths.pending_metadata,
        _metadata_text(pending),
        root=paths.pending_dir,
    )
    _fsync_directory(paths.pending_dir)


def _parse_pending_metadata(text: str) -> PendingPublication:
    try:
        raw: object = json.loads(text)
    except json.JSONDecodeError as exc:
        raise PublicationError("pending publication metadata is invalid JSON") from exc
    if not isinstance(raw, dict):
        raise PublicationError("pending publication metadata has invalid fields")
    data = cast("dict[str, object]", raw)
    if frozenset(data) != _PENDING_KEYS:
        raise PublicationError("pending publication metadata has invalid fields")
    string_keys: tuple[str, ...] = (
        "storage_uri",
        "repo_name",
        "skill",
        "run_id",
        "remote_key",
        "archive_sha256",
        "manifest_sha256",
        "last_error",
    )
    if any(not isinstance(data[key], str) for key in string_keys):
        raise PublicationError("pending publication metadata has invalid string fields")
    integer_keys: tuple[str, ...] = ("schema_version", "archive_size", "attempts")
    if any(not isinstance(data[key], int) or isinstance(data[key], bool) for key in integer_keys):
        raise PublicationError("pending publication metadata has invalid integer fields")
    return PendingPublication(
        schema_version=cast("int", data["schema_version"]),
        storage_uri=cast("str", data["storage_uri"]),
        repo_name=cast("str", data["repo_name"]),
        skill=cast("str", data["skill"]),
        run_id=cast("str", data["run_id"]),
        remote_key=cast("str", data["remote_key"]),
        archive_sha256=cast("str", data["archive_sha256"]),
        archive_size=cast("int", data["archive_size"]),
        manifest_sha256=cast("str", data["manifest_sha256"]),
        attempts=cast("int", data["attempts"]),
        last_error=cast("str", data["last_error"]),
    )


def _validate_pending(
    *,
    paths: PublicationPaths,
    pending: PendingPublication,
    request: PublicationRequest,
    repo_name: str,
) -> PendingPublication:
    expected_key: str = f"run-logs/{request.skill}/{request.run_id}.tar.gz"
    identity: tuple[object, ...] = (
        pending.schema_version,
        pending.storage_uri,
        pending.repo_name,
        pending.skill,
        pending.run_id,
        pending.remote_key,
    )
    expected_identity: tuple[object, ...] = (
        _PENDING_SCHEMA_VERSION,
        request.storage_root.uri,
        repo_name,
        request.skill,
        request.run_id,
        expected_key,
    )
    if identity != expected_identity:
        raise PublicationError("pending publication identity does not match the live request")
    if (
        not _valid_sha256(pending.archive_sha256)
        or not _valid_sha256(pending.manifest_sha256)
        or pending.archive_size <= 0
        or pending.attempts < 0
    ):
        raise PublicationError("pending publication metadata has invalid content identity")
    archive_sha256, archive_size = _sha256_regular_file(
        paths.pending_archive,
        root=paths.pending_dir,
    )
    if (archive_sha256, archive_size) != (pending.archive_sha256, pending.archive_size):
        raise PublicationError("pending archive does not match its durable content identity")
    return pending


def _valid_sha256(value: str) -> bool:
    return len(value) == _SHA256_HEX_LENGTH and all(
        character in "0123456789abcdef" for character in value
    )


def _load_pending(
    *,
    paths: PublicationPaths,
    request: PublicationRequest,
    repo_name: str,
) -> PendingPublication:
    root: Path = larch_io.validate_trusted_directory(paths.pending_dir)
    text: str = larch_io.read_trusted_text(
        paths.pending_metadata,
        root=root,
        reject_cr=True,
    )
    return _validate_pending(
        paths=paths,
        pending=_parse_pending_metadata(text),
        request=request,
        repo_name=repo_name,
    )


def _create_pending(
    *,
    paths: PublicationPaths,
    request: PublicationRequest,
    repo_name: str,
) -> PendingPublication:
    parent: Path = ensure_concurrent_directory(paths.pending_dir.parent)
    temporary: Path | None = Path(
        tempfile.mkdtemp(dir=parent, prefix=f".{request.run_id}.pending-")
    )
    temporary.chmod(0o700)
    try:
        if request.staging_root is None:
            raise PublicationError("a staging root is required to create a pending archive")
        created = run_log_archive.create_run_archive(
            staging_root=request.staging_root,
            output_dir=temporary,
            skill=request.skill,
            run_id=request.run_id,
        )
        archive_path: Path = temporary / _PENDING_ARCHIVE_NAME
        _ = created.archive_path.rename(archive_path)
        pending = PendingPublication(
            schema_version=_PENDING_SCHEMA_VERSION,
            storage_uri=request.storage_root.uri,
            repo_name=repo_name,
            skill=request.skill,
            run_id=request.run_id,
            remote_key=f"run-logs/{request.skill}/{request.run_id}.tar.gz",
            archive_sha256=created.archive_sha256,
            archive_size=archive_path.stat(follow_symlinks=False).st_size,
            manifest_sha256=created.manifest_sha256,
            attempts=0,
            last_error="",
        )
        temporary_paths = PublicationPaths(
            pending_dir=temporary,
            pending_archive=archive_path,
            pending_metadata=temporary / _PENDING_METADATA_NAME,
            cache_dir=paths.cache_dir,
            lock_file=paths.lock_file,
        )
        _write_pending_metadata(temporary_paths, pending)
        _ = temporary.rename(paths.pending_dir)
        _fsync_directory(parent)
        temporary = None
        return _load_pending(
            paths=paths,
            request=request,
            repo_name=repo_name,
        )
    finally:
        if temporary is not None:
            shutil.rmtree(temporary)


def _pending_for_request(
    *,
    paths: PublicationPaths,
    request: PublicationRequest,
    repo_name: str,
) -> PendingPublication:
    if paths.pending_dir.exists() or paths.pending_dir.is_symlink():
        return _load_pending(
            paths=paths,
            request=request,
            repo_name=repo_name,
        )
    if request.staging_root is None:
        raise PublicationError("no durable pending archive exists and --staging-root was not provided")
    return _create_pending(
        paths=paths,
        request=request,
        repo_name=repo_name,
    )


def _matching_remote_exists(
    *,
    store: ObjectStore,
    pending: PendingPublication,
    paths: PublicationPaths,
) -> bool:
    remote: RemoteObject = store.metadata(pending.remote_key)
    if remote.size != pending.archive_size:
        return False
    with tempfile.NamedTemporaryFile(
        dir=paths.pending_dir,
        prefix=".remote-verify-",
        delete=False,
    ) as handle:
        downloaded: Path = Path(handle.name)
    try:
        store.download(pending.remote_key, downloaded)
        remote_sha256, remote_size = _sha256_regular_file(downloaded, root=paths.pending_dir)
        return (remote_sha256, remote_size) == (pending.archive_sha256, pending.archive_size)
    finally:
        downloaded.unlink(missing_ok=True)


def _publish_remote(
    *,
    store: ObjectStore,
    pending: PendingPublication,
    paths: PublicationPaths,
) -> RemotePublicationStatus:
    try:
        uploaded: RemoteObject = store.upload_create(pending.remote_key, paths.pending_archive)
    except ObjectStoreError as exc:
        if exc.kind is not ObjectStoreErrorKind.ALREADY_EXISTS:
            raise
        if not _matching_remote_exists(store=store, pending=pending, paths=paths):
            raise PublicationError(
                "immutable remote key already exists with different content"
            ) from exc
        return RemotePublicationStatus.MATCHED
    if uploaded.key != pending.remote_key or uploaded.size != pending.archive_size:
        raise PublicationError("create-only upload returned a mismatched object identity")
    verified: RemoteObject = store.metadata(pending.remote_key)
    if verified.key != pending.remote_key or verified.size != pending.archive_size:
        raise PublicationError("uploaded remote object failed metadata verification")
    return RemotePublicationStatus.CREATED


def _cache_result(
    *,
    paths: PublicationPaths,
    pending: PendingPublication,
    staging_root: Path | None,
) -> tuple[RunArchiveMaterializationResult, CachePublicationStatus]:
    _ = ensure_concurrent_directory(paths.cache_dir.parent)
    if paths.cache_dir.exists() or paths.cache_dir.is_symlink():
        existing: RunArchiveMaterializationResult = run_log_archive.verify_materialized_run_directory(
            run_dir=paths.cache_dir,
            expected_skill=pending.skill,
            expected_run_id=pending.run_id,
        )
        if existing.manifest_sha256 != pending.manifest_sha256:
            raise PublicationError("existing cache directory contains different run content")
        return existing, CachePublicationStatus.PRESENT
    if staging_root is not None:
        promoted: RunArchiveMaterializationResult = run_log_archive.promote_staging_run_directory(
            staging_root=staging_root,
            run_dir=paths.cache_dir,
            expected_skill=pending.skill,
            expected_run_id=pending.run_id,
            expected_manifest_sha256=pending.manifest_sha256,
        )
        return promoted, CachePublicationStatus.PROMOTED
    materialized: RunArchiveMaterializationResult = run_log_archive.materialize_run_archive(
        archive_path=paths.pending_archive,
        run_dir=paths.cache_dir,
        expected_skill=pending.skill,
        expected_run_id=pending.run_id,
    )
    return materialized, CachePublicationStatus.MATERIALIZED


def _failure_token(exc: Exception) -> str:
    if isinstance(exc, ObjectStoreError):
        return f"object-{exc.operation}-{exc.kind.value}"
    if isinstance(exc, PublicationError):
        return "publication-invariant"
    if isinstance(exc, (EOFError, OSError, tarfile.TarError, TypeError, ValueError)):
        return "local-integrity"
    return "internal"


def _complete_pending(paths: PublicationPaths) -> None:
    completed: Path = paths.pending_dir.with_name(
        f".{paths.pending_dir.name}.complete-{os.getpid()}-{os.urandom(4).hex()}"
    )
    _ = paths.pending_dir.rename(completed)
    _fsync_directory(completed.parent)
    with suppress(OSError):
        shutil.rmtree(completed)


def publish_run(
    *,
    request: PublicationRequest,
    store: ObjectStore | None = None,
    environ: Mapping[str, str] | None = None,
) -> PublicationResult:
    """Publish one immutable archive and atomically populate its local cache."""
    root: Path = larch_io.validate_trusted_directory(request.repo_root)
    repo_name: str = validated_component(root.name, label="repository name", slug=False)
    skill_name: str = validated_component(request.skill, label="skill", slug=True)
    run_name: str = validated_component(request.run_id, label="run-id", slug=True)
    normalized_request = replace(
        request,
        repo_root=root,
        skill=skill_name,
        run_id=run_name,
    )
    paths: PublicationPaths = publication_paths(
        request=normalized_request,
        environ=environ,
    )
    active_store: ObjectStore = (
        object_store_for(normalized_request.storage_root, environ=environ)
        if store is None
        else store
    )
    with publication_lock(paths.lock_file):
        pending: PendingPublication = _pending_for_request(
            paths=paths,
            request=normalized_request,
            repo_name=repo_name,
        )
        pending = replace(pending, attempts=pending.attempts + 1, last_error="")
        _write_pending_metadata(paths, pending)
        try:
            remote_status: RemotePublicationStatus = _publish_remote(
                store=active_store,
                pending=pending,
                paths=paths,
            )
            cache_result, cache_status = _cache_result(
                paths=paths,
                pending=pending,
                staging_root=normalized_request.staging_root,
            )
            if cache_result.manifest_sha256 != pending.manifest_sha256:
                raise PublicationError("published cache failed manifest identity verification")
        except (
            EOFError,
            ObjectStoreError,
            OSError,
            PublicationError,
            tarfile.TarError,
            TypeError,
            ValueError,
        ) as exc:
            _write_pending_metadata(paths, replace(pending, last_error=_failure_token(exc)))
            raise
        _complete_pending(paths)
    return PublicationResult(
        remote_key=pending.remote_key,
        archive_sha256=pending.archive_sha256,
        cache_dir=paths.cache_dir,
        remote_status=remote_status,
        cache_status=cache_status,
    )


def main(argv: Sequence[str]) -> int:
    """Publish or retry one run and emit its machine-readable postconditions."""
    parser = argparse.ArgumentParser(prog="cli.py run-log publish")
    _ = parser.add_argument("--repo-root", required=True)
    _ = parser.add_argument("--skill", required=True)
    _ = parser.add_argument("--run-id", required=True)
    _ = parser.add_argument("--staging-root")
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
        result: PublicationResult = publish_run(
            request=PublicationRequest(
                repo_root=repo_root,
                storage_root=storage_root,
                skill=args.skill,
                run_id=args.run_id,
                staging_root=Path(args.staging_root) if args.staging_root else None,
            ),
        )
    except StorageConfigurationError as exc:
        print(f"publication failed: {exc}", file=sys.stderr)
        return config.EXIT_STORAGE_CONFIG
    except (
        EOFError,
        ObjectStoreError,
        OSError,
        PublicationError,
        tarfile.TarError,
        TypeError,
        ValueError,
    ) as exc:
        print(f"publication failed: {exc}", file=sys.stderr)
        return config.EXIT_INTERNAL_ERROR
    print(f"REMOTE_KEY={result.remote_key}")
    print(f"ARCHIVE_SHA256={result.archive_sha256}")
    print(f"CACHE_DIR={result.cache_dir}")
    print(f"REMOTE_STATUS={result.remote_status.value}")
    print(f"CACHE_STATUS={result.cache_status.value}")
    print("PUBLISH_OK=true")
    return config.EXIT_OK
