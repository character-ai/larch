#!/usr/bin/env bash
# check-main-sync.sh — Detect and resolve committed-but-unpushed larch-log
# flush commits on local main before a run starts.
#
# Checks whether local main is ahead of origin/main. If all ahead commits
# are larch-log flush commits (subject matches "chore(larch-logs): flush *"
# and all touched files are under "larch-logs/"), auto-resets local main
# to origin/main. If non-log commits are present, emits SYNC_STATUS=blocked
# and exits 1.
#
# Only meaningful when the current branch is main. On any other branch the
# script emits SYNC_STATUS=not-main and exits 0 immediately.
#
# Usage:
#   check-main-sync.sh
#
# Stdout contract:
#   SYNC_STATUS=ok           — local main is in sync with origin/main (0 ahead)
#   SYNC_STATUS=not-main     — not on main; check skipped
#   SYNC_STATUS=reset        — all ahead commits were flush commits; reset done
#   SYNC_STATUS=blocked      — ahead commits include non-log changes; blocked
#   SYNC_STATUS=probe-error  — git probe failed; unable to determine state
#   AHEAD_COUNT=<N>          — number of commits local main is ahead (when > 0)
#   ERROR=<message>          — when SYNC_STATUS=blocked or probe-error
#
# Exit codes:
#   0 — ok, not-main, or reset (run may proceed)
#   1 — blocked (non-log ahead commits; caller should abort)
#   2 — argument validation error or git probe failure

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init

while [ $# -gt 0 ]; do
    case "$1" in
        *)
            larch_errf 'check-main-sync.sh: unknown flag: %s\n' "$1"
            exit 2
            ;;
    esac
done

# Only applies to the main branch.
CURRENT_BRANCH=$(git symbolic-ref --short HEAD 2>/dev/null || echo "")
if [ "$CURRENT_BRANCH" != "main" ]; then
    emit_kv SYNC_STATUS not-main
    exit 0
fi

# Count commits local main is ahead of origin/main.
ahead_exit=0
AHEAD=$(git rev-list --count "origin/main..HEAD" 2>/dev/null) || ahead_exit=$?

if [ "$ahead_exit" -ne 0 ] || [ -z "$AHEAD" ]; then
    emit_kv SYNC_STATUS probe-error
    emit_kv ERROR "git rev-list failed or produced empty output (exit $ahead_exit)"
    exit 2
fi

# Normalize: a non-numeric result (shouldn't happen, but guard anyway).
case "$AHEAD" in
    ''|*[!0-9]*) AHEAD=0 ;;
esac

if [ "$AHEAD" -eq 0 ]; then
    emit_kv SYNC_STATUS ok
    emit_kv AHEAD_COUNT 0
    exit 0
fi

# Inspect the ahead commits. All must be larch-log flush commits.
_all_flushes=true
while IFS= read -r _subj; do
    case "$_subj" in
        "chore(larch-logs): flush "*) ;;
        *) _all_flushes=false; break ;;
    esac
done < <(git log origin/main..HEAD --format=%s 2>/dev/null || true)

# All touched files must be under larch-logs/.
_larch_log_diff_only=true
while IFS= read -r _f; do
    case "$_f" in
        "larch-logs/"*) ;;
        *) _larch_log_diff_only=false; break ;;
    esac
done < <(git diff --name-only origin/main HEAD 2>/dev/null || true)

if [ "$_all_flushes" = "true" ] && [ "$_larch_log_diff_only" = "true" ]; then
    # All ahead commits are larch-log flush commits. Reset to origin/main.
    git reset --hard origin/main >/dev/null 2>&1
    emit_kv SYNC_STATUS reset
    emit_kv AHEAD_COUNT "$AHEAD"
    exit 0
fi

# Non-log commits are present. Block the run.
emit_kv SYNC_STATUS blocked
emit_kv AHEAD_COUNT "$AHEAD"
emit_kv ERROR "local main is $AHEAD commit(s) ahead of origin/main with non-log changes; push or reconcile before re-running"
exit 1
