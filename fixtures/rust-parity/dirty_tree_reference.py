#!/usr/bin/env python3
"""Frozen Python oracle for the #8060 dirty-tree baseline parity test.

This is test-only compatibility code.  Product dispatch no longer imports it.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys


def run_git(arguments: list[str], cwd: str) -> tuple[int, bytes]:
    completed = subprocess.run(
        ["git", *arguments],
        check=False,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    return completed.returncode, completed.stdout


def split_nul(value: bytes) -> set[bytes]:
    return {path for path in value.split(b"\0") if path}


def write_atomic(path: Path, data: bytes) -> None:
    temporary = path.with_name(f"{path.name}.tmp.{os.getpid()}")
    temporary.write_bytes(data)
    temporary.replace(path)


def render(
    status: str,
    *,
    baseline_state: str,
    reason: str = "",
    tracked_paths_file: str = "",
    new_untracked_paths_file: str = "",
) -> list[str]:
    lines = [
        f"STATUS={status}",
        "MODE=baseline",
        f"UNTRACKED_BASELINE={baseline_state}",
    ]
    if tracked_paths_file:
        lines.append(f"TRACKED_PATHS_FILE={tracked_paths_file}")
    if new_untracked_paths_file:
        lines.append(f"NEW_UNTRACKED_PATHS_FILE={new_untracked_paths_file}")
    if status != "clean" or reason:
        lines.append(f"REASON={reason or 'unknown'}")
    return lines


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="dirty-tree baseline")
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--sidecar", required=True)
    parser.add_argument("--cwd", required=True)
    args = parser.parse_args(argv)

    baseline = Path(args.baseline)
    sidecar = Path(args.sidecar)
    commands = [
        ["status", "--porcelain"],
        ["diff", "--name-only", "-z"],
        ["diff", "--name-only", "--cached", "-z"],
        ["ls-files", "--others", "--exclude-standard", "-z"],
    ]
    output: list[bytes] = []
    for command in commands:
        return_code, stdout = run_git(command, args.cwd)
        if return_code:
            raise RuntimeError(f"Git oracle failed for {command!r}")
        output.append(stdout)

    tracked = sorted(split_nul(output[1]) | split_nul(output[2]))
    current_untracked = split_nul(output[3])
    baseline_state = "present" if baseline.is_file() else "missing"
    tracked_paths_file = ""
    new_untracked_paths_file = ""
    if tracked:
        tracked_path = Path(f"{sidecar}.tracked-paths")
        write_atomic(tracked_path, b"\0".join(tracked) + b"\0")
        tracked_paths_file = str(tracked_path)
    if baseline_state == "missing" and current_untracked:
        lines = render(
            "unknown",
            baseline_state=baseline_state,
            reason="baseline-missing-untracked-ambiguous",
            tracked_paths_file=tracked_paths_file,
        )
    else:
        known = split_nul(baseline.read_bytes()) if baseline_state == "present" else set()
        new_untracked = sorted(current_untracked - known)
        if new_untracked:
            untracked_path = Path(f"{sidecar}.new-untracked-paths")
            write_atomic(untracked_path, b"\0".join(new_untracked) + b"\0")
            new_untracked_paths_file = str(untracked_path)
        lines = render(
            "dirty" if tracked or new_untracked else "clean",
            baseline_state=baseline_state,
            reason="working-tree-dirty" if tracked or new_untracked else "",
            tracked_paths_file=tracked_paths_file,
            new_untracked_paths_file=new_untracked_paths_file,
        )

    text = "\n".join(lines) + "\n"
    print(text, end="")
    write_atomic(sidecar, text.encode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
