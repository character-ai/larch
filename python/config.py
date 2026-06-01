"""Tunables for the ship-pr Python rewrite (stdlib-only; no logic)."""

from __future__ import annotations

from typing import Final, Literal

# Exit codes (align with ship-pr / implement conventions)
EXIT_OK: Final = 0
EXIT_USAGE: Final = 2
EXIT_BAIL: Final = 4
EXIT_STALL: Final = 6
EXIT_TIMEOUT: Final = 124

# Subprocess / CI wait
SUBPROCESS_DEFAULT_TIMEOUT_SEC: Final = 1800
CI_WAIT_TIMEOUT_SEC: Final = 1800
CI_WAIT_POLL_INTERVAL_SEC: Final = 10
CI_WAIT_EMPTY_CHECKS_GRACE_SEC: Final = 0

# Transient retry (parity with scripts/lib-net.sh)
TRANSIENT_RETRY_MAX_ATTEMPTS: Final = 3
TRANSIENT_RETRY_BACKOFF_SEC: Final = (2, 4)

# Loop caps
RCC_MAX_ITER_DEFAULT: Final = 3
CI_LOCAL_FIX_ITER_DEFAULT: Final = 6
WATERFALL_MAX_TIERS: Final = 3

# Fixer tier order (parity with ship-pr run_ci_fix_vendor)
FIXER_TIER_ORDER: Final[tuple[str, ...]] = ("cursor", "codex", "claude")

# Environment variable names
ENV_LARCH_SHIP_PR_IMPL: Final = "LARCH_SHIP_PR_IMPL"
ENV_LARCH_CI_LOCAL_FIX_ITER: Final = "LARCH_CI_LOCAL_FIX_ITER"
ENV_LARCH_NO_LOGS_COMMIT: Final = "LARCH_NO_LOGS_COMMIT"
ENV_LARCH_RUN_ID: Final = "LARCH_RUN_ID"
ENV_IMPLEMENT_TMPDIR: Final = "IMPLEMENT_TMPDIR"
ENV_LARCH_QUIET_DISABLE: Final = "LARCH_QUIET_DISABLE"

# Implementation selector values
SHIP_PR_IMPL_BASH: Final = "bash"
SHIP_PR_IMPL_PYTHON: Final = "python"

# Path / artifact templates (format with .format or str.replace as needed)
PATH_MANIFEST_TEMPLATE: Final = "{tmpdir}/manifest.json"
PATH_QA_PENDING_TEMPLATE: Final = "{tmpdir}/qa-pending.json"
PATH_QUIET_LOG_TEMPLATE: Final = "{tmpdir}/larch-quiet-{script}-{pid}.log"
PATH_JSONL_JOURNAL_TEMPLATE: Final = "{tmpdir}/larch-journal-{run_id}.jsonl"

# Redaction placeholders (must not match redact patterns)
REDACTED_TOKEN: Final = "<REDACTED-TOKEN>"
REDACTED_PRIVATE_KEY: Final = "<REDACTED-PRIVATE-KEY>"
REDACTED_TMPDIR: Final = "<TMPDIR>"
REDACTED_OPERATOR_REPO: Final = "<OPERATOR_REPO_PATH>"

# proc.run timeout handling
PROC_TIMEOUT_EXIT_CODE: Final = EXIT_TIMEOUT

ToolName = Literal["cursor", "codex", "claude"]

# Version bump / changelog (Phase 2 ports; not wired into live path until Phase 7)
BUMP_COMMIT_SUBJECT_TEMPLATE: Final = "Bump version to {version}"
CHANGELOG_COMMIT_SUBJECT_TEMPLATE: Final = "Update CHANGELOG for {version}"
SEMVER_RE: Final = r"^[0-9]+\.[0-9]+\.[0-9]+$"
PLUGIN_JSON_PATH: Final = ".claude-plugin/plugin.json"
CHANGELOG_DEFAULT_PATH: Final = "CHANGELOG.md"
DEFAULT_BUMP_FILES: Final = (".claude-plugin/plugin.json",)
DROP_BUMP_MAX_DEPTH: Final = 10
DROP_CHANGELOG_MAX_DEPTH: Final = 20
IDEMPOTENCY_DEPTH: Final = 3
BUMP_VERSION_ARMED_SENTINEL: Final = ".bump-version-armed"
APPLY_BUMP_MAX_RETRIES: Final = 10
TRANSPARENT_CHANGELOG_SUBJECT_PREFIX: Final = "Update CHANGELOG for "
TRANSPARENT_LARCH_LOGS_SUBJECT_PREFIX: Final = "chore(larch-logs): "
CLASSIFY_SCOPE_DIRS: Final[tuple[str, ...]] = ("skills", "agents")
ENV_LARCH_BUMP_FILES: Final = "LARCH_BUMP_FILES"
BUMP_VERSION_SKILL_PATH: Final = ".claude/skills/bump-version/SKILL.md"
APPLY_BUMP_ALLOWED_UNTRACKED_SUFFIXES: Final = (".launcher-stderr", ".redacted.log")
GIT_COMMIT_CO_AUTHORED_BY_TRAILER: Final = "Co-Authored-By: Claude Code <noreply@anthropic.com>"

# CI monitor loop (Phase 6)
CI_MONITOR_MAX_ITERATIONS: Final = 50
CI_MONITOR_MAX_REBASES: Final = 20
CI_MONITOR_MAX_FIX_ATTEMPTS: Final = 10
CI_MONITOR_FIX_WATERFALL_MAX_ATTEMPTS: Final = 3
CI_MONITOR_TRANSIENT_RERUN_MAX: Final = 1
CI_MONITOR_STATUS_FAILURE_BAIL: Final = 3
CI_MONITOR_LOG_TAIL_LINES: Final = 100
CI_FIX_ROLE: Final = "fix"
CI_FIXABLE_JOBS: Final[frozenset[str]] = frozenset({
    "lint",
    "lint-mermaid",
    "shellcheck",
    "test-harnesses",
    "agent-lint",
    "agnix",
    "smoke-dialectic",
    "agent-sync",
    "python-lint",
    "python-tests",
})
