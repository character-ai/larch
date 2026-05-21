#!/usr/bin/env bash
# clarify-state.sh — derive clarification STATE from issue comment markers.
#
# Usage: clarify-state.sh --issue <N> [--repo OWNER/REPO]
#
# Stdout: LAST_REQUEST_ID=, LAST_RESPONSE_ID=, STATE=clean|awaiting-response|response-pending|ambiguous

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init

REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REDACT_HELPER="$REPO_ROOT/scripts/redact-secrets.sh"

MARK_LINE='^[[:space:]]*<!--[[:space:]]+larch:clarify-(request|response)[[:space:]]+id=[1-9][0-9]*[[:space:]]*-->[[:space:]]*$'

usage() {
    while IFS= read -r line; do larch_err "$line"; done <<'USAGE'
Usage: clarify-state.sh --issue <N> [--repo OWNER/REPO]
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
REPO_ARG=""
while [ $# -gt 0 ]; do
    case "$1" in
        --issue) ISSUE="${2:?}"; shift 2 ;;
        --repo) REPO_ARG="${2:?}"; shift 2 ;;
        *) larch_err "clarify-state.sh: unknown option: $1"; usage; exit 1 ;;
    esac
done

if [ -z "$ISSUE" ]; then
    usage
    exit 1
fi

case "$ISSUE" in
    ''|*[!0-9]*) larch_err "clarify-state.sh: --issue must be a positive integer"; exit 1 ;;
esac
if [ "$ISSUE" = "0" ]; then
    larch_err "clarify-state.sh: --issue must be a positive integer"
    exit 1
fi

REPO=$(resolve_repo "$REPO_ARG")

ERR_TMP=$(mktemp "${TMPDIR:-/tmp}/clarify-state-err.XXXXXX")
trap 'rm -f "$ERR_TMP"' EXIT

MERGED=""
if ! MERGED=$(gh api --paginate --slurp "repos/${REPO}/issues/${ISSUE}/comments" 2>"$ERR_TMP" | jq -s 'add // []' 2>>"$ERR_TMP"); then
    ERR_CONTENT=$(cat "$ERR_TMP" 2>/dev/null || true)
    emit_gh_failure "$ERR_CONTENT"
fi

FIRST_LINES=$(mktemp "${TMPDIR:-/tmp}/clarify-state-fl.XXXXXX")
EVENTS=$(mktemp "${TMPDIR:-/tmp}/clarify-state-ev.XXXXXX")
trap 'rm -f "$ERR_TMP" "$FIRST_LINES" "$EVENTS"' EXIT

printf '%s' "$MERGED" | jq -r '.[] | (.body // "" | (split("\n")[0] // ""))' > "$FIRST_LINES"

while IFS= read -r line || [ -n "$line" ]; do
    [ -z "$line" ] && continue
    if printf '%s' "$line" | grep -q -E "$MARK_LINE"; then
        kind=$(printf '%s' "$line" | sed -E 's/^[[:space:]]*<!--[[:space:]]+larch:clarify-(request|response)[[:space:]]+id=([1-9][0-9]*)[[:space:]]*-->.*/\1/')
        mid=$(printf '%s' "$line" | sed -E 's/^[[:space:]]*<!--[[:space:]]+larch:clarify-(request|response)[[:space:]]+id=([1-9][0-9]*)[[:space:]]*-->.*/\2/')
        printf '%s %s\n' "$kind" "$mid" >> "$EVENTS"
    fi
done < "$FIRST_LINES"

STATE_OUT=$(awk '
function max(a,b){ return a>b?a:b }
BEGIN{ amb=0; max_so_far=0; n=0; last_req=""; last_resp="" }
{
    n++
    kind[n]=$1
    id[n]=$2+0
    if (id[n] < max_so_far) amb=1
    max_so_far=max(max_so_far, id[n])
    if (kind[n]=="request") rq[id[n]]++
    else sc[id[n]]++
    if (kind[n]=="request") { last_req=id[n]; last_req_i=n }
    if (kind[n]=="response") last_resp=id[n]
}
END {
    for (k in rq) if (rq[k]>1) amb=1
    for (k in sc) if (sc[k]>1) amb=1
    for (i=1;i<=n;i++) {
        if (kind[i]=="response") {
            seen=0
            for (j=1;j<i;j++)
                if (kind[j]=="request" && id[j]==id[i]) seen=1
            if (!seen) amb=1
        }
    }
    max_all=0
    for (i=1;i<=n;i++) if (id[i]>max_all) max_all=id[i]

    if (amb) {
        printf "STATE=ambiguous\n"
        printf "LAST_REQUEST_ID=%s\n", (last_req==""?"":last_req)
        printf "LAST_RESPONSE_ID=%s\n", (last_resp==""?"":last_resp)
        exit 0
    }
    if (last_req=="") {
        printf "STATE=clean\nLAST_REQUEST_ID=\nLAST_RESPONSE_ID=\n"
        exit 0
    }
    rid=last_req
    li=last_req_i
    has_match=0
    for (i=li+1;i<=n;i++)
        if (kind[i]=="response" && id[i]==rid) has_match=1
    if (!has_match) {
        printf "STATE=awaiting-response\n"
        printf "LAST_REQUEST_ID=%s\n", rid
        printf "LAST_RESPONSE_ID=%s\n", (last_resp==""?"":last_resp)
        exit 0
    }
    gap_unsat=0
    for (k=1;k<rid;k++)
        if (rq[k]>0 && sc[k]==0) gap_unsat=1
    if (gap_unsat) {
        printf "STATE=ambiguous\n"
        printf "LAST_REQUEST_ID=%s\n", rid
        printf "LAST_RESPONSE_ID=%s\n", (last_resp==""?"":last_resp)
        exit 0
    }
    if (rid==max_all) {
        printf "STATE=response-pending\n"
        printf "LAST_REQUEST_ID=%s\n", rid
        printf "LAST_RESPONSE_ID=%s\n", (last_resp==""?"":last_resp)
        exit 0
    }
    printf "STATE=ambiguous\n"
    printf "LAST_REQUEST_ID=%s\n", rid
    printf "LAST_RESPONSE_ID=%s\n", (last_resp==""?"":last_resp)
}
' "$EVENTS")

# awk prints KEY=value lines; re-emit via emit_kv for quiet routing
while IFS= read -r kv; do
    [ -z "$kv" ] && continue
    key="${kv%%=*}"
    val="${kv#*=}"
    emit_kv "$key" "$val"
done <<EOF
$STATE_OUT
EOF

exit 0
