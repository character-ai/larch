"""Seed initial ship-pr state CLI functions."""
# pyright: reportPrivateUsage=false

from __future__ import annotations

import argparse
import json
import os
import sys
from contextlib import suppress
from pathlib import Path

from larch.errors import ShipError
from larch.implement.ship_state import (
    INITIAL_SHIP_STATE_KEYS,
    _bool_arg,
    _state_bool,
    _state_file_has_kv,
    _path_under,
    _validate_ship_state_value,
    _valid_branch_name,
    _valid_repo_slug,
    _tmpdir_under_allowed_root,
)


def _validate_seed_identity_args(args: argparse.Namespace) -> None:
    branch = (args.branch or "").strip()
    issue = (args.issue or "").strip()
    repo = (args.repo or "").strip()
    run_id = (args.run_id or "").strip()
    if not branch or not _valid_branch_name(branch):
        raise ShipError("--branch must be a non-empty valid branch name")
    if not issue or not issue.isdigit():
        raise ShipError("--issue must be a non-empty digit issue number")
    if not repo or not _valid_repo_slug(repo):
        raise ShipError("--repo must be a non-empty owner/repo slug")
    if not run_id:
        raise ShipError("--run-id must be non-empty")


def _validate_seed_manifest(path_text: str) -> None:
    if not path_text:
        return
    path = Path(path_text)
    if path.name.endswith(".env"):
        raise ShipError("MANIFEST_PATH must point at a readable JSON manifest, not a shell env file")
    try:
        with path.open("r", encoding="utf-8") as handle:
            parsed = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise ShipError("MANIFEST_PATH must point at a readable JSON manifest") from exc
    if not isinstance(parsed, dict):
        raise ShipError("MANIFEST_PATH JSON manifest must be an object")


def _seed_initial_state_fields(args: argparse.Namespace) -> dict[str, str]:
    stall_step = args.stall_step or ""
    merge = _bool_arg(args.merge)
    draft = False if stall_step else _bool_arg(args.draft)
    fields = {
        "PHASE": "checks",
        "BRANCH_NAME": args.branch or "",
        "ISSUE_NUMBER": args.issue or "",
        "RUN_ID": args.run_id or "",
        "REPO": args.repo or "",
        "REPO_UNAVAILABLE": _state_bool(value=_bool_arg(args.repo_unavailable)),
        "FORKED_TARGET": _state_bool(value=_bool_arg(args.forked)),
        "MERGE": _state_bool(value=merge),
        "DRAFT": _state_bool(value=draft),
        "DEFERRED": _state_bool(value=_bool_arg(args.deferred)),
        "PR_CLOSED": "false",
        "DONE_RENAME_APPLIED": "false",
        "STALL_TRACKING": _state_bool(value=_bool_arg(args.stall_tracking)),
        "STALL_STEP": stall_step,
        "BAIL_NEEDS_USER_INPUT": "false",
        "BAIL_REASON": args.bail_reason or "",
        "BAIL_FAILURE_DETAIL_LOG": args.bail_failure_detail_log or "",
        "CI_PASSED": "false",
        "PR_NUMBER": "",
        "PR_URL": "",
        "PR_TITLE": "",
        "RESUME_PHASE": "",
        "CALLER_KIND": "",
        "REBASE_COUNT": "0",
        "FIX_ATTEMPTS": "0",
        "ITERATION": "0",
        "TRANSIENT_RETRIES": "0",
        "FAILED_RUN_ID": "",
        "MANIFEST_PATH": args.manifest_path or "",
        "TOOL_LABEL": args.tool_label or "",
        "DESIGN_ONLY_DONE": "false",
        "EXPECTED_SESSION_ID": args.expected_session_id or "",
        "EXPECTED_TMPDIR_BASENAME_PREFIX": args.expected_tmpdir_basename_prefix or "",
        "NO_ADMIN_FALLBACK": _state_bool(value=_bool_arg(args.no_admin_fallback)),
        "NO_LOGS_COMMIT": _state_bool(value=_bool_arg(args.no_logs_commit)),
        "IMPLEMENT_TMPDIR": args.tmpdir or "",
        "CI_FIX_REBASE_PENDING": "false",
        "OOS_PENDING": "false",
    }
    return {key: fields[key] for key in INITIAL_SHIP_STATE_KEYS}


