#!/usr/bin/env bash
# get-issue-info.sh — Query a single field from a GitHub issue.
#
# Usage:
#   get-issue-info.sh --issue <N> --field <state|url>
#
# Output (KEY=value on stdout):
#   VALUE=<result>    (on success — e.g., VALUE=OPEN or VALUE=https://...)
#   VALUE=            (on failure — gh error, auth, network, invalid issue)
#
# Exit codes:
#   0 — always (fail-open for caller convenience)

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init

ISSUE=""
FIELD=""
REPO=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --issue) ISSUE="${2:?--issue requires a value}"; shift 2 ;;
        --field) FIELD="${2:?--field requires a value}"; shift 2 ;;
        --repo) REPO="${2:?--repo requires a value}"; shift 2 ;;
        *) larch_err "get-issue-info.sh: unknown flag: $1"; emit_kv VALUE ""; exit 0 ;;
    esac
done

if [[ -z "$ISSUE" || -z "$FIELD" ]]; then
    larch_err "get-issue-info.sh: --issue and --field are required"
    emit_kv VALUE ""
    exit 0
fi

case "$FIELD" in
    state|url) ;;
    *) larch_err "get-issue-info.sh: --field must be 'state' or 'url'"; emit_kv VALUE ""; exit 0 ;;
esac

if [[ -z "$REPO" ]]; then
    REPO=$("$SCRIPT_DIR/resolve-repo.sh" 2>/dev/null) || REPO=""
fi
GH_REPO_ARGS=()
if [[ -n "$REPO" ]]; then
    GH_REPO_ARGS=(--repo "$REPO")
fi

RESULT=$(gh issue view "$ISSUE" "${GH_REPO_ARGS[@]}" --json "$FIELD" --jq ".$FIELD" 2>/dev/null) || RESULT=""
emit_kv VALUE "$RESULT"
exit 0
