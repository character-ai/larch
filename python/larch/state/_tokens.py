"""Token allowlists, safe-value rendering, and shared low-level utilities for stall recovery."""

# pyright: reportUnusedCallResult=false
# pyright: reportUnusedFunction=false

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from pathlib import Path

from larch import io as larch_io
from larch.core import config

# ---------------------------------------------------------------------------
# Scalar constants
# ---------------------------------------------------------------------------

CONTROL_CHAR_ORDINAL_LIMIT = 32

_REPO_ROOT = Path(__file__).resolve().parents[3]

# ---------------------------------------------------------------------------
# Default artifact file-name constants
# ---------------------------------------------------------------------------

_DEFAULT_CLASSIFICATION_FILE = "stall-recovery-classification.env"
_DEFAULT_ATTEMPTS_FILE = "stall-recovery-attempts.env"
_DEFAULT_ESCALATION_LEDGER = "stall-recovery-escalation-ledger.tsv"
_DEFAULT_ESCALATION_FALLBACK = "stall-recovery-escalation-fallback.tsv"
_DEFAULT_RECORD_FAILURE_MARKER = "stall-recovery-escalation-record-failure.env"
_DEFAULT_ROOT_CAUSE_FILE = "stall-recovery-root-cause.md"
_DEFAULT_BOUNDED_ROOT_CAUSE_FILE = "stall-recovery-bounded-root-cause.md"
_DEFAULT_SENSITIVE_CORPUS = "stall-recovery-sensitive-corpus.env"
_DEFAULT_ISSUE_INPUT = "stall-recovery-issue-input.md"
_DEFAULT_CHAT_PRINT = "stall-recovery-chat-print.md"
_DEFAULT_TITLE_FILE = "stall-recovery-title.txt"
_DEFAULT_OPERATOR_ACTION_RECORD = "stall-recovery-operator-action-record.md"
_DEFAULT_OPERATOR_ACTION_SENTINEL = "stall-recovery-operator-action.env"
_DEFAULT_TIER_A_ATTEMPTS_SLICE = "stall-recovery-tier-a-attempts.md"
_DEFAULT_TIER_A_ESCALATION_SLICE = "stall-recovery-tier-a-escalation.md"
_DEFAULT_TIER_A_ROOT_CAUSE_SLICE = "stall-recovery-tier-a-root-cause.md"
_DEFAULT_TIER_B_ATTEMPTS_SLICE = "stall-recovery-bounded-attempts.md"
_DEFAULT_TIER_B_ESCALATION_SLICE = "stall-recovery-bounded-escalation-summary.md"
_DEFAULT_TIER_B_ROOT_CAUSE_SLICE = "stall-recovery-bounded-root-cause-public.md"

# ---------------------------------------------------------------------------
# Token allowlists
# ---------------------------------------------------------------------------

