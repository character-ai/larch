#!/usr/bin/env bash
# clarify-label.sh — idempotent add/remove of needs-design-clarification label.
#
# Usage: clarify-label.sh --issue <N> --action add|remove [--repo OWNER/REPO]
#
# Stdout: CHANGED=, ACTION=, LABEL=needs-design-clarification

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init

REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REDACT_HELPER="$REPO_ROOT/scripts/redact-secrets.sh"

LABEL_NAME="needs-design-clarification"

usage() {
    while IFS= read -r line; do larch_err "$line"; done <<'USAGE'
Usage: clarify-label.sh --issue <N> --action add|remove [--repo OWNER/REPO]
USAGE
}

resolve_repo() {
    local r
    if [ -n "${1:-}" ]; then
        printf '%s' "$1"
        return 0
    fi
    r=$(gh repo view --json nameWithOwner --jq '.nameWithOwner' 2>/dev/null) || r=""
    if [ -z "$r" ]; then
        emit_kv FAILED "true"
        emit_kv ERROR "could not determine repo"
        exit 2
    fi
    printf '%s' "$r"
}

redact_gh_error() {
    local err_text="$1" redacted status=0
    if [ ! -x "$REDACT_HELPER" ]; then
        printf '%s' 'gh stderr redaction unavailable'
        return 0
    fi
    redacted=$(printf '%s' "$err_text" | "$REDACT_HELPER") || status=$?
    if [ "$status" -ne 0 ]; then
        printf '%s' 'gh stderr redaction failed'
        return 0
    fi
    case "$redacted" in
        *'[content truncated'*)
            printf '%s' 'gh stderr redaction unavailable'
            return 0
            ;;
    esac
    printf '%s' "$redacted" | tr '\n' ' ' | head -c 500
}

emit_gh_failure() {
    local flat
    flat=$(redact_gh_error "$1")
    emit_kv FAILED "true"
    emit_kv ERROR "$flat"
    exit 2
}

ISSUE=""
ACTION=""
REPO_ARG=""
while [ $# -gt 0 ]; do
    case "$1" in
        --issue) ISSUE="${2:?}"; shift 2 ;;
        --action) ACTION="${2:?}"; shift 2 ;;
        --repo) REPO_ARG="${2:?}"; shift 2 ;;
        *) larch_err "clarify-label.sh: unknown option: $1"; usage; exit 1 ;;
    esac
done

if [ -z "$ISSUE" ] || [ -z "$ACTION" ]; then
    usage
    exit 1
fi

case "$ISSUE" in
    ''|*[!0-9]*) larch_err "clarify-label.sh: --issue must be a positive integer"; exit 1 ;;
esac
if [ "$ISSUE" = "0" ]; then
    larch_err "clarify-label.sh: --issue must be a positive integer"
    exit 1
fi

case "$ACTION" in
    add|remove) ;;
    *) larch_err "clarify-label.sh: --action must be add or remove"; exit 1 ;;
esac

REPO=$(resolve_repo "$REPO_ARG")

ERR_TMP=$(mktemp "${TMPDIR:-/tmp}/clarify-label-err.XXXXXX")
trap 'rm -f "$ERR_TMP"' EXIT

LABELS_OUT=""
if ! LABELS_OUT=$(gh issue view "$ISSUE" --repo "$REPO" --json labels --jq '.labels[].name' 2>"$ERR_TMP"); then
    ERR_CONTENT=$(cat "$ERR_TMP" 2>/dev/null || true)
    emit_gh_failure "$ERR_CONTENT"
fi

HAS=false
while IFS= read -r ln || [ -n "$ln" ]; do
    [ "$ln" = "$LABEL_NAME" ] && HAS=true
done <<EOF
$LABELS_OUT
EOF

CHANGED=false
case "$ACTION" in
    add)
        if [ "$HAS" = "true" ]; then
            CHANGED=false
        else
            if ! gh issue edit "$ISSUE" --repo "$REPO" --add-label "$LABEL_NAME" 2>"$ERR_TMP"; then
                ERR_CONTENT=$(cat "$ERR_TMP" 2>/dev/null || true)
                emit_gh_failure "$ERR_CONTENT"
            fi
            CHANGED=true
        fi
        ;;
    remove)
        if [ "$HAS" = "false" ]; then
            CHANGED=false
        else
            if ! gh issue edit "$ISSUE" --repo "$REPO" --remove-label "$LABEL_NAME" 2>"$ERR_TMP"; then
                ERR_CONTENT=$(cat "$ERR_TMP" 2>/dev/null || true)
                emit_gh_failure "$ERR_CONTENT"
            fi
            CHANGED=true
        fi
        ;;
esac

emit_kv CHANGED "$CHANGED"
emit_kv ACTION "$ACTION"
emit_kv LABEL "$LABEL_NAME"
exit 0
