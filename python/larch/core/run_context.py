"""Frozen run context passed through ship-pr phases."""

from __future__ import annotations

import os
from dataclasses import dataclass, fields, replace
from pathlib import Path
from typing import Any, Mapping, Optional

from larch import io as larch_io


# -----------------------------------------------------------------------------
# Helpers for environment and state-file parsing
# -----------------------------------------------------------------------------

def _env_bool(env: Mapping[str, str], key: str, default: bool = False) -> bool:
    raw = env.get(key)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(env: Mapping[str, str], key: str) -> Optional[int]:
    raw = env.get(key, "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _read_state_file(path: Optional[Path]) -> dict[str, str]:
    """Read a state file and return a mapping of keys to values."""
    if path is None or not path.is_file():
        return {}
    try:
        raw = path.read_text(encoding="utf-8", errors="strict")
    except OSError:
        return {}
    # The larch_io.read_kv function expects a path and key, but we want all keys.
    # Since the original code used it per key, we'll implement a simple parser here.
    # Assuming the state file is a simple key=value format (one per line).
    result: dict[str, str] = {}
    for line in raw.splitlines():
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        result[key.strip()] = val.strip()
    return result


def _state_value(state: dict[str, str], key: str, default: str = "") -> str:
    return state.get(key, default)


def _state_bool(state: dict[str, str], key: str, default: bool = False) -> bool:
    raw = state.get(key)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _state_int(state: dict[str, str], key: str, default: int = 0) -> int:
    raw = state.get(key, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


# -----------------------------------------------------------------------------
# RunContext definition with declarative field resolution
# -----------------------------------------------------------------------------

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
    merge_method: str = "squash"

    # Field resolution rules: each entry maps a field name to a configuration.
    # The configuration is a dict with:
    #   - "env": environment variable name(s) – first found wins
    #   - "state": state file key(s) – used as fallback if no env value
    #   - "default": default value (if any)
    #   - "converter": function that takes (env_value, state_value) and returns the final value
    # If "converter" is absent, the value is resolved as:
    #     env_val if env_val is not None else state_val if state_val is not None else default
    _FIELD_SPECS = {
        "branch": {"env": ["BRANCH_NAME", "BRANCH"], "default": ""},
        "issue": {"env": ["ISSUE_NUMBER", "ISSUE"], "default": ""},
        "repo": {"env": ["REPO"], "default": ""},
        "run_id": {"env": ["RUN_ID", "LARCH_RUN_ID"], "default": ""},
        "tmpdir": {"env": ["IMPLEMENT_TMPDIR"], "default": ""},
        "merge": {"env": ["MERGE"], "default": False, "converter": lambda e, s: _env_bool({k: e for k in ("MERGE",)}, "MERGE", False) if e is not None else False},
        # We need a more flexible converter system. Let's just implement each field manually in from_env.
        # Actually, it's easier to keep a list of resolvers.
    }

    @classmethod
    def from_env(cls, *, env: Optional[Mapping[str, str]] = None) -> RunContext:
        """Build a RunContext from environment variables and the state file."""
        source = dict(os.environ if env is None else env)
        tmpdir = source.get("IMPLEMENT_TMPDIR", "")
        state_path = Path(source.get("SHIP_PR_STATE_FILE", "")) if source.get("SHIP_PR_STATE_FILE") else None
        state = _read_state_file(state_path)

        # Helper to resolve a value: first env (with optional aliases), then state (with optional aliases), then default.
        def resolve(
            env_keys: list[str],
            state_keys: list[str] | None = None,
            default: Any = "",
            converter: Optional[callable] = None,
        ) -> Any:
            # Check environment variables in order
            for key in env_keys:
                if key in source:
                    val = source[key]
                    if converter is not None:
                        # If converter is provided, it will handle the env value
                        # but we still need to pass the state value as fallback.
                        # We'll implement converter as (env_val, state_val) -> result.
                        # We'll call it with env_val and state_val (which we may need to fetch)
                        state_val = None
                        if state_keys:
                            for sk in state_keys:
                                if sk in state:
                                    state_val = state[sk]
                                    break
                        return converter(val, state_val)
                    return val
            # Fallback to state file
            if state_keys:
                for key in state_keys:
                    if key in state:
                        val = state[key]
                        if converter is not None:
                            return converter(None, val)
                        return val
            # Default
            if converter is not None:
                return converter(None, None)
            return default

        # Now define each field with its own resolver.
        # To keep it concise, we'll just write a series of assignments using the resolve function.
        # This is still cleaner than the original huge block.

        pr_number = _env_int(source, "PR_NUMBER")
        no_logs = _env_bool(source, "NO_LOGS_COMMIT") or _env_bool(source, "LARCH_NO_LOGS_COMMIT")
        forked = _env_bool(source, "FORKED_TARGET") or _env_bool(source, "FORKED")
        ci_fix_rebase_pending = _env_bool(source, "CI_FIX_REBASE_PENDING") or _state_bool(state, "CI_FIX_REBASE_PENDING")
        # Compute plan_file
        default_plan = Path(tmpdir) / "plan.txt" if tmpdir else None
        plan_file = source.get("PLAN_FILE", "")
        if not plan_file and default_plan and default_plan.is_file():
            plan_file = str(default_plan)

        # Build the dataclass instance
        return cls(
            branch=resolve(["BRANCH_NAME", "BRANCH"], default=""),
            issue=resolve(["ISSUE_NUMBER", "ISSUE"], default=""),
            repo=resolve(["REPO"], default=""),
            run_id=resolve(["RUN_ID", "LARCH_RUN_ID"], default=""),
            tmpdir=tmpdir,
            merge=_env_bool(source, "MERGE", False),
            draft=_env_bool(source, "DRAFT", False),
            forked=forked,
            manifest_path=source.get("MANIFEST_PATH", ""),
            tool_label=source.get("TOOL_LABEL") or source.get("IMPLEMENT_TOOL", "codex"),
            no_admin_fallback=_env_bool(source, "NO_ADMIN_FALLBACK", False),
            repo_unavailable=_env_bool(source, "REPO_UNAVAILABLE", False),
            pr_number=pr_number,
            state_file=source.get("SHIP_PR_STATE_FILE"),
            no_logs_commit=no_logs,
            merge_result=source.get("MERGE_RESULT", ""),
            pr_closed=_env_bool(source, "PR_CLOSED", False),
            design_only_done=_env_bool(source, "DESIGN_ONLY_DONE", False),
            stall_tracking=_env_bool(source, "STALL_TRACKING", False) or _state_bool(state, "STALL_TRACKING", False),
            stall_step=source.get("STALL_STEP", "") or _state_value(state, "STALL_STEP", ""),
            bail_needs_user_input=_env_bool(source, "BAIL_NEEDS_USER_INPUT", False),
            done_rename_applied=_env_bool(source, "DONE_RENAME_APPLIED", False),
            issue_number=resolve(["ISSUE_NUMBER", "ISSUE"], default=""),
            pr_title=source.get("PR_TITLE", ""),
            pr_url=source.get("PR_URL", ""),
            expected_session_id=source.get("EXPECTED_SESSION_ID", ""),
            expected_tmpdir_basename_prefix=source.get("EXPECTED_TMPDIR_BASENAME_PREFIX", ""),
            deferred=_env_bool(source, "DEFERRED", False),
            plan_file=plan_file,
            summary=source.get("PR_SUMMARY", ""),
            mermaid=source.get("PR_MERMAID", ""),
            test_plan=source.get("PR_TEST_PLAN", ""),
            final_bail_reason=source.get("FINAL_BAIL_REASON", ""),
            codex_present=_env_bool(source, "CODEX_BINARY_FOUND", False),
            cursor_present=_env_bool(source, "CURSOR_BINARY_FOUND", False),
            ci_fix_rebase_pending=ci_fix_rebase_pending,
            iteration=_env_int(source, "ITERATION") or _state_int(state, "ITERATION", 0),
            rebase_count=_env_int(source, "REBASE_COUNT") or _state_int(state, "REBASE_COUNT", 0),
            fix_attempts=_env_int(source, "FIX_ATTEMPTS") or _state_int(state, "FIX_ATTEMPTS", 0),
            transient_retries=_env_int(source, "TRANSIENT_RETRIES") or _state_int(state, "TRANSIENT_RETRIES", 0),
        )

    @property
    def branch_name(self) -> str:
        return self.branch

    @property
    def forked_target(self) -> bool:
        return self.forked

    def with_(self, **changes: object) -> RunContext:
        # Allow aliases for backward compatibility
        if "branch_name" in changes:
            changes["branch"] = changes.pop("branch_name")
        if "forked_target" in changes:
            changes["forked"] = changes.pop("forked_target")
        known = {f.name for f in fields(self)}
        unknown = set(changes) - known
        if unknown:
            raise TypeError(f"unknown RunContext fields: {sorted(unknown)}")
        return replace(self, **changes)
