#!/usr/bin/env bash
# refresh-execution-issues.sh — refresh metadata comment with execution issue counts.
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
    larch_err "Usage: refresh-execution-issues.sh --implement-tmpdir PATH [--best-effort]"
}

fail_usage() {
    usage
    emit_kv REFRESHED false
    emit_kv ERROR "$1"
    exit 2
}

read_kv() {
    local key=$1 file=$2
    [ -f "$file" ] || return 0
    python3 "$PLUGIN_ROOT/python/cli.py" kv get --key "$key" --file "$file" --match first 2>/dev/null
}

read_plugin_version() {
    python3 "$PLUGIN_ROOT/python/cli.py" plugin read-version 2>/dev/null | python3 "$PLUGIN_ROOT/python/cli.py" kv get --key LARCH_PLUGIN_VERSION --match first 2>/dev/null
}

IMPLEMENT_TMPDIR=""
BEST_EFFORT=false
while [ $# -gt 0 ]; do
    case "$1" in
        --implement-tmpdir) [ $# -ge 2 ] || fail_usage "--implement-tmpdir requires a value"; IMPLEMENT_TMPDIR=$2; shift 2 ;;
        --best-effort) BEST_EFFORT=true; shift ;;
        --help) usage; exit 0 ;;
        *) fail_usage "unknown option: $1" ;;
    esac
done

[ -n "$IMPLEMENT_TMPDIR" ] || fail_usage "--implement-tmpdir is required"
[ -d "$IMPLEMENT_TMPDIR" ] || fail_usage "--implement-tmpdir not found"

SESSION_ENV="$IMPLEMENT_TMPDIR/session-env.sh"
PARENT_ISSUE="$IMPLEMENT_TMPDIR/parent-issue.md"

ISSUE="$(read_kv ISSUE_NUMBER "$PARENT_ISSUE")"
RUN_ID="$(read_kv RUN_ID "$PARENT_ISSUE")"
[ -n "$RUN_ID" ] || RUN_ID="$(tr -d '\r\n' < "$IMPLEMENT_TMPDIR/session-id" 2>/dev/null || true)"
REPO="$(read_kv REPO "$SESSION_ENV")"

if [ -z "$ISSUE" ] || [ "$ISSUE" = "0" ]; then
    emit_kv REFRESHED true
    emit_kv REASON issue-not-set
    exit 0
fi
case "$ISSUE" in *[!0-9]*) emit_kv REFRESHED false; emit_kv ERROR "ISSUE_NUMBER must be numeric"; [ "$BEST_EFFORT" = true ] && exit 0; exit 1 ;; esac

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
        agent="$(read_kv AGENT "$SESSION_ENV")"; [ -n "$agent" ] || agent="claude"
        coder="$(read_kv CODER "$SESSION_ENV")"; [ -n "$coder" ] || coder="claude"
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
    [ "$BEST_EFFORT" = true ] && exit 0
    exit 1
}

args=(upsert-summary --issue "$ISSUE" --marker "<!-- larch:metadata v1 runid=$RUN_ID -->" --content-file "$summary")
[ -z "$REPO" ] || args+=(--repo "$REPO")
if python3 "$PLUGIN_ROOT/python/cli.py" tracking-issue "${args[@]}" >"$IMPLEMENT_TMPDIR/refresh-execution-issues.out" 2>"$IMPLEMENT_TMPDIR/refresh-execution-issues.err"; then
    emit_kv REFRESHED true
    exit 0
fi

emit_kv REFRESHED false
emit_kv ERROR "$(tr '\n' ' ' < "$IMPLEMENT_TMPDIR/refresh-execution-issues.err" | head -c 500)"
[ "$BEST_EFFORT" = true ] && exit 0
exit 1
