#!/usr/bin/env bash
# Run project-local relevant checks with bounded green-path stdout.

set -euo pipefail
LC_ALL=C

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init

SITE=""
TMPDIR_ARG="${IMPLEMENT_TMPDIR:-${REVIEW_TMPDIR:-}}"

fail() {
    local reason="$1"
    local code="${2:-1}"
    emit "STATUS=fail FAILURE_REASON=$reason"
    exit "$code"
}

usage() {
    larch_err "usage: run-relevant-checks-captured.sh --site <label> [--tmpdir <path>]"
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
    local prefix=""

    [[ -n "$tmpdir" && "$tmpdir" == /* ]] || return 1
    [[ -d "$tmpdir" && ! -L "$tmpdir" ]] || return 1
    canonical=$(canonical_dir "$tmpdir") || return 1

    case "$(basename "$canonical")" in
        claude-implement-*) prefix="claude-implement" ;;
        claude-review-*) prefix="claude-review" ;;
        *) return 1 ;;
    esac

    # Accept canonical XDG cache root AND /tmp fallback roots that
    # session-setup.sh uses when the cache root is unwritable. macOS resolves
    # /tmp -> /private/tmp; mktemp may emit either form, so canonicalize each
    # candidate and try every one. The basename guard above already pins this
    # to claude-implement-* / claude-review-* dirs, so foreign /tmp dirs are
    # not accepted just because /tmp is on the allow-list.
    # Cache sessions root: descendant matching is fine (operators may nest
    # custom XDG_CACHE_HOME paths). /tmp fallback roots: require the canonical
    # session dir to be a DIRECT child of the canonical root — session-setup.sh
    # only ever creates fallback session dirs that way, and accepting deeper
    # nesting would let an attacker-controlled or accidentally-shaped
    # /tmp/foo/claude-implement-bar pass.
    local accepted_root="" candidate="" canonical_parent=""
    canonical_parent=$(dirname -- "$canonical")
    if [[ -n "$cache_root" ]]; then
        local cache_sessions=""
        cache_sessions=$(canonical_dir "$cache_root/larch/sessions") || cache_sessions=""
        if [[ -n "$cache_sessions" ]] && under_root "$canonical" "$cache_sessions"; then
            accepted_root="$cache_sessions"
        fi
    fi
    if [[ -z "$accepted_root" ]]; then
        for candidate in "/tmp" "/private/tmp"; do
            local resolved=""
            resolved=$(canonical_dir "$candidate") || continue
            if [[ "$canonical_parent" == "$resolved" ]]; then
                accepted_root="$resolved"
                break
            fi
        done
    fi
    [[ -n "$accepted_root" ]] || return 1
    [[ "$prefix" == "claude-implement" || "$prefix" == "claude-review" ]] || return 1
    printf '%s\n' "$canonical"
}

TMPDIR_CANONICAL=$(validate_tmpdir "$TMPDIR_ARG") || fail "tmpdir-validation" 2

case "$SITE" in
    step3)
        IMPLEMENT_TMPDIR="$TMPDIR_CANONICAL" "$SCRIPT_DIR/token-ledger.sh" mark "Step 3 — checks first pass" || true
        IMPLEMENT_TMPDIR="$TMPDIR_CANONICAL" "$SCRIPT_DIR/timing-ledger.sh" mark "Step 3 — checks first pass" || true
        ;;
    step6)
        IMPLEMENT_TMPDIR="$TMPDIR_CANONICAL" "$SCRIPT_DIR/token-ledger.sh" mark "Step 6 — checks second pass" || true
        IMPLEMENT_TMPDIR="$TMPDIR_CANONICAL" "$SCRIPT_DIR/timing-ledger.sh" mark "Step 6 — checks second pass" || true
        ;;
esac

if [[ -n "${CLAUDE_PROJECT_DIR:-}" ]]; then
    REPO_ROOT="$CLAUDE_PROJECT_DIR"
else
    REPO_ROOT=$(git -C "$PWD" rev-parse --show-toplevel 2>/dev/null) || REPO_ROOT=""
fi
[[ -n "$REPO_ROOT" ]] || fail "repo-root-unresolved" 1

CHECK_SCRIPT="$REPO_ROOT/.claude/skills/relevant-checks/scripts/run-checks.sh"
if [[ ! -x "$CHECK_SCRIPT" ]]; then
    emit "STATUS=fail EXIT_CODE=127 FAILURE_REASON=missing-check-script"
    exit 127
fi

umask 077
LOG_DIR="$TMPDIR_CANONICAL/relevant-checks"
mkdir -p "$LOG_DIR" || fail "log-dir-create-failed" 1
# Reject a pre-existing symlink at LOG_DIR — TMPDIR_CANONICAL is a larch
# session dir but a same-user attacker could pre-place a symlink. fail-closed.
# Use an `if` block, not `[[ ]] && fail` — under `set -e` the latter exits 1
# when LOG_DIR is NOT a symlink (the `&&` list's overall non-zero exit trips
# `set -e`). The `if` form makes the success branch a no-op.
if [[ -L "$LOG_DIR" ]]; then
    fail "log-dir-symlink-rejected" 1
fi
chmod 700 "$LOG_DIR" || fail "log-dir-chmod-failed" 1

# Allocate a unique attempt log under LOG_DIR. Distinguish collision (file
# already exists at this attempt index — bump the counter and retry) from
# hard failure (unwritable, quota-exceeded, out-of-inodes — emit a structured
# failure envelope and bail). Cap the attempt counter at a generous-but-fixed
# limit so a pathological state cannot loop forever.
attempt=1
LOG_FILE=""
while (( attempt <= 100 )); do
    LOG_FILE="$LOG_DIR/$SITE-$attempt.log"
    if (set -C; : > "$LOG_FILE") 2>/dev/null; then
        chmod 600 "$LOG_FILE" || fail "log-file-chmod-failed" 1
        break
    fi
    if [[ -e "$LOG_FILE" ]]; then
        # Collision at this attempt index — try the next one.
        attempt=$((attempt + 1))
        LOG_FILE=""
        continue
    fi
    # Non-collision failure (read-only mount, quota, ENOSPC, ...). Bail.
    fail "log-allocation" 1
done
[[ -n "$LOG_FILE" ]] || fail "log-allocation-attempt-cap" 1

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
        emit "RELEVANT_CHECKS_OK=true SITE=$SITE COVERAGE=$coverage WARN=agent-lint-missing"
    else
        emit "RELEVANT_CHECKS_OK=true SITE=$SITE COVERAGE=$coverage"
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
    emit "STATUS=fail FAILURE_REASON=redaction-failed"
    exit 1
fi
if ! "$SCRIPT_DIR/redact-tmpdir-paths.sh" < "$LOG_FILE" | "$SCRIPT_DIR/redact-secrets.sh" > "$REDACTED_LOG_FILE"; then
    rm -f "$REDACTED_LOG_FILE"
    emit "STATUS=fail FAILURE_REASON=redaction-failed"
    exit 1
fi
chmod 600 "$REDACTED_LOG_FILE"

emit_kv STATUS fail
emit_kv EXIT_CODE "$rc"
emit_kv LOG_FILE "$LOG_FILE"
emit_kv LOG_BYTES "$LOG_BYTES"
emit_kv PHASE "$phase"
emit_kv REDACTED_LOG_FILE "$REDACTED_LOG_FILE"
exit "$rc"
