"""Python replacement for python3 python/cli.py verify skill-called."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import git
from larch.core import proc


def _emit(*, verified: bool, reason: str) -> int:
    print(f"VERIFIED={'true' if verified else 'false'}")
    print(f"REASON={reason}")
    return 0


def _usage() -> None:
    print(
        "Usage: verify skill-called "
        "(--sentinel-file PATH | --stdout-line RE --stdout-file PATH | "
        "--commit-delta N --before-count N)",
        file=sys.stderr,
    )


def _parse(argv: list[str]) -> dict[str, str] | None:
    parsed: dict[str, str] = {}
    idx = 0
    while idx < len(argv):
        arg = argv[idx]
        if arg in {
            "--sentinel-file",
            "--stdout-line",
            "--stdout-file",
            "--commit-delta",
            "--before-count",
        }:
            if idx + 1 >= len(argv):
                _usage()
                return None
            parsed[arg] = argv[idx + 1]
            idx += 2
        elif arg in {"-h", "--help"}:
            _usage()
            return {}
        else:
            print(f"ERROR: Unknown argument: {arg}", file=sys.stderr)
            _usage()
            return None
    return parsed


def _mode(parsed: dict[str, str]) -> str | None:
    modes = [
        "--sentinel-file" in parsed,
        "--stdout-line" in parsed or "--stdout-file" in parsed,
        "--commit-delta" in parsed or "--before-count" in parsed,
    ]
    if sum(1 for item in modes if item) != 1:
        print("ERROR: pass exactly one verification mode", file=sys.stderr)
        return None
    if modes[0]:
        return "sentinel"
    if modes[1]:
        return "stdout"
    return "commit"


def _nonnegative(text: str) -> int | None:
    return int(text) if re.fullmatch(r"[0-9]+", text or "") else None


def main(argv: list[str]) -> int:
    parsed = _parse(argv)
    if parsed is None:
        return 1
    if parsed == {} and any(arg in {"-h", "--help"} for arg in argv):
        return 0
    mode = _mode(parsed)
    if mode is None:
        return 1
    if mode == "sentinel":
        raw = parsed.get("--sentinel-file", "")
        if not raw:
            print("ERROR: --sentinel-file requires a non-empty path", file=sys.stderr)
            return 1
        path = Path(raw)
        if not path.exists():
            return _emit(verified=False, reason="missing_path")
        if not path.is_file():
            return _emit(verified=False, reason="not_regular_file")
        if path.stat().st_size == 0:
            return _emit(verified=False, reason="empty_file")
        return _emit(verified=True, reason="ok")
    if mode == "stdout":
        regex = parsed.get("--stdout-line", "")
        stdout_file = parsed.get("--stdout-file", "")
        if not regex:
            print(
                "ERROR: --stdout-line requires a non-empty regex "
                "(empty would match any non-empty line)",
                file=sys.stderr,
            )
            return 1
        if not stdout_file:
            print("ERROR: --stdout-line requires --stdout-file", file=sys.stderr)
            return 1
        path = Path(stdout_file)
        if not path.is_file():
            return _emit(verified=False, reason="missing_stdout_file")
        result = subprocess.run(
            ["grep", "-E", "-q", "--", regex, str(path)],  # noqa: S607
            env={"LC_ALL": "C"},
            check=False,
        )
        if result.returncode == 0:
            return _emit(verified=True, reason="ok")
        if result.returncode == 1:
            return _emit(verified=False, reason="no_match")
        print(
            f"ERROR: grep failed (exit {result.returncode}) "
            "— regex may be malformed or file unreadable",
            file=sys.stderr,
        )
        return 1
    expected = _nonnegative(parsed.get("--commit-delta", ""))
    before = _nonnegative(parsed.get("--before-count", ""))
    if expected is None:
        print("ERROR: --commit-delta value must be a non-negative integer", file=sys.stderr)
        return 1
    if before is None:
        print("ERROR: --before-count value must be a non-negative integer", file=sys.stderr)
        return 1
    result = git.count_commits(proc)
    if result.status != "ok":
        return _emit(verified=False, reason=result.status)
    delta = result.count - before
    return _emit(
        verified=delta == expected,
        reason="ok" if delta == expected else "commit_delta_mismatch",
    )
