#!/usr/bin/env bash
# named-block-write.sh — replace, append, or delete a named larch issue-body block.

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
Usage: named-block-write.sh --marker <name> --issue <N> (--content-file <path> | --delete) [--repo OWNER/REPO]
USAGE
}

emit_usage_error() {
    usage
    exit 1
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

emit_redaction_failure() {
    emit_kv FAILED "true"
    emit_kv ERROR "redaction: helper failed or not executable"
    exit 3
}

classify_current() {
    local f="$1" start_count end_count
    start_count=$(grep -c -E "$MARK_START" "$f" 2>/dev/null) || start_count=0
    end_count=$(grep -c -E "$MARK_END" "$f" 2>/dev/null) || end_count=0

    if [ "$start_count" -eq 0 ] && [ "$end_count" -eq 0 ]; then
        NB_CLASSIFY="absent"
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
    NB_START_LINE=$(grep -n -E "$MARK_START" "$f" | head -1 | cut -d: -f1)
    NB_END_LINE=$(grep -n -E "$MARK_END" "$f" | head -1 | cut -d: -f1)
    if [ "$NB_END_LINE" -lt "$NB_START_LINE" ]; then
        emit_kv MALFORMED "end-before-start"
        exit 1
    fi
    NB_CLASSIFY="present"
}

MARKER=""
ISSUE=""
CONTENT_FILE=""
REPO_ARG=""
DELETE=false
while [ $# -gt 0 ]; do
    case "$1" in
        --marker) MARKER="${2:?}"; shift 2 ;;
        --issue) ISSUE="${2:?}"; shift 2 ;;
        --content-file) CONTENT_FILE="${2:?}"; shift 2 ;;
        --delete) DELETE=true; shift ;;
        --repo) REPO_ARG="${2:?}"; shift 2 ;;
        *) larch_err "named-block-write.sh: unknown option: $1"; emit_usage_error ;;
    esac
done

if [ -z "$MARKER" ] || [ -z "$ISSUE" ]; then
    emit_usage_error
fi
case "$MARKER" in
    plan|design-pause) ;;
    *)
        if ! printf '%s' "$MARKER" | grep -Eq '^[a-z0-9][a-z0-9-]*$'; then
            larch_err "named-block-write.sh: --marker must match ^[a-z0-9][a-z0-9-]*$"
            exit 1
        fi
        larch_err "named-block-write.sh: unsupported marker: $MARKER"
        exit 1
        ;;
esac
case "$ISSUE" in
    ''|*[!0-9]*) larch_err "named-block-write.sh: --issue must be a positive integer"; exit 1 ;;
esac
if [ "$ISSUE" = "0" ]; then
    larch_err "named-block-write.sh: --issue must be a positive integer"
    exit 1
fi
if [ "$DELETE" = true ] && [ -n "$CONTENT_FILE" ]; then
    larch_err "named-block-write.sh: --delete and --content-file are mutually exclusive"
    exit 1
fi
if [ "$DELETE" = false ] && [ -z "$CONTENT_FILE" ]; then
    emit_usage_error
fi
if [ -n "$CONTENT_FILE" ] && [ ! -f "$CONTENT_FILE" ]; then
    emit_kv FAILED "true"
    emit_kv ERROR "content file not found: $CONTENT_FILE"
    exit 1
fi

MARK_START="^[[:space:]]*<!--[[:space:]]+larch:${MARKER}:start[[:space:]]+-->[[:space:]]*$"
MARK_END="^[[:space:]]*<!--[[:space:]]+larch:${MARKER}:end[[:space:]]+-->[[:space:]]*$"
CANON_START="<!-- larch:${MARKER}:start -->"
CANON_END="<!-- larch:${MARKER}:end -->"

REPO=$(resolve_repo "$REPO_ARG")

