#!/usr/bin/env bash
# tracking-issue-summary.sh — upsert slim marker-keyed tracking comments.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REDACT="$SCRIPT_DIR/redact-secrets.sh"

usage() {
    cat <<'USAGE' >&2
Usage:
  tracking-issue-summary.sh upsert-summary --issue N --marker M --content-file F [--repo OWNER/REPO]
USAGE
}

fail() {
    local code="$1"
    local msg="$2"
    echo "FAILED=true"
    echo "ERROR=$msg"
    exit "$code"
}

redact_text() {
    [ -x "$REDACT" ] || fail 3 "redaction helper missing: $REDACT"
    printf '%s' "$1" | "$REDACT" || fail 3 "redaction failed"
}

cmd="${1:-}"
[ -n "$cmd" ] || { usage; exit 1; }
shift

case "$cmd" in
    upsert-summary)
        ISSUE=""; MARKER=""; CONTENT_FILE=""; REPO=""
        while [ $# -gt 0 ]; do
            case "$1" in
                --issue) ISSUE="${2:?--issue requires a value}"; shift 2 ;;
                --marker) MARKER="${2:?--marker requires a value}"; shift 2 ;;
                --content-file) CONTENT_FILE="${2:?--content-file requires a value}"; shift 2 ;;
                --repo) REPO="${2:?--repo requires a value}"; shift 2 ;;
                *) usage; fail 1 "unknown option for upsert-summary: $1" ;;
            esac
        done
        [ -n "$ISSUE" ] || fail 1 "--issue is required"
        [ -n "$MARKER" ] || fail 1 "--marker is required"
        [ -f "$CONTENT_FILE" ] || fail 1 "content file not found: $CONTENT_FILE"
        case "$ISSUE" in *[!0-9]*|"") fail 1 "invalid issue: $ISSUE" ;; esac
        case "$MARKER" in '<!-- larch:'*' -->') ;; *) fail 1 "invalid marker: $MARKER" ;; esac
        if [ -z "$REPO" ]; then
            REPO="$(gh repo view --json nameWithOwner --jq '.nameWithOwner' 2>/dev/null || true)"
            [ -n "$REPO" ] || fail 2 "could not determine repo"
        fi
        content="$(cat "$CONTENT_FILE")"
        body="$MARKER"$'\n\n'"$content"
        body="$(redact_text "$body")"
        list_err="$(mktemp)"
        list_out="$(gh api "/repos/${REPO}/issues/${ISSUE}/comments" --paginate --jq '.[] | (.id|tostring) + "\t" + (.body // "" | split("\n")[0])' 2>"$list_err")" || {
            err="$(cat "$list_err")"
            rm -f "$list_err"
            fail 2 "gh api comments fetch failed: $(redact_text "$err" | tr '\n' ' ' | head -c 500)"
        }
        rm -f "$list_err"
        ids="$(printf '%s\n' "$list_out" | awk -F'\t' -v marker="$MARKER" '$2 == marker { print $1 }')"
        count="$(printf '%s\n' "$ids" | awk 'NF { n++ } END { print n + 0 }')"
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
            echo "COMMENT_ID="
            echo "COMMENT_URL=$url"
            echo "UPDATED=false"
        elif [ "$count" -eq 1 ]; then
            id="$(printf '%s\n' "$ids" | awk 'NF { print; exit }')"
            json_tmp="$(mktemp)"
            err_tmp="$(mktemp)"
            trap 'rm -f "$tmp" "${json_tmp:-}" "${err_tmp:-}"' EXIT
            jq -n --arg body "$body" '{body:$body}' > "$json_tmp"
            out="$(gh api "/repos/${REPO}/issues/comments/${id}" -X PATCH --input "$json_tmp" --jq '.html_url // ""' 2>"$err_tmp")" \
                || fail 2 "gh api comment patch failed: $(redact_text "$(cat "$err_tmp")" | tr '\n' ' ' | head -c 500)"
            echo "COMMENT_ID=$id"
            echo "COMMENT_URL=$out"
            echo "UPDATED=true"
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