_OUTCOMES = frozenset({
    "failed-plan-write", "failed-publish", "failed-postplan", "failed-clarify",
    "failed-judge-panel", "failed-publish-tail", "approved", "approved-partition",
})
_GENERIC_SITES = frozenset({
    "step2b", "gate-b", "step3-review", "discussion-round2", "step5c",
    "design-publish", "clarify-loop", "judge-panel", "decompose-panel",
})
_COMMON_SITES = frozenset({
    "step3", "step5", "step5-self-review", "step5-mav", "step6", "step8", "step18a",
    "review-loop", "lint-fix-loop", "ship-pr", "ship-pr-ci-initial", "ship-pr-ci-merge",
    "ship-pr-ci-per-job", "ship-pr-internal", "recovery-inline",
})
_GENERIC_TRIGGERS = frozenset({
    "main-agent-apply-required", "postplan-operator-required", "exhausted", "failed",
    "unavailable", "skipped-cycle-cap", "postplan-failed", "publish-tail-failed",
    "plan-write-failed", "publish-failed", "panel-failed", "panel-init-failed", "tally-error",
    "degraded-empty-collector", "judge-panel-collapse", "decompose-panel-retry-exhausted",
})
_COMMON_TRIGGERS = frozenset({
    "main-agent-required", "coder-main-agent-required", "main-agent-vote-required",
    "fix-attempts-exhausted", "design-flaw", "escalate", "all-vendors-failed",
    "ci-fix-exhausted", "first-fixer-non-health", "local-unfixable",
    "ship-pr-internal-lint-fix", "lint-fix-main-agent-required", "step2-impl",
    "step8-shippr", "dispatch-failed",
})
_GENERIC_BAILS = frozenset({
    "failed-plan-write", "failed-publish", "failed-postplan", "failed-clarify",
    "failed-judge-panel", "failed-publish-tail", "clarify-hard-halt", "postplan-failed",
    "publish-failed", "publish-tail-failed", "plan-write-failed", "judge-panel-collapse",
    "decompose-panel-retry-exhausted", "validator-autofix-exhausted",
    "validator-autofix-failed", "validator-autofix-unavailable",
    "validator-autofix-skipped-cycle-cap", "operator-action", "panel-init-failed",
})
_GENERIC_STEPS = frozenset({
    "validator", "postplan", "publish", "clarify", "panel", "judge-panel", "step2b", "step3", "step5c",
})
_GENERIC_PHASES = frozenset({
    "plan-write", "publish", "postplan", "clarify-loop", "judge-panel", "validation", "teardown",
})
_COMMON_PHASES = frozenset({
    "checks", "review", "implementation", "impl", "step2", "step5", "step8", "ship", "ship-pr",
    "pr-prep", "pr-create", "ci-initial", "ci-merge", "evaluate-failure", "force-push-gate",
    "bump", "merge", "postmerge", "rebase-failed",
})
_GENERIC_SOURCE_SCRIPTS = frozenset({
    "split-path", "design-publish", "design-step3-review", "design-step5c",
    "clarify-loop", "prompt-step", "validator", "postplan", "decompose-panel", "bash", "python",
})
_DISPATCH_BAIL_TOKENS = frozenset({
    "branch-changed", "cap_hit", "codex-runtime-failure", "cursor-bailed-no-reason",
    "cursor-modified-history", "cursor-runtime-failure", "detached-head-prohibited",
    "dirty-state-after-timeout", "interactive-subprocess-unsupported", "main-branch-post-dispatch",
    "main-branch-prohibited", "manifest-missing", "manifest-oos-materialization-failed",
    "manifest-schema-invalid", "protected-path-modified", "qa-pending-missing",
    "redactor-not-executable", "resume-incompatible", "submodule-dirty",
    "wrapper-validation-failure", "orchestrator-envelope-invalid",
})

# ---------------------------------------------------------------------------
# Shared I/O utilities
# ---------------------------------------------------------------------------


def emit(*, key: str, value: object) -> None:
    print(f"{key}={value}")


def read_kv(*, path: Path, key: str, default: str = "") -> str:
    return larch_io.read_kv(path=path, key=key, default=default, first_match=False, cr_strip="strip", on_error_default=False)


def write_kvs(*, path: Path, values: Mapping[str, object]) -> None:
    larch_io.write_kvs(path=path, values=values)


# ---------------------------------------------------------------------------
# Small shared utilities
# ---------------------------------------------------------------------------


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _issue_url_number(url: str) -> str | None:
    match: re.Match[str] | None = re.fullmatch(r"https://github.com/[^/#]+/[^/#]+/issues/(\d+)", url)
    return match.group(1) if match else None


def _validate_tmpdir_local_file(*, tmpdir: Path, file_path: Path) -> bool:
    if not file_path.is_absolute() or file_path.is_symlink() or not file_path.is_file():
        return False
    try:
        _ = file_path.resolve().relative_to(tmpdir.resolve())
    except ValueError:
        return False
    return True


def _validate_tmpdir_write_path(*, tmpdir: Path, path: Path) -> bool:
    if not path.is_absolute() or path.is_symlink():
        return False
    try:
        resolved_parent = path.parent.resolve(strict=True)
        resolved_tmpdir = tmpdir.resolve(strict=True)
    except OSError:
        return False
    if resolved_parent != resolved_tmpdir and resolved_tmpdir not in resolved_parent.parents:
        return False
    return not path.exists() or (path.is_file() and not path.is_symlink())


def _state_file_syntax_ok(path: Path) -> bool:
    if not path.is_file():
        return False
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            return False
    return True


