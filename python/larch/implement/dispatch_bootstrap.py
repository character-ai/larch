# pyright: reportUnusedFunction=false, reportUnusedCallResult=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportPrivateUsage=false
"""Step 0 bootstrap entrypoints."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

from larch.implement.dispatch_helpers import (
    _env_value,
    _invoke_cli,
    _parse_kv,
    _read_session_key_default,
    _rehydrate_larch_triplet,
    _rehydrate_plugin_root,
    _run_cli_forward,
    _session_get,
    _tmpdir_from_env,
    _tracking_sentinel_values,
    _write_text_atomic,
)


def step0_bootstrap_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py implement step-0-bootstrap")
    parser.add_argument("--mode", choices=("initial", "resume"), required=True)
    parser.add_argument("--issue-number", default="")
    parser.add_argument("--preflight-tmpdir", default="")
    parser.add_argument("--coder", default="")
    parser.add_argument("--force-requested", choices=("", "true", "false"), default="")
    parser.add_argument("--self-review-requested", choices=("", "true", "false"), default="")
    parser.add_argument("--forked-target", choices=("", "true", "false"), default="")
    parser.add_argument("--merge-requested", choices=("", "true", "false"), default="")
    parser.add_argument("--draft-requested", choices=("", "true", "false"), default="")
    parser.add_argument("--no-admin-fallback", choices=("", "true", "false"), default="")
    parser.add_argument("--no-logs-commit", choices=("", "true", "false"), default="")
    parser.add_argument("--upstream-repo", default="")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--caller-env", default="")
    parser.add_argument("--session-env", default="")
    parser.add_argument("--non-interactive", choices=("true", "false"), default="")
    args = parser.parse_args(argv)
    implement_tmpdir_raw = os.environ.get("IMPLEMENT_TMPDIR", "")
    implement_tmpdir = Path(implement_tmpdir_raw) if implement_tmpdir_raw else None
    _rehydrate_plugin_root(implement_tmpdir)
    issue = args.issue_number or os.environ.get("TARGET_ISSUE_NUMBER", os.environ.get("ISSUE_NUMBER", ""))
    preflight = args.preflight_tmpdir or os.environ.get("PREFLIGHT_TMPDIR", "")
    coder = args.coder or _env_value(name="coder")
    force = args.force_requested
    self_review = args.self_review_requested
    forked = args.forked_target
    merge = args.merge_requested
    draft = args.draft_requested
    no_admin = args.no_admin_fallback
    no_logs = args.no_logs_commit
    upstream = args.upstream_repo or os.environ.get("UPSTREAM_REPO", "")
    run_id = args.run_id or os.environ.get("RUN_ID", "")
    caller_env = args.caller_env or args.session_env or os.environ.get("CALLER_ENV_PATH", os.environ.get("SESSION_ENV_PATH", ""))
    if args.mode == "resume" and implement_tmpdir:
        if not preflight and (implement_tmpdir / "preflight-tmpdir.env").is_file():
            preflight = _session_get(file=implement_tmpdir / "preflight-tmpdir.env", key="PREFLIGHT_TMPDIR", default="")
        if not forked:
            forked = _read_session_key_default(implement_tmpdir=implement_tmpdir, key="FORKED_TARGET", default="false")
        force = _env_value(name="force_requested") if _env_value(name="force_requested") in {"true", "false"} else _session_get(file=implement_tmpdir / "run-flags.sh", key="FORCE_REQUESTED", default=force)
        self_review = _env_value(name="self_review") if _env_value(name="self_review") in {"true", "false"} else _session_get(file=implement_tmpdir / "run-flags.sh", key="SELF_REVIEW_REQUESTED", default=self_review)
        seed = implement_tmpdir / "ship-seed-input.env"
        merge = _env_value(name="merge") or _session_get(file=seed, key="MERGE", default=merge)
        draft = _env_value(name="draft") or _session_get(file=seed, key="DRAFT", default=draft)
        no_admin = _env_value(name="no_admin_fallback") or _session_get(file=seed, key="NO_ADMIN_FALLBACK", default=no_admin)
        no_logs = _env_value(name="no_logs_commit") or _session_get(file=seed, key="NO_LOGS_COMMIT", default=no_logs)
        if not issue:
            sentinel_values = _tracking_sentinel_values(implement_tmpdir / "parent-issue.md")
            issue = sentinel_values.get("ISSUE_NUMBER", "") or _read_session_key_default(implement_tmpdir=implement_tmpdir, key="ISSUE_NUMBER", default="")
            run_id = run_id or sentinel_values.get("RUN_ID", "")
        run_id = run_id or _read_session_key_default(implement_tmpdir=implement_tmpdir, key="RUN_ID", default="")
    if forked == "true" and not upstream:
        fork = _invoke_cli(["admission", "fork-env"])
        if fork.stdout:
            sys.stdout.write(fork.stdout)
        if fork.returncode != 0:
            return fork.returncode
        values = _parse_kv(fork.stdout)
        caller_env = values.get("CALLER_ENV_PATH", caller_env)
        upstream = values.get("UPSTREAM_REPO", upstream)
        os.environ["FORK_REPO"] = values.get("FORK_REPO", os.environ.get("FORK_REPO", ""))
        os.environ["FORK_OWNER"] = values.get("FORK_OWNER", os.environ.get("FORK_OWNER", ""))
        forked = values.get("FORKED_TARGET", forked)
    if implement_tmpdir:
        _rehydrate_larch_triplet(implement_tmpdir)
        if preflight:
            _write_text_atomic(path=implement_tmpdir / "preflight-tmpdir.env", text=f"PREFLIGHT_TMPDIR={preflight}\n")
    non_interactive = args.non_interactive
    if not non_interactive:
        resolved = _invoke_cli(["bootstrap", "resolve-non-interactive"])
        non_interactive = "true" if resolved.stdout.strip() == "true" else "false"
    os.environ["LARCH_CLAUDE_PID"] = os.environ.get("LARCH_CLAUDE_PID", str(os.getppid()))
    invoke_args = [
        "bootstrap", "invoke", "--mode", args.mode,
        "--issue-number", issue,
        "--preflight-tmpdir", preflight,
        "--coder", coder,
        "--force-requested", force or "false",
        "--self-review-requested", self_review or "false",
        "--forked-target", forked or "false",
        "--merge-requested", merge or "false",
        "--draft-requested", draft or "false",
        "--no-admin-fallback", no_admin or "false",
        "--no-logs-commit", no_logs or "false",
        "--upstream-repo", upstream,
        "--run-id", run_id,
        "--caller-env", caller_env,
        "--non-interactive", non_interactive,
    ]
    result = _invoke_cli(invoke_args)
    if result.returncode != 0:
        return result.returncode
    if args.mode != "resume":
        print("progress: type p (or progress) at any time")
    if result.stdout:
        sys.stdout.write(result.stdout)
    return 0


def step0_degraded_gate_main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(prog="cli.py implement step-0-degraded-gate").parse_args(argv)
    implement_tmpdir = _tmpdir_from_env()
    _rehydrate_plugin_root(implement_tmpdir)
    codex_binary_found = _read_session_key_default(implement_tmpdir=implement_tmpdir, key="CODEX_BINARY_FOUND", default="")
    cursor_binary_found = _read_session_key_default(implement_tmpdir=implement_tmpdir, key="CURSOR_BINARY_FOUND", default="")
    check_args = ["agent", "check-reviewers"]
    if shutil.which("codex") is None:
        check_args.append("--skip-codex-probe")
    if shutil.which("cursor") is None:
        check_args.append("--skip-cursor-probe")
    probe = _invoke_cli(check_args)
    if probe.returncode != 0:
        probe = _invoke_cli(check_args)
    values = _parse_kv(probe.stdout)
    return _run_cli_forward([
        "agent", "degraded-tools-gate", "--skill", "implement",
        "--codex-present", values.get("CODEX_PRESENT", ""),
        "--cursor-present", values.get("CURSOR_PRESENT", ""),
        "--codex-binary-found", codex_binary_found,
        "--cursor-binary-found", cursor_binary_found,
    ])
