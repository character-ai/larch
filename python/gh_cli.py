# pyright: reportUnusedCallResult=false
"""Thin CLI entrypoints for gh/repo helper primitives."""

from __future__ import annotations

import argparse
import sys

import gh
import proc


def resolve_repo_main(argv: list[str]) -> int:
    if argv:
        print(f"resolve-repo.sh: unknown argument: {argv[0]}", file=sys.stderr)
        return 1
    repo = gh.resolve_repo(proc)
    if not repo:
        print("ERROR=could not resolve repo (gh repo view + git remote both failed)", file=sys.stderr)
        return 1
    print(repo)
    return 0


def remote_repo_main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("Usage: github-remote-repo.sh <remote-name-or-url>", file=sys.stderr)
        return 2
    repo = gh.remote_repo(proc, argv[0])
    if not repo:
        print("github-remote-repo.sh: cannot parse remote", file=sys.stderr)
        return 2
    print(repo)
    return 0


def run_logs_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py gh run-logs")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--repo", required=True)
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 1
    text, rc = gh.run_logs_failed(proc, args.run_id, repo=args.repo)
    sys.stdout.write(text)
    return rc


def workflow_path_main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("**⚠ read-workflow-path: artifact path not provided; defaulting to unknown**", file=sys.stderr)
        print("unknown")
        return 0
    value = gh.read_workflow_path(argv[0])
    if value == "unknown":
        print("**⚠ read-workflow-path: workflow_path/design_classification missing or invalid; defaulting to unknown**", file=sys.stderr)
    print(value)
    return 0
