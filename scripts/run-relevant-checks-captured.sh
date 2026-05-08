#!/usr/bin/env bash
# Run project-local relevant checks with bounded green-path stdout.

set -euo pipefail
LC_ALL=C

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

SITE=""
TMPDIR_ARG="${IMPLEMENT_TMPDIR:-${REVIEW_TMPDIR:-}}"

fail() {
    local reason="$1"
    local code="${2:-1}"
    printf 'STATUS=fail FAILURE_REASON=%s\n' "$reason"
    exit "$code"
}

usage() {
    echo "usage: run-relevant-checks-captured.sh --site <label> [--tmpdir <path>]" >&2
    exit 2
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --site)
            [[ $# -ge 2 ]] || usage
            SITE="$2"
            shift 2
            ;;
        --tmpdir)
            [[ $# -ge 2 ]] || usage
            TMPDIR_ARG="$2"
            shift 2
            ;;
        *)
            usage
            ;;
    esac
done

if [[ -z "$SITE" || ! "$SITE" =~ ^[A-Za-z0-9._-]+$ || "$SITE" == .* || "$SITE" == *..* ]]; then
    fail "site-validation" 2
fi

canonical_dir() {
    local path="$1"
    [[ -d "$path" ]] || return 1
    (cd "$path" 2>/dev/null && pwd -P)
}

under_root() {
    local path="$1"
    local root="$2"
    [[ "$path" == "$root" ]] || [[ "$path" == "$root"/* ]]
}

validate_tmpdir() {
    local tmpdir="$1"
    local canonical=""
    local cache_root="${XDG_CACHE_HOME:-${HOME:-}/.cache}"
    local sessions_root=""
    local prefix=""

    [[ -n "$tmpdir" && "$tmpdir" == /* ]] || return 1
    [[ -d "$tmpdir" && ! -L "$tmpdir" ]] || return 1
    canonical=$(canonical_dir "$tmpdir") || return 1
    [[ -n "$cache_root" ]] || return 1
    sessions_root=$(canonical_dir "$cache_root/larch/sessions") || return 1

    case "$(basename "$canonical")" in
        claude-implement-*) prefix="claude-implement" ;;
        claude-review-*) prefix="claude-review" ;;
        *) return 1 ;;
    esac

    under_root "$canonical" "$sessions_root" || return 1
    [[ "$prefix" == "claude-implement" || "$prefix" == "claude-review" ]] || return 1
    printf '%s\n' "$canonical"
}

TMPDIR_CANONICAL=$(validate_tmpdir "$TMPDIR_ARG") || fail "tmpdir-validation" 2

if [[ -n "${CLAUDE_PROJECT_DIR:-}" ]]; then
    REPO_ROOT="$CLAUDE_PROJECT_DIR"
else
    REPO_ROOT=$(git -C "$PWD" rev-parse --show-toplevel 2>/dev/null) || REPO_ROOT=""
fi
[[ -n "$REPO_ROOT" ]] || fail "repo-root-unresolved" 1

CHECK_SCRIPT="$REPO_ROOT/.claude/skills/relevant-checks/scripts/run-checks.sh"
if [[ ! -x "$CHECK_SCRIPT" ]]; then
    printf 'STATUS=fail EXIT_CODE=127 FAILURE_REASON=missing-check-script\n'
    exit 127
fi

umask 077
LOG_DIR="$TMPDIR_CANONICAL/relevant-checks"
mkdir -p "$LOG_DIR"
chmod 700 "$LOG_DIR"

attempt=1
while :; do
    LOG_FILE="$LOG_DIR/$SITE-$attempt.log"
    if (set -C; : > "$LOG_FILE") 2>/dev/null; then
        chmod 600 "$LOG_FILE"
        break
    fi
    attempt=$((attempt + 1))
done

if "$CHECK_SCRIPT" >"$LOG_FILE" 2>&1; then
    rc=0
else
    rc=$?
fi

has_precommit=false
has_agent_lint=false
has_agent_lint_warning=false
grep -q '=== Running pre-commit' "$LOG_FILE" && has_precommit=true
grep -q '=== Running agent-lint ===' "$LOG_FILE" && has_agent_lint=true
grep -q 'WARNING: agent-lint not found on PATH' "$LOG_FILE" && has_agent_lint_warning=true

if [[ "$rc" -eq 0 ]]; then
    coverage="changed-file-only"
    if [[ "$has_precommit" == "true" && "$has_agent_lint" == "true" ]]; then
        coverage="full"
    elif [[ "$has_precommit" == "false" && "$has_agent_lint" == "true" ]]; then
        coverage="post-check-only"
    fi
    if [[ "$has_agent_lint_warning" == "true" ]]; then
        printf 'RELEVANT_CHECKS_OK=true SITE=%s COVERAGE=%s WARN=agent-lint-missing\n' "$SITE" "$coverage"
    else
        printf 'RELEVANT_CHECKS_OK=true SITE=%s COVERAGE=%s\n' "$SITE" "$coverage"
    fi
    exit 0
fi

phase="unknown"
if [[ "$has_agent_lint" == "true" ]]; then
    phase="agent-lint"
elif [[ "$has_precommit" == "true" ]]; then
    phase="pre-commit"
fi

LOG_BYTES=$(wc -c < "$LOG_FILE" | tr -d '[:space:]')
REDACTED_LOG_FILE="$LOG_DIR/$SITE-$attempt.redacted.log"
if [[ ! -x "$SCRIPT_DIR/redact-tmpdir-paths.sh" || ! -x "$SCRIPT_DIR/redact-secrets.sh" ]]; then
    printf 'STATUS=fail FAILURE_REASON=redaction-failed\n'
    exit 1
fi
if ! "$SCRIPT_DIR/redact-tmpdir-paths.sh" < "$LOG_FILE" | "$SCRIPT_DIR/redact-secrets.sh" > "$REDACTED_LOG_FILE"; then
    rm -f "$REDACTED_LOG_FILE"
    printf 'STATUS=fail FAILURE_REASON=redaction-failed\n'
    exit 1
fi
chmod 600 "$REDACTED_LOG_FILE"

printf 'STATUS=fail\n'
printf 'EXIT_CODE=%s\n' "$rc"
printf 'LOG_FILE=%s\n' "$LOG_FILE"
printf 'LOG_BYTES=%s\n' "$LOG_BYTES"
printf 'PHASE=%s\n' "$phase"
printf 'REDACTED_LOG_FILE=%s\n' "$REDACTED_LOG_FILE"
exit "$rc"
