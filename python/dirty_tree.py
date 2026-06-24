# pyright: reportUnusedCallResult=false
"""Dirty-tree detector and scope-marker helpers for larch orchestration."""

from __future__ import annotations

import argparse
import contextlib
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import issue_wire
import logging_util

_META_PATH_RE = re.compile(r"^[A-Za-z0-9./_-]+$")


def _valid_meta_path(value: str) -> bool:
    return bool(value) and _META_PATH_RE.fullmatch(value) is not None


def _run_bytes(argv: list[str], cwd: str | None = None) -> tuple[int, bytes]:
    try:
        completed = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False, cwd=cwd)
    except OSError:
        return 127, b""
    return completed.returncode, completed.stdout


def _write_atomic(path: Path, data: bytes) -> bool:
    tmp = path.with_name(path.name + f".tmp.{os.getpid()}")
    try:
        tmp.write_bytes(data)
        tmp.replace(path)
    except OSError:
        with contextlib.suppress(OSError):
            tmp.unlink()
        return False
    return True


def _split_nul(data: bytes) -> set[bytes]:
    return {part for part in data.split(b"\0") if part}


def _result_lines(
    *,
    status: str,
    mode: str,
    reason: str = "",
    baseline_state: str = "",
    tracked_paths_file: str = "",
    new_untracked_paths_file: str = "",
) -> list[str]:
    lines = [f"STATUS={status}", f"MODE={mode}"]
    if mode == "baseline":
        lines.append(f"UNTRACKED_BASELINE={baseline_state or 'missing'}")
    if tracked_paths_file:
        lines.append(f"TRACKED_PATHS_FILE={tracked_paths_file}")
    if new_untracked_paths_file:
        lines.append(f"NEW_UNTRACKED_PATHS_FILE={new_untracked_paths_file}")
    if status != "clean" or reason:
        lines.append(f"REASON={reason or 'unknown'}")
    return lines


def _publish(lines: list[str], sidecar: str = "") -> None:
    text = "\n".join(lines) + "\n"
    logging_util.emit(text.rstrip("\n"))
    if sidecar:
        _ = _write_atomic(Path(sidecar), text.encode())


def checkpoint(*, sidecar: str = "", cwd: str | None = None) -> list[str]:
    _ = sidecar
    rc, status = _run_bytes(["git", "status", "--porcelain"], cwd=cwd)
    if rc != 0:
        return _result_lines(status="unknown", mode="checkpoint", reason="git-status-failed")
    if status:
        return _result_lines(status="dirty", mode="checkpoint", reason="checkpoint-dirty")
    return _result_lines(status="clean", mode="checkpoint")


def baseline(*, baseline_path: str, sidecar: str = "", cwd: str | None = None) -> list[str]:
    if sidecar and not _valid_meta_path(sidecar):
        return _result_lines(
            status="unknown",
            mode="baseline",
            reason="bad-sidecar-path",
            baseline_state="missing",
        )
    if not _valid_meta_path(baseline_path):
        return _result_lines(
            status="unknown",
            mode="baseline",
            reason="bad-baseline-path",
            baseline_state="missing",
        )

    rc, _status = _run_bytes(["git", "status", "--porcelain"], cwd=cwd)
    if rc != 0:
        return _result_lines(status="unknown", mode="baseline", reason="git-status-failed", baseline_state="missing")
    rc, unstaged = _run_bytes(["git", "diff", "--name-only", "-z"], cwd=cwd)
    if rc != 0:
        return _result_lines(status="unknown", mode="baseline", reason="git-diff-failed", baseline_state="missing")
    rc, staged = _run_bytes(["git", "diff", "--name-only", "--cached", "-z"], cwd=cwd)
    if rc != 0:
        return _result_lines(status="unknown", mode="baseline", reason="git-diff-cached-failed", baseline_state="missing")
    rc, current_untracked = _run_bytes(["git", "ls-files", "--others", "--exclude-standard", "-z"], cwd=cwd)
    if rc != 0:
        return _result_lines(status="unknown", mode="baseline", reason="git-ls-files-failed", baseline_state="missing")

    tracked = sorted(_split_nul(unstaged) | _split_nul(staged))
    current_untracked_set = _split_nul(current_untracked)
    baseline_file = Path(baseline_path)
    baseline_state = "present" if baseline_file.is_file() else "missing"
    prefix = sidecar or str(Path(tempfile.gettempdir()) / f"larch-mid-run-dirty-tree.{os.getpid()}")
    tracked_paths_file = ""
    if tracked:
        tracked_paths_file = prefix + ".tracked-paths"
        if not _write_atomic(Path(tracked_paths_file), b"\0".join(tracked) + b"\0"):
            return _result_lines(
                status="unknown",
                mode="baseline",
                reason="tracked-paths-write-failed",
                baseline_state=baseline_state,
            )
    new_untracked: list[bytes] = []
    if baseline_state == "present":
        try:
            baseline_set = _split_nul(baseline_file.read_bytes())
        except OSError:
            return _result_lines(
                status="unknown",
                mode="baseline",
                reason="baseline-sort-failed",
                baseline_state=baseline_state,
            )
        new_untracked = sorted(current_untracked_set - baseline_set)
    elif current_untracked_set:
        return _result_lines(
            status="unknown",
            mode="baseline",
            reason="baseline-missing-untracked-ambiguous",
            baseline_state=baseline_state,
            tracked_paths_file=tracked_paths_file,
        )

    new_untracked_paths_file = ""
    if new_untracked:
        new_untracked_paths_file = prefix + ".new-untracked-paths"
        if not _write_atomic(Path(new_untracked_paths_file), b"\0".join(new_untracked) + b"\0"):
            return _result_lines(
                status="unknown",
                mode="baseline",
                reason="new-untracked-paths-write-failed",
                baseline_state=baseline_state,
            )
    if tracked_paths_file or new_untracked_paths_file:
        return _result_lines(
            status="dirty",
            mode="baseline",
            reason="working-tree-dirty",
            baseline_state=baseline_state,
            tracked_paths_file=tracked_paths_file,
            new_untracked_paths_file=new_untracked_paths_file,
        )
    return _result_lines(status="clean", mode="baseline", baseline_state=baseline_state)


