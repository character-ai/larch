"""Python CLI entrypoint for committed /design run-log publishing."""

from __future__ import annotations

import contextlib
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from collections.abc import Sequence


def _emit(k: str, v: str) -> None:
    print(f"{k}={v}")


def _validate_repo(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9._-]+/[A-Za-z0-9._-]+", value))


def _validate_slug(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9._-]+", value))


def _persist_metadata(design_tmpdir: Path, pr_number: str, pr_url: str, recovery_branch: str) -> None:
    with contextlib.suppress(OSError):
        _ = (design_tmpdir / ".design-log-publish-metadata.env").write_text(
            f"DESIGN_LOG_PR_NUMBER={pr_number}\nDESIGN_LOG_PR_URL={pr_url}\nDESIGN_LOG_RECOVERY_BRANCH={recovery_branch}\n",
            encoding="utf-8",
        )


def _copy_tree_redacted(plugin_root: Path, source: Path, dest: Path) -> bool:
    if source.is_symlink():
        return False
    if source.is_file():
        dest.parent.mkdir(parents=True, exist_ok=True)
        red = subprocess.run(
            [sys.executable, str(plugin_root / "python" / "cli.py"), "redact", "tmpdir-paths"],
            input=source.read_text(encoding="utf-8", errors="replace"),
            text=True,
            capture_output=True,
            check=False,
        )
        if red.returncode != 0:
            return False
        sec = subprocess.run(
            [sys.executable, str(plugin_root / "python" / "cli.py"), "redact", "secrets"],
            input=red.stdout,
            text=True,
            capture_output=True,
            check=False,
        )
        if sec.returncode != 0:
            return False
        _ = dest.write_text(sec.stdout, encoding="utf-8")
        return True
    if source.is_dir():
        for child in source.iterdir():
            if child.is_symlink():
                continue
            if not _copy_tree_redacted(plugin_root, child, dest / child.name):
                return False
        return True
    return True


def log_publish_main(argv: Sequence[str]) -> int:
    args = list(argv)
    parsed = {"--design-tmpdir": "", "--run-id": "", "--issue": "", "--repo": "", "--reason": "final"}
    dry_run = False
    i = 0
    while i < len(args):
        token = args[i]
        if token in parsed:
            if i + 1 >= len(args):
                return 1
            parsed[token] = args[i + 1]
            i += 2
            continue
        if token == "--dry-run":
            dry_run = True
            i += 1
            continue
        if token in {"-h", "--help"}:
            return 0
        return 1
    if not parsed["--design-tmpdir"] or not parsed["--run-id"] or not parsed["--issue"]:
        return 1
    design_tmpdir = Path(parsed["--design-tmpdir"])
    if not design_tmpdir.is_dir():
        _emit("PUBLISH_OK", "false")
        _emit("PR_NUMBER", "")
        _emit("PR_URL", "")
        return 0
    if not parsed["--issue"].isdigit() or parsed["--issue"] == "0":
        _emit("PUBLISH_OK", "false")
        _emit("PR_NUMBER", "")
        _emit("PR_URL", "")
        return 0
    if not _validate_slug(parsed["--run-id"]):
        _emit("PUBLISH_OK", "false")
        _emit("PR_NUMBER", "")
        _emit("PR_URL", "")
        return 0
    if parsed["--repo"] and not _validate_repo(parsed["--repo"]):
        return 1
    if parsed["--reason"] not in {"final", "pause"}:
        _emit("PUBLISH_OK", "false")
        _emit("PR_NUMBER", "")
        _emit("PR_URL", "")
        return 0

    if dry_run:
        for cmd in ("git", "gh"):
            if shutil.which(cmd) is None:
                _emit("PUBLISH_OK", "false")
                _emit("PR_NUMBER", "")
                _emit("PR_URL", "")
                return 0
        repo_root = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=False).stdout.strip()  # noqa: S607
        if not repo_root:
            _emit("PUBLISH_OK", "false")
            _emit("PR_NUMBER", "")
            _emit("PR_URL", "")
            return 0
        _persist_metadata(design_tmpdir, "", "", "")
        _emit("PUBLISH_OK", "true")
        _emit("PR_NUMBER", "")
        _emit("PR_URL", "")
        return 0

    plugin_root = Path(os.environ.get("CLAUDE_PLUGIN_ROOT", Path(__file__).resolve().parents[1]))
    repo_root = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=False).stdout.strip()  # noqa: S607
    if not repo_root:
        _emit("PUBLISH_OK", "false")
        _emit("PR_NUMBER", "")
        _emit("PR_URL", "")
        return 0
    run_dest = Path(repo_root) / "larch-logs" / "design" / parsed["--run-id"]
    run_dest.mkdir(parents=True, exist_ok=True)
    init = subprocess.run(
        [
            sys.executable,
            str(plugin_root / "python" / "cli.py"),
            "run-log",
            "init",
            "--log-root",
            str(Path(repo_root) / "larch-logs"),
            "--skill",
            "design",
            "--run-id",
            parsed["--run-id"],
            "--issue",
            parsed["--issue"],
        ],
        check=False,
    )
    if init.returncode != 0:
        _emit("PUBLISH_OK", "false")
        _emit("PR_NUMBER", "")
        _emit("PR_URL", "")
        return 0

    for child in design_tmpdir.iterdir():
        if child.name == ".design-log-publish-metadata.env":
            continue
        if not _copy_tree_redacted(plugin_root, child, run_dest / child.name):
            _emit("PUBLISH_OK", "false")
            _emit("PR_NUMBER", "")
            _emit("PR_URL", "")
            return 0

    _persist_metadata(design_tmpdir, "", "", "")
    _emit("PUBLISH_OK", "true")
    _emit("PR_NUMBER", "")
    _emit("PR_URL", "")
    return 0
