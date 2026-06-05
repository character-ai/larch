#!/usr/bin/env bash
# compute-pr-line-counts.sh — PR diff line counts split by larch-logs vs code.
set -euo pipefail

REPO=""
PR_NUMBER=""

usage() {
    printf 'Usage: compute-pr-line-counts.sh --pr-number <N> [--repo <owner/name>]\n' >&2
}

while [ $# -gt 0 ]; do
    case "$1" in
        --repo)
            REPO="${2:-}"
            shift 2
            ;;
        --pr-number)
            PR_NUMBER="${2:-}"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            usage
            exit 2
            ;;
    esac
done

case "$PR_NUMBER" in
    '' | 0 | *[!0-9]*)
        printf 'LINES_STATUS=skipped\nREASON=no-pr\n'
        exit 0
        ;;
esac

if [ -n "$REPO" ]; then
    _repo_owner="${REPO%%/*}"
    _repo_name="${REPO#*/}"
    if [ "$_repo_owner" = "$REPO" ] || [ -z "$_repo_name" ] || [ "$_repo_name" != "${_repo_name#*/}" ] || [ -z "$_repo_owner" ]; then
        printf 'LINES_STATUS=skipped\nREASON=invalid-repo\n'
        exit 0
    fi
    endpoint="repos/${REPO}/pulls/${PR_NUMBER}/files"
else
    endpoint="repos/{owner}/{repo}/pulls/${PR_NUMBER}/files"
fi

tsv_tmp="$(mktemp "${TMPDIR:-/tmp}/compute-pr-line-counts.XXXXXX")"
# shellcheck disable=SC2317
cleanup() { rm -f "$tsv_tmp"; }
trap cleanup EXIT

set +e
gh api --paginate "$endpoint" --jq '.[] | [.filename, .additions, .deletions] | @tsv' >"$tsv_tmp" 2>/dev/null
gh_rc=$?
set -e

if [ "$gh_rc" -ne 0 ]; then
    printf 'LINES_STATUS=unavailable\nREASON=gh-failed\n'
    exit 0
fi

awk -F '\t' '
BEGIN {
    code_added = 0
    code_deleted = 0
    logs_added = 0
    logs_deleted = 0
}
NF >= 3 {
    path = $1
    add = $2 + 0
    del = $3 + 0
    if (path ~ /^larch-logs\//) {
        logs_added += add
        logs_deleted += del
    } else {
        code_added += add
        code_deleted += del
    }
}
END {
    printf "LINES_STATUS=ok\n"
    printf "CODE_ADDED=%d\n", code_added
    printf "CODE_DELETED=%d\n", code_deleted
    printf "LOGS_ADDED=%d\n", logs_added
    printf "LOGS_DELETED=%d\n", logs_deleted
}
' "$tsv_tmp"

trap - EXIT
rm -f "$tsv_tmp"
exit 0