def _read_state_file(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if path.is_file():
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                out[k] = v.strip("\r")
    return out


# STEP values written to .bg-wait-active by checks-commit-route sites (see
# dispatch_commit_route.py _checks_commit_route_marker), mapped to the
# STALL_STEP token stall-recovery classification expects for that site.
_CHECKS_MARKER_STALL_STEPS: dict[str, str] = {
    "implement-step3-checks": "3",
    "implement-step5-self-review": "5",
}


def _abandoned_checks_marker_stall_step(tmpdir: Path) -> str | None:
    """Detect a checks-commit-route .bg-wait-active marker left by a dead process.

    A process killed before it can run its own cleanup (external kill, not the
    in-process graceful timeout handled by _run_leg_with_timeout) never gets a
    chance to write STALL_TRACKING=true anywhere, so the normal stall layers
    all read false. The marker written before the risky leg starts is the only
    surviving evidence in that case. Returns the STALL_STEP token for the
    marked site only when the recorded PID is confirmed dead; returns None
    when there is no marker, it belongs to a non-checks site (step5-review,
    step8-ship), or its PID is still alive or unreadable.
    """
    marker = tmpdir / ".bg-wait-active"
    if not marker.is_file() or marker.is_symlink():
        return None
    values = _read_state_file(marker)
    stall_step = _CHECKS_MARKER_STALL_STEPS.get(values.get("STEP", ""))
    if stall_step is None:
        return None
    pid_raw = values.get("PID", "")
    if not pid_raw.isdigit():
        return None
    try:
        os.kill(int(pid_raw), 0)
    except ProcessLookupError:
        return stall_step
    except OSError:
        return None
    return None


def _text_file_contains(*, path: Path, needle: str) -> bool:
    if not path.is_file():
        return False
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return needle.lower() in text.lower()


# ---------------------------------------------------------------------------
# Token allowlist validation
# ---------------------------------------------------------------------------


def _safe_outcome(value: str) -> bool:
    return value in _OUTCOMES or (
        value.startswith("cancelled-") and bool(re.fullmatch(r"[A-Za-z0-9._:-]+", value))
    )


def _safe_step(value: str, *, generic: bool) -> bool:
    if generic and value in _GENERIC_STEPS:
        return True
    if value in {"bump-branch-guard", "merge-loop-iteration-cap", "rebase-failed"}:
        return True
    if re.fullmatch(r"[2-9]|1[0-5]", value):
        return True
    return bool(re.fullmatch(r"(8|9|10|11|12|13|14|15)([a-z][0-9]?|-[a-z0-9]+(-[a-z0-9]+)*)?", value))


def _safe_token(*, kind: str, value: str, generic: bool) -> bool:  # noqa: PLR0911
    if not value:
        return False
    if kind == "outcome":
        return _safe_outcome(value)
    if kind == "step":
        return _safe_step(value, generic=generic)
    if kind == "phase":
        return value in _COMMON_PHASES or (generic and value in _GENERIC_PHASES)
    if kind == "site":
        return value in _COMMON_SITES or (generic and value in _GENERIC_SITES)
    if kind == "trigger":
        return (
            value in _COMMON_TRIGGERS
            or (generic and value in _GENERIC_TRIGGERS)
            or bool(re.fullmatch(r"ci-local-unfixable:[A-Za-z0-9_,-]+", value))
        )
    if kind == "bail":
        return not value or (generic and value in _GENERIC_BAILS)
    if kind == "source-script":
        return generic and value in _GENERIC_SOURCE_SCRIPTS
    if kind == "root-cause":
        return value in {"larch-defect", "environment", "operator-action"}
    return False


def _safe_matched_pattern_value(value: str) -> str:
    allowed = {
        "no-stall", "no-match", "step-contract", "terminal-step", "rebase-transient",
        "protected-path-bail-token", "submodule-restricted-bail-token", "terminal-bail",
        "recovery-out-of-scope", "test-output", "lint-output", "dispatch-output",
        "dispatch-bail-token", "transient-output", "ci-fix-exhausted-with-detail",
        "same-cause-repeat", "fallback", "bail-token", "lint-fix-bail-token",
        "checks-leg-abandoned",
    }
    return value if value in allowed else "redacted"


def _reject_rawish_token_value(value: str) -> bool:
    if any(ch in value for ch in "\n\r "):
        return True
    return bool(re.search(r"[{}()\[\]<>|&;`$]", value))


def _reject_rawish_terminal_value(value: str) -> bool:
    if any(ch in value for ch in "\n\r"):
        return True
    lower = value.lower()
    return any(token in lower for token in ("http://", "https://", "github.com", "/users/", "/home/", " larch ", "```"))


def _safe_bail_reason_value(value: str, *, generic: bool) -> bool:
    if not value:
        return True
    if generic and value in _GENERIC_BAILS:
        return True
    if value in config.STALL_RECOVERY_BAIL_REASON_TOKENS:
        return True
    if re.fullmatch(r"ci-local-unfixable:[A-Za-z0-9_,-]+", value):
        return True
    expanded = {
        "adopted-issue-closed", "adopted-issue-is-pr", "branch-create-failed", "ci-fix-exhausted",
        "dirty-state-after-timeout", "dirty-tree", "fix-attempts-exhausted", "main-branch-post-dispatch",
        "orchestrator-envelope-invalid", "protected-path-edit-required-out-of-scope", "qa-loop-exceeded",
        "recovery-out-of-scope", "review-required", "run-flags-persist-failed", "ship-pr-internal-lint-fix",
        "tracking-init-failed", "wrapper-validation-failure", "branch-changed", "cap_hit",
        "codex-runtime-failure", "cursor-bailed-no-reason", "cursor-modified-history", "cursor-runtime-failure",
        "detached-head-prohibited", "interactive-subprocess-unsupported", "main-branch-prohibited",
        "manifest-missing", "manifest-oos-materialization-failed", "manifest-schema-invalid",
        "protected-path-modified", "protected-path-modification-required",
        "qa-pending-missing", "redactor-not-executable", "resume-incompatible",
        "submodule-dirty", "submodule-edit-required-out-of-scope", "local-unfixable", "checks-failed",
        "checks-timeout", "ci-health-failed", "ci-timeout", "ci-status-error", "ci-too-many-rebases",
        "no-fix-path", "main-agent-required", "coder-main-agent-required", "main-agent-vote-required",
    }
    return value in expanded


def _safe_source_script_value(value: str, *, generic: bool) -> bool:
    if value in {"codex", "cursor", "claude", "bash", "python", "ship-pr", "lint-fix-loop", "run-step5-review"}:
        return True
    return generic and value in _GENERIC_SOURCE_SCRIPTS


def _render_safe_bail_reason_value(value: str, *, generic: bool) -> str:
    if not value:
        return ""
    return value if _safe_bail_reason_value(value, generic=generic) else "redacted"


def _render_safe_source_script_value(value: str, *, generic: bool) -> str:
    if not value:
        return ""
    return value if _safe_source_script_value(value, generic=generic) else "redacted"


# ---------------------------------------------------------------------------
# Safe-value rendering helpers used by classify and report
# ---------------------------------------------------------------------------


def _safe_class_value(value: str) -> str:
    allowed = {
        "transient-infra", "test-failure", "lint-failure", "dispatch-failure", "protected-path",
        "submodule-restricted", "ci-fix-exhausted", "same-cause-repeat", "contract-failure", "unrecoverable",
        "environment", "operator-action", "larch-defect", "",
    }
    return value if value in allowed else "unrecoverable"


def _safe_step_value(value: str) -> str:
    if _safe_step(value, generic=True):
        return value
    return value if value == "unknown" else "unknown"


def _safe_phase_value(value: str) -> str:
    if _safe_token(kind="phase", value=value, generic=True):
        return value
    return value if value == "unknown" else "unknown"


def _safe_dispatcher_value(value: str, *, generic: bool = False) -> str:
    if not value:
        return "unknown"
    if value in {"codex", "cursor", "claude", "bash", "python", "ship-pr", "lint-fix-loop", "run-step5-review"}:
        return value
    if generic and value in _GENERIC_SOURCE_SCRIPTS:
        return value
    return "redacted"


def _safe_bail_value(value: str) -> str:
    if not value:
        return "none"
    return value if _safe_bail_reason_value(value, generic=True) else "redacted"


def _safe_simple_token(value: str, *, fallback: str = "redacted") -> str:
    return value if value and re.fullmatch(r"[A-Za-z0-9._:-]+", value) else fallback


# ---------------------------------------------------------------------------
# Report label helpers
# ---------------------------------------------------------------------------


def _safe_title_summary(summary: str) -> str:
    value = summary.strip()
    if not value or any(ch in value for ch in "\r\n"):
        return ""
    lower = value.lower()
    if value.startswith(("/", "#")) or ".." in value or "`" in value or "<!-- larch:" in value:
        return ""
    if "github.com" in lower or "/pull/" in lower or "larch-logs/" in value:
        return ""
    if any(ord(ch) < CONTROL_CHAR_ORDINAL_LIMIT for ch in value):
        return ""
    if re.search(r"(^|\s)[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+", value):
        return ""
    return value


def _report_skill_label(*, profile: str, prefix: str) -> str:
    if profile != "generic":
        return "/implement"
    if prefix == "design-failure":
        return "/design"
    if prefix:
        return f"/{prefix.split('-', 1)[0]}"
    return "/implement"
