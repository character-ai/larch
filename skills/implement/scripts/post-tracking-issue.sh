#!/usr/bin/env bash
# post-tracking-issue.sh — publish the Step 0 larch:metadata summary (post-adoption).
# shellcheck disable=SC2016
#
# Reads all session state from $IMPLEMENT_TMPDIR files; callers pass only
# --implement-tmpdir to avoid non-determinism from many CLI arguments.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
larch_err() { printf '%s\n' "$*" >&2; }
emit() { printf '%s\n' "$*"; }
emit_kv() {
    local key=$1 value=${2-}
    case "$value" in *$'\n'*|*$'\r'*) larch_err "emit_kv: value for key ${key} must not contain newline or carriage return"; return 2 ;; esac
    printf '%s=%s\n' "$key" "$value"
}
larch_quiet_init() { :; }

usage() {
    larch_err "Usage: post-tracking-issue.sh --implement-tmpdir PATH [--issue-number N] [--run-id ID] [--adopted true|false] [--force-requested true|false]"
}

fail_usage() {
    usage
    emit_kv POSTED false
    emit_kv COMMENT_URL ""
    emit_kv ERROR "$1"
    exit 2
}

read_kv() {
    local key=$1 file=$2
    [ -f "$file" ] || return 0
    awk -v k="$key" 'BEGIN{p=k"="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$file" 2>/dev/null
}

IMPLEMENT_TMPDIR=""
ISSUE_NUMBER_ARG=""
RUN_ID_ARG=""
ADOPTED_ARG=""
FORCE_REQUESTED="false"
while [ $# -gt 0 ]; do
    case "$1" in
        --implement-tmpdir) [ $# -ge 2 ] || fail_usage "--implement-tmpdir requires a value"; IMPLEMENT_TMPDIR=$2; shift 2 ;;
        --issue-number) [ $# -ge 2 ] || fail_usage "--issue-number requires a value"; ISSUE_NUMBER_ARG=$2; shift 2 ;;
        --run-id) [ $# -ge 2 ] || fail_usage "--run-id requires a value"; RUN_ID_ARG=$2; shift 2 ;;
        --adopted) [ $# -ge 2 ] || fail_usage "--adopted requires a value"; ADOPTED_ARG=$2; shift 2 ;;
        --force-requested) [ $# -ge 2 ] || fail_usage "--force-requested requires a value"; FORCE_REQUESTED=$2; shift 2 ;;
        --help) usage; exit 0 ;;
        *) fail_usage "unknown option: $1" ;;
    esac
done

[ -n "$IMPLEMENT_TMPDIR" ] || fail_usage "--implement-tmpdir is required"
[ -d "$IMPLEMENT_TMPDIR" ] || fail_usage "--implement-tmpdir not found"

case "${ADOPTED_ARG:-true}" in true|false) ;; *) fail_usage "--adopted must be true or false" ;; esac
case "$FORCE_REQUESTED" in true|false) ;; *) fail_usage "--force-requested must be true or false" ;; esac
case "$RUN_ID_ARG" in ""|*[!A-Za-z0-9._-]*) [ -z "$RUN_ID_ARG" ] || fail_usage "--run-id must match ^[A-Za-z0-9._-]+$" ;; esac

SESSION_ENV="$IMPLEMENT_TMPDIR/session-env.sh"
PARENT_ISSUE="$IMPLEMENT_TMPDIR/parent-issue.md"
RUN_FLAGS="$IMPLEMENT_TMPDIR/run-flags.sh"

if [ -n "$ISSUE_NUMBER_ARG" ]; then
    ISSUE="$ISSUE_NUMBER_ARG"
else
    ISSUE="$(read_kv ISSUE_NUMBER "$PARENT_ISSUE")"
