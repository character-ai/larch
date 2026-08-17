# pyright: reportUnusedCallResult=false, reportUnusedFunction=false
"""Read-only persisted run-identity helpers for Rust-owned progress state.

The Rust ``progress`` commands exclusively own clone-local pointers,
breadcrumbs, and stale-state cleanup. Python retains only session environment
parsing needed to address a process-owned run without consulting mutable
progress state.
"""

from __future__ import annotations

import contextlib
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Iterable, Mapping, Optional

__all__ = [
    "CURRENT_RUN_FILENAME",
    "PersistedRunResult",
    "validate_run_id",
    "resolve_owned_run_id",
    "resolve_persisted_repo_root",
    "resolve_persisted_run",
]

CURRENT_RUN_FILENAME: Final[str] = "current"
_RUN_ID_PATTERN: Final[re.Pattern[str]] = re.compile(r"[A-Za-z0-9._-]{1,128}")
_ENV_FILENAMES: Final[tuple[str, ...]] = ("source-env.sh", "session-env.sh")
_RUN_ID_PREFIXES: Final[tuple[str, ...]] = (
    "LARCH_RUN_ID=",
    "export LARCH_RUN_ID=",
)
_REPO_ROOT_PREFIXES: Final[tuple[str, ...]] = (
    "REPO_ROOT=",
    "export REPO_ROOT=",
)


@dataclass(frozen=True)
class PersistedRunResult:
    """Session-owned run identity recovered from persisted environment files."""

    run_id: str | None
    repo_root: Path | None


def validate_run_id(run_id: str) -> str:
    """Return a safe run ID, reserving ``current`` for the Rust pointer owner."""
    if not run_id:
        raise ValueError("run ID must be non-empty")
    if run_id in {".", "..", CURRENT_RUN_FILENAME}:
        raise ValueError(f"reserved run ID: {run_id}")
    if _RUN_ID_PATTERN.fullmatch(run_id) is None:
        raise ValueError("run ID must contain only letters, digits, dot, underscore, or dash")
    return run_id


def _parse_shell_value(raw: str, prefixes: Iterable[str]) -> str | None:
    """Extract the value of a shell assignment from a raw line."""
    line = raw.strip()
    if not line or line.startswith("#"):
        return None
    for prefix in prefixes:
        if line.startswith(prefix):
            value = line[len(prefix):].strip()
            # Strip one pair of matching quotes if present
            if len(value) >= 2 and value[0] == value[-1] in "\"'":
                value = value[1:-1]
            return value
    return None


def _read_env_files(session_dir: Path) -> dict[str, str | None]:
    """Read all environment files in the session directory and return a dict
    of variable names to their parsed values (or None if not found).
    """
    result: dict[str, str | None] = {
        "LARCH_RUN_ID": None,
        "REPO_ROOT": None,
    }
    for filename in _ENV_FILENAMES:
        path = session_dir / filename
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line in lines:
            # Run ID
            if result["LARCH_RUN_ID"] is None:
                val = _parse_shell_value(line, _RUN_ID_PREFIXES)
                if val is not None:
                    result["LARCH_RUN_ID"] = val
            # Repo root
            if result["REPO_ROOT"] is None:
                val = _parse_shell_value(line, _REPO_ROOT_PREFIXES)
                if val is not None:
                    # Only keep if it is an absolute existing directory
                    candidate = Path(val)
                    if candidate.is_absolute() and candidate.is_dir():
                        with contextlib.suppress(OSError):
                            result["REPO_ROOT"] = str(candidate.resolve())
            # Stop early if both are found
            if result["LARCH_RUN_ID"] is not None and result["REPO_ROOT"] is not None:
                break
    return result


def resolve_owned_run_id(
    *,
    explicit: str | None = None,
    tmpdir: str | Path | None = None,
    env: Mapping[str, str] | None = None,
) -> str | None:
    """Resolve a process-owned run ID without consulting the active pointer.

    The ID is resolved from (in order):
    1. The ``explicit`` argument.
    2. The ``LARCH_RUN_ID`` environment variable.
    3. The environment files found in ``tmpdir`` (if provided).
    The first valid value is returned; invalid values are skipped.
    """
    env_map = os.environ if env is None else env
    candidates = [value for value in (explicit, env_map.get("LARCH_RUN_ID")) if value]
    if tmpdir is not None:
        session_dir = Path(tmpdir)
        env_vars = _read_env_files(session_dir)
        if env_vars["LARCH_RUN_ID"] is not None:
            candidates.append(env_vars["LARCH_RUN_ID"])
    for candidate in candidates:
        with contextlib.suppress(ValueError):
            return validate_run_id(candidate)
    return None


def resolve_persisted_repo_root(*, tmpdir: str | Path) -> Path | None:
    """Resolve the persisted consumer root for a session-owned run."""
    session_dir = Path(tmpdir)
    env_vars = _read_env_files(session_dir)
    raw = env_vars.get("REPO_ROOT")
    if raw is not None:
        return Path(raw)
    return None


def resolve_persisted_run(
    *,
    tmpdir: str | Path,
    env: Mapping[str, str] | None = None,
) -> PersistedRunResult:
    """Resolve the persisted run ID and consumer root without mutable state.

    This reads the environment files only once, making it more efficient than
    calling the individual resolvers separately.
    """
    session_dir = Path(tmpdir)
    env_vars = _read_env_files(session_dir)

    # Resolve run ID using explicit, env, and the file data
    explicit = None  # no explicit here; we only use env and file
    env_map = os.environ if env is None else env
    candidates: list[str] = []
    if env_val := env_map.get("LARCH_RUN_ID"):
        candidates.append(env_val)
    if file_val := env_vars["LARCH_RUN_ID"]:
        candidates.append(file_val)
    run_id = None
    for candidate in candidates:
        with contextlib.suppress(ValueError):
            run_id = validate_run_id(candidate)
            break

    repo_root = None
    if raw := env_vars["REPO_ROOT"]:
        repo_root = Path(raw)

    return PersistedRunResult(run_id=run_id, repo_root=repo_root)
