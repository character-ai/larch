#!/usr/bin/env bash
# cleanup.sh — Remove stale larch session temp directories by age.
#
# Outputs (KEY=value on stdout):
#   SESSION_COUNT=<N>      Number of running claude processes detected (informational).
#   CACHE_REMOVED=<N>      Entries removed from ~/.cache/larch/sessions/.
#   TMP_REMOVED=<N>        Entries removed from /tmp matching larch patterns.
#   SYMLINKS_REMOVED=<N>   Dangling current-design-env-*.sh symlinks removed.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init

stat_mtime() {
    local file="$1"
    local mt

    if mt=$(stat -c '%Y' -- "$file" 2>/dev/null) && [[ "$mt" =~ ^[0-9]+$ ]]; then
        printf '%s\n' "$mt"
        return 0
    fi
    if mt=$(stat -f '%m' -- "$file" 2>/dev/null) && [[ "$mt" =~ ^[0-9]+$ ]]; then
        printf '%s\n' "$mt"
        return 0
    fi
    printf '0\n'
    return 0
}

newest_activity_mtime() {
    local entry="$1"
    local newest path mt
    local paths

    newest=$(stat_mtime "$entry")
    if ! paths=$(find "$entry" -mindepth 1 -maxdepth 5 -print 2>/dev/null); then
        larch_err "Warning: failed to scan session activity for '$entry'; skipping deletion."
        return 1
    fi

    while IFS= read -r path; do
        [ -n "$path" ] || continue
        mt=$(stat_mtime "$path")
        if [ "$mt" -gt "$newest" ]; then
            newest="$mt"
        fi
    done <<< "$paths"
    printf '%s\n' "$newest"
}

parse_retention_days() {
    local raw="${LARCH_CLEANUP_RETENTION_DAYS:-7}"
    if [[ "$raw" =~ ^[1-9][0-9]*$ ]]; then
        printf '%s\n' "$raw"
        return 0
    fi
    larch_err "Warning: invalid LARCH_CLEANUP_RETENTION_DAYS='${raw}'; using 7."
    printf '7\n'
}

RETENTION_DAYS=$(parse_retention_days)
NOW=$(date +%s 2>/dev/null || true)
if ! [[ "$NOW" =~ ^[0-9]+$ ]]; then
    larch_err "Error: failed to determine the current epoch time; refusing cleanup."
    exit 1
fi
CUTOFF=$((NOW - RETENTION_DAYS * 86400))

# --- Session count (informational only) ---------------------------------------
SESSION_COUNT=0
SESSION_COUNT=$(pgrep -x claude 2>/dev/null | wc -l | tr -d ' ') || SESSION_COUNT=0
emit_kv SESSION_COUNT "$SESSION_COUNT"

should_remove_by_age() {
    local entry="$1"
    local newest

    newest=$(newest_activity_mtime "$entry") || return 1
    [ "$newest" -lt "$CUTOFF" ]
}

# --- Clean ~/.cache/larch/sessions/ -------------------------------------------
CACHE_DIR="${XDG_CACHE_HOME:-${HOME}/.cache}/larch/sessions"
CACHE_REMOVED=0

if [[ -d "$CACHE_DIR" ]]; then
    while IFS= read -r -d $'\0' entry; do
        [[ -d "$entry" ]] || continue
        if should_remove_by_age "$entry"; then
            rm -rf "$entry"
            (( CACHE_REMOVED++ )) || true
        fi
    done < <(find "$CACHE_DIR" -mindepth 1 -maxdepth 1 -print0 2>/dev/null) || true
fi

emit_kv CACHE_REMOVED "$CACHE_REMOVED"

# --- Clean /tmp larch patterns -------------------------------------------------
TMP_REMOVED=0
TMP_ROOT="${LARCH_TEST_TMP_ROOT:-/tmp}"
TMP_PATTERNS=(
    "claude-implement-*"
    "claude-fix-issue-*"
    "claude-review-*"
    "claudin-review-*"
    "claude-issue-test"
    "wait-reviewers-*"
    "test-health-empty-caller-env-*"
    "test-health-explicit-false-*"
    "test-health-explicit-true-*"
    "test-session-setup-*"
    "larch-*"
    "larch3-fresh"
    "larch3-plan-review-prompts.sh"
    "larch4-review.diff"
    "check-review-bogus.err"
    "commit-msg-*-review.txt"
    "commit-msg-review-*.txt"
    "cr-debug-design"
    "issue-*-design-comment.md"
)

for pattern in "${TMP_PATTERNS[@]}"; do
    for entry in "$TMP_ROOT"/${pattern}; do
        [[ -e "$entry" || -L "$entry" ]] || continue
        if [[ -d "$entry" ]]; then
            if should_remove_by_age "$entry"; then
                rm -rf "$entry"
                (( TMP_REMOVED++ )) || true
            fi
        elif [[ -f "$entry" ]]; then
            if [ "$(stat_mtime "$entry")" -lt "$CUTOFF" ]; then
                rm -f "$entry"
                (( TMP_REMOVED++ )) || true
            fi
        fi
    done
done

emit_kv TMP_REMOVED "$TMP_REMOVED"

# --- Reap dangling current-design-env-*.sh symlinks ---------------------------
SYMLINKS_REMOVED=0
SESSIONS_PARENT="${XDG_CACHE_HOME:-${HOME}/.cache}/larch/sessions"
if [[ -d "$SESSIONS_PARENT" ]]; then
    while IFS= read -r -d $'\0' link; do
        [[ -L "$link" ]] || continue
        [[ -e "$link" ]] && continue
        rm -f "$link"
        (( SYMLINKS_REMOVED++ )) || true
    done < <(find "$SESSIONS_PARENT" -maxdepth 1 -name 'current-design-env-*.sh' -type l -print0 2>/dev/null) || true
fi

emit_kv SYMLINKS_REMOVED "$SYMLINKS_REMOVED"

# --- Summary ------------------------------------------------------------------
larch_err ""
larch_err "Cleanup complete:"
larch_err "  ~/.cache/larch/sessions/: $CACHE_REMOVED entries removed"
larch_err "  /tmp (larch patterns):    $TMP_REMOVED entries removed"
larch_err "  dangling design-env links: $SYMLINKS_REMOVED removed"
