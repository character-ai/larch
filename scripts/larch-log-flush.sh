#!/usr/bin/env bash
# larch-log-flush.sh — best-effort explicit flush for active /implement runs.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"

if [ -z "${IMPLEMENT_TMPDIR:-}" ]; then
    exit 0
fi

if [ "${LARCH_NO_LOGS_COMMIT:-false}" = "true" ]; then
    exit 0
fi

if [ -e "$IMPLEMENT_TMPDIR/post-merge-sentinel" ]; then
    exit 0
fi

session_id_file="$IMPLEMENT_TMPDIR/session-id"
if [ ! -s "$session_id_file" ]; then
    exit 0
fi

run_id="$(tr -d '\r\n' < "$session_id_file" 2>/dev/null || true)"
if [ -z "$run_id" ]; then
    exit 0
fi

issue_log="$IMPLEMENT_TMPDIR/execution-issues.md"
sentinel="$IMPLEMENT_TMPDIR/.execution-issues-flushed.sha"
checkpoint="$IMPLEMENT_TMPDIR/.execution-issues-step7a-reached"
batch_path="$IMPLEMENT_TMPDIR/larch-logs/implement/$run_id/execution-issues.ndjson"
if [ -s "$issue_log" ] && { [ -f "$checkpoint" ] || [ -f "$sentinel" ] || [ -f "$batch_path" ]; }; then
    "$SCRIPT_DIR/../skills/implement/scripts/flush-execution-issues.sh" \
        --log-root "$IMPLEMENT_TMPDIR/larch-logs" \
        --run-id "$run_id" \
        --issue-log "$issue_log" \
        --step-label commit-tail \
        --source-label "execution-issues.md commit-tail" \
        >/dev/null 2>&1 || true
fi

# Capture the commit's stdout contract so a secret-scrub warning is not lost:
# larch-log.sh commit emits SECRET_SCRUB_VIOLATIONS=<n> when the pre-flush gate
# redacted a secret. This script's stderr IS surfaced by its caller (unlike the
# commit's own, which is quieted), so re-print the warning here.
flush_commit_out="$("$SCRIPT_DIR/larch-log.sh" commit \
    --log-root "$IMPLEMENT_TMPDIR/larch-logs" \
    --skill implement \
    --run-id "$run_id" 2>/dev/null)" || {
    printf 'larch-log-flush.sh: warn — larch-log commit failed for run %s (continuing)\n' "$run_id" >&2
}
flush_scrub_n="$(printf '%s\n' "${flush_commit_out:-}" | sed -n 's/^SECRET_SCRUB_VIOLATIONS=//p' | tail -1)"
case "${flush_scrub_n:-}" in ''|*[!0-9]*) flush_scrub_n=0 ;; esac
if [ "$flush_scrub_n" -gt 0 ]; then
    printf 'larch-log-flush.sh: SECURITY WARNING — scrub-log-secrets.sh redacted %s secret-shaped value(s) from run %s logs before flush; ROTATE the affected credential(s)\n' "$flush_scrub_n" "$run_id" >&2
fi

exit 0