def baseline_main(argv: list[str]) -> int:
    os.environ["LARCH_QUIET_DISABLE"] = "1"
    parser = argparse.ArgumentParser(prog="dirty-tree baseline")
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--sidecar", default="")
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        _publish(_result_lines(status="unknown", mode="baseline", reason="argv-error", baseline_state="missing"))
        return 0
    lines = baseline(baseline_path=args.baseline, sidecar=args.sidecar)
    _publish(lines, args.sidecar if _valid_meta_path(args.sidecar) else "")
    return 0


def checkpoint_main(argv: list[str]) -> int:
    os.environ["LARCH_QUIET_DISABLE"] = "1"
    parser = argparse.ArgumentParser(prog="dirty-tree checkpoint")
    parser.add_argument("--sidecar", default="")
    parser.add_argument("--cwd", default="")
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        _publish(_result_lines(status="unknown", mode="checkpoint", reason="argv-error"))
        return 0
    # Run git in the consumer repo, not the process CWD. When larch runs from the
    # plugin cache (not a git repo), an unset cwd makes `git status` exit non-zero
    # and map to STATUS=unknown, which callers treat as dirty (issue #4509).
    # Precedence: explicit --cwd, then the LARCH_CONSUMER_REPO env var, then unset.
    cwd = args.cwd or os.environ.get("LARCH_CONSUMER_REPO", "")
    lines = checkpoint(sidecar=args.sidecar, cwd=cwd or None)
    _publish(lines, args.sidecar if _valid_meta_path(args.sidecar) else "")
    return 0


def scope_check_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="dirty-tree scope-check", add_help=True)
    parser.add_argument("--plan-file", required=True)
    parser.add_argument("--paths-file", required=True)
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 2 if int(exc.code or 0) != 0 else 0
    plan = Path(args.plan_file)
    paths = Path(args.paths_file)
    if not plan.is_file():
        print(f"dirty-tree scope-check: plan file not found: {args.plan_file}", file=sys.stderr)
        return 2
    if not paths.is_file():
        print(f"dirty-tree scope-check: recovery paths file not found: {args.paths_file}", file=sys.stderr)
        return 2
    try:
        scope = set(issue_wire.extract_scope_paths(plan_text=plan.read_text(encoding="utf-8", errors="replace")))
        candidates = [p.decode("utf-8", "surrogateescape") for p in paths.read_bytes().split(b"\0") if p]
    except OSError as exc:
        print(f"dirty-tree scope-check: {exc}", file=sys.stderr)
        return 2
    out_of_scope = [p for p in candidates if p not in scope]
    if out_of_scope:
        for item in out_of_scope:
            print(item, file=sys.stderr)
        return 1
    return 0


def _strip_code(text: str) -> str:
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    return re.sub(r"`[^`\n]*`", "", text)


def _norm_candidate(text: str) -> str:
    value = " ".join(_strip_code(text).strip().split())
    return re.sub(r"^\[(?:important|nit|latent)\]\s*", "", value, flags=re.IGNORECASE)


def has_scope_reduction_marker(text: str) -> bool:
    body = _strip_code(text)
    for line in body.splitlines():
        stripped = line.strip()
        match = re.match(r"^###\s+FINDING_[0-9]+:\s*(.*)$", stripped, re.IGNORECASE)
        if match and re.match(r"^\[SCOPE-REDUCTION\]", _norm_candidate(match.group(1))):
            return True
        match = re.match(r"^-?\s*(?:\*\*)?Concern(?:\*\*)?:\s*(.*)$", stripped, re.IGNORECASE)
        if match and re.match(r"^\[SCOPE-REDUCTION\]", _norm_candidate(match.group(1))):
            return True
        match = re.match(r"^\s*what:\s*(.*)$", stripped, re.IGNORECASE)
        if match and re.match(r"^\[SCOPE-REDUCTION\]", _norm_candidate(match.group(1))):
            return True
    return False


def scope_marker_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="dirty-tree scope-marker", add_help=True)
    parser.add_argument("--file", default="-")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 2 if int(exc.code or 0) != 0 else 0
    try:
        if args.file in {"", "-"}:
            text = sys.stdin.read()
        else:
            text = Path(args.file).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return 1
    return 0 if has_scope_reduction_marker(text) else 1


if __name__ == "__main__":
    raise SystemExit(checkpoint_main(sys.argv[1:]))
