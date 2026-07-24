"""Repository-scoped mutable state for run-log analyzers."""

from __future__ import annotations
import hashlib
import os
import stat
from collections.abc import Generator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Final
from larch import io as larch_io
from larch.report import run_log_publish, storage_config

_ENV_XDG_STATE_HOME: Final = "XDG_STATE_HOME"
MISSING_DIGEST: Final = "missing"
SHA256_HEX_LENGTH: Final = 64


class AnalysisStateError(RuntimeError):
    """A mutable analysis-state integrity check failed."""


class AnalysisStateConflict(AnalysisStateError):
    """A writer started from state that another invocation replaced."""


@dataclass(frozen=True)
class StateSnapshot:
    data: bytes | None
    digest: str


def repository_state_root(
    *,
    repo_root: Path,
    storage: storage_config.ToolRepositoryStorage | None = None,
    state_home: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> Path:
    """Return the literal repository root for mutable analyzer state."""
    trusted_repo = larch_io.validate_trusted_directory(repo_root)
    active_storage: storage_config.ToolRepositoryStorage = (
        storage
        if storage is not None
        else storage_config.load_tool_repository_storage(
            repo_root=trusted_repo, environ=environ
        )
    )
    environment = os.environ if environ is None else environ
    resolved_home = state_home or run_log_publish.xdg_home(
        environ=environment,
        variable=_ENV_XDG_STATE_HOME,
        fallback=Path.home() / ".local" / "state",
    )
    if not resolved_home.is_absolute():
        raise ValueError("analysis state home must be an absolute path")
    return (
        resolved_home.expanduser().resolve()
        / "larch"
        / "analysis-state"
        / "v2"
        / active_storage.client_repo
        / active_storage.storage_origin_id
    )


def state_path(  # noqa: PLR0913 - state identity, owner, home, and environment remain explicit.
    *,
    repo_root: Path,
    storage: storage_config.ToolRepositoryStorage | None = None,
    owner: str,
    name: str,
    state_home: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> Path:
    owner_name = run_log_publish.validated_component(
        owner, label="state owner", slug=True
    )
    file_name = run_log_publish.validated_component(
        name, label="state file", slug=False
    )
    return (
        repository_state_root(
            repo_root=repo_root,
            storage=storage,
            state_home=state_home,
            environ=environ,
        )
        / owner_name
        / file_name
    )


def output_path(  # noqa: PLR0913 - output creation shares the explicit state-path boundary.
    *,
    repo_root: Path,
    storage: storage_config.ToolRepositoryStorage | None = None,
    owner: str,
    name: str,
    state_home: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> Path:
    path = state_path(
        repo_root=repo_root,
        storage=storage,
        owner=owner,
        name=name,
        state_home=state_home,
        environ=environ,
    )
    _ = run_log_publish.ensure_concurrent_directory(path.parent)
    return path


def _snapshot_unlocked(path: Path) -> StateSnapshot:
    try:
        entry = path.stat(follow_symlinks=False)
    except FileNotFoundError:
        return StateSnapshot(None, MISSING_DIGEST)
    if not stat.S_ISREG(entry.st_mode):
        raise AnalysisStateError(f"analysis state is not a regular file: {path}")
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise AnalysisStateError(f"analysis state is unreadable: {path}") from exc
    current = path.stat(follow_symlinks=False)
    if not stat.S_ISREG(current.st_mode) or (
        current.st_dev,
        current.st_ino,
        current.st_size,
        current.st_mtime_ns,
    ) != (entry.st_dev, entry.st_ino, entry.st_size, entry.st_mtime_ns):
        raise AnalysisStateError(f"analysis state changed while reading: {path}")
    return StateSnapshot(data, hashlib.sha256(data).hexdigest())


@contextmanager
def state_lock(path: Path) -> Generator[None, None, None]:
    lock_path = path.with_name(f".{path.name}.lock")
    try:
        with run_log_publish.publication_lock(lock_path):
            try:
                entry = path.stat(follow_symlinks=False)
            except FileNotFoundError:
                entry = None
            if entry is not None and not stat.S_ISREG(entry.st_mode):
                raise AnalysisStateError(
                    f"analysis state is not a regular file: {path}"
                )
            yield
    except OSError as exc:
        raise AnalysisStateError(f"could not lock analysis state: {path}") from exc


def read_snapshot(path: Path) -> StateSnapshot:
    with state_lock(path):
        return _snapshot_unlocked(path)


def _atomic_write_unlocked(path: Path, data: bytes) -> None:
    parent = run_log_publish.ensure_concurrent_directory(path.parent)
    target = parent / path.name
    if target.is_symlink():
        raise AnalysisStateError(f"refusing symlinked analysis state: {target}")
    try:
        larch_io.trusted_atomic_write(target, data.decode("utf-8"), root=parent)
        target.chmod(0o600)
    except (OSError, UnicodeDecodeError) as exc:
        raise AnalysisStateError(f"could not write analysis state: {target}") from exc


def write_bytes(path: Path, data: bytes, *, expected_digest: str) -> str:
    if expected_digest != MISSING_DIGEST and (
        len(expected_digest) != SHA256_HEX_LENGTH
        or any(char not in "0123456789abcdef" for char in expected_digest)
    ):
        raise ValueError("expected analysis-state digest must be 'missing' or SHA-256")
    with state_lock(path):
        current = _snapshot_unlocked(path)
        if current.digest != expected_digest:
            raise AnalysisStateConflict(f"analysis state changed concurrently: {path}")
        _atomic_write_unlocked(path, data)
        return hashlib.sha256(data).hexdigest()


def append_bytes(path: Path, data: bytes) -> None:
    """Atomically append while holding the owner lock."""
    with state_lock(path):
        current = _snapshot_unlocked(path).data or b""
        _atomic_write_unlocked(path, current + data)