def _write_initial_ship_state(args: argparse.Namespace) -> None:
    tmpdir = Path(args.tmpdir or "")
    if not _tmpdir_under_allowed_root(str(tmpdir)):
        raise ShipError("--tmpdir is not an allowed implement tmpdir")
    state_file = Path(args.state_file or (tmpdir / "ship-pr-state.sh"))
    if not _path_under(parent=tmpdir, child=state_file):
        raise ShipError("--state-file must stay under --tmpdir")
    if state_file.is_symlink():
        raise ShipError(f"refusing to write symlinked ship state path: {state_file}")
    if _state_file_has_kv(state_file):
        raise ShipError("ship initial state is create-if-absent only; refusing to overwrite existing state")
    _validate_seed_identity_args(args)
    fields = _seed_initial_state_fields(args)
    _validate_seed_manifest(fields["MANIFEST_PATH"])
    for key, value in fields.items():
        if key != key.upper() or "=" in key:
            raise ShipError(f"invalid ship state key: {key}")
        _validate_ship_state_value(key=key, value=value)
    state_file.parent.mkdir(parents=True, exist_ok=True)
    tmp = state_file.with_suffix(state_file.suffix + ".tmp")
    if tmp.is_symlink():
        raise ShipError(f"refusing to write symlinked ship state temp path: {tmp}")
    with suppress(FileNotFoundError):
        tmp.unlink()
    data = "".join(f"{key}={fields[key]}\n" for key in INITIAL_SHIP_STATE_KEYS)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd: int | None = None
    try:
        fd = os.open(tmp, flags, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            fd = None
            _ = handle.write(data)
        _ = tmp.replace(state_file)
    except FileExistsError as exc:
        raise ShipError(f"refusing to overwrite existing ship state temp file: {tmp}") from exc
    finally:
        if fd is not None:
            os.close(fd)
        with suppress(OSError):
            if tmp.exists() and not tmp.is_symlink():
                tmp.unlink()


def build_seed_initial_state_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Seed initial ship-pr state")
    _ = parser.add_argument("--tmpdir", required=True)
    _ = parser.add_argument("--state-file")
    _ = parser.add_argument("--branch", required=True)
    _ = parser.add_argument("--issue", required=True)
    _ = parser.add_argument("--repo", required=True)
    _ = parser.add_argument("--run-id", required=True)
    _ = parser.add_argument("--manifest-path", default="")
    _ = parser.add_argument("--tool-label", default="")
    _ = parser.add_argument("--merge", default="false")
    _ = parser.add_argument("--draft", default="false")
    _ = parser.add_argument("--forked", default="false")
    _ = parser.add_argument("--repo-unavailable", default="false")
    _ = parser.add_argument("--deferred", default="false")
    _ = parser.add_argument("--no-admin-fallback", default="false")
    _ = parser.add_argument("--no-logs-commit", default="false")
    _ = parser.add_argument("--expected-session-id", default="")
    _ = parser.add_argument("--expected-tmpdir-basename-prefix", default="")
    _ = parser.add_argument("--stall-tracking", default="false")
    _ = parser.add_argument("--stall-step", default="")
    _ = parser.add_argument("--bail-reason", default="")
    _ = parser.add_argument("--bail-failure-detail-log", default="")
    return parser


def seed_initial_state_main(argv: list[str] | None = None) -> int:
    parser = build_seed_initial_state_parser()
    try:
        args = parser.parse_args(argv)
        _write_initial_ship_state(args)
        return 0
    except SystemExit as exc:
        return int(exc.code or 1)
    except ShipError as exc:
        print(f"ship seed-initial-state: {exc}", file=sys.stderr)
        return 2
