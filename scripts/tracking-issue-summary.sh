#!/usr/bin/env bash
# tracking-issue-summary.sh — upsert slim marker-keyed tracking comments.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init
REDACT="$SCRIPT_DIR/redact-secrets.sh"
REDACT_PATHS="$SCRIPT_DIR/redact-tmpdir-paths.sh"

usage() {
    while IFS= read -r line; do larch_err "$line"; done <<'USAGE'
Usage:
  tracking-issue-summary.sh upsert-summary --issue N --marker M --content-file F [--repo OWNER/REPO] [--comment-id N]
USAGE
}

fail() {
    local code="$1"
    local msg="$2"
    larch_err "FAILED=true"
    larch_err "ERROR=$msg"
    exit "$code"
}

redact_text() {
    [ -x "$REDACT" ] || fail 3 "redaction helper missing: $REDACT"
    printf '%s' "$1" | "$REDACT" || fail 3 "redaction failed"
}

normalize_first_line() {
    local line=$1
    if [[ "${line:0:3}" == $'\xef\xbb\xbf' ]]; then
        line="${line:3}"
    fi
    line="${line%$'\r'}"
    printf '%s' "$line"
}

validate_repo() {
    local repo="$1"
    [[ "$repo" =~ ^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$ ]] || fail 1 "invalid repo: expected OWNER/REPO"
}

cmd="${1:-}"
[ -n "$cmd" ] || { usage; exit 1; }
shift

case "$cmd" in
    upsert-summary)
        ISSUE=""; MARKER=""; CONTENT_FILE=""; REPO=""; COMMENT_ID=""
        while [ $# -gt 0 ]; do
            case "$1" in
                --issue) ISSUE="${2:?--issue requires a value}"; shift 2 ;;
                --marker) MARKER="${2:?--marker requires a value}"; shift 2 ;;
                --content-file) CONTENT_FILE="${2:?--content-file requires a value}"; shift 2 ;;
                --repo) REPO="${2:?--repo requires a value}"; shift 2 ;;
                --comment-id) COMMENT_ID="${2:?--comment-id requires a value}"; shift 2 ;;
                *) usage; fail 1 "unknown option for upsert-summary: $1" ;;
            esac
        done
        [ -n "$ISSUE" ] || fail 1 "--issue is required"
        [ -n "$MARKER" ] || fail 1 "--marker is required"
        [ -f "$CONTENT_FILE" ] || fail 1 "content file not found: $CONTENT_FILE"
        case "$ISSUE" in *[!0-9]*|"") fail 1 "invalid issue: $ISSUE" ;; esac
        case "$MARKER" in '<!-- larch:'*' -->') ;; *) fail 1 "invalid marker: $MARKER" ;; esac
        case "$COMMENT_ID" in ""|*[!0-9]*) [ -z "$COMMENT_ID" ] || fail 1 "invalid comment id: $COMMENT_ID" ;; esac
        if [ -z "$REPO" ]; then
            REPO="$(gh repo view --json nameWithOwner --jq '.nameWithOwner' 2>/dev/null || true)"
            [ -n "$REPO" ] || fail 2 "could not determine repo"
        fi
        validate_repo "$REPO"
        content="$(cat "$CONTENT_FILE")"
        body="$MARKER"$'\n\n'"$content"
        if [ -x "$REDACT_PATHS" ]; then
            body="$(printf '%s' "$body" | "$REDACT_PATHS" 2>/dev/null || printf '%s' "$body")"
        fi
        body="$(redact_text "$body")"
        ids=""
        count=0
        if [ -n "$COMMENT_ID" ]; then
            ids="$COMMENT_ID"
            count=1
        else
            list_err="$(mktemp)"
            list_out="$(gh api "/repos/${REPO}/issues/${ISSUE}/comments" --paginate --jq '.[] | (.id|tostring) + "\t" + (.body // "" | split("\n")[0])' 2>"$list_err")" || {
                err="$(cat "$list_err")"
                rm -f "$list_err"
                fail 2 "gh api comments fetch failed: $(redact_text "$err" | tr '\n' ' ' | head -c 500)"
            }
            rm -f "$list_err"
            ids="$(printf '%s\n' "$list_out" | while IFS=$'\t' read -r id first_line; do
                [ -n "$id" ] || continue
                first_line="$(normalize_first_line "$first_line")"
                if [ "$first_line" = "$MARKER" ]; then
                    printf '%s\n' "$id"
                fi
            done)"
            count="$(printf '%s\n' "$ids" | awk 'NF { n++ } END { print n + 0 }')"
        fi
        tmp="$(mktemp)"
        json_tmp=""
        trap 'rm -f "$tmp" "${json_tmp:-}"' EXIT
        printf '%s' "$body" > "$tmp"
        if [ "$count" -eq 0 ]; then
            err_tmp="$(mktemp)"
            trap 'rm -f "$tmp" "${json_tmp:-}" "${err_tmp:-}"' EXIT
            out="$(gh issue comment "$ISSUE" --repo "$REPO" --body-file "$tmp" 2>"$err_tmp")" \
                || fail 2 "gh issue comment failed: $(redact_text "$(cat "$err_tmp")" | tr '\n' ' ' | head -c 500)"
            url="$(printf '%s\n' "$out" | grep -oE 'https?://[^[:space:]]+' | tail -1 || true)"
            emit_kv COMMENT_ID ""
            emit_kv COMMENT_URL "$url"
            emit_kv UPDATED false
        elif [ "$count" -eq 1 ]; then
            id="$(printf '%s\n' "$ids" | awk 'NF { print; exit }')"
            json_tmp="$(mktemp)"
            err_tmp="$(mktemp)"
            trap 'rm -f "$tmp" "${json_tmp:-}" "${err_tmp:-}"' EXIT
            jq -n --arg body "$body" '{body:$body}' > "$json_tmp"
            out="$(gh api "/repos/${REPO}/issues/comments/${id}" -X PATCH --input "$json_tmp" --jq '.html_url // ""' 2>"$err_tmp")" \
                || fail 2 "gh api comment patch failed: $(redact_text "$(cat "$err_tmp")" | tr '\n' ' ' | head -c 500)"
            emit_kv COMMENT_ID "$id"
            emit_kv COMMENT_URL "$out"
            emit_kv UPDATED true
        else
            flat="$(printf '%s' "$ids" | paste -sd, -)"
            fail 2 "multiple summary comments found for marker (ids: $flat)"
        fi
        ;;
    *)
        usage
        fail 1 "unknown command: $cmd"
        ;;
esac
