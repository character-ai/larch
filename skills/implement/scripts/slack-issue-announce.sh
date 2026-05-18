#!/usr/bin/env bash
# slack-issue-announce.sh — optional Step 16a Slack notification.
#
# Reads all session state from $IMPLEMENT_TMPDIR files; callers pass only
# --implement-tmpdir to avoid non-determinism from many CLI arguments.
# Silently skips when LARCH_SLACK_WEBHOOK_URL is unset.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
# shellcheck disable=SC1091
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init

usage() {
    larch_err "Usage: slack-issue-announce.sh --implement-tmpdir PATH"
}

fail_usage() {
    usage
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
while [ $# -gt 0 ]; do
    case "$1" in
        --implement-tmpdir) [ $# -ge 2 ] || fail_usage "--implement-tmpdir requires a value"; IMPLEMENT_TMPDIR=$2; shift 2 ;;
        --help) usage; exit 0 ;;
        *) fail_usage "unknown option: $1" ;;
    esac
done

[ -n "$IMPLEMENT_TMPDIR" ] || fail_usage "--implement-tmpdir is required"
[ -d "$IMPLEMENT_TMPDIR" ] || fail_usage "--implement-tmpdir not found"

PARENT_ISSUE="$IMPLEMENT_TMPDIR/parent-issue.md"
SHIP_PR_STATE="$IMPLEMENT_TMPDIR/ship-pr-state.sh"

ISSUE_NUMBER="$(read_kv ISSUE_NUMBER "$PARENT_ISSUE")"; [ -n "$ISSUE_NUMBER" ] || ISSUE_NUMBER="0"
RUN_ID="$(read_kv RUN_ID "$PARENT_ISSUE")"
[ -n "$RUN_ID" ] || RUN_ID="$(tr -d '\r\n' < "$IMPLEMENT_TMPDIR/session-id" 2>/dev/null || true)"
PR_URL="$(read_kv PR_URL "$SHIP_PR_STATE")"; [ -n "$PR_URL" ] || PR_URL="N/A"
PR_TITLE="$(read_kv PR_TITLE "$SHIP_PR_STATE")"

case "$ISSUE_NUMBER" in *[!0-9]*|"") emit_kv STATUS failed; emit_kv ERROR "ISSUE_NUMBER must be numeric"; exit 1 ;; esac

if [ "$ISSUE_NUMBER" = "0" ]; then
    emit_kv STATUS skipped
    emit_kv REASON "issue-not-set"
    exit 0
fi

if [ -z "${LARCH_SLACK_WEBHOOK_URL:-}" ]; then
    emit_kv STATUS skipped
    emit_kv REASON "webhook-not-set"
    exit 0
fi

text="Implement run $RUN_ID opened PR $PR_URL for tracking issue #$ISSUE_NUMBER"
[ -z "$PR_TITLE" ] || text="$text — $PR_TITLE"
payload="$(jq -cn --arg text "$text" '{text:$text}')" || {
    emit_kv STATUS failed
    emit_kv ERROR "payload-json-failed"
    exit 1
}

err_file="$IMPLEMENT_TMPDIR/slack-issue-announce.err"
curl_bin="${__LARCH_FAKE_CURL:-curl}"
if "$curl_bin" -sS -X POST -H 'Content-Type: application/json' --data "$payload" "$LARCH_SLACK_WEBHOOK_URL" >/dev/null 2>"$err_file"; then
    emit_kv STATUS posted
    exit 0
fi

emit_kv STATUS failed
emit_kv ERROR "$(tr '\n' ' ' < "$err_file" | head -c 500)"
exit 1