ERR_TMP=$(mktemp "${TMPDIR:-/tmp}/named-block-write-err.XXXXXX")
CUR_BODY_FILE=$(mktemp "${TMPDIR:-/tmp}/named-block-write-cur.XXXXXX")
COMPOSED=$(mktemp "${TMPDIR:-/tmp}/named-block-write-new.XXXXXX")
BLOCK_TMP=$(mktemp "${TMPDIR:-/tmp}/named-block-write-blk.XXXXXX")
REDACTED_OUT=$(mktemp "${TMPDIR:-/tmp}/named-block-write-red.XXXXXX")
EDIT_TMP=""
trap 'rm -f "$ERR_TMP" "$CUR_BODY_FILE" "$COMPOSED" "$BLOCK_TMP" "$REDACTED_OUT"; [ -n "${EDIT_TMP:-}" ] && rm -f "$EDIT_TMP"' EXIT

BODY=""
if ! BODY=$(gh issue view "$ISSUE" --repo "$REPO" --json body 2>"$ERR_TMP" | jq -r '.body // ""' 2>>"$ERR_TMP"); then
    ERR_CONTENT=$(cat "$ERR_TMP" 2>/dev/null || true)
    emit_gh_failure "$ERR_CONTENT"
fi

printf '%s' "$BODY" > "$CUR_BODY_FILE"

NB_CLASSIFY=""
NB_START_LINE=""
NB_END_LINE=""
classify_current "$CUR_BODY_FILE"

MODE=""
MARKERS_PRESENT="false"
if [ "$DELETE" = true ]; then
    if [ "$NB_CLASSIFY" = "absent" ]; then
        cp "$CUR_BODY_FILE" "$COMPOSED"
        MODE="absent-noop"
        MARKERS_PRESENT="false"
    else
        awk -v s="$NB_START_LINE" -v e="$NB_END_LINE" 'NR<s || NR>e' "$CUR_BODY_FILE" > "$COMPOSED"
        MODE="removed"
        MARKERS_PRESENT="true"
    fi
else
    INNER=$(cat "$CONTENT_FILE")
    {
        printf '%s\n' "$CANON_START"
        if [ -n "$INNER" ]; then
            printf '%s\n' "$INNER"
        fi
        printf '%s\n' "$CANON_END"
    } > "$BLOCK_TMP"

    if [ "$NB_CLASSIFY" = "absent" ]; then
        MARKERS_PRESENT="false"
        if [ ! -s "$CUR_BODY_FILE" ]; then
            cp "$BLOCK_TMP" "$COMPOSED"
        else
            cat "$CUR_BODY_FILE" > "$COMPOSED"
            printf '\n\n' >> "$COMPOSED"
            cat "$BLOCK_TMP" >> "$COMPOSED"
        fi
        MODE="appended"
    else
        MARKERS_PRESENT="true"
        awk -v s="$NB_START_LINE" 'NR<s' "$CUR_BODY_FILE" > "$COMPOSED"
        cat "$BLOCK_TMP" >> "$COMPOSED"
        awk -v e="$NB_END_LINE" 'NR>e' "$CUR_BODY_FILE" >> "$COMPOSED"
        MODE="replaced"
    fi
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

EDIT_TMP=$(mktemp "${TMPDIR:-/tmp}/named-block-write-edit.XXXXXX")
cp "$REDACTED_OUT" "$EDIT_TMP"

edit_fail_file=$(mktemp "${TMPDIR:-/tmp}/named-block-write-edit.XXXXXX")
if with_transient_retry transient_envelope_predicate_none "$edit_fail_file" \
    gh issue edit "$ISSUE" --repo "$REPO" --body-file "$EDIT_TMP"; then
    :
else
    ERR_CONTENT=$(cat "$ERR_TMP" 2>/dev/null || true)
    rm -f "$edit_fail_file"
    emit_gh_failure "$ERR_CONTENT"
fi
rm -f "$edit_fail_file"

emit_kv WRITTEN "true"
emit_kv MODE "$MODE"
emit_kv MARKERS_PRESENT "$MARKERS_PRESENT"
emit_kv BODY_BYTES "$BODY_BYTES"
exit 0
