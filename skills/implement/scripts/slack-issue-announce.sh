#!/usr/bin/env bash
# slack-issue-announce.sh — optional Step 16a Slack notification.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
# shellcheck disable=SC1091
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init

usage() {
    larch_err "Usage: slack-issue-announce.sh --pr-url URL --issue-number N --run-id ID [--pr-title TEXT]"
}

fail_usage() {
    usage
    emit_kv STATUS failed
    emit_kv ERROR "$1"
    exit 2
}

PR_URL=""
ISSUE_NUMBER=""
RUN_ID=""
PR_TITLE=""
while [ $# -gt 0 ]; do
    case "$1" in
        --pr-url) [ $# -ge 2 ] || fail_usage "--pr-url requires a value"; PR_URL=$2; shift 2 ;;
        --issue-number) [ $# -ge 2 ] || fail_usage "--issue-number requires a value"; ISSUE_NUMBER=$2; shift 2 ;;
        --run-id) [ $# -ge 2 ] || fail_usage "--run-id requires a value"; RUN_ID=$2; shift 2 ;;
        --pr-title) [ $# -ge 2 ] || fail_usage "--pr-title requires a value"; PR_TITLE=$2; shift 2 ;;
        --help) usage; exit 0 ;;
        *) fail_usage "unknown option: $1" ;;
    esac
done

[ -n "$PR_URL" ] || fail_usage "--pr-url is required"
[ -n "$ISSUE_NUMBER" ] || fail_usage "--issue-number is required"
[ -n "$RUN_ID" ] || fail_usage "--run-id is required"
case "$ISSUE_NUMBER" in *[!0-9]*|"") fail_usage "--issue-number must be numeric" ;; esac

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

curl_bin="${__LARCH_FAKE_CURL:-curl}"
if "$curl_bin" -sS -X POST -H 'Content-Type: application/json' --data "$payload" "$LARCH_SLACK_WEBHOOK_URL" >/dev/null 2>"${TMPDIR:-/tmp}/slack-issue-announce.$$.err"; then
    emit_kv STATUS posted
    exit 0
fi

emit_kv STATUS failed
emit_kv ERROR "$(tr '\n' ' ' < "${TMPDIR:-/tmp}/slack-issue-announce.$$.err" | head -c 500)"
rm -f "${TMPDIR:-/tmp}/slack-issue-announce.$$.err"
exit 1
