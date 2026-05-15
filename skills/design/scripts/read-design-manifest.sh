#!/usr/bin/env bash
# read-design-manifest.sh — Safely verify a /design artifact manifest.

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd -P)
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/../../../scripts/lib-quiet.sh"
larch_quiet_init

# Round 3 FINDING_R3_G: the sibling .md contract promises this script never
# exits non-zero for manifest rejection — every reject path emits
# MANIFEST_FAILED=true / ERROR=<token> and exits 0. Without an ERR trap,
# unexpected I/O failures (disk, race on manifest deletion mid-read) under
# set -euo pipefail can terminate non-zero with no envelope, silently
# breaking fail-closed callers that only parse stdout. Catch any unhandled
# failure and emit the documented internal-error envelope.
# shellcheck disable=SC2317
on_err() {
    emit_kv MANIFEST_FAILED true
    emit_kv ERROR internal-error
    exit 0
}
trap on_err ERR

IMPLEMENT_TMPDIR="${IMPLEMENT_TMPDIR:-}"
MANIFEST=""
EMIT_LOAD_BREADCRUMB=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --implement-tmpdir)
            IMPLEMENT_TMPDIR="${2:?--implement-tmpdir requires a value}"
            shift 2
            ;;
        --manifest)
            MANIFEST="${2:?--manifest requires a value}"
            shift 2
            ;;
        --emit-load-breadcrumb)
            EMIT_LOAD_BREADCRUMB=true
            shift
            ;;
        *)
            emit_kv MANIFEST_FAILED true
            emit_kv ERROR unknown-flag
            exit 0
            ;;
    esac
done

if [[ -z "$IMPLEMENT_TMPDIR" ]]; then
    emit_kv MANIFEST_FAILED true
    emit_kv ERROR missing-implement-tmpdir
    exit 0
fi

EXPORT_DIR="$IMPLEMENT_TMPDIR/design-export"
if [[ -z "$MANIFEST" ]]; then
    MANIFEST="$EXPORT_DIR/manifest.env"
fi

fail() {
    emit_kv MANIFEST_FAILED true
    emit_kv ERROR "$1"
    exit 0
}

if [[ ! -f "$MANIFEST" || ! -s "$MANIFEST" ]]; then
    fail "manifest-not-found"
fi

canonical_dir() {
    local path="$1"
    local dir
    dir=$(cd -P "$path" 2>/dev/null && pwd -P) || return 1
    printf '%s\n' "$dir"
}

canonical_file() {
    local path="$1"
    local dir base
    dir=$(dirname "$path")
    base=$(basename "$path")
    dir=$(cd -P "$dir" 2>/dev/null && pwd -P) || return 1
    printf '%s/%s\n' "$dir" "$base"
}

EXPORT_CANON=$(canonical_dir "$EXPORT_DIR") || fail "export-dir-not-found"

check_value() {
    local value="$1"
    case "$value" in
        *$'\001'*|*$'\002'*|*$'\003'*|*$'\004'*|*$'\005'*|*$'\006'*|*$'\007'*|*$'\010'*|*$'\011'*|*$'\013'*|*$'\014'*|*$'\015'*|*$'\016'*|*$'\017'*|*$'\020'*|*$'\021'*|*$'\022'*|*$'\023'*|*$'\024'*|*$'\025'*|*$'\026'*|*$'\027'*|*$'\030'*|*$'\031'*|*$'\032'*|*$'\033'*|*$'\034'*|*$'\035'*|*$'\036'*|*$'\037'*|*$'\177'*)
            fail "control-char"
            ;;
    esac
}

PATH_OUTPUT=""

