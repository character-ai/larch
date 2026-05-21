#!/usr/bin/env bash
# plan-block-write.sh — replace or append larch:plan marker block in issue body.
#
# Usage: plan-block-write.sh --issue <N> --content-file <path> [--repo OWNER/REPO]
#
# Stdout: WRITTEN=, MODE=, MARKERS_PRESENT=, BODY_BYTES=.
# Malformed body: MALFORMED=…, exit 1. gh failure: FAILED=true ERROR=…, exit 2.
# Redaction failure: FAILED=true ERROR=…, exit 3.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init

REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REDACT_HELPER="$REPO_ROOT/scripts/redact-secrets.sh"

MARK_START='^[[:space:]]*<!--[[:space:]]+larch:plan:start[[:space:]]+-->[[:space:]]*$'
MARK_END='^[[:space:]]*<!--[[:space:]]+larch:plan:end[[:space:]]+-->[[:space:]]*$'
CANON_START='<!-- larch:plan:start -->'
CANON_END='<!-- larch:plan:end -->'

usage() {
    while IFS= read -r line; do larch_err "$line"; done <<'USAGE'
Usage: plan-block-write.sh --issue <N> --content-file <path> [--repo OWNER/REPO]
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

emit_redaction_failure() {
    emit_kv FAILED "true"
    emit_kv ERROR "redaction: helper failed or not executable"
    exit 3
}

# Sets: PB_CLASSIFY (absent|present), PB_START_LINE, PB_END_LINE; or emits MALFORMED and exits 1.
plan_block_classify_current() {
    local f="$1" start_count end_count
    start_count=$(grep -c -E "$MARK_START" "$f" 2>/dev/null) || start_count=0
    end_count=$(grep -c -E "$MARK_END" "$f" 2>/dev/null) || end_count=0

    if [ "$start_count" -eq 0 ] && [ "$end_count" -eq 0 ]; then
        PB_CLASSIFY="absent"
        return 0
    fi
    if [ "$start_count" -gt 1 ]; then
        emit_kv MALFORMED "multiple-start"
        exit 1
    fi
    if [ "$end_count" -gt 1 ]; then
        emit_kv MALFORMED "multiple-end"
        exit 1
    fi
    if [ "$start_count" -eq 1 ] && [ "$end_count" -eq 0 ]; then
        emit_kv MALFORMED "start-without-end"
        exit 1
    fi
    if [ "$start_count" -eq 0 ] && [ "$end_count" -eq 1 ]; then
        emit_kv MALFORMED "end-without-start"
        exit 1
    fi
    PB_START_LINE=$(grep -n -E "$MARK_START" "$f" | head -1 | cut -d: -f1)
    PB_END_LINE=$(grep -n -E "$MARK_END" "$f" | head -1 | cut -d: -f1)
    if [ "$PB_END_LINE" -lt "$PB_START_LINE" ]; then
        emit_kv MALFORMED "end-before-start"
        exit 1
    fi
    PB_CLASSIFY="present"
}

ISSUE=""
CONTENT_FILE=""
REPO_ARG=""
while [ $# -gt 0 ]; do
    case "$1" in
        --issue) ISSUE="${2:?}"; shift 2 ;;
        --content-file) CONTENT_FILE="${2:?}"; shift 2 ;;
        --repo) REPO_ARG="${2:?}"; shift 2 ;;
        *) larch_err "plan-block-write.sh: unknown option: $1"; usage; exit 1 ;;
    esac
done

if [ -z "$ISSUE" ] || [ -z "$CONTENT_FILE" ]; then
    usage
    exit 1
fi

case "$ISSUE" in
    ''|*[!0-9]*) larch_err "plan-block-write.sh: --issue must be a positive integer"; exit 1 ;;
esac
if [ "$ISSUE" = "0" ]; then
    larch_err "plan-block-write.sh: --issue must be a positive integer"
    exit 1
fi

if [ ! -f "$CONTENT_FILE" ]; then
    emit_kv FAILED "true"
    emit_kv ERROR "content file not found: $CONTENT_FILE"
    exit 1
