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
from typing import Final


CURRENT_RUN_FILENAME = "current"
_RUN_ID_PATTERN: Final[re.Pattern[str]] = re.compile(r"[A-Za-z0-9._-]{1,128}")


@dataclass(frozen=True)
class PersistedRunResult:
    """Session-owned run identity recovered from persisted environment files."""

    run_id: str | None
    repo_root: Path | None


def validate_run_id(run_id: str) -> str:
    """Return a safe run ID, reserving ``current`` for the Rust pointer owner."""
    if not run_id:
        msg = "run ID must be non-empty"
        raise ValueError(msg)
    if run_id in {".", "..", CURRENT_RUN_FILENAME}:
        msg = f"reserved run ID: {run_id}"
        raise ValueError(msg)
    if _RUN_ID_PATTERN.fullmatch(run_id) is None:
        msg = "run ID must contain only letters, digits, dot, underscore, or dash"
        raise ValueError(msg)
    return run_id


def _persisted_run_id_candidates(tmpdir: str | Path) -> list[str]:
    candidates: list[str] = []
    root = Path(tmpdir)
    for path in (root / "session-env.sh", root / "source-env.sh"):
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        candidates.extend(
            raw[len(prefix):].strip().strip("'\"")
            for raw in lines
            for prefix in ("LARCH_RUN_ID=", "export LARCH_RUN_ID=")
            if raw.startswith(prefix)
        )
    return candidates


def resolve_owned_run_id(
    *,
    explicit: str | None = None,
    tmpdir: str | Path | None = None,
    env: dict[str, str] | None = None,
) -> str | None:
    """Resolve a process-owned run ID without consulting the active pointer."""
    env_map = os.environ if env is None else env
    candidates = [value for value in (explicit, env_map.get("LARCH_RUN_ID")) if value]
    if tmpdir is not None:
        candidates.extend(_persisted_run_id_candidates(tmpdir))
    for candidate in candidates:
        with contextlib.suppress(ValueError):
            return validate_run_id(candidate)
    return None


def resolve_persisted_repo_root(*, tmpdir: str | Path) -> Path | None:
    """Resolve the persisted consumer root for a session-owned run."""
    root = Path(tmpdir)
    for path in (root / "source-env.sh", root / "session-env.sh"):
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for raw in lines:
            for prefix in ("REPO_ROOT=", "export REPO_ROOT="):
                if raw.startswith(prefix):
                    candidate = Path(raw[len(prefix):].strip().strip("'\""))
                    if candidate.is_absolute() and candidate.is_dir():
                        with contextlib.suppress(OSError):
                            return candidate.resolve()
    return None


def resolve_persisted_run(
    *,
    tmpdir: str | Path,
    env: dict[str, str] | None = None,
) -> PersistedRunResult:
    """Resolve the persisted run ID and consumer root without mutable state."""
    return PersistedRunResult(
        run_id=resolve_owned_run_id(tmpdir=tmpdir, env=env),
        repo_root=resolve_persisted_repo_root(tmpdir=tmpdir),
    )
