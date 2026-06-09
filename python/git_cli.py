# pyright: reportUnusedCallResult=false
"""Thin CLI entrypoints for git helper primitives."""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

import git
import logging_util
import phantom
import proc


def _emit_kv(key: str, value: object) -> None:
    logging_util.emit_kv(key, str(value))


def _parse(parser: argparse.ArgumentParser, argv: list[str]) -> argparse.Namespace | None:
    try:
        return parser.parse_args(argv)
    except SystemExit:
        return None


def commit_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py git commit", add_help=True)
    parser.add_argument("-m", dest="message", default="")
    parser.add_argument("--no-trailer", action="store_true")
    parser.add_argument("--only", action="store_true")
    parser.add_argument("--pathspec-from-file", default=None)
    parser.add_argument("--pathspec-file-nul", action="store_true")
    parser.add_argument("files", nargs="*")
    args = _parse(parser, argv)
    if args is None:
        return 1
    if not args.message.strip():
        print("git-commit.sh: commit message must be non-empty", file=sys.stderr)
        return 1
    if args.pathspec_from_file:
        staged = git.add_pathspec_file(
            proc,
            args.pathspec_from_file,
            pathspec_file_nul=args.pathspec_file_nul,
        )
    elif args.files:
        staged = git.add(proc, *args.files)
    else:
        staged = None
    if staged is not None and staged.returncode != 0:
        sys.stdout.write(staged.stdout)
        sys.stderr.write(staged.stderr)
        return staged.returncode
    result = git.commit_with_trailer(
        proc,
        args.message,
        only=args.only,
        no_trailer=args.no_trailer,
        paths=tuple(args.files),
        pathspec_from_file=args.pathspec_from_file,
        pathspec_file_nul=args.pathspec_file_nul,
    )
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    return result.returncode


def stage_main(argv: list[str]) -> int:
    if not argv:
        print("git-stage.sh: at least one file argument is required", file=sys.stderr)
        print("usage: git-stage.sh <file> [<file> ...]", file=sys.stderr)
        return 1
    result = git.add(proc, *argv)
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    return result.returncode


def amend_add_main(argv: list[str]) -> int:
    if not argv:
        print("git-amend-add.sh: at least one file argument is required", file=sys.stderr)
        print("usage: git-amend-add.sh <file> [<file> ...]", file=sys.stderr)
        return 1
    result = git.amend_add(proc, argv)
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    return result.returncode


def current_branch_main(argv: list[str]) -> int:
    if argv:
        print(f"git-current-branch.sh: unknown argument: {argv[0]}", file=sys.stderr)
        return 1
    branch = git.try_current_branch(proc)
    if not branch:
        print("git-current-branch.sh: not on a named branch (detached HEAD or not a git repo)", file=sys.stderr)
        return 1
    _emit_kv("BRANCH", branch)
    return 0


def branch_info_main(argv: list[str]) -> int:
    if argv:
        print(f"git-branch-info.sh: unknown argument: {argv[0]}", file=sys.stderr)
        return 1
    info = git.branch_info(proc)
    if info is None:
        return 1
    _emit_kv("HEAD_SHA", info.head_sha)
    _emit_kv("CURRENT_BRANCH", info.current_branch)
    return 0


def conflict_files_main(argv: list[str]) -> int:
    if argv:
        print(f"git-conflict-files.sh: unknown argument: {argv[0]}", file=sys.stderr)
        return 1
    for item in git.try_conflict_files(proc):
        _emit_kv("FILE", item.path)
        _emit_kv("STAGE_1", str(item.stage_1).lower())
        _emit_kv("STAGE_2", str(item.stage_2).lower())
        _emit_kv("STAGE_3", str(item.stage_3).lower())
        print()
    return 0


def rebase_abort_main(argv: list[str]) -> int:
    if argv:
        print(f"git-rebase-abort.sh: unknown argument: {argv[0]}", file=sys.stderr)
        return 0
    _ = git.rebase_abort(proc)
    return 0


def rebase_skip_main(argv: list[str]) -> int:
    if argv:
        print(f"git-rebase-skip.sh: unknown argument: {argv[0]}", file=sys.stderr)
        return 1
    result = git.rebase_skip(proc)
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    return result.returncode


def checkout_ours_main(argv: list[str]) -> int:
    if not argv:
        print("git-checkout-ours.sh: at least one file argument is required", file=sys.stderr)
        print("usage: git-checkout-ours.sh <file> [<file> ...]", file=sys.stderr)
        return 1
    result = git.checkout_ours(proc, *argv)
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    return result.returncode


def show_stage_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py git show-stage")
    parser.add_argument("--stage", required=True)
    parser.add_argument("--file", required=True)
    args = _parse(parser, argv)
    if args is None or args.stage not in {"1", "2", "3"}:
        return 1
    result = git.show_file(proc, f":{args.stage}:{args.file}")
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    return result.returncode


def sync_local_main_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py git sync-local-main")
    parser.add_argument("--base-remote", default="origin")
    parser.add_argument("--base-ref", default="main")
    args = _parse(parser, argv)
    if args is None:
        return 1
    result, rc = git.sync_local_main(proc, base_remote=args.base_remote, base_ref=args.base_ref)
    if rc == 0:
        _emit_kv("RESULT", result)
    else:
        print(f"git-sync-local-main.sh: {result}", file=sys.stderr)
    return rc


