"""Typed local-state consumer for Rust-owned run-log publication.

The publish command, pending retry record, archive writer, remote transport,
and cache promotion live in Rust.  This module deliberately retains only
Python consumers' local path and lock types while those callers migrate.
"""

from __future__ import annotations

import fcntl
import os
import stat
from collections.abc import Generator, Mapping
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Final

from larch import io as larch_io
from larch.report.run_log_batch import validate_run_id_slug
from larch.report.storage_config import ToolRepositoryStorage

_ENV_XDG_CACHE_HOME: Final = "XDG_CACHE_HOME"
_ENV_XDG_STATE_HOME: Final = "XDG_STATE_HOME"
_ASCII_CONTROL_BOUND: Final = 32
_ASCII_DELETE: Final = 127


class PublicationError(RuntimeError):
    """A Rust run-log publication boundary rejected a request."""


class RemotePublicationStatus(StrEnum):
    """How the Rust publication boundary reached remote postcondition."""

    CREATED = "created"
    MATCHED = "matched"


class CachePublicationStatus(StrEnum):
    """How the Rust publication boundary reached local cache postcondition."""

    PROMOTED = "promoted"
    MATERIALIZED = "materialized"
    PRESENT = "present"


@dataclass(frozen=True)
class PublicationPaths:
    """Local paths retained for non-publication Python consumers."""

    pending_dir: Path
    pending_archive: Path
    pending_metadata: Path
    cache_dir: Path
    lock_file: Path


@dataclass(frozen=True)
class PublicationRequest:
    """Path inputs retained for typed Python consumers during cutover."""

    repo_root: Path
    storage_root: ToolRepositoryStorage
    skill: str
    run_id: str
    staging_root: Path | None
    cache_home: Path | None = None
    state_home: Path | None = None


@dataclass(frozen=True)
class PublicationResult:
    """Verified publication fields parsed from the Rust lifecycle envelope."""

    remote_key: str
    archive_sha256: str
    cache_dir: Path
    remote_status: RemotePublicationStatus
    cache_status: CachePublicationStatus


def validated_component(value: str, *, label: str, slug: bool) -> str:
    """Validate a single local-state path component."""
    invalid = (
        not value
        or value in {".", ".."}
        or "/" in value
        or "\\" in value
        or any(
            ord(character) < _ASCII_CONTROL_BOUND or ord(character) == _ASCII_DELETE
            for character in value
        )
    )
    if invalid or (slug and not validate_run_id_slug(value)):
        raise ValueError(f"invalid {label}: {value!r}")
    return value


def xdg_home(*, environ: Mapping[str, str], variable: str, fallback: Path) -> Path:
    """Resolve one absolute XDG home for a local-only consumer."""
    configured = environ.get(variable, "")
    selected = Path(configured) if configured else fallback
    if not selected.is_absolute():
        raise ValueError(f"{variable} must be an absolute path")
    return selected


def repository_cache_root(
    *,
    storage: ToolRepositoryStorage,
    cache_home: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> Path:
    """Return the storage-origin-bound v2 cache root."""
    environment = os.environ if environ is None else environ
    home = cache_home or xdg_home(
        environ=environment,
        variable=_ENV_XDG_CACHE_HOME,
        fallback=Path.home() / ".cache",
    )
    if not home.is_absolute():
        raise ValueError("publication cache home must be an absolute path")
    return (
        home
        / "larch"
        / "run-logs"
        / "v2"
        / storage.client_repo
        / storage.storage_origin_id
    )


def publication_paths(
    *, request: PublicationRequest, environ: Mapping[str, str] | None = None
) -> PublicationPaths:
    """Resolve local cache and lock paths for non-publication consumers."""
    _ = larch_io.validate_trusted_directory(request.repo_root)
    skill = validated_component(request.skill, label="skill", slug=True)
    run_id = validated_component(request.run_id, label="run-id", slug=True)
    environment = os.environ if environ is None else environ
    cache_dir = (
        repository_cache_root(
            storage=request.storage_root,
            cache_home=request.cache_home,
            environ=environment,
        )
        / skill
        / run_id
    )
    state_home = request.state_home or xdg_home(
        environ=environment,
        variable=_ENV_XDG_STATE_HOME,
        fallback=Path.home() / ".local" / "state",
    )
    if not state_home.is_absolute():
        raise ValueError("publication state home must be an absolute path")
    pending_dir = (
        state_home
        / "larch"
        / "run-log-pending"
        / "v2"
        / request.storage_root.client_repo
        / request.storage_root.storage_origin_id
        / skill
        / run_id
    )
    lock_file = (
        state_home
        / "larch"
        / "run-log-locks"
        / "v2"
        / request.storage_root.client_repo
        / request.storage_root.storage_origin_id
        / skill
        / f"{run_id}.lock"
    )
    return PublicationPaths(
        pending_dir=pending_dir,
        pending_archive=pending_dir / "archive.tar.gz",
        pending_metadata=pending_dir / "retry.json",
        cache_dir=cache_dir,
        lock_file=lock_file,
    )


def ensure_concurrent_directory(path: Path) -> Path:
    """Create a trusted directory while tolerating one creator race."""
    directory = path if path.is_absolute() else Path.cwd() / path
    try:
        return larch_io.validate_trusted_directory(directory)
    except OSError:
        pass
    if directory == directory.parent:
        raise OSError(f"cannot create trusted local-state directory: {directory}")
    _ = ensure_concurrent_directory(directory.parent)
    with suppress(FileExistsError):
        directory.mkdir(mode=0o700)
    return larch_io.validate_trusted_directory(directory)


@contextmanager
def publication_lock(path: Path) -> Generator[None, None, None]:
    """Hold the local advisory lock used by remaining Python state owners."""
    parent = ensure_concurrent_directory(path.parent)
    lock_path = parent / path.name
    if lock_path.is_symlink():
        raise OSError(f"refusing symlinked publication lock: {lock_path}")
    flags = os.O_RDWR | os.O_CREAT
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(lock_path, flags, 0o600)
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode):
            raise OSError(f"publication lock is not a regular file: {lock_path}")
        os.fchmod(descriptor, 0o600)
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        with suppress(OSError):
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)
