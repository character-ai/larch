"""Install the larch progress statusline into clone-local Claude settings."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import sys
from pathlib import Path
from typing import Any, cast

from larch import io as larch_io

LOCAL_SETTINGS = Path(".claude") / "settings.local.json"
LARCH_COMMAND_MARKER = ".cache/larch/statusline.sh"


def _launcher_path() -> Path:
    return Path.home() / ".cache" / "larch" / "statusline.sh"


def _notice_sentinel() -> Path:
    return Path.home() / ".cache" / "larch" / ".statusline-install-notice"


def _payload_repo_root(stdin_text: str) -> str:
    try:
        parsed = json.loads(stdin_text or "{}")
    except json.JSONDecodeError:
        return ""
    if not isinstance(parsed, dict):
        return ""
    payload = cast("dict[str, Any]", parsed)
    workspace = payload.get("workspace")
    workspace_map = cast("dict[str, Any]", workspace) if isinstance(workspace, dict) else {}
    current_dir = workspace_map.get("current_dir")
    if isinstance(current_dir, str):
        return current_dir
    cwd = payload.get("cwd")
    return cwd if isinstance(cwd, str) else ""


def _read_json_object(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return {}
    if path.is_symlink() or not path.is_file():
        return None
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(parsed, dict):
        return None
    return cast("dict[str, Any]", parsed)


def _statusline_command(settings: dict[str, Any]) -> str:
    status = settings.get("statusLine")
    status_map = cast("dict[str, Any]", status) if isinstance(status, dict) else {}
    command = status_map.get("command")
    return command if isinstance(command, str) else ""


def _read_user_statusline() -> str:
    settings = _read_json_object(Path.home() / ".claude" / "settings.json")
    if settings is None:
        return ""
    command = _statusline_command(settings)
    if "\n" in command or "\r" in command:
        return ""
    if LARCH_COMMAND_MARKER in command or "progress statusline" in command:
        return ""
    return command


def _launcher_text(*, plugin_root: Path, user_command: str) -> str:
    quoted_user = shlex.quote(user_command)
    return (
        "#!/usr/bin/env bash\n"
        "set -uo pipefail\n"
        "INPUT=$(cat 2>/dev/null || true)\n"
        f"USER_STATUSLINE_CMD={quoted_user}\n"
        'if [ -n "$USER_STATUSLINE_CMD" ] && command -v python3 >/dev/null 2>&1; then\n'
        "  STATUSLINE_INPUT=\"$INPUT\" python3 - \"$USER_STATUSLINE_CMD\" <<'PY' 2>/dev/null || true\n"
        'import os\n'
        'import subprocess\n'
        'import sys\n'
        'cmd = sys.argv[1]\n'
        'if cmd:\n'
        '    subprocess.run(["bash", "-lc", cmd], input=os.environ.get("STATUSLINE_INPUT", ""), text=True, timeout=1, check=False)\n'
        'PY\n'
        'fi\n'
        "if command -v python3 >/dev/null 2>&1; then\n"
        f"  printf '%s' \"$INPUT\" | python3 {shlex.quote(str(plugin_root / 'python' / 'cli.py'))} progress statusline 2>/dev/null || true\n"
        "fi\n"
    )


def _safe_existing_file(path: Path) -> bool:
    return not path.exists() or (path.is_file() and not path.is_symlink())


def install_statusline(*, repo_root: Path, plugin_root: Path, notice: bool = False) -> bool:
    if os.environ.get("LARCH_STATUSLINE_DISABLE") == "1":
        return False
    try:
        repo = repo_root.expanduser().resolve()
        plugin = plugin_root.expanduser().resolve()
        settings_path = repo / LOCAL_SETTINGS
        larch_io.assert_no_symlink_path_or_ancestors(settings_path)
        launcher = _launcher_path()
        notice_sentinel = _notice_sentinel()
        larch_io.assert_no_symlink_path_or_ancestors(launcher)
        if not _safe_existing_file(settings_path) or not _safe_existing_file(launcher):
            return False
        user_command = _read_user_statusline()
        larch_io.atomic_write(
            path=launcher,
            text=_launcher_text(plugin_root=plugin, user_command=user_command),
            nofollow=True,
            mode=0o755,
        )
        settings = _read_json_object(settings_path)
        if settings is None:
            return False
        current = _statusline_command(settings)
        if current and LARCH_COMMAND_MARKER not in current and "progress statusline" not in current:
            return False
        first_install = not current
        settings["statusLine"] = {"type": "command", "command": str(launcher), "refreshInterval": 2}
        rendered = json.dumps(settings, indent=2, sort_keys=True) + "\n"
        larch_io.atomic_write(path=settings_path, text=rendered, nofollow=True, mode=0o600)
        if notice and first_install and not notice_sentinel.exists():
            larch_io.atomic_write(path=notice_sentinel, text="installed\n", nofollow=True, mode=0o600)
            print("larch: installed progress statusline (set LARCH_STATUSLINE_DISABLE=1 to opt out)")
        return True
    except (OSError, TypeError, ValueError):
        return False


def install_statusline_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py progress install-statusline")
    _ = parser.add_argument("--plugin-root", default=os.environ.get("CLAUDE_PLUGIN_ROOT", ""))
    _ = parser.add_argument("--repo-root", default="")
    _ = parser.add_argument("--notice", action="store_true")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 2
    if os.environ.get("LARCH_STATUSLINE_DISABLE") == "1":
        return 0
    stdin_text = sys.stdin.read()
    repo_raw = args.repo_root or _payload_repo_root(stdin_text)
    plugin_raw = args.plugin_root or os.environ.get("CLAUDE_PLUGIN_ROOT", "")
    if not repo_raw or not plugin_raw:
        return 0
    _ = install_statusline(repo_root=Path(repo_raw), plugin_root=Path(plugin_raw), notice=args.notice)
    return 0
