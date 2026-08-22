#!/usr/bin/env python3
"""Frozen black-box reference for the #8789 command cutover."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def read_kv(path: Path, key: str) -> str:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return ""
    for line in lines:
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1].removesuffix("\r")
    return ""


def compose_summary(arguments: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py pr compose-summary")
    parser.add_argument("--plan-goals-file", required=True)
    args = parser.parse_args(arguments)
    supplied = args.plan_goals_file
    root = Path.cwd()
    plan = Path(supplied)
    plan = plan.resolve() if plan.is_absolute() else (root / plan).resolve()
    try:
        plan.relative_to(root.resolve())
    except ValueError:
        print(f"ERROR=plan-goals path escapes repo root: {supplied}", file=sys.stderr)
        return 2
    if not plan.is_file() or plan.stat().st_size == 0:
        print(f"ERROR=plan-goals file missing or empty: {supplied}", file=sys.stderr)
        return 2
    in_goal = False
    goal = ""
    for line in plan.read_text(encoding="utf-8").splitlines():
        if line.startswith("## Goal"):
            in_goal = True
            continue
        if in_goal and line.startswith("#"):
            break
        if in_goal and line.strip():
            goal = line.strip()
            break
    if not goal:
        print(f"ERROR=no Goal line found in {supplied}", file=sys.stderr)
        return 2
    print(f"- {goal}")
    return 0


def create_branch(arguments: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py pr create-branch")
    parser.add_argument("--branch", default="")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--base-remote", default="origin")
    parser.add_argument("--base-ref", default="main")
    try:
        args = parser.parse_args(arguments)
    except SystemExit:
        return 2
    if not args.branch:
        print("create-branch.sh: --branch is required", file=sys.stderr)
        return 2
    raise RuntimeError("the frozen fixture must not create a branch")


def create_pr(arguments: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py pr create")
    parser.add_argument("--repo", default=None)
    parser.add_argument("--branch", default=None)
    parser.add_argument("--title", required=True)
    parser.add_argument("--body-file", required=True)
    parser.add_argument("--base", default=None)
    parser.add_argument("--draft", action="store_true")
    try:
        parser.parse_args(arguments)
    except SystemExit:
        return 1
    raise RuntimeError("the frozen fixture must not create a pull request")


def body_update(arguments: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py pr body-update")
    parser.add_argument("--pr", required=True)
    parser.add_argument("--repo", default=None)
    parser.add_argument("--body-file", required=True)
    try:
        args = parser.parse_args(arguments)
    except SystemExit:
        return 2
    if not Path(args.body_file).is_file():
        print("UPDATED=false")
        print(f"ERROR=body file not found: {args.body_file}")
        return 2
    raise RuntimeError("the frozen fixture must not update a pull request")


def checks(arguments: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py pr checks")
    parser.add_argument("--pr", required=True, type=int)
    parser.add_argument("--repo", required=True)
    try:
        parser.parse_args(arguments)
    except SystemExit:
        return 1
    raise RuntimeError("the frozen fixture must not read live checks")


def closes_issue(arguments: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py pr closes-issue")
    parser.add_argument("--body-file", default=None)
    parser.add_argument("--repo", default=None)
    try:
        args = parser.parse_args(arguments)
    except SystemExit:
        return 1
    if args.body_file:
        try:
            body = Path(args.body_file).read_text(encoding="utf-8")
        except OSError:
            print()
            return 0
        match = re.search(r"Closes #([0-9]+)", body)
        print(match.group(1) if match else "")
        return 0
    print()
    return 0


def post_issue(arguments: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py tracking post-issue")
    parser.add_argument("--implement-tmpdir", required=True)
    parser.add_argument("--issue-number", default="")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--adopted", default="true")
    parser.add_argument("--force-requested", default="false")
    args = parser.parse_args(arguments)
    error = ""
    code = 0
    if args.adopted not in {"true", "false"}:
        code, error = 2, "--adopted must be true or false"
    elif args.force_requested not in {"true", "false"}:
        code, error = 2, "--force-requested must be true or false"
    else:
        root = Path(args.implement_tmpdir)
        parent = root / "parent-issue.md"
        session = root / "session-env.sh"
        issue = args.issue_number or read_kv(parent, "ISSUE_NUMBER")
        run = (
            args.run_id
            or read_kv(parent, "RUN_ID")
            or ((root / "session-id").read_text(encoding="utf-8").strip() if (root / "session-id").is_file() else "")
            or read_kv(session, "LARCH_TOKEN_SESSION_ID")
        )
        if not issue:
            code, error = 1, "ISSUE_NUMBER not found in parent-issue.md"
        elif not issue.isdigit():
            code, error = 1, "ISSUE_NUMBER must be numeric"
        elif not re.fullmatch(r"[A-Za-z0-9._-]+", run or ""):
            code, error = 1, "RUN_ID must match ^[A-Za-z0-9._-]+$"
        else:
            raise RuntimeError("the frozen fixture must not reach a live GitHub mutation")
    print("POSTED=false")
    print("COMMENT_URL=")
    if error:
        print(f"ERROR={error}")
    return code


def main() -> int:
    if len(sys.argv) < 2:
        print("fixture command required", file=sys.stderr)
        return 2
    command, arguments = sys.argv[1], sys.argv[2:]
    if command == "pr-compose-summary":
        return compose_summary(arguments)
    if command == "pr-create-branch":
        return create_branch(arguments)
    if command == "pr-create":
        return create_pr(arguments)
    if command == "pr-body-update":
        return body_update(arguments)
    if command == "pr-checks":
        return checks(arguments)
    if command == "pr-closes-issue":
        return closes_issue(arguments)
    if command == "tracking-post-issue":
        return post_issue(arguments)
    print(f"unknown fixture command: {command}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
