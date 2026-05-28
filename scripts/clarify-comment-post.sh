#!/usr/bin/env bash
# clarify-comment-post.sh — post larch:clarify-request / clarify-response marker comment.
#
# Usage: clarify-comment-post.sh --issue <N> --kind request|response --id <N> \
#          --content-file <path> [--repo OWNER/REPO]
#
# Stdout: POSTED=, COMMENT_ID=, COMMENT_URL=, MARKER=.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init
# shellcheck source=scripts/lib-net.sh
source "$SCRIPT_DIR/lib-net.sh"

REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REDACT_HELPER="$REPO_ROOT/scripts/redact-secrets.sh"

usage() {
    while IFS= read -r line; do larch_err "$line"; done <<'USAGE'
Usage: clarify-comment-post.sh --issue <N> --kind request|response --id <N> \
         --content-file <path> [--repo OWNER/REPO]
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
KIND=""
CID=""
CONTENT_FILE=""
REPO_ARG=""
while [ $# -gt 0 ]; do
    case "$1" in
        --issue) ISSUE="${2:?}"; shift 2 ;;
        --kind) KIND="${2:?}"; shift 2 ;;
        --id) CID="${2:?}"; shift 2 ;;
        --content-file) CONTENT_FILE="${2:?}"; shift 2 ;;
        --repo) REPO_ARG="${2:?}"; shift 2 ;;
        *) larch_err "clarify-comment-post.sh: unknown option: $1"; usage; exit 1 ;;
    esac
done

if [ -z "$ISSUE" ] || [ -z "$KIND" ] || [ -z "$CID" ] || [ -z "$CONTENT_FILE" ]; then
    usage
    exit 1
fi

case "$ISSUE" in
    ''|*[!0-9]*) larch_err "clarify-comment-post.sh: --issue must be a positive integer"; exit 1 ;;
esac
if [ "$ISSUE" = "0" ]; then
    larch_err "clarify-comment-post.sh: --issue must be a positive integer"
    exit 1
fi

case "$KIND" in
    request|response) ;;
    *)
        emit_kv FAILED "true"
        emit_kv ERROR "invalid-kind"
        exit 1
        ;;
esac

case "$CID" in
    ''|*[!0-9]*)
        emit_kv FAILED "true"
        emit_kv ERROR "invalid-id"
        exit 1
        ;;
esac
if [ "$CID" = "0" ]; then
    emit_kv FAILED "true"
    emit_kv ERROR "invalid-id"
    exit 1
fi

if [ ! -f "$CONTENT_FILE" ]; then
    emit_kv FAILED "true"
    emit_kv ERROR "content file not found: $CONTENT_FILE"
    exit 1
fi

REPO=$(resolve_repo "$REPO_ARG")

MARKER_LINE="<!-- larch:clarify-${KIND} id=${CID} -->"
BODY_TMP=$(mktemp "${TMPDIR:-/tmp}/clarify-comment.XXXXXX")
ERR_TMP=$(mktemp "${TMPDIR:-/tmp}/clarify-comment-err.XXXXXX")
trap 'rm -f "$BODY_TMP" "$ERR_TMP"' EXIT

{
    printf '%s\n' "$MARKER_LINE"
    cat "$CONTENT_FILE"
} > "$BODY_TMP"

if [ ! -x "$REDACT_HELPER" ]; then
    emit_kv FAILED "true"
    emit_kv ERROR "redact-secrets.sh not executable"
    exit 2
fi

REDACTED=$(mktemp "${TMPDIR:-/tmp}/clarify-comment-red.XXXXXX")
trap 'rm -f "$BODY_TMP" "$ERR_TMP" "$REDACTED"' EXIT
if ! "$REDACT_HELPER" < "$BODY_TMP" > "$REDACTED"; then
    emit_kv FAILED "true"
    emit_kv ERROR "redaction failed"
    exit 2
fi

OUT_URL=""
comment_fail_file=$(mktemp "${TMPDIR:-/tmp}/clarify-comment-post.XXXXXX")
if gh issue comment "$ISSUE" --repo "$REPO" --body-file "$REDACTED" >"$comment_fail_file" 2>&1; then
    :
else
    ERR_CONTENT=$(cat "$comment_fail_file" 2>/dev/null || true)
    rm -f "$comment_fail_file"
    emit_gh_failure "$ERR_CONTENT"
fi
OUT_URL=$(cat "$comment_fail_file" 2>/dev/null || true)
rm -f "$comment_fail_file"

# gh prints URL; extract numeric comment id from ...#issuecomment-123
COMMENT_NUM=""
case "$OUT_URL" in
    *issuecomment-*)
        COMMENT_NUM="${OUT_URL##*issuecomment-}"
        COMMENT_NUM="${COMMENT_NUM%%[^0-9]*}"
        ;;
esac

emit_kv POSTED "true"
emit_kv COMMENT_ID "${COMMENT_NUM:-}"
emit_kv COMMENT_URL "$OUT_URL"
emit_kv MARKER "$MARKER_LINE"
exit 0
