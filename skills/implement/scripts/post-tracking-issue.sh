#!/usr/bin/env bash
# post-tracking-issue.sh — publish the Step 0.5 larch:metadata summary.
# shellcheck disable=SC2016

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
# shellcheck disable=SC1091
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init

usage() {
    larch_err "Usage: post-tracking-issue.sh --issue N --run-id ID --session-env PATH [--agent claude] [--coder claude] [--repo OWNER/REPO]"
}

fail_usage() {
    usage
    emit_kv POSTED false
    emit_kv COMMENT_URL ""
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
SESSION_ENV=""
AGENT="claude"
CODER="claude"
REPO=""

while [ $# -gt 0 ]; do
    case "$1" in
        --issue) [ $# -ge 2 ] || fail_usage "--issue requires a value"; ISSUE=$2; shift 2 ;;
        --run-id) [ $# -ge 2 ] || fail_usage "--run-id requires a value"; RUN_ID=$2; shift 2 ;;
        --session-env) [ $# -ge 2 ] || fail_usage "--session-env requires a value"; SESSION_ENV=$2; shift 2 ;;
        --agent) [ $# -ge 2 ] || fail_usage "--agent requires a value"; AGENT=$2; shift 2 ;;
        --coder) [ $# -ge 2 ] || fail_usage "--coder requires a value"; CODER=$2; shift 2 ;;
        --repo) [ $# -ge 2 ] || fail_usage "--repo requires a value"; REPO=$2; shift 2 ;;
        --help) usage; exit 0 ;;
        *) fail_usage "unknown option: $1" ;;
    esac
done

[ -n "$ISSUE" ] || fail_usage "--issue is required"
[ -n "$RUN_ID" ] || fail_usage "--run-id is required"
[ -n "$SESSION_ENV" ] || fail_usage "--session-env is required"
case "$ISSUE" in *[!0-9]*|"") fail_usage "--issue must be numeric" ;; esac
case "$RUN_ID" in ""|*[!A-Za-z0-9-]*) fail_usage "--run-id must contain only letters, numbers, and hyphens" ;; esac
[ -f "$SESSION_ENV" ] || fail_usage "--session-env file not found"

if [ -z "$REPO" ]; then
    REPO="$(read_env_key REPO "$SESSION_ENV")"
fi

tmpdir="$(dirname "$SESSION_ENV")"
summary="$tmpdir/summary-metadata.md"
version="$("$PLUGIN_ROOT/scripts/read-plugin-version.sh" 2>/dev/null | awk -F= '/^LARCH_PLUGIN_VERSION=/{print $2; exit}')"
[ -n "$version" ] || version="unknown"

{
    printf 'Run ID: `%s`\n' "$RUN_ID"
    printf 'Logs: `larch-logs/implement/%s/`\n' "$RUN_ID"
    printf 'Tracking issue: #%s\n' "$ISSUE"
    printf 'Agent: `%s`\n' "$AGENT"
    printf 'Coder: `%s`\n' "$CODER"
    printf 'Larch version: `%s`\n' "$version"
} > "$summary" || {
    emit_kv POSTED false
    emit_kv COMMENT_URL ""
    emit_kv ERROR "could not write summary"
    exit 1
}

marker="<!-- larch:metadata v1 runid=$RUN_ID -->"
out_file="$tmpdir/post-tracking-issue.out"
err_file="$tmpdir/post-tracking-issue.err"
args=(upsert-summary --issue "$ISSUE" --marker "$marker" --content-file "$summary")
[ -z "$REPO" ] || args+=(--repo "$REPO")

if "$PLUGIN_ROOT/scripts/tracking-issue-summary.sh" "${args[@]}" >"$out_file" 2>"$err_file"; then
    emit_kv POSTED true
    emit_kv COMMENT_URL "$(awk -F= '$1=="COMMENT_URL"{print substr($0,index($0,"=")+1); exit}' "$out_file")"
    exit 0
fi

emit_kv POSTED false
emit_kv COMMENT_URL ""
emit_kv ERROR "$(tr '\n' ' ' < "$err_file" | head -c 500)"
exit 1
