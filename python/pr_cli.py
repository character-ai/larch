# pyright: reportUnusedCallResult=false
"""Thin CLI entrypoints for PR helper primitives."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import gh
import pr
import proc


def _emit_kv(key: str, value: object) -> None:
    print(f"{key}={value}")


def _parse(parser: argparse.ArgumentParser, argv: list[str]) -> argparse.Namespace | None:
    try:
        return parser.parse_args(argv)
    except SystemExit:
        return None


def create_branch_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py pr create-branch")
    parser.add_argument("--branch", required=True)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--base-remote", default="origin")
    parser.add_argument("--base-ref", default="main")
    args = _parse(parser, argv)
    if args is None:
        return 2
    result = pr.create_branch(
        proc,
        branch=args.branch,
        base_remote=args.base_remote,
        base_ref=args.base_ref,
        check=args.check,
    )
    _emit_kv("BRANCH", result.branch)
    _emit_kv("BASE", result.base)
    _emit_kv("STATUS", result.status)
    return result.exit_code


def create_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py pr create")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--branch", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--body-file", required=True)
    parser.add_argument("--base", default=None)
    parser.add_argument("--draft", action="store_true")
    args = _parse(parser, argv)
    if args is None:
        return 1
    try:
        with Path(args.body_file).open(encoding="utf-8") as handle:
            body = handle.read()
    except OSError as exc:
        print(f"create-pr.sh: cannot read body file: {exc}", file=sys.stderr)
        return 2
    try:
        result = pr.create_pr_parity(
            proc,
            repo=args.repo,
            branch=args.branch,
            title=args.title,
            body=body,
            base=args.base,
            draft=args.draft,
        )
    except Exception as exc:  # pylint: disable=broad-except
        _emit_kv("PR_STATUS", "error")
        _emit_kv("PR_NUMBER", 0)
        _emit_kv("PR_URL", "")
        _emit_kv("PR_TITLE", args.title)
        print(str(exc), file=sys.stderr)
        return 2
    _emit_kv("PR_NUMBER", result.number)
    _emit_kv("PR_URL", result.url)
    _emit_kv("PR_TITLE", result.title)
    _emit_kv("PR_STATUS", result.status)
    return result.exit_code


def body_update_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py pr body-update")
    parser.add_argument("--pr", required=True)
    parser.add_argument("--repo", default=None)
    parser.add_argument("--body-file", required=True)
    args = _parse(parser, argv)
    if args is None:
        return 2
    result = gh.pr_edit_body_file(proc, args.pr, args.body_file, repo=args.repo)
    _emit_kv("UPDATED", str(result.updated).lower())
    _emit_kv("ERROR", result.error)
    return result.exit_code


def checks_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py pr checks")
    parser.add_argument("--pr", required=True, type=int)
    parser.add_argument("--repo", required=True)
    args = _parse(parser, argv)
    if args is None:
        return 1
    result = gh.pr_checks_text_read(proc, args.pr, repo=args.repo)
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    return result.returncode


def closes_issue_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py pr closes-issue")
    parser.add_argument("--body-file", default=None)
    parser.add_argument("--repo", default=None)
    args = _parse(parser, argv)
    if args is None:
        return 1
    if args.body_file:
        try:
            with Path(args.body_file).open(encoding="utf-8") as handle:
                print(gh.extract_closes_issue(handle.read()))
        except OSError:
            print()
        return 0
    repo = args.repo or gh.resolve_repo(proc) or ""
    if not repo:
        print()
        return 0
    print(gh.extract_closes_issue_from_current_pr(proc, repo=repo))
    return 0
