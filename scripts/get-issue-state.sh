#!/usr/bin/env bash
# get-issue-state.sh — fetch state and URL for a GitHub issue, and report
# whether the URL points at a pull request.
#
# Wraps the inline `gh issue view <N> --json state,url --jq '{state,url}'`
# probe used at /implement Step 0 tracking adoption (Branch 2 and related
# paths) for PR-vs-issue detection and CLOSED-state detection on adopted issues.
#
# Usage:
#   get-issue-state.sh --issue N [--repo OWNER/REPO]
#
# Output (stdout, KEY=VALUE):
#   On success:
#     STATE=OPEN|CLOSED
#     URL=<url>
#     IS_PR=true|false
#   On failure:
#     FAILED=true
#     ERROR=<single-line message>
#
# Exit codes:
#   0 — success (success envelope written)
#   1 — invocation error (missing --issue) or gh failure (FAILED envelope written)

set -uo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init

ISSUE=""
REPO=""

while [ $# -gt 0 ]; do
    case "$1" in
        --issue) ISSUE="${2:-}"; shift 2 ;;
        --repo)  REPO="${2:-}"; shift 2 ;;
        *)
            emit_kv FAILED true
            emit_kv ERROR "unknown flag: $1"
            exit 1 ;;
    esac
done

if [ -z "$ISSUE" ]; then
    emit_kv FAILED true
    emit_kv ERROR "--issue is required"
    exit 1
fi

case "$ISSUE" in
    *[!0-9]*) emit_kv FAILED true; emit_kv ERROR "--issue must be numeric"; exit 1 ;;
esac

if [ -z "$REPO" ]; then
    REPO=$("$SCRIPT_DIR/resolve-repo.sh" 2>/dev/null) || REPO=""
fi

# shellcheck disable=SC2054  # 'state,url' is a single --json value, not two array elements
GH_ARGS=(issue view "$ISSUE" --json "state,url")
[ -n "$REPO" ] && GH_ARGS+=(--repo "$REPO")

if ! OUT=$(gh "${GH_ARGS[@]}" --jq '.state + "\t" + .url' 2>&1); then
    emit_kv FAILED true
    # Compress whitespace and trim for a single-line ERROR.
    SAFE=$(printf '%s' "$OUT" | tr '\n' ' ' | sed 's/  */ /g')
    emit_kv ERROR "gh issue view failed: $SAFE"
    exit 1
fi

STATE="${OUT%%$'\t'*}"
URL="${OUT#*$'\t'}"

if [[ "$URL" == *"/pull/"* ]]; then
    IS_PR=true
else
    IS_PR=false
fi

emit_kv STATE "$STATE"
emit_kv URL "$URL"
emit_kv IS_PR "$IS_PR"
exit 0