fi

REPO=$(resolve_repo "$REPO_ARG")

ERR_TMP=$(mktemp "${TMPDIR:-/tmp}/plan-block-write-err.XXXXXX")
CUR_BODY_FILE=$(mktemp "${TMPDIR:-/tmp}/plan-block-write-cur.XXXXXX")
COMPOSED=$(mktemp "${TMPDIR:-/tmp}/plan-block-write-new.XXXXXX")
BLOCK_TMP=$(mktemp "${TMPDIR:-/tmp}/plan-block-write-blk.XXXXXX")
REDACTED_OUT=$(mktemp "${TMPDIR:-/tmp}/plan-block-write-red.XXXXXX")
EDIT_TMP=""
trap 'rm -f "$ERR_TMP" "$CUR_BODY_FILE" "$COMPOSED" "$BLOCK_TMP" "$REDACTED_OUT"; [ -n "${EDIT_TMP:-}" ] && rm -f "$EDIT_TMP"' EXIT

BODY=""
if ! BODY=$(gh issue view "$ISSUE" --repo "$REPO" --json body 2>"$ERR_TMP" | jq -r '.body // ""' 2>>"$ERR_TMP"); then
    ERR_CONTENT=$(cat "$ERR_TMP" 2>/dev/null || true)
    emit_gh_failure "$ERR_CONTENT"
fi

printf '%s' "$BODY" > "$CUR_BODY_FILE"

PB_CLASSIFY=""
PB_START_LINE=""
PB_END_LINE=""
plan_block_classify_current "$CUR_BODY_FILE"

INNER=$(cat "$CONTENT_FILE")
{
    printf '%s\n' "$CANON_START"
    if [ -n "$INNER" ]; then
        printf '%s\n' "$INNER"
    fi
    printf '%s\n' "$CANON_END"
} > "$BLOCK_TMP"

MODE=""
MARKERS_PRESENT="false"
if [ "$PB_CLASSIFY" = "absent" ]; then
    MARKERS_PRESENT="false"
    if [ ! -s "$CUR_BODY_FILE" ]; then
        cp "$BLOCK_TMP" "$COMPOSED"
        MODE="appended"
    else
        cat "$CUR_BODY_FILE" > "$COMPOSED"
        printf '\n\n' >> "$COMPOSED"
        cat "$BLOCK_TMP" >> "$COMPOSED"
        MODE="appended"
    fi
else
    MARKERS_PRESENT="true"
    awk -v s="$PB_START_LINE" 'NR<s' "$CUR_BODY_FILE" > "$COMPOSED"
    cat "$BLOCK_TMP" >> "$COMPOSED"
    awk -v e="$PB_END_LINE" 'NR>e' "$CUR_BODY_FILE" >> "$COMPOSED"
    MODE="replaced"
fi

if [ ! -x "$REDACT_HELPER" ]; then
    emit_kv FAILED "true"
    emit_kv ERROR "redact-secrets.sh not executable"
    exit 3
fi
if ! "$REDACT_HELPER" < "$COMPOSED" > "$REDACTED_OUT"; then
    emit_redaction_failure
fi

BODY_BYTES=$(wc -c < "$REDACTED_OUT" | tr -d ' ')

EDIT_TMP=$(mktemp "${TMPDIR:-/tmp}/plan-block-write-edit.XXXXXX")
cp "$REDACTED_OUT" "$EDIT_TMP"

if ! gh issue edit "$ISSUE" --repo "$REPO" --body-file "$EDIT_TMP" 2>"$ERR_TMP"; then
    ERR_CONTENT=$(cat "$ERR_TMP" 2>/dev/null || true)
    emit_gh_failure "$ERR_CONTENT"
fi

emit_kv WRITTEN "true"
emit_kv MODE "$MODE"
emit_kv MARKERS_PRESENT "$MARKERS_PRESENT"
emit_kv BODY_BYTES "$BODY_BYTES"
exit 0