def clean_tree_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py git clean-tree")
    parser.add_argument("--fail-closed", action="store_true")
    args = _parse(parser, argv)
    if args is None:
        return 2
    result = git.clean_tree(proc, fail_closed=args.fail_closed)
    _emit_kv("CLEAN", result.clean)
    if result.dirty_out:
        _emit_kv("DIRTY_OUT", result.dirty_out)
    if result.probe_error:
        _emit_kv("PROBE_ERROR", result.probe_error)
    return result.exit_code


def snapshot_untracked_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py git snapshot-untracked", add_help=False)
    parser.add_argument("--output", default="")
    parser.add_argument("--nul", action="store_true")
    args = _parse(parser, argv)
    if args is None or not args.output:
        print("snapshot-untracked.sh: --output is required", file=sys.stderr)
        return 0
    return git.snapshot_untracked(proc, args.output, nul=args.nul)


def count_commits_main(argv: list[str]) -> int:
    if argv:
        print(f"git count-commits: unknown argument: {argv[0]}", file=sys.stderr)
        return 1
    result = git.count_commits(proc)
    status_file = os.environ.get("COUNT_COMMITS_STATUS_FILE", "")
    if status_file:
        try:
            with Path(status_file).open("w", encoding="utf-8") as handle:
                handle.write(result.status + "\n")
        except OSError:
            pass
    if result.status == "missing_main_ref":
        print("WARN: lib-count-commits.sh: neither local 'main' nor 'origin/main' exists; cannot determine commit base. Returning 0.", file=sys.stderr)
    print(result.count)
    return 0


def check_main_sync_main(argv: list[str]) -> int:
    if argv:
        print(f"check-main-sync.sh: unknown flag: {argv[0]}", file=sys.stderr)
        return 2
    result = git.check_main_sync(proc)
    _emit_kv("SYNC_STATUS", result.status)
    if result.ahead_count is not None:
        _emit_kv("AHEAD_COUNT", result.ahead_count)
    if result.error:
        _emit_kv("ERROR", result.error)
    return result.exit_code


def check_remote_branch_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py git check-remote-branch", add_help=False)
    parser.add_argument("--branch", default="")
    parser.add_argument("--remote", default="origin")
    args = _parse(parser, argv)
    if args is None or not args.branch:
        _emit_kv("STATE", "error")
        _emit_kv("RC", 1)
        _emit_kv("ERROR", "--branch is required")
        return 0
    result = git.remote_branch_state(proc, args.branch, remote=args.remote)
    _emit_kv("STATE", result.state)
    _emit_kv("RC", result.rc)
    if result.error:
        _emit_kv("ERROR", result.error)
    return 0


def _emit_phantom_dirty_result(result: phantom.PhantomDirtyResult) -> None:
    _emit_kv("STATUS", result.status)
    if result.reason:
        _emit_kv("REASON", result.reason)
    if result.status == "phantom":
        _emit_kv("PHANTOM_COUNT", result.count)
        _emit_kv("PHANTOM_PATHS_FILE", result.paths_file)


def check_phantom_dirty_main(argv: list[str]) -> int:
    baseline = ""
    step = ""
    phantom_paths_dir = ""
    parse_error = ""
    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg == "--baseline":
            if index + 1 >= len(argv):
                parse_error = "baseline-missing-value"
                break
            baseline = argv[index + 1]
            index += 2
            continue
        if arg == "--step":
            if index + 1 >= len(argv):
                parse_error = "step-missing-value"
                break
            step = argv[index + 1]
            index += 2
            continue
        if arg == "--phantom-paths-dir":
            if index + 1 >= len(argv):
                parse_error = "phantom-paths-dir-missing-value"
                break
            phantom_paths_dir = argv[index + 1]
            index += 2
            continue
        parse_error = "unknown-flag"
        break

    if not parse_error:
        if not baseline:
            parse_error = "baseline-required"
        elif not step:
            parse_error = "step-required"
        elif not phantom_paths_dir:
            parse_error = "phantom-paths-dir-required"

    if parse_error:
        _emit_kv("STATUS", "unknown")
        _emit_kv("REASON", parse_error)
        return 0

    if not re.fullmatch(r"^[A-Za-z0-9_.-]+$", step):
        _emit_kv("STATUS", "unknown")
        _emit_kv("REASON", "bad-step")
        return 0

    result = phantom.check_phantom_dirty(
        proc,
        step=step,
        baseline_file=baseline,
        phantom_paths_dir=phantom_paths_dir,
    )
    _emit_phantom_dirty_result(result)
    return 0


def phantom_probe_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py git phantom-probe")
    parser.add_argument("--step", required=True)
    parser.add_argument("--baseline-file", default=None)
    args = _parse(parser, argv)
    if args is None:
        return 2
    print(f"→ phantom-probe: {args.step}", file=sys.stderr)
    result = phantom.probe_with_warn(
        proc,
        step=args.step,
        baseline_file=args.baseline_file,
    )
    _emit_kv("PHANTOM_STATUS", result.dirty.status)
    if result.dirty.reason:
        _emit_kv("PHANTOM_REASON", result.dirty.reason)
    _emit_kv("PHANTOM_COUNT", result.dirty.count)
    _emit_kv("PHANTOM_PATHS_FILE", result.dirty.paths_file)
    if result.append_warn_error:
        _emit_kv("PHANTOM_APPEND_WARN_ERROR", result.append_warn_error)
    return 0
