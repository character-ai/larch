"""Fail-silent Claude Code statusline renderer for larch progress breadcrumbs."""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, cast

from larch.bgjob import registry
from larch.report import progress_file

YELLOW = "\033[33m"
RESET = "\033[0m"
DEFAULT_STALE_AFTER_S = 300
DEFAULT_HIDE_AFTER_S = 3600
MAX_LINES = 3


def _positive_int(raw: str | None, *, default: int, max_value: int | None = None) -> int:
    value = int(raw) if raw and raw.isdigit() and int(raw) > 0 else default
    if max_value is not None:
        value = min(value, max_value)
    return value


def _read_statusline_payload(text: str) -> dict[str, Any]:
    try:
        parsed = json.loads(text or "{}")
    except json.JSONDecodeError:
        return {}
    if isinstance(parsed, dict):
        return cast("dict[str, Any]", parsed)
    return {}


def _repo_from_payload(payload: dict[str, Any]) -> Path | None:
    workspace = payload.get("workspace")
    workspace_map = cast("dict[str, Any]", workspace) if isinstance(workspace, dict) else {}
    current_dir = workspace_map.get("current_dir")
    cwd = payload.get("cwd")
    raw = current_dir if isinstance(current_dir, str) and current_dir else cwd if isinstance(cwd, str) else os.environ.get("PWD", "")
    if not raw:
        return None
    path = Path(raw).expanduser()
    if not path.is_absolute():
        return None
    try:
        return path.resolve()
    except OSError:
        return path


def _tail_breadcrumbs(path: Path, *, count: int) -> list[str]:
    if path.is_symlink() or not path.is_file():
        return []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    clean = [line for line in lines if line.startswith("[") and "] " in line and "\t" not in line]
    return clean[-count:]


def _clone_has_live_bgjob(repo_root: Path) -> bool:
    with contextlib.suppress(Exception):
        repo_real = repo_root.resolve()
        for _path, entry in registry.iter_entries():
            if entry is None:
                continue
            with contextlib.suppress(OSError):
                if entry.clone_path.resolve() != repo_real:
                    continue
                if registry.child_liveness(entry).live:
                    return True
    return False


def _age_suffix(*, path: Path, repo_root: Path, now: float, stale_after_s: int, hide_after_s: int) -> str | None:
    try:
        age_s = max(0, int(now - path.stat().st_mtime))
    except OSError:
        return None
    if age_s < stale_after_s:
        return ""
    if _clone_has_live_bgjob(repo_root):
        return ""
    if age_s >= hide_after_s:
        return None
    age_min = max(1, age_s // 60)
    return f" (stale {age_min}m)"


def _truncate(text: str, *, columns: int) -> str:
    if columns <= 0 or len(text) <= columns:
        return text
    if columns <= 1:
        return text[:columns]
    return text[: columns - 1] + "…"


def render_statusline(*, stdin_text: str, env: dict[str, str] | None = None) -> str:
    env_map = os.environ if env is None else env
    payload = _read_statusline_payload(stdin_text)
    repo_root = _repo_from_payload(payload)
    if repo_root is None:
        return ""
    line_count = _positive_int(env_map.get("LARCH_STATUSLINE_LINES"), default=1, max_value=MAX_LINES)
    path = progress_file.progress_path(repo_root)
    rows = _tail_breadcrumbs(path, count=line_count)
    if not rows:
        return ""
    now = float(env_map.get("LARCH_TEST_STATUSLINE_NOW", "") or time.time())
    suffix = _age_suffix(
        path=path,
        repo_root=repo_root,
        now=now,
        stale_after_s=_positive_int(env_map.get("LARCH_STATUSLINE_STALE_AFTER_S"), default=DEFAULT_STALE_AFTER_S),
        hide_after_s=_positive_int(env_map.get("LARCH_STATUSLINE_HIDE_AFTER_S"), default=DEFAULT_HIDE_AFTER_S),
    )
    if suffix is None:
        return ""
    stamp = time.strftime("%H:%M", time.localtime(now))
    text_rows = [f"larch {stamp}: {row}{suffix}" for row in rows]
    rendered = "\n".join(text_rows)
    columns = _positive_int(env_map.get("COLUMNS"), default=0)
    if columns:
        rendered = "\n".join(_truncate(row, columns=columns) for row in rendered.splitlines())
    return f"{YELLOW}{rendered}{RESET}\n"


def statusline_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py progress statusline", add_help=True)
    try:
        _ = parser.parse_args(argv)
        text = sys.stdin.read()
        rendered = render_statusline(stdin_text=text)
        if rendered:
            _ = sys.stdout.write(rendered)
    except Exception:  # pylint: disable=broad-except
        return 0
    return 0
