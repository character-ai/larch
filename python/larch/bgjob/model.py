"""Typed models and path validation for the bgjob subsystem."""

from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass
from pathlib import Path

from larch.core import config, process_identity


@dataclass(frozen=True)
class OwnerIdentity:
    recorded: process_identity.RecordedProcessIdentity | None


@dataclass(frozen=True)
class JobSpec:
    step: str
    tmpdir: Path
    log_dir: Path
    budget_s: int
    command: tuple[str, ...]
    run_id: str
    owner: OwnerIdentity
    sentinel_paths: tuple[Path, ...] = ()
    merge_result_env: Path | None = None


@dataclass(frozen=True)
class RegistryEntry:
    step: str
    run_id: str
    tmpdir: Path
    log_dir: Path
    clone_path: Path
    daemon: process_identity.RecordedProcessIdentity
    child: process_identity.RecordedProcessIdentity
    owner: process_identity.RecordedProcessIdentity | None
    start_epoch: int
    budget_s: int
    stdout_log: Path
    stderr_log: Path
    result_env: Path


@dataclass(frozen=True)
class LivenessVerdict:
    live: bool
    reason: str


@dataclass(frozen=True)
class WaitResult:
    status: str
    rows: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class ResultEnvRows:
    rows: tuple[tuple[str, str], ...]


def validate_slug(value: str, *, label: str) -> str:
    if not value or ".." in value or "/" in value or "\\" in value:
        msg = f"invalid {label}: {value!r}"
        raise ValueError(msg)
    if re.fullmatch(config.BGJOB_SLUG_PATTERN, value) is None:
        msg = f"invalid {label}: {value!r}"
        raise ValueError(msg)
    return value


def default_run_id(*, tmpdir: Path, clone_path: Path) -> str:
    _ = clone_path
    material = str(tmpdir.resolve())
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]


def checked_dir(path: Path, *, label: str, must_exist: bool = True) -> Path:
    resolved = path.expanduser().resolve()
    if not resolved.is_absolute():
        msg = f"{label} must be absolute: {path}"
        raise ValueError(msg)
    if path.is_symlink() or resolved.is_symlink():
        msg = f"{label} must not be a symlink: {path}"
        raise ValueError(msg)
    if must_exist and not resolved.is_dir():
        msg = f"{label} is not a directory: {path}"
        raise ValueError(msg)
    return resolved


def ensure_under(path: Path, root: Path, *, label: str) -> Path:
    resolved = path.expanduser().resolve()
    root_resolved = root.expanduser().resolve()
    try:
        _ = resolved.relative_to(root_resolved)
    except ValueError as exc:
        msg = f"{label} escapes {root_resolved}: {resolved}"
        raise ValueError(msg) from exc
    return resolved


def bgjob_dir(tmpdir: Path) -> Path:
    root = checked_dir(tmpdir, label="tmpdir")
    return root / config.BGJOB_TMP_SUBDIR


def result_env_path(*, tmpdir: Path, step: str) -> Path:
    slug = validate_slug(step, label="step")
    root = bgjob_dir(tmpdir)
    return ensure_under(root / f"{slug}{config.BGJOB_RESULT_ENV_SUFFIX}", root, label="result env")


def log_paths(*, tmpdir: Path, log_dir: Path | None, step: str) -> tuple[Path, Path, Path]:
    slug = validate_slug(step, label="step")
    root = bgjob_dir(tmpdir) if log_dir is None else checked_dir(log_dir, label="log-dir", must_exist=False)
    _ = root.mkdir(parents=True, exist_ok=True)
    if root.is_symlink():
        msg = f"log-dir must not be a symlink: {root}"
        raise ValueError(msg)
    stdout_log = ensure_under(root / f"{slug}.stdout.log", root, label="stdout log")
    stderr_log = ensure_under(root / f"{slug}.stderr.log", root, label="stderr log")
    return root, stdout_log, stderr_log


def registry_root() -> Path:
    override = os.environ.get(config.ENV_BGJOB_REGISTRY_ROOT, "")
    root = Path(override).expanduser() if override else Path.home() / ".cache" / "larch" / config.BGJOB_REGISTRY_DIRNAME
    _ = root.mkdir(parents=True, exist_ok=True)
    if root.is_symlink():
        msg = f"registry root must not be a symlink: {root}"
        raise ValueError(msg)
    return root.resolve()


def registry_path(*, run_id: str, step: str, root: Path | None = None) -> Path:
    run_slug = validate_slug(run_id, label="run-id")
    step_slug = validate_slug(step, label="step")
    registry = registry_root() if root is None else checked_dir(root, label="registry-root", must_exist=False)
    registry.mkdir(parents=True, exist_ok=True)
    return ensure_under(registry / f"{run_slug}-{step_slug}.env", registry, label="registry path")


def reject_line_value(value: object, *, label: str) -> str:
    text = str(value)
    if "\n" in text or "\r" in text:
        msg = f"{label} contains a newline or carriage return"
        raise ValueError(msg)
    return text
