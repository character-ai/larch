#!/usr/bin/env bash
# refresh-run-logs.sh — Re-render and commit larch-log token/timing artifacts before a push.
# Exits 0 with no commit when the PR is already merged; fail-closed when the probe fails.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(git -C "$PWD" rev-parse --show-toplevel 2>/dev/null)" || REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd -P)"

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

# Fail-closed merge probe: missing or unreadable state file → treat as merged.
[ -f "$STATE_FILE" ] || { printf 'REFRESH_SKIPPED=true REASON=state-file-missing-fail-closed\n'; exit 0; }

kv() { awk -F= -v k="$1" '$1==k{print $2;exit}' "$STATE_FILE" 2>/dev/null || true; }

case "$(kv MERGE_RESULT)" in
    merged|admin_merged) printf 'REFRESH_SKIPPED=true REASON=post-merge\n'; exit 0 ;;
esac

run_id=$(kv RUN_ID)
[ -n "$run_id" ] || { printf 'REFRESH_SKIPPED=true REASON=no-run-id\n'; exit 0; }
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

# Re-render and write token report.
"$SCRIPT_DIR/token-report.sh"  --full --output "$IMPL_TMPDIR/token-report-refresh.md"  2>/dev/null || true
"$SCRIPT_DIR/larch-log.sh" write --log-root "$log_root" --skill implement --run-id "$run_id" \
    --batch token-report --input-file "$IMPL_TMPDIR/token-report-refresh.md" 2>/dev/null || true

# Re-render and write timing report.
"$SCRIPT_DIR/timing-report.sh" --full --output "$IMPL_TMPDIR/timing-report-refresh.md" 2>/dev/null || true
"$SCRIPT_DIR/larch-log.sh" write --log-root "$log_root" --skill implement --run-id "$run_id" \
    --batch timing-report --input-file "$IMPL_TMPDIR/timing-report-refresh.md" 2>/dev/null || true

# Stage and commit the updated files (no push — caller owns the push).
log_dir="larch-logs/implement/$run_id"
git -C "$REPO_ROOT" add -- "$log_dir" 2>/dev/null || true
if ! git -C "$REPO_ROOT" diff --quiet --cached -- "$log_dir" 2>/dev/null; then
    git -C "$REPO_ROOT" commit -m "chore(larch-logs): refresh implement run $run_id" -- "$log_dir" >/dev/null
    printf 'REFRESH_COMMITTED=true\n'
else
    printf 'REFRESH_COMMITTED=false REASON=no-changes\n'
fi
