# pyright: reportUnusedFunction=false, reportUnusedCallResult=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportPrivateUsage=false
"""Step 0 bootstrap entrypoints."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

from larch import io as larch_io
from larch.core import config
from larch.implement.dispatch_helpers import (
    _first_nonempty,
    _invoke_cli,
    _parse_kv,
    _read_kv_file,
    _read_session_key_default,
    _rehydrate_larch_triplet,
    _rehydrate_plugin_root,
    _run_cli_forward,
    _tmpdir_from_env,
    _tracking_sentinel_values,
    _write_text_atomic,
)

_DIFFICULTY_VALUES = {"", "TRIVIAL", "MODERATE", "HARD"}


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


def _die_argv(message: str) -> int:
    print(f"step-0-bootstrap: {message}", file=sys.stderr)
    return 2


def _read_run_flag(*, implement_tmpdir: Path, key: str, default: str = "") -> str:
    return larch_io.read_kv(
        path=implement_tmpdir / "run-flags.sh",
        key=key,
        default=default,
        first_match=True,
    )


def _apply_resume_rehydration(*, implement_tmpdir: Path, args: argparse.Namespace) -> None:  # noqa: C901, PLR0912 - resume rehydration fills each optional arg from its own env, seed, or session fallback
    if not args.preflight_tmpdir:
        preflight_file = implement_tmpdir / "preflight-tmpdir.env"
        if preflight_file.is_file():
            args.preflight_tmpdir = _read_kv_file(path=preflight_file, key="PREFLIGHT_TMPDIR", default="")
    if not args.forked_target:
        session_forked = _read_session_key_default(implement_tmpdir=implement_tmpdir, key="FORKED_TARGET", default="false")
        if session_forked in {"true", "false"}:
            args.forked_target = session_forked
    if args.force_requested not in {"true", "false"}:
        run_force = _read_run_flag(implement_tmpdir=implement_tmpdir, key="FORCE_REQUESTED")
        if run_force in {"true", "false"}:
            args.force_requested = run_force
    if args.self_review_requested not in {"true", "false"}:
        run_self_review = _read_run_flag(implement_tmpdir=implement_tmpdir, key="SELF_REVIEW_REQUESTED")
        if run_self_review in {"true", "false"}:
            args.self_review_requested = run_self_review
    if args.self_implement_requested not in {"true", "false"}:
        run_self_implement = _read_run_flag(implement_tmpdir=implement_tmpdir, key="SELF_IMPLEMENT_REQUESTED")
        if run_self_implement in {"true", "false"}:
            args.self_implement_requested = run_self_implement
    seed_file = implement_tmpdir / "ship-seed-input.env"
    if not args.merge_requested:
        args.merge_requested = _read_kv_file(path=seed_file, key="MERGE", default="false") or "false"
    if not args.draft_requested:
        args.draft_requested = _read_kv_file(path=seed_file, key="DRAFT", default="false") or "false"
    if not args.no_admin_fallback:
        args.no_admin_fallback = _read_kv_file(path=seed_file, key="NO_ADMIN_FALLBACK", default="false") or "false"
    if not args.no_logs_commit:
        args.no_logs_commit = _read_kv_file(path=seed_file, key="NO_LOGS_COMMIT", default="false") or "false"
    if not args.issue_number:
        sentinel = _tracking_sentinel_values(implement_tmpdir / "parent-issue.md")
        issue = _first_nonempty(sentinel.get("ISSUE_NUMBER", ""), _read_session_key_default(implement_tmpdir=implement_tmpdir, key="ISSUE_NUMBER", default=""))
        if issue:
            args.issue_number = issue
            os.environ[config.ENV_ISSUE_NUMBER] = issue
        if not args.run_id:
            run_id = _first_nonempty(sentinel.get("RUN_ID", ""), _read_session_key_default(implement_tmpdir=implement_tmpdir, key="RUN_ID", default=""))
            if run_id:
                args.run_id = run_id
    if not args.run_id:
        session_run_id = _read_session_key_default(implement_tmpdir=implement_tmpdir, key="RUN_ID", default="")
        if session_run_id:
            args.run_id = session_run_id


def _apply_fork_env(args: argparse.Namespace) -> int:  # noqa: C901 - fork-env fanout maps each optional KV to a distinct arg or env assignment
    result = _invoke_cli(["admission", "fork-env"])
    if result.returncode != 0:
        if result.stdout:
            sys.stdout.write(result.stdout)
            sys.stdout.flush()
        if result.stderr:
            sys.stderr.write(result.stderr)
            sys.stderr.flush()
        return result.returncode
    values = _parse_kv(result.stdout)
    if values.get("CALLER_ENV_PATH"):
        args.caller_env = values["CALLER_ENV_PATH"]
    if values.get("UPSTREAM_REPO"):
        args.upstream_repo = values["UPSTREAM_REPO"]
    if values.get("FORK_REPO"):
        os.environ["FORK_REPO"] = values["FORK_REPO"]
    if values.get("FORK_OWNER"):
        os.environ["FORK_OWNER"] = values["FORK_OWNER"]
    if values.get("FORKED_TARGET") in {"true", "false"}:
        args.forked_target = values["FORKED_TARGET"]
    if result.stdout:
        sys.stdout.write(result.stdout)
        if not result.stdout.endswith("\n"):
            sys.stdout.write("\n")
        sys.stdout.flush()
    return 0


def step0_bootstrap_main(argv: list[str] | None = None) -> int:  # noqa: C901 - bootstrap entrypoint validates flags then assembles the resume and invoke argv
    parser = argparse.ArgumentParser(prog="cli.py implement step-0-bootstrap")
    parser.add_argument("--mode", choices=("initial", "resume"), required=True)
    parser.add_argument("--issue-number", default="")
    parser.add_argument("--preflight-tmpdir", default="")
    parser.add_argument("--coder", default="")
    parser.add_argument("--force-requested", default="")
    parser.add_argument("--self-review-requested", default="")
    parser.add_argument("--self-implement-requested", default="")
    parser.add_argument("--forked-target", default="")
    parser.add_argument("--merge-requested", default="")
    parser.add_argument("--draft-requested", default="")
    parser.add_argument("--no-admin-fallback", default="")
    parser.add_argument("--no-logs-commit", default="")
    parser.add_argument("--upstream-repo", default="")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--caller-env", default="")
    parser.add_argument("--session-env", default="")
    parser.add_argument("--non-interactive", default="")
    parser.add_argument("--difficulty", default="")
    args = parser.parse_args(argv)

    for flag in (
        "force-requested",
        "self-review-requested",
        "self-implement-requested",
        "forked-target",
        "merge-requested",
        "draft-requested",
        "no-admin-fallback",
        "no-logs-commit",
        "non-interactive",
    ):
        attr = flag.replace("-", "_")
        value = getattr(args, attr)
        if value not in {"", "true", "false"}:
            return _die_argv(f"--{flag} must be true or false")
    if args.difficulty not in _DIFFICULTY_VALUES:
        return _die_argv("--difficulty must be TRIVIAL, MODERATE, or HARD")

    implement_tmpdir_raw = os.environ.get(config.ENV_IMPLEMENT_TMPDIR, "")
    implement_tmpdir = Path(implement_tmpdir_raw) if implement_tmpdir_raw else None
    if implement_tmpdir is not None:
        _rehydrate_plugin_root(implement_tmpdir)
    else:
        _rehydrate_plugin_root(None)

    if args.mode == "resume":
        if implement_tmpdir is None:
            print("bootstrap invoke: --mode resume requires exported IMPLEMENT_TMPDIR", file=sys.stderr)
            return 2
        _apply_resume_rehydration(implement_tmpdir=implement_tmpdir, args=args)

    if args.forked_target == "true" and not args.upstream_repo:
        fork_rc = _apply_fork_env(args)
        if fork_rc != 0:
            return fork_rc

    if implement_tmpdir is not None:
        _rehydrate_larch_triplet(implement_tmpdir)

    os.environ["LARCH_CLAUDE_PID"] = os.environ.get("LARCH_CLAUDE_PID") or str(os.getppid())

    if args.preflight_tmpdir and implement_tmpdir is not None:
        _write_text_atomic(path=implement_tmpdir / "preflight-tmpdir.env", text=f"PREFLIGHT_TMPDIR={args.preflight_tmpdir}\n")

    non_interactive = args.non_interactive
    if non_interactive == "":
        resolved = _invoke_cli(["bootstrap", "resolve-non-interactive"])
        non_interactive = "true" if resolved.stdout.strip() == "true" else "false"

    invoke_args = [
        "bootstrap", "invoke",
        "--mode", args.mode,
        "--issue-number", args.issue_number or os.environ.get(config.ENV_ISSUE_NUMBER, ""),
        "--preflight-tmpdir", args.preflight_tmpdir,
        "--coder", args.coder,
        "--force-requested", args.force_requested or "false",
        "--self-review-requested", args.self_review_requested or "false",
        "--self-implement-requested", args.self_implement_requested or "false",
        "--forked-target", args.forked_target or "false",
        "--merge-requested", args.merge_requested or "false",
        "--draft-requested", args.draft_requested or "false",
        "--no-admin-fallback", args.no_admin_fallback or "false",
        "--no-logs-commit", args.no_logs_commit or "false",
        "--upstream-repo", args.upstream_repo,
        "--run-id", args.run_id,
        "--caller-env", args.caller_env or args.session_env,
        "--non-interactive", non_interactive,
        "--difficulty", args.difficulty,
    ]
    return _run_cli_forward(invoke_args)
