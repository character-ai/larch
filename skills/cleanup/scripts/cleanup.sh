#!/usr/bin/env bash
# cleanup.sh — Remove leftover larch session temp directories.
#
# Outputs (KEY=value on stdout):
#   SESSION_COUNT=<N>      Number of running claude processes detected.
#   CACHE_REMOVED=<N>      Entries removed from ~/.cache/larch/sessions/.
#   TMP_REMOVED=<N>        Entries removed from /tmp matching larch patterns.
#
# Exits non-zero when multiple Claude sessions are detected (no cleanup performed).

set -euo pipefail

# --- Singleton guard -----------------------------------------------------------
# Count running 'claude' processes. pgrep -x matches the exact binary name.
SESSION_COUNT=0
SESSION_COUNT=$(pgrep -x claude 2>/dev/null | wc -l | tr -d ' ') || SESSION_COUNT=0

echo "SESSION_COUNT=$SESSION_COUNT"

if [[ "$SESSION_COUNT" -gt 1 ]]; then
    echo "**⚠ cleanup: $SESSION_COUNT Claude sessions detected. Aborting to protect active session state.**" >&2
    PIDS=$(pgrep -x claude 2>/dev/null | tr '\n' ' ' || true)
    echo "  Active PIDs: $PIDS" >&2
    exit 1
fi

# --- Clean ~/.cache/larch/sessions/ -------------------------------------------
# Skip dirs with a .larch-keepalive file to protect any active session
# (applies even when SESSION_COUNT == 1, i.e. only this Claude is running).
CACHE_DIR="${XDG_CACHE_HOME:-${HOME}/.cache}/larch/sessions"
CACHE_REMOVED=0

if [[ -d "$CACHE_DIR" ]]; then
    while IFS= read -r -d $'\0' entry; do
        [[ -d "$entry" ]] || continue
        if [[ -f "$entry/.larch-keepalive" ]]; then
            continue  # skip active session
        fi
        rm -rf "$entry"
        (( CACHE_REMOVED++ )) || true
    done < <(find "$CACHE_DIR" -mindepth 1 -maxdepth 1 -print0 2>/dev/null) || true
fi

echo "CACHE_REMOVED=$CACHE_REMOVED"

# --- Clean /tmp larch patterns -------------------------------------------------
TMP_REMOVED=0
TMP_PATTERNS=(
    "claude-implement-*"
    "claude-fix-issue-*"
    "claude-review-*"
    "claudin-review-*"   # historical typo prefix from early larch sessions
    "claude-issue-test"
    "wait-reviewers-*"
    "test-health-check-gemini-empty-*"
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
    # Guard against non-matching glob: skip if entry does not exist.
    for entry in /tmp/${pattern}; do
        [[ -e "$entry" || -L "$entry" ]] || continue
        # session-setup.sh falls back to /tmp when ~/.cache is unwritable;
        # the same .larch-keepalive sentinel applies here.
        [[ -d "$entry" && -f "$entry/.larch-keepalive" ]] && continue
        rm -rf "$entry"
        (( TMP_REMOVED++ )) || true
    done
done

echo "TMP_REMOVED=$TMP_REMOVED"

# --- Summary ------------------------------------------------------------------
echo ""
echo "Cleanup complete:"
echo "  ~/.cache/larch/sessions/: $CACHE_REMOVED entries removed"
echo "  /tmp (larch patterns):    $TMP_REMOVED entries removed"
