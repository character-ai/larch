#!/usr/bin/env bash
# check-phantom-dirty.sh - Map baseline dirty-tree output to phantom warnings.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init

BASELINE=""
STEP=""
PHANTOM_PATHS_DIR=""
PARSE_ERROR=""

emit_status() {
    local status="$1"
    local reason="${2:-}"
    emit_kv STATUS "$status"
    if [[ -n "$reason" ]]; then
        emit_kv REASON "$reason"
    fi
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --baseline)
            if [[ $# -lt 2 ]]; then PARSE_ERROR="baseline-missing-value"; break; fi
            BASELINE="$2"; shift 2 ;;
        --step)
            if [[ $# -lt 2 ]]; then PARSE_ERROR="step-missing-value"; break; fi
            STEP="$2"; shift 2 ;;
        --phantom-paths-dir)
            if [[ $# -lt 2 ]]; then PARSE_ERROR="phantom-paths-dir-missing-value"; break; fi
            PHANTOM_PATHS_DIR="$2"; shift 2 ;;
        *)
            PARSE_ERROR="unknown-flag"; break ;;
    esac
done

if [[ -z "$PARSE_ERROR" ]]; then
    [[ -n "$BASELINE" ]] || PARSE_ERROR="baseline-required"
    [[ -n "$STEP" ]] || PARSE_ERROR="step-required"
    [[ -n "$PHANTOM_PATHS_DIR" ]] || PARSE_ERROR="phantom-paths-dir-required"
fi

if [[ -n "$PARSE_ERROR" ]]; then
    emit_status unknown "$PARSE_ERROR"
fi

if ! [[ "$STEP" =~ ^[A-Za-z0-9_.-]+$ ]]; then
    emit_status unknown "bad-step"
fi

CHECK_OUT=""
if ! CHECK_OUT=$("$SCRIPT_DIR/check-mid-run-dirty-tree.sh" --mode baseline --baseline "$BASELINE" 2>/dev/null); then
    emit_status unknown "check-mid-run-dirty-tree-failed"
fi

STATUS=""
REASON=""
NEW_UNTRACKED_PATHS_FILE=""

while IFS= read -r line; do
    case "$line" in
        STATUS=*) STATUS="${line#STATUS=}" ;;
        REASON=*) REASON="${line#REASON=}" ;;
        NEW_UNTRACKED_PATHS_FILE=*) NEW_UNTRACKED_PATHS_FILE="${line#NEW_UNTRACKED_PATHS_FILE=}" ;;
    esac
done <<< "$CHECK_OUT"

case "$STATUS" in
    clean)
        emit_status clean
        ;;
    dirty)
        if [[ -n "$NEW_UNTRACKED_PATHS_FILE" && -s "$NEW_UNTRACKED_PATHS_FILE" ]]; then
            mkdir -p "$PHANTOM_PATHS_DIR" 2>/dev/null || emit_status unknown "phantom-paths-dir-create-failed"
            PHANTOM_PATHS_FILE="$PHANTOM_PATHS_DIR/phantom-paths-$STEP.z"
            cp "$NEW_UNTRACKED_PATHS_FILE" "$PHANTOM_PATHS_FILE" 2>/dev/null || emit_status unknown "phantom-paths-write-failed"
            if ! PHANTOM_COUNT=$(LC_ALL=C tr -cd '\0' < "$PHANTOM_PATHS_FILE" | wc -c | tr -d '[:space:]'); then
                emit_status unknown "phantom-count-failed"
            fi
            emit_kv STATUS phantom
            emit_kv PHANTOM_COUNT "$PHANTOM_COUNT"
            emit_kv PHANTOM_PATHS_FILE "$PHANTOM_PATHS_FILE"
            exit 0
        fi
        emit_status tracked-only
        ;;
    unknown)
        emit_status unknown "${REASON:-unknown}"
        ;;
    *)
        emit_status unknown "unparseable-check-output"
        ;;
esac
