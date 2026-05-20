#!/usr/bin/env bash
# refresh-run-logs.sh — Re-render and commit larch-log token/timing artifacts before a push.
# Exits 0 with no commit when the PR is already merged; fail-closed when the probe fails.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init

STATE_FILE=""
IMPL_TMPDIR=""

while [ $# -gt 0 ]; do
    case "$1" in
        --state-file)      STATE_FILE="${2:?--state-file requires a value}";      shift 2 ;;
        --implement-tmpdir) IMPL_TMPDIR="${2:?--implement-tmpdir requires a value}"; shift 2 ;;
        *) larch_errf 'refresh-run-logs.sh: unknown option: %s\n' "$1"; exit 1 ;;
    esac
done

[ -n "$STATE_FILE"  ] || { larch_errf 'refresh-run-logs.sh: --state-file is required\n'; exit 1; }
[ -n "$IMPL_TMPDIR" ] || { larch_errf 'refresh-run-logs.sh: --implement-tmpdir is required\n'; exit 1; }

# Fail-closed merge probe: missing state file → treat as merged.
[ -f "$STATE_FILE" ] || { emit "REFRESH_SKIPPED=true REASON=state-file-missing-fail-closed"; exit 0; }

kv() { awk -F= -v k="$1" '$1==k{print $2;exit}' "$STATE_FILE" 2>/dev/null || true; }

# All terminal merge outcomes short-circuit (post-merge safety property).
case "$(kv MERGE_RESULT)" in
    merged|admin_merged|already_merged) emit "REFRESH_SKIPPED=true REASON=post-merge"; exit 0 ;;
esac

run_id=$(kv RUN_ID)
[ -n "$run_id" ] || { emit "REFRESH_SKIPPED=true REASON=no-run-id"; exit 0; }
pr_url=$(kv PR_URL)

# Reject path-traversal characters in RUN_ID before it reaches git pathspecs.
case "$run_id" in
    */*|*'..'*) { emit "REFRESH_SKIPPED=true REASON=invalid-run-id"; exit 0; } ;;
esac

[ "$(kv NO_LOGS_COMMIT)" = "true" ] && { emit "REFRESH_SKIPPED=true REASON=no-logs-commit"; exit 0; }

# Load session env so token/timing report renderers can find their ledgers.
session_env="$IMPL_TMPDIR/session-env.sh"
if [ -f "$session_env" ]; then
    _rsk() { "$SCRIPT_DIR/read-session-env-key.sh" --file "$session_env" --key "$1" --default "" 2>/dev/null || true; }
    LARCH_TOKEN_SESSION_ID="$(_rsk LARCH_TOKEN_SESSION_ID)"; export LARCH_TOKEN_SESSION_ID
    LARCH_CLAUDE_SOURCE_FILE="$(_rsk LARCH_CLAUDE_SOURCE_FILE)"; export LARCH_CLAUDE_SOURCE_FILE
    LARCH_TIMING_LEDGER="$(_rsk LARCH_TIMING_LEDGER)"; export LARCH_TIMING_LEDGER
fi
export IMPLEMENT_TMPDIR="$IMPL_TMPDIR"

log_root="$IMPL_TMPDIR/larch-logs"
issue_log="$IMPL_TMPDIR/execution-issues.md"
sentinel="$IMPL_TMPDIR/.execution-issues-flushed.sha"
checkpoint="$IMPL_TMPDIR/.execution-issues-step7a-reached"
batch_path="$log_root/implement/$run_id/execution-issues.ndjson"

if [ -s "$issue_log" ] && { [ -f "$checkpoint" ] || [ -f "$sentinel" ] || [ -f "$batch_path" ]; }; then
    "$SCRIPT_DIR/../skills/implement/scripts/flush-execution-issues.sh" \
        --log-root "$log_root" \
        --run-id "$run_id" \
        --issue-log "$issue_log" \
        --step-label pre-push \
        --source-label "execution-issues.md pre-push refresh" \
        2>/dev/null || true
fi

if [ -n "$pr_url" ]; then
    "$SCRIPT_DIR/../skills/implement/scripts/write-final-report.sh" \
        --implement-tmpdir "$IMPL_TMPDIR" 2>/dev/null || true
fi

# Re-render and write token and timing reports.
"$SCRIPT_DIR/token-report.sh"  --full --format json --output "$IMPL_TMPDIR/token-report-refresh.json"  2>/dev/null || true
"$SCRIPT_DIR/larch-log.sh" write --log-root "$log_root" --skill implement --run-id "$run_id" \
    --batch token-report --input-file "$IMPL_TMPDIR/token-report-refresh.json" 2>/dev/null || true
"$SCRIPT_DIR/timing-report.sh" --full --format json --output "$IMPL_TMPDIR/timing-report-refresh.json" 2>/dev/null || true
"$SCRIPT_DIR/larch-log.sh" write --log-root "$log_root" --skill implement --run-id "$run_id" \
    --batch timing-report --input-file "$IMPL_TMPDIR/timing-report-refresh.json" 2>/dev/null || true
# Re-capture session transcript so CI-retry pushes carry the most recent turns.
# Use the already-exported LARCH_CLAUDE_SOURCE_FILE (set by the session-env block above
# when session-env.sh exists); falls back to empty string if missing, which causes the
# script to attempt fallback discovery. Redirect stdout so SESSION_TRANSCRIPT_STATUS does
# not pollute the caller's output stream.
"$SCRIPT_DIR/capture-session-transcript.sh" \
    --source-file "${LARCH_CLAUDE_SOURCE_FILE:-}" \
    --log-root "$log_root" \
    --skill implement \
    --run-id "$run_id" \
    --no-logs-commit "false" >/dev/null 2>&1 || true

# Commit via larch-log.sh, which handles the tmpdir→repo copy and git operations.
# No push — caller owns the push.
commit_out=$("$SCRIPT_DIR/larch-log.sh" commit \
    --log-root "$log_root" --skill implement --run-id "$run_id" 2>/dev/null || true)
if printf '%s\n' "$commit_out" | grep -q '^UNCHANGED=true'; then
    emit "REFRESH_COMMITTED=false REASON=no-changes"
else
    emit_kv REFRESH_COMMITTED true
fi
