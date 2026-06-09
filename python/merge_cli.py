# pyright: reportUnusedCallResult=false
"""Thin CLI entrypoint for merge helper primitives."""

from __future__ import annotations

import argparse
import tempfile

import logging_util
import merge
import proc
from run_context import RunContext


def _emit_kv(key: str, value: object) -> None:
    logging_util.emit_kv(key, str(value))


def pr_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py merge pr")
    parser.add_argument("--pr", required=True, type=int)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--no-admin-fallback", action="store_true")
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 1
    ctx = RunContext(
        branch="",
        issue="",
        repo=args.repo,
        run_id="",
        tmpdir=tempfile.gettempdir(),
        merge=True,
        draft=False,
        forked=False,
        manifest_path="",
        tool_label="codex",
        no_admin_fallback=args.no_admin_fallback,
        repo_unavailable=False,
        pr_number=args.pr,
        no_logs_commit=True,
    )
    result = merge.merge_pr(proc, ctx, post_flush=False)
    _emit_kv("MERGE_RESULT", result.result)
    _emit_kv("ERROR", result.error)
    return 0
