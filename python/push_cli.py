# pyright: reportUnusedCallResult=false
"""Thin CLI entrypoints for push/rebase helper primitives."""

from __future__ import annotations

import argparse
import sys

import git
import logging_util
import phantom
import proc
import push
import rebase

_REBASE_FAILED_EXIT = 3


def _emit_kv(key: str, value: object) -> None:
    logging_util.emit_kv(key, str(value))


def _parse(parser: argparse.ArgumentParser, argv: list[str]) -> argparse.Namespace | None:
    try:
        return parser.parse_args(argv)
    except SystemExit:
        return None


def _rebase_sanitize(text: str) -> str:
    return " ".join(text.split())


def _conflict_files_csv(result: rebase.RebasePushResult) -> str:
    if result.conflict_files:
        return result.conflict_files
    files = [item.path for item in git.try_conflict_files(proc)]
    return ",".join(files)


def _emit_rebase_checkpoint_keys(result: rebase.RebasePushResult) -> int:
    if result.skipped_already_pushed:
        _emit_kv("SKIPPED_ALREADY_PUSHED", "true")
    if result.skipped_already_fresh:
        _emit_kv("SKIPPED_ALREADY_FRESH", "true")
    if result.conflict_files:
        _emit_kv("CONFLICT_FILES", result.conflict_files)
    if result.rebase_error:
        _emit_kv("REBASE_ERROR", result.rebase_error)

    if result.exit_code == 0:
        if result.skipped_already_pushed or result.skipped_already_fresh:
            _emit_kv("REBASE_OUTCOME", "skipped")
        else:
            _emit_kv("REBASE_OUTCOME", "ok")
        return 0
    if result.exit_code == 1:
        _emit_kv("REBASE_OUTCOME", "conflict")
        _emit_kv("CONFLICT_FILES", _conflict_files_csv(result))
        return 1
    if result.exit_code == _REBASE_FAILED_EXIT:
        _emit_kv("REBASE_OUTCOME", "failed")
        err = result.rebase_error or "rebase-failed"
        _emit_kv("REBASE_ERROR", _rebase_sanitize(err))
        return 3
    _emit_kv("REBASE_OUTCOME", "failed")
    _emit_kv("REBASE_ERROR", f"unexpected-rc-{result.exit_code}")
    return result.exit_code


def branch_main(argv: list[str]) -> int:
    if argv:
        print(f"git-push.sh: unknown argument: {argv[0]}", file=sys.stderr)
        return 1
    result = push.push_current_branch(proc)
    if result.branch:
        _emit_kv("BRANCH", result.branch)
    if result.stderr:
        sys.stderr.write(result.stderr)
    return result.exit_code


def force_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py push force")
    parser.add_argument("--expected-remote-oid", default=None)
    args = _parse(parser, argv)
    if args is None:
        return 2
    result = git.force_push_recovery(
        proc,
        expected_remote_oid=args.expected_remote_oid,
    )
    if result.branch:
        _emit_kv("BRANCH", result.branch)
    elif result.status == "detached_head":
        print("git-force-push.sh: not on a named branch", file=sys.stderr)
    _emit_kv("PUSHED", str(result.pushed).lower())
    _emit_kv("STATUS", result.status)
    if result.pushed:
        return 0
    if result.status in {"detached_head", "branch_mismatch", "status_failed"}:
        return 2
    return 1


def rebase_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py push rebase")
    parser.add_argument("--continue", dest="continue_mode", action="store_true")
    parser.add_argument("--no-push", action="store_true")
    parser.add_argument("--skip-if-pushed", action="store_true")
    parser.add_argument("--keep-on-conflict", action="store_true")
    parser.add_argument("--base-remote", default="origin")
    parser.add_argument("--base-ref", default="main")
    args = _parse(parser, argv)
    if args is None:
        return 3
    result = rebase.rebase_push(
        proc,
        continue_mode=args.continue_mode,
        no_push=args.no_push,
        skip_if_pushed=args.skip_if_pushed,
        keep_on_conflict=args.keep_on_conflict,
        base_remote=args.base_remote,
        base_ref=args.base_ref,
    )
    if result.skipped_already_pushed:
        _emit_kv("SKIPPED_ALREADY_PUSHED", "true")
    if result.skipped_already_fresh:
        _emit_kv("SKIPPED_ALREADY_FRESH", "true")
    if result.conflict_files:
        _emit_kv("CONFLICT_FILES", result.conflict_files)
    if result.rebase_error:
        _emit_kv("REBASE_ERROR", result.rebase_error)
    if result.push_error:
        _emit_kv("PUSH_ERROR", result.push_error)
    return result.exit_code


def checkpoint_probe_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py push checkpoint-probe")
    parser.add_argument("step_prefix")
    parser.add_argument("short_name")
    parser.add_argument("--base-remote", default="origin")
    parser.add_argument("--base-ref", default="main")
    args = _parse(parser, argv)
    if args is None:
        return 2
    print(f"→ rebase-probe: {args.step_prefix} {args.short_name}", file=sys.stderr)
    result = rebase.rebase_push(
        proc,
        no_push=True,
        skip_if_pushed=True,
        keep_on_conflict=True,
        base_remote=args.base_remote,
        base_ref=args.base_ref,
    )
    rc = _emit_rebase_checkpoint_keys(result)
    if rc != 0:
        return rc
    probe = phantom.probe_with_warn(proc, step=f"{args.step_prefix}-post-rebase")
    _emit_kv("PHANTOM_STATUS", probe.dirty.status)
    if probe.dirty.reason:
        _emit_kv("PHANTOM_REASON", probe.dirty.reason)
    _emit_kv("PHANTOM_COUNT", probe.dirty.count)
    if probe.dirty.paths_file:
        _emit_kv("PHANTOM_PATHS_FILE", probe.dirty.paths_file)
    if probe.append_warn_error:
        _emit_kv("PHANTOM_APPEND_WARN_ERROR", probe.append_warn_error)
    return 0
