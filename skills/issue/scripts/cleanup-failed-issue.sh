#!/usr/bin/env bash
# cleanup-failed-issue.sh — Best-effort close of an orphan GitHub issue when
# /issue's dependency-wiring path exhausts retries and the just-created issue
# would otherwise persist in the repo without its declared blockers.
#
# Single-attempt close (no retry) since this is itself a best-effort recovery
# step — if the close fails (permissions, lock, transient), /issue surfaces
# the issue URL on stderr so the operator can manually close.
#
# Usage:
#   cleanup-failed-issue.sh --issue-number N [--repo OWNER/REPO]
#
# Output (key=value on stdout):
#   On success:
#     CLOSED=true
#     ISSUE=<N>
#   On failure:
#     CLOSED=false
#     ISSUE=<N>
#     ERROR=<redacted-msg>
#
# Exit code: always 0 (best-effort). Caller distinguishes via CLOSED= field.

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/../../.." && pwd)
REDACT_HELPER="$REPO_ROOT/scripts/redact-secrets.sh"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$REPO_ROOT}"
# shellcheck source=scripts/lib-quiet.sh
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init

ISSUE=""
REPO=""

usage() {
    cat <<USAGE >&2
Usage: cleanup-failed-issue.sh --issue-number N [--repo OWNER/REPO]
USAGE
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --issue-number) ISSUE="${2:?--issue-number requires a value}"; shift 2 ;;
        --repo) REPO="${2:?--repo requires a value}"; shift 2 ;;
        # Unknown options exit 0 (per the always-best-effort contract) but MUST
        # still emit the CLOSED=false machine-readable contract on stdout so
        # callers parsing `CLOSED=` can distinguish "close not attempted due to
        # bad invocation" from absent output. Without this, SKILL.md Step 6's
        # orphan-recovery branch would silently fall through on a typo'd flag.
        *) echo "Unknown option: $1" >&2; usage
           emit_kv CLOSED "false"
           emit_kv ISSUE "${ISSUE:-unknown}"
           emit_kv ERROR "unknown option: $1"
           exit 0 ;;
    esac
done

if [[ -z "$ISSUE" || ! "$ISSUE" =~ ^[0-9]+$ ]]; then
    emit_kv CLOSED "false"
    emit_kv ISSUE "$ISSUE"
    emit_kv ERROR "invalid or missing --issue-number"
    exit 0
fi

if [[ -z "$REPO" ]]; then
    REPO=$(gh repo view --json nameWithOwner --jq '.nameWithOwner' 2>/dev/null) || REPO=""
    if [[ -z "$REPO" ]]; then
        emit_kv CLOSED "false"
        emit_kv ISSUE "$ISSUE"
        emit_kv ERROR "could not determine repo"
        exit 0
    fi
fi

ERR_TMP=$(mktemp)
trap 'rm -f "$ERR_TMP"' EXIT

if gh issue close --repo "$REPO" "$ISSUE" --reason "not planned" >/dev/null 2>"$ERR_TMP"; then
    emit_kv CLOSED "true"
    emit_kv ISSUE "$ISSUE"
    exit 0
fi

ERR_CONTENT=$(cat "$ERR_TMP")
REDACTED_ERR=$(printf '%s' "$ERR_CONTENT" | "$REDACT_HELPER" 2>/dev/null) || REDACTED_ERR="(redaction-helper failed; original suppressed)"
ERR_FLAT=$(echo "$REDACTED_ERR" | tr '\n' ' ' | head -c 500)
emit_kv CLOSED "false"
emit_kv ISSUE "$ISSUE"
emit_kv ERROR "$ERR_FLAT"
exit 0