fi
RUN_ID="$RUN_ID_ARG"
[ -n "$RUN_ID" ] || RUN_ID="$(read_kv RUN_ID "$PARENT_ISSUE")"
[ -n "$RUN_ID" ] || RUN_ID="$(tr -d '\r\n' < "$IMPLEMENT_TMPDIR/session-id" 2>/dev/null || true)"
[ -n "$RUN_ID" ] || RUN_ID="$(read_kv LARCH_TOKEN_SESSION_ID "$SESSION_ENV")"
REPO="$(read_kv REPO "$SESSION_ENV")"
AGENT="$(read_kv AGENT "$SESSION_ENV")"; [ -n "$AGENT" ] || AGENT="claude"
CODER="$(read_kv CODER "$SESSION_ENV")"; [ -n "$CODER" ] || CODER="claude"
PERSISTED_FORCE="$(read_kv FORCE_REQUESTED "$RUN_FLAGS")"
if [ "$FORCE_REQUESTED" = "false" ] && [ "$PERSISTED_FORCE" = "true" ]; then
    FORCE_REQUESTED="true"
fi

[ -n "$ISSUE" ] || { emit_kv POSTED false; emit_kv COMMENT_URL ""; emit_kv ERROR "ISSUE_NUMBER not found in parent-issue.md"; exit 1; }
[ -n "$RUN_ID" ] || { emit_kv POSTED false; emit_kv COMMENT_URL ""; emit_kv ERROR "RUN_ID not found in parent-issue.md, session-id, or session-env LARCH_TOKEN_SESSION_ID"; exit 1; }
case "$ISSUE" in *[!0-9]*|"") emit_kv POSTED false; emit_kv COMMENT_URL ""; emit_kv ERROR "ISSUE_NUMBER must be numeric"; exit 1 ;; esac
case "$RUN_ID" in *[!A-Za-z0-9._-]*|"") emit_kv POSTED false; emit_kv COMMENT_URL ""; emit_kv ERROR "RUN_ID must match ^[A-Za-z0-9._-]+$"; exit 1 ;; esac

summary="$IMPLEMENT_TMPDIR/summary-metadata.md"
version="$(python3 "$PLUGIN_ROOT/python/cli.py" plugin read-version 2>/dev/null | awk -F= '/^LARCH_PLUGIN_VERSION=/{print $2; exit}' || true)"
[ -n "$version" ] || version="unknown"

{
    printf 'Run ID: `%s`\n' "$RUN_ID"
    printf 'Logs: `larch-logs/implement/%s/`\n' "$RUN_ID"
    printf 'Tracking issue: #%s\n' "$ISSUE"
    printf 'Agent: `%s`\n' "$AGENT"
    printf 'Coder: `%s`\n' "$CODER"
    if [ "$FORCE_REQUESTED" = "true" ]; then
        printf 'Force: true\n'
    fi
    printf 'Larch version: `%s`\n' "$version"
} > "$summary" || {
    emit_kv POSTED false
    emit_kv COMMENT_URL ""
    emit_kv ERROR "could not write summary"
    exit 1
}

marker="<!-- larch:metadata v1 runid=$RUN_ID -->"
out_file="$IMPLEMENT_TMPDIR/post-tracking-issue.out"
err_file="$IMPLEMENT_TMPDIR/post-tracking-issue.err"
args=(upsert-summary --issue "$ISSUE" --marker "$marker" --content-file "$summary")
[ -z "$REPO" ] || args+=(--repo "$REPO")

if python3 "$PLUGIN_ROOT/python/cli.py" tracking-issue "${args[@]}" >"$out_file" 2>"$err_file"; then
    # When --issue-number was provided, write the sentinel now that the post
    # succeeded — co-locating the write with success so the sentinel is never
    # present without a confirmed metadata comment.
    if [ -n "$ISSUE_NUMBER_ARG" ]; then
        _adopted="${ADOPTED_ARG:-true}"
        printf 'ISSUE_NUMBER=%s\nRUN_ID=%s\nADOPTED=%s\n' "$ISSUE" "$RUN_ID" "$_adopted" > "$PARENT_ISSUE"
    fi
    emit_kv POSTED true
    emit_kv COMMENT_URL "$(awk -F= '$1=="COMMENT_URL"{print substr($0,index($0,"=")+1); exit}' "$out_file")"
    exit 0
fi

emit_kv POSTED false
emit_kv COMMENT_URL ""
emit_kv ERROR "$(tr '\n' ' ' < "$err_file" | head -c 500)"
exit 1
