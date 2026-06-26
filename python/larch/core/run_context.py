"""Frozen run context passed through ship-pr phases."""

from __future__ import annotations

import os
from dataclasses import dataclass, fields, replace
from pathlib import Path


def _env_bool(*, env: dict[str, str], key: str, default: bool = False) -> bool:
    raw = env.get(key)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(*, env: dict[str, str], key: str) -> int | None:
    raw = env.get(key, "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _state_value(*, path: str | None, key: str) -> str:
    if not path:
        return ""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""
    prefix = f"{key}="
    value = ""
    for line in text.splitlines():
        if line.startswith(prefix):
            value = line.removeprefix(prefix)
    return value


def _state_bool(*, path: str | None, key: str) -> bool:
    return _state_value(path=path, key=key).strip().lower() in {"1", "true", "yes", "on"}


def _state_int(*, path: str | None, key: str) -> int:
    raw = _state_value(path=path, key=key).strip()
    try:
        return int(raw)
    except ValueError:
        return 0


@dataclass(frozen=True)
class RunContext:
    branch: str
    issue: str
    repo: str
    run_id: str
    tmpdir: str
    merge: bool
    draft: bool
    forked: bool
    manifest_path: str
    tool_label: str
    no_admin_fallback: bool
    repo_unavailable: bool
    pr_number: int | None = None
    state_file: str | None = None
    no_logs_commit: bool = False
    merge_result: str = ""
    pr_closed: bool = False
    design_only_done: bool = False
    stall_tracking: bool = False
    stall_step: str = ""
    bail_needs_user_input: bool = False
    done_rename_applied: bool = False
    issue_number: str = ""
    pr_title: str = ""
    pr_url: str = ""
    expected_session_id: str = ""
    expected_tmpdir_basename_prefix: str = ""
    deferred: bool = False
    plan_file: str = ""
    summary: str = ""
    mermaid: str = ""
    test_plan: str = ""
    final_bail_reason: str = ""
    codex_present: bool = False
    cursor_present: bool = False
    ci_fix_rebase_pending: bool = False
    iteration: int = 0
    rebase_count: int = 0
    fix_attempts: int = 0
    transient_retries: int = 0
    oos_pending: bool = True

    @classmethod
    def from_env(cls, *, env: dict[str, str] | None = None) -> RunContext:
        source = dict(os.environ if env is None else env)
        tmpdir = source.get("IMPLEMENT_TMPDIR", "")
        branch = source.get("BRANCH_NAME") or source.get("BRANCH") or ""
        issue = source.get("ISSUE_NUMBER") or source.get("ISSUE") or ""
        pr_number = _env_int(env=source, key="PR_NUMBER")
        run_id = source.get("RUN_ID") or source.get("LARCH_RUN_ID", "")
        repo = source.get("REPO", "")
        no_logs = _env_bool(env=source, key="NO_LOGS_COMMIT") or _env_bool(
            env=source,
            key="LARCH_NO_LOGS_COMMIT",
        )
        default_plan_file: Path | None = Path(tmpdir) / "plan.txt" if tmpdir else None
        state_file = source.get("SHIP_PR_STATE_FILE") or None
        ci_fix_rebase_pending = _env_bool(env=source, key="CI_FIX_REBASE_PENDING") or _state_bool(
            path=state_file,
            key="CI_FIX_REBASE_PENDING",
        )
        return cls(
            branch=branch,
            issue=issue,
            repo=repo,
            run_id=run_id,
            tmpdir=tmpdir,
            merge=_env_bool(env=source, key="MERGE"),
            draft=_env_bool(env=source, key="DRAFT"),
            forked=_env_bool(env=source, key="FORKED_TARGET") or _env_bool(env=source, key="FORKED"),
            manifest_path=source.get("MANIFEST_PATH", ""),
            tool_label=source.get("TOOL_LABEL") or source.get("IMPLEMENT_TOOL", "codex"),
            no_admin_fallback=_env_bool(env=source, key="NO_ADMIN_FALLBACK"),
            repo_unavailable=_env_bool(env=source, key="REPO_UNAVAILABLE"),
            pr_number=pr_number,
            state_file=state_file,
            no_logs_commit=no_logs,
            merge_result=source.get("MERGE_RESULT", ""),
            pr_closed=_env_bool(env=source, key="PR_CLOSED"),
            design_only_done=_env_bool(env=source, key="DESIGN_ONLY_DONE"),
            stall_tracking=_env_bool(env=source, key="STALL_TRACKING") or _state_bool(path=state_file, key="STALL_TRACKING"),
            stall_step=source.get("STALL_STEP", "") or _state_value(path=state_file, key="STALL_STEP"),
            bail_needs_user_input=_env_bool(env=source, key="BAIL_NEEDS_USER_INPUT"),
            done_rename_applied=_env_bool(env=source, key="DONE_RENAME_APPLIED"),
            issue_number=issue,
            pr_title=source.get("PR_TITLE", ""),
            pr_url=source.get("PR_URL", ""),
            expected_session_id=source.get("EXPECTED_SESSION_ID", ""),
            expected_tmpdir_basename_prefix=source.get(
                "EXPECTED_TMPDIR_BASENAME_PREFIX",
                "",
            ),
            deferred=_env_bool(env=source, key="DEFERRED"),
            plan_file=source.get("PLAN_FILE", "")
            or (
                str(default_plan_file)
                if default_plan_file is not None and default_plan_file.is_file()
                else ""
            ),
            summary=source.get("PR_SUMMARY", ""),
            mermaid=source.get("PR_MERMAID", ""),
            test_plan=source.get("PR_TEST_PLAN", ""),
            final_bail_reason=source.get("FINAL_BAIL_REASON", ""),
            codex_present=_env_bool(env=source, key="CODEX_BINARY_FOUND"),
            cursor_present=_env_bool(env=source, key="CURSOR_BINARY_FOUND"),
            ci_fix_rebase_pending=ci_fix_rebase_pending,
            iteration=_env_int(env=source, key="ITERATION") or _state_int(path=state_file, key="ITERATION"),
            rebase_count=_env_int(env=source, key="REBASE_COUNT") or _state_int(path=state_file, key="REBASE_COUNT"),
            fix_attempts=_env_int(env=source, key="FIX_ATTEMPTS") or _state_int(path=state_file, key="FIX_ATTEMPTS"),
            transient_retries=_env_int(env=source, key="TRANSIENT_RETRIES") or _state_int(path=state_file, key="TRANSIENT_RETRIES"),
        )

    @property
    def branch_name(self) -> str:
        return self.branch

    @property
    def forked_target(self) -> bool:
        return self.forked

    def with_(self, **changes: object) -> RunContext:
        if "branch_name" in changes:
            changes["branch"] = changes.pop("branch_name")
        if "forked_target" in changes:
            changes["forked"] = changes.pop("forked_target")
        known: set[str] = {f.name for f in fields(self)}
        unknown: set[str] = set(changes) - known
        if unknown:
            msg = f"unknown RunContext fields: {sorted(unknown)}"
            raise TypeError(msg)
        return replace(self, **changes)
