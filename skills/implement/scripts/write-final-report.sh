#!/usr/bin/env bash
# write-final-report.sh — write final summary file and tracking comment.
#
# Reads all session state from $IMPLEMENT_TMPDIR files; callers pass only
# --implement-tmpdir to avoid non-determinism from many CLI arguments.
# PR_URL and STALL_TRACKING are read from ship-pr-state.sh when present.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
# shellcheck disable=SC1091
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init

usage() {
    larch_err "Usage: write-final-report.sh --implement-tmpdir PATH [--comment-only]"
}

fail_usage() {
    usage
    emit_kv COMMENT_URL ""
    emit_kv STATUS failed
    emit_kv ERROR "$1"
    exit 2
}

read_kv() {
    local key=$1 file=$2
    [ -f "$file" ] || return 0
    awk -v k="$key" 'BEGIN{p=k"="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$file" 2>/dev/null
}

IMPLEMENT_TMPDIR=""
COMMENT_ONLY=false
while [ $# -gt 0 ]; do
    case "$1" in
        --implement-tmpdir) [ $# -ge 2 ] || fail_usage "--implement-tmpdir requires a value"; IMPLEMENT_TMPDIR=$2; shift 2 ;;
        --comment-only) COMMENT_ONLY=true; shift ;;
        --help) usage; exit 0 ;;
        *) fail_usage "unknown option: $1" ;;
    esac
done

[ -n "$IMPLEMENT_TMPDIR" ] || fail_usage "--implement-tmpdir is required"
[ -d "$IMPLEMENT_TMPDIR" ] || fail_usage "--implement-tmpdir not found"

PARENT_ISSUE="$IMPLEMENT_TMPDIR/parent-issue.md"
SESSION_ENV="$IMPLEMENT_TMPDIR/session-env.sh"
SHIP_PR_STATE="$IMPLEMENT_TMPDIR/ship-pr-state.sh"

ISSUE="$(read_kv ISSUE_NUMBER "$PARENT_ISSUE")"; [ -n "$ISSUE" ] || ISSUE="0"
RUN_ID="$(read_kv RUN_ID "$PARENT_ISSUE")"
[ -n "$RUN_ID" ] || RUN_ID="$(tr -d '\r\n' < "$IMPLEMENT_TMPDIR/session-id" 2>/dev/null || true)"
PR_URL="$(read_kv PR_URL "$SHIP_PR_STATE")"; [ -n "$PR_URL" ] || PR_URL="N/A"
STALL_TRACKING="$(read_kv STALL_TRACKING "$SHIP_PR_STATE")"; [ -n "$STALL_TRACKING" ] || STALL_TRACKING="false"
REPO="$(read_kv REPO "$SESSION_ENV")"

case "$ISSUE" in *[!0-9]*|"") emit_kv COMMENT_URL ""; emit_kv STATUS failed; emit_kv ERROR "ISSUE_NUMBER must be numeric"; exit 1 ;; esac

run_dir="$IMPLEMENT_TMPDIR/larch-logs/implement/$RUN_ID"
mkdir -p "$run_dir" || {
    emit_kv COMMENT_URL ""
    emit_kv STATUS failed
    emit_kv ERROR "could not create run log directory"
    exit 1
}

summary="$IMPLEMENT_TMPDIR/summary-final.md"
{
    printf 'Status: %s\n' "$STALL_TRACKING"
    printf 'PR: %s\n' "$PR_URL"
    printf 'Logs: larch-logs/implement/%s/\n' "$RUN_ID"
} > "$summary" || {
    emit_kv COMMENT_URL ""
    emit_kv STATUS failed
    emit_kv ERROR "could not write summary"
    exit 1
}
if [ "$COMMENT_ONLY" != "true" ]; then
    cp "$summary" "$run_dir/final-summary.md" 2>/dev/null || true
fi

if [ "$ISSUE" = "0" ]; then
    emit_kv COMMENT_URL ""
    emit_kv STATUS skipped
    emit_kv REASON "issue-not-set"
    exit 0
fi

args=(upsert-summary --issue "$ISSUE" --marker "<!-- larch:final-summary v1 runid=$RUN_ID -->" --content-file "$summary")
[ -z "$REPO" ] || args+=(--repo "$REPO")
out_file="$IMPLEMENT_TMPDIR/write-final-report.out"
err_file="$IMPLEMENT_TMPDIR/write-final-report.err"
if "$PLUGIN_ROOT/scripts/tracking-issue-summary.sh" "${args[@]}" >"$out_file" 2>"$err_file"; then
    emit_kv COMMENT_URL "$(awk -F= '$1=="COMMENT_URL"{print substr($0,index($0,"=")+1); exit}' "$out_file")"
    emit_kv STATUS ok
    exit 0
fi

emit_kv COMMENT_URL ""
emit_kv STATUS failed
emit_kv ERROR "$(tr '\n' ' ' < "$err_file" | head -c 500)"
exit 1
