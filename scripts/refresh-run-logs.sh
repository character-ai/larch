#!/usr/bin/env bash
# refresh-run-logs.sh — Re-render and commit larch-log token/timing artifacts before a push.
# Exits 0 with no commit when the PR is already merged; fail-closed when the probe fails.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"

STATE_FILE=""
IMPL_TMPDIR=""

while [ $# -gt 0 ]; do
    case "$1" in
        --state-file)      STATE_FILE="${2:?--state-file requires a value}";      shift 2 ;;
        --implement-tmpdir) IMPL_TMPDIR="${2:?--implement-tmpdir requires a value}"; shift 2 ;;
        *) printf 'refresh-run-logs.sh: unknown option: %s\n' "$1" >&2; exit 1 ;;
    esac
done

[ -n "$STATE_FILE"  ] || { printf 'refresh-run-logs.sh: --state-file is required\n'      >&2; exit 1; }
[ -n "$IMPL_TMPDIR" ] || { printf 'refresh-run-logs.sh: --implement-tmpdir is required\n' >&2; exit 1; }

# Fail-closed merge probe: missing state file → treat as merged.
[ -f "$STATE_FILE" ] || { printf 'REFRESH_SKIPPED=true REASON=state-file-missing-fail-closed\n'; exit 0; }

kv() { awk -F= -v k="$1" '$1==k{print $2;exit}' "$STATE_FILE" 2>/dev/null || true; }

# All terminal merge outcomes short-circuit (post-merge safety property).
case "$(kv MERGE_RESULT)" in
    merged|admin_merged|already_merged) printf 'REFRESH_SKIPPED=true REASON=post-merge\n'; exit 0 ;;
esac

run_id=$(kv RUN_ID)
[ -n "$run_id" ] || { printf 'REFRESH_SKIPPED=true REASON=no-run-id\n'; exit 0; }

# Reject path-traversal characters in RUN_ID before it reaches git pathspecs.
case "$run_id" in
    */*|*'..'*) { printf 'REFRESH_SKIPPED=true REASON=invalid-run-id\n'; exit 0; } ;;
esac

[ "$(kv NO_LOGS_COMMIT)" = "true" ] && { printf 'REFRESH_SKIPPED=true REASON=no-logs-commit\n'; exit 0; }

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

# Re-render and write token and timing reports.
"$SCRIPT_DIR/token-report.sh"  --full --output "$IMPL_TMPDIR/token-report-refresh.md"  2>/dev/null || true
"$SCRIPT_DIR/larch-log.sh" write --log-root "$log_root" --skill implement --run-id "$run_id" \
    --batch token-report --input-file "$IMPL_TMPDIR/token-report-refresh.md" 2>/dev/null || true
"$SCRIPT_DIR/timing-report.sh" --full --output "$IMPL_TMPDIR/timing-report-refresh.md" 2>/dev/null || true
"$SCRIPT_DIR/larch-log.sh" write --log-root "$log_root" --skill implement --run-id "$run_id" \
    --batch timing-report --input-file "$IMPL_TMPDIR/timing-report-refresh.md" 2>/dev/null || true

# Commit via larch-log.sh, which handles the tmpdir→repo copy and git operations.
# No push — caller owns the push.
commit_out=$("$SCRIPT_DIR/larch-log.sh" commit \
    --log-root "$log_root" --skill implement --run-id "$run_id" --no-push 2>/dev/null || true)
if printf '%s\n' "$commit_out" | grep -q '^UNCHANGED=true'; then
    printf 'REFRESH_COMMITTED=false REASON=no-changes\n'
else
    printf 'REFRESH_COMMITTED=true\n'
fi
