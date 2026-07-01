"""Shared safe helpers for committed larch run-log corpus walks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast
from collections.abc import Callable

from larch.report.report_tokens_models import safe_int


def _warn(warn: Callable[[str], None] | None, message: str) -> None:
    if warn is not None:
        warn(message)


def load_run_manifest(run_dir: Path, warn: Callable[[str], None] | None = None) -> dict[str, Any] | None:
    """Return an accepted run manifest, or ``None`` after optional warnings."""
    manifest_path = run_dir / "manifest.json"
    parsed: object | None = None
    message = ""
    if manifest_path.is_symlink():
        message = f"manifest.json at {manifest_path} is a symlink; skipping"
    elif not manifest_path.is_file():
        message = f"manifest for {run_dir} is missing; skipping"
    else:
        try:
            parsed = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            message = f"invalid manifest.json at {manifest_path}: {exc}; skipping"
    if message:
        _warn(warn, message)
        return None
    if not isinstance(parsed, dict):
        _warn(warn, f"manifest for {run_dir} is not a JSON object; skipping")
        return None
    manifest = cast("dict[str, object]", parsed)
    accepted = bool(manifest) and safe_int(value=manifest.get("issue_number")) > 0
    if accepted:
        return {str(key): value for key, value in manifest.items()}
    if not manifest:
        _warn(warn, f"manifest for {run_dir} is empty and lacks numeric issue_number; skipping")
    else:
        _warn(warn, f"manifest for {run_dir} lacks numeric issue_number; skipping")
    return None


def is_valid_run_dir(run_dir: Path, warn: Callable[[str], None] | None = None) -> bool:
    """Return True when ``run_dir`` has an accepted run manifest."""
    return load_run_manifest(run_dir, warn=warn) is not None


def run_dirs(log_base: Path, warn: Callable[[str], None] | None = None) -> list[Path]:
    """Return symlink-safe, manifest-accepted child run directories."""
    dirs: list[Path] = []
    try:
        resolved_base = log_base.resolve(strict=True)
    except OSError as exc:
        _warn(warn, f"log root {log_base} is missing or unreadable: {exc}; no run logs scanned")
        return []
    for path in sorted(log_base.glob("*")):
        if path.is_symlink():
            _warn(warn, f"run directory {path} is a symlink; skipping")
            continue
        if not path.is_dir():
            continue
        try:
            resolved = path.resolve(strict=True)
        except OSError as exc:
            _warn(warn, f"could not resolve run directory {path}: {exc}; skipping")
            continue
        if not (resolved == resolved_base or resolved_base in resolved.parents):
            _warn(warn, f"run directory {path} resolves outside {log_base}; skipping")
            continue
        if not is_valid_run_dir(path, warn=warn):
            continue
        dirs.append(path)
    return dirs


def safe_transcript_path(run_dir: Path) -> Path | None:
    """Return a contained regular session transcript path for an accepted run."""
    transcript = run_dir / "session-transcript.jsonl"
    if transcript.is_symlink() or not transcript.is_file():
        return None
    try:
        resolved_run = run_dir.resolve(strict=True)
        resolved_transcript = transcript.resolve(strict=True)
    except OSError:
        return None
    if resolved_transcript == resolved_run or resolved_run in resolved_transcript.parents:
        return transcript
    return None
