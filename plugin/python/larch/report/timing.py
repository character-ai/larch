"""Read-only timing-ledger compatibility helpers.

The Rust ``timing`` commands exclusively own ledger mutation, validation,
locking, and row construction. Python retains this bounded resolver solely for
review code that needs to locate an already-owned ledger before deciding
whether a diagnostic span is applicable.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path


_LEDGER_BASENAME = "timing-ledger.tsv"


def _allowed_roots(*, env: Mapping[str, str]) -> list[Path]:
    roots: list[Path] = []
    candidates = [
        Path(env.get("TMPDIR") or "/tmp"),  # noqa: S108 - matches Rust's trusted system fallback.
        Path("/private/tmp"),
    ]
    for key in ("IMPLEMENT_TMPDIR", "DESIGN_TMPDIR", "REVIEW_TMPDIR"):
        raw = env.get(key, "")
        if raw:
            candidates.append(Path(raw))
    session = env.get("SESSION_ENV_PATH", "")
    if session:
        candidates.append(Path(session).parent)
    for candidate in candidates:
        if not candidate.is_dir():
            continue
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        if resolved not in roots:
            roots.append(resolved)
    return roots


def _under_allowed_root(*, path: Path, roots: list[Path]) -> bool:
    try:
        resolved = path.resolve(strict=False)
    except OSError:
        return False
    return any(resolved == root or root in resolved.parents for root in roots)


def _validate_ledger_path(*, raw: str, env: Mapping[str, str]) -> Path:
    candidate = Path(raw)
    if not raw or ".." in candidate.parts:
        msg = f"ledger path must not be empty or contain '..': {raw}"
        raise ValueError(msg)
    roots = _allowed_roots(env=env)
    default_root = roots[0] if roots else Path("/tmp").resolve()  # noqa: S108 - matches Rust's trusted system fallback.
    if not candidate.is_absolute():
        candidate = default_root / candidate
    if not _under_allowed_root(path=candidate, roots=roots):
        msg = f"ledger path not under an allowed root: {raw}"
        raise ValueError(msg)
    if candidate.is_symlink():
        msg = f"ledger is a symlink: {candidate}"
        raise ValueError(msg)
    if candidate.exists() and not candidate.is_file():
        msg = f"ledger exists but is not a regular file: {candidate}"
        raise ValueError(msg)
    return candidate.resolve(strict=False)


def resolve_timing_ledger_path(
    *,
    ledger: str | None = None,
    env: Mapping[str, str] | None = None,
) -> Path | None:
    """Resolve a safe timing-ledger location without creating or changing it."""
    env_map = os.environ if env is None else env
    if ledger:
        return _validate_ledger_path(raw=ledger, env=env_map)
    declared = env_map.get("LARCH_TIMING_LEDGER", "")
    if declared:
        try:
            return _validate_ledger_path(raw=declared, env=env_map)
        except ValueError:
            pass
    for key in ("IMPLEMENT_TMPDIR", "SESSION_ENV_PATH", "DESIGN_TMPDIR", "REVIEW_TMPDIR"):
        raw = env_map.get(key, "")
        candidate = Path(raw).parent if key == "SESSION_ENV_PATH" and raw else Path(raw)
        if raw and candidate.is_dir():
            try:
                return candidate.resolve() / _LEDGER_BASENAME
            except OSError:
                continue
    return None
