#!/usr/bin/env bash
# plan-block-read.sh — extract <!-- larch:plan:start --> … <!-- larch:plan:end --> from issue body.
#
# Usage: plan-block-read.sh --issue <N> --output <path> [--repo OWNER/REPO]
#
# Stdout: BLOCK_PRESENT=true|false, OUTPUT=<path> when present.
# Malformed: MALFORMED=<token> on stdout, exit 1.
# gh failure: FAILED=true ERROR=…, exit 2.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init

REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REDACT_HELPER="$REPO_ROOT/scripts/redact-secrets.sh"

MARK_START='^[[:space:]]*<!--[[:space:]]+larch:plan:start[[:space:]]+-->[[:space:]]*$'
MARK_END='^[[:space:]]*<!--[[:space:]]+larch:plan:end[[:space:]]+-->[[:space:]]*$'

usage() {
    while IFS= read -r line; do larch_err "$line"; done <<'USAGE'
Usage: plan-block-read.sh --issue <N> --output <path> [--repo OWNER/REPO]
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
    local err_text="$1" redacted
    if [ ! -x "$REDACT_HELPER" ]; then
        printf '%s' "$err_text" | tr '\n' ' ' | head -c 500
        return
    fi
    redacted=$(printf '%s' "$err_text" | "$REDACT_HELPER") || printf '%s' "$err_text"
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
OUT_PATH=""
REPO_ARG=""
while [ $# -gt 0 ]; do
    case "$1" in
        --issue) ISSUE="${2:?}"; shift 2 ;;
        --output) OUT_PATH="${2:?}"; shift 2 ;;
        --repo) REPO_ARG="${2:?}"; shift 2 ;;
        *) larch_err "plan-block-read.sh: unknown option: $1"; usage; exit 1 ;;
    esac
done

if [ -z "$ISSUE" ] || [ -z "$OUT_PATH" ]; then
    usage
    exit 1
fi

case "$ISSUE" in
    ''|*[!0-9]*) larch_err "plan-block-read.sh: --issue must be a positive integer"; exit 1 ;;
esac
if [ "$ISSUE" = "0" ]; then
    larch_err "plan-block-read.sh: --issue must be a positive integer"
    exit 1
fi

REPO=$(resolve_repo "$REPO_ARG")

ERR_TMP=$(mktemp "${TMPDIR:-/tmp}/plan-block-read-err.XXXXXX")
trap 'rm -f "$ERR_TMP"' EXIT

BODY=""
if ! BODY=$(gh issue view "$ISSUE" --repo "$REPO" --json body --jq -r '(.body // "")' 2>"$ERR_TMP"); then
    ERR_CONTENT=$(cat "$ERR_TMP" 2>/dev/null || true)
    emit_gh_failure "$ERR_CONTENT"
fi

BODY_TMP=$(mktemp "${TMPDIR:-/tmp}/plan-block-read-body.XXXXXX")
printf '%s' "$BODY" > "$BODY_TMP"

start_count=0
end_count=0
start_count=$(grep -c -E "$MARK_START" "$BODY_TMP" 2>/dev/null) || start_count=0
end_count=$(grep -c -E "$MARK_END" "$BODY_TMP" 2>/dev/null) || end_count=0

malformed_out() {
    emit_kv MALFORMED "$1"
    rm -f "$BODY_TMP"
    exit 1
}

if [ "$start_count" -eq 0 ] && [ "$end_count" -eq 0 ]; then
    : > "$OUT_PATH"
    emit_kv BLOCK_PRESENT "false"
    rm -f "$BODY_TMP"
    exit 0
fi

if [ "$start_count" -gt 1 ]; then
    malformed_out "multiple-start"
fi
if [ "$end_count" -gt 1 ]; then
    malformed_out "multiple-end"
fi
if [ "$start_count" -eq 1 ] && [ "$end_count" -eq 0 ]; then
    malformed_out "start-without-end"
fi
if [ "$start_count" -eq 0 ] && [ "$end_count" -eq 1 ]; then
    malformed_out "end-without-start"
fi

# Exactly one start and one end from here.
start_line=$(grep -n -E "$MARK_START" "$BODY_TMP" | head -1 | cut -d: -f1)
end_line=$(grep -n -E "$MARK_END" "$BODY_TMP" | head -1 | cut -d: -f1)

if [ "$end_line" -lt "$start_line" ]; then
    malformed_out "end-before-start"
fi

# Inner lines: between start_line and end_line exclusive.
awk -v s="$start_line" -v e="$end_line" 'NR>s && NR<e' "$BODY_TMP" > "$OUT_PATH"

emit_kv BLOCK_PRESENT "true"
emit_kv OUTPUT "$OUT_PATH"
rm -f "$BODY_TMP"
exit 0
