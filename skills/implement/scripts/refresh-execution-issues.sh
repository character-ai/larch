#!/usr/bin/env bash
# refresh-execution-issues.sh — refresh metadata comment with execution issue counts.
# shellcheck disable=SC2016

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
# shellcheck disable=SC1091
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init

usage() {
    larch_err "Usage: refresh-execution-issues.sh --issue N --run-id ID --session-env PATH --implement-tmpdir PATH [--repo OWNER/REPO]"
}

fail_usage() {
    usage
    emit_kv REFRESHED false
    emit_kv ERROR "$1"
    exit 2
}

read_env_key() {
    local key=$1 file=$2
    [ -f "$file" ] || return 0
    awk -v k="$key" 'BEGIN{p=k"="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$file" 2>/dev/null
}

read_plugin_version() {
    "$PLUGIN_ROOT/scripts/read-plugin-version.sh" 2>/dev/null | awk -F= '/^LARCH_PLUGIN_VERSION=/{print $2; exit}'
}

ISSUE=""
RUN_ID=""
SESSION_ENV=""
IMPLEMENT_TMPDIR=""
REPO=""
while [ $# -gt 0 ]; do
    case "$1" in
        --issue) [ $# -ge 2 ] || fail_usage "--issue requires a value"; ISSUE=$2; shift 2 ;;
        --run-id) [ $# -ge 2 ] || fail_usage "--run-id requires a value"; RUN_ID=$2; shift 2 ;;
        --session-env) [ $# -ge 2 ] || fail_usage "--session-env requires a value"; SESSION_ENV=$2; shift 2 ;;
        --implement-tmpdir) [ $# -ge 2 ] || fail_usage "--implement-tmpdir requires a value"; IMPLEMENT_TMPDIR=$2; shift 2 ;;
        --repo) [ $# -ge 2 ] || fail_usage "--repo requires a value"; REPO=$2; shift 2 ;;
        --help) usage; exit 0 ;;
        *) fail_usage "unknown option: $1" ;;
    esac
done

[ -n "$ISSUE" ] || fail_usage "--issue is required"
[ -n "$RUN_ID" ] || fail_usage "--run-id is required"
[ -n "$SESSION_ENV" ] || fail_usage "--session-env is required"
[ -n "$IMPLEMENT_TMPDIR" ] || fail_usage "--implement-tmpdir is required"
case "$ISSUE" in *[!0-9]*|"") fail_usage "--issue must be numeric" ;; esac
[ -d "$IMPLEMENT_TMPDIR" ] || fail_usage "--implement-tmpdir not found"

[ -n "$REPO" ] || REPO="$(read_env_key REPO "$SESSION_ENV")"
if [ "$ISSUE" = "0" ]; then
    emit_kv REFRESHED true
    emit_kv REASON issue-not-set
    exit 0
fi

issue_log="$IMPLEMENT_TMPDIR/execution-issues.md"
summary="$IMPLEMENT_TMPDIR/summary-metadata.md"
existing_summary=""
count=0
[ ! -s "$issue_log" ] || count="$(grep -c '^- ' "$issue_log" 2>/dev/null || printf '0')"
[ ! -s "$summary" ] || existing_summary="$(cat "$summary")"

{
    if [ -n "$existing_summary" ]; then
        printf '%s\n' "$existing_summary" | awk '!/^Execution issues pending flush: `[^`]*`$/'
    else
        version="$(read_plugin_version)"
        [ -n "$version" ] || version="unknown"
        agent="$(read_env_key AGENT "$SESSION_ENV")"
        coder="$(read_env_key CODER "$SESSION_ENV")"
        [ -n "$agent" ] || agent="claude"
        [ -n "$coder" ] || coder="claude"
        printf 'Run ID: `%s`\n' "$RUN_ID"
        printf 'Logs: `larch-logs/implement/%s/`\n' "$RUN_ID"
        printf 'Tracking issue: #%s\n' "$ISSUE"
        printf 'Agent: `%s`\n' "$agent"
        printf 'Coder: `%s`\n' "$coder"
        printf 'Larch version: `%s`\n' "$version"
    fi
    printf 'Execution issues pending flush: `%s`\n' "$count"
} > "$summary" || {
    emit_kv REFRESHED false
    emit_kv ERROR "could not write summary"
    exit 1
}

args=(upsert-summary --issue "$ISSUE" --marker "<!-- larch:metadata v1 runid=$RUN_ID -->" --content-file "$summary")
[ -z "$REPO" ] || args+=(--repo "$REPO")
if "$PLUGIN_ROOT/scripts/tracking-issue-summary.sh" "${args[@]}" >"$IMPLEMENT_TMPDIR/refresh-execution-issues.out" 2>"$IMPLEMENT_TMPDIR/refresh-execution-issues.err"; then
    emit_kv REFRESHED true
    exit 0
fi

emit_kv REFRESHED false
emit_kv ERROR "$(tr '\n' ' ' < "$IMPLEMENT_TMPDIR/refresh-execution-issues.err" | head -c 500)"
exit 1