check_path() {
    local key="$1"
    local value="$2"
    local require_nonempty="$3"
    local canon

    [[ "$value" = /* ]] || fail "path-not-absolute"
    [[ ! -L "$value" ]] || fail "symlink-rejected"
    [[ -f "$value" ]] || fail "path-not-regular"
    canon=$(canonical_file "$value") || fail "path-not-regular"
    case "$canon" in
        "$EXPORT_CANON"/*) ;;
        *) fail "path-escaped-export-dir" ;;
    esac
    if [[ "$require_nonempty" = true && ! -s "$value" ]]; then
        fail "required-empty"
    fi
    PATH_OUTPUT+=$(printf '%s=%s\n' "$key" "$canon")$'\n'
}

LOAD_BEARING_KEYS=(MANIFEST_VERSION PLAN_FILE PLAN_REVIEW_TALLY_FILE CONTESTED_CRITERIA_FILE OOS_FILE REJECTED_FINDINGS_FILE ACCEPTED_PLAN_FINDINGS_FILE ARCHITECTURE_DIAGRAM_FILE TIMESTAMP SESSION_ID)

is_load_bearing_key() {
    local k="$1"
    local lb
    for lb in "${LOAD_BEARING_KEYS[@]}"; do
        [[ "$lb" = "$k" ]] && return 0
    done
    return 1
}

SEEN_KEYS=""

mark_seen_key() {
    local k="$1"
    is_load_bearing_key "$k" || return 0
    case " $SEEN_KEYS " in
        *" $k "*) fail "duplicate-key:$k" ;;
    esac
    SEEN_KEYS+=" $k"
}

MANIFEST_VERSION=""
PLAN_FILE=""
PLAN_REVIEW_TALLY_FILE=""
CONTESTED_CRITERIA_FILE=""
OOS_FILE=""
REJECTED_FINDINGS_FILE=""
ACCEPTED_PLAN_FINDINGS_FILE=""
ARCHITECTURE_DIAGRAM_FILE=""
TIMESTAMP=""
SESSION_ID=""

while IFS= read -r line || [[ -n "$line" ]]; do
    [[ -n "$line" ]] || fail "malformed-line"
    case "$line" in
        *=*) ;;
        *) fail "malformed-line" ;;
    esac
    key=${line%%=*}
    value=${line#*=}
    [[ "$key" =~ ^[A-Z][A-Z0-9_]*$ ]] || fail "invalid-key"
    check_value "$value"
    mark_seen_key "$key"
    case "$key" in
        MANIFEST_VERSION) MANIFEST_VERSION="$value" ;;
        PLAN_FILE) PLAN_FILE="$value" ;;
        PLAN_REVIEW_TALLY_FILE) PLAN_REVIEW_TALLY_FILE="$value" ;;
        CONTESTED_CRITERIA_FILE) CONTESTED_CRITERIA_FILE="$value" ;;
        OOS_FILE) OOS_FILE="$value" ;;
        REJECTED_FINDINGS_FILE) REJECTED_FINDINGS_FILE="$value" ;;
        ACCEPTED_PLAN_FINDINGS_FILE) ACCEPTED_PLAN_FINDINGS_FILE="$value" ;;
        ARCHITECTURE_DIAGRAM_FILE) ARCHITECTURE_DIAGRAM_FILE="$value" ;;
        TIMESTAMP) TIMESTAMP="$value" ;;
        SESSION_ID) SESSION_ID="$value" ;;
        *) ;;
    esac
done < "$MANIFEST"

[[ "$MANIFEST_VERSION" = "1" ]] || fail "unsupported-version"
[[ -n "$PLAN_FILE" ]] || fail "missing-plan-file"
[[ -n "$PLAN_REVIEW_TALLY_FILE" ]] || fail "missing-plan-review-tally-file"
[[ -n "$CONTESTED_CRITERIA_FILE" ]] || fail "missing-contested-criteria-file"
[[ -n "$OOS_FILE" ]] || fail "missing-oos-file"
[[ -n "$REJECTED_FINDINGS_FILE" ]] || fail "missing-rejected-findings-file"
[[ -n "$ACCEPTED_PLAN_FINDINGS_FILE" ]] || fail "missing-accepted-plan-findings-file"
[[ -n "$TIMESTAMP" ]] || fail "missing-timestamp"
[[ -n "$SESSION_ID" ]] || fail "missing-session-id"

check_path "PLAN_FILE" "$PLAN_FILE" true
check_path "PLAN_REVIEW_TALLY_FILE" "$PLAN_REVIEW_TALLY_FILE" true
check_path "CONTESTED_CRITERIA_FILE" "$CONTESTED_CRITERIA_FILE" false
check_path "OOS_FILE" "$OOS_FILE" false
check_path "REJECTED_FINDINGS_FILE" "$REJECTED_FINDINGS_FILE" false
check_path "ACCEPTED_PLAN_FINDINGS_FILE" "$ACCEPTED_PLAN_FINDINGS_FILE" false
if [[ -n "$ARCHITECTURE_DIAGRAM_FILE" ]]; then
    check_path "ARCHITECTURE_DIAGRAM_FILE" "$ARCHITECTURE_DIAGRAM_FILE" false
fi

# All path validations passed. Emit success envelope: MANIFEST_OK=true must
# precede the buffered KEY=value lines so a fail-closed consumer sees a clean
# envelope (FINDING_1 of /review Round 1).
emit_kv MANIFEST_OK true
while IFS= read -r line || [[ -n "$line" ]]; do
    [[ -n "$line" ]] || continue
    emit "$line"
done <<< "$PATH_OUTPUT"
emit_kv TIMESTAMP "$TIMESTAMP"
emit_kv SESSION_ID "$SESSION_ID"

if [[ "$EMIT_LOAD_BREADCRUMB" = true ]]; then
    # Human-readable breadcrumb. Deliberately uses "plan=<basename>" rather than
    # "PLAN_FILE=<basename>" so the line cannot be mis-captured by a
    # non-anchored `grep 'PLAN_FILE='` extraction over the reader's stdout —
    # the load-bearing envelope key stays unique to the canonical-path line
    # emitted earlier by check_path.
    emit_breadcrumb "📥 1: design plan — manifest loaded (plan=$(basename "$PLAN_FILE"))"
fi
