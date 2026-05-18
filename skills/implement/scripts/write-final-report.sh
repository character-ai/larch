#!/usr/bin/env bash
# write-final-report.sh — write final summary file and tracking comment.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
# shellcheck disable=SC1091
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init

usage() {
    larch_err "Usage: write-final-report.sh --issue N --run-id ID --pr-url URL --stall-tracking BOOL --session-env PATH --implement-tmpdir PATH [--repo OWNER/REPO]"
}

fail_usage() {
    usage
    emit_kv COMMENT_URL ""
    emit_kv STATUS failed
    emit_kv ERROR "$1"
    exit 2
}

read_env_key() {
    local key=$1 file=$2
    [ -f "$file" ] || return 0
    awk -v k="$key" 'BEGIN{p=k"="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$file" 2>/dev/null
}

ISSUE=""
RUN_ID=""
PR_URL=""
STALL_TRACKING=""
SESSION_ENV=""
IMPLEMENT_TMPDIR=""
REPO=""
while [ $# -gt 0 ]; do
    case "$1" in
        --issue) [ $# -ge 2 ] || fail_usage "--issue requires a value"; ISSUE=$2; shift 2 ;;
        --run-id) [ $# -ge 2 ] || fail_usage "--run-id requires a value"; RUN_ID=$2; shift 2 ;;
        --pr-url) [ $# -ge 2 ] || fail_usage "--pr-url requires a value"; PR_URL=$2; shift 2 ;;
        --stall-tracking) [ $# -ge 2 ] || fail_usage "--stall-tracking requires a value"; STALL_TRACKING=$2; shift 2 ;;
        --session-env) [ $# -ge 2 ] || fail_usage "--session-env requires a value"; SESSION_ENV=$2; shift 2 ;;
        --implement-tmpdir) [ $# -ge 2 ] || fail_usage "--implement-tmpdir requires a value"; IMPLEMENT_TMPDIR=$2; shift 2 ;;
        --repo) [ $# -ge 2 ] || fail_usage "--repo requires a value"; REPO=$2; shift 2 ;;
        --help) usage; exit 0 ;;
        *) fail_usage "unknown option: $1" ;;
    esac
done

[ -n "$RUN_ID" ] || fail_usage "--run-id is required"
[ -n "$PR_URL" ] || fail_usage "--pr-url is required"
[ -n "$STALL_TRACKING" ] || fail_usage "--stall-tracking is required"
[ -n "$SESSION_ENV" ] || fail_usage "--session-env is required"
[ -n "$IMPLEMENT_TMPDIR" ] || fail_usage "--implement-tmpdir is required"
[ -n "$ISSUE" ] || ISSUE=0
case "$ISSUE" in *[!0-9]*|"") fail_usage "--issue must be numeric" ;; esac
[ -d "$IMPLEMENT_TMPDIR" ] || fail_usage "--implement-tmpdir not found"
[ -n "$REPO" ] || REPO="$(read_env_key REPO "$SESSION_ENV")"

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
cp "$summary" "$run_dir/final-summary.md" 2>/dev/null || true

if [ "$ISSUE" = "0" ]; then
    emit_kv COMMENT_URL ""
    emit_kv STATUS skipped
    emit_kv REASON "issue-not-set"
    exit 0
fi

args=(upsert-summary --issue "$ISSUE" --marker "<!-- larch:final-summary v1 runid=$RUN_ID -->" --content-file "$summary")
[ -z "$REPO" ] || args+=(--repo "$REPO")
if "$PLUGIN_ROOT/scripts/tracking-issue-summary.sh" "${args[@]}" >"$IMPLEMENT_TMPDIR/write-final-report.out" 2>"$IMPLEMENT_TMPDIR/write-final-report.err"; then
    emit_kv COMMENT_URL "$(awk -F= '$1=="COMMENT_URL"{print substr($0,index($0,"=")+1); exit}' "$IMPLEMENT_TMPDIR/write-final-report.out")"
    emit_kv STATUS ok
    exit 0
fi

emit_kv COMMENT_URL ""
emit_kv STATUS failed
emit_kv ERROR "$(tr '\n' ' ' < "$IMPLEMENT_TMPDIR/write-final-report.err" | head -c 500)"
exit 1
