#!/usr/bin/env bash
# gather-context.sh — Gather /review diff or description context.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init

usage() {
    larch_err "Usage: gather-context.sh --mode diff|description --output-dir DIR [--description-text TEXT --scope-files FILE]"
}

MODE=""
OUTPUT_DIR=""
DESCRIPTION_TEXT=""
SCOPE_FILES=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --mode) MODE="${2:?--mode requires a value}"; shift 2 ;;
        --output-dir) OUTPUT_DIR="${2:?--output-dir requires a value}"; shift 2 ;;
        --description-text) DESCRIPTION_TEXT="${2:?--description-text requires a value}"; shift 2 ;;
        --scope-files) SCOPE_FILES="${2:?--scope-files requires a value}"; shift 2 ;;
        --help) usage; exit 0 ;;
        *) larch_err "gather-context.sh: unknown option: $1"; usage; exit 2 ;;
    esac
done

[[ "$MODE" == "diff" || "$MODE" == "description" ]] || { larch_err "gather-context.sh: --mode must be diff or description"; exit 2; }
[[ -n "$OUTPUT_DIR" ]] || { larch_err "gather-context.sh: --output-dir is required"; exit 2; }
mkdir -p "$OUTPUT_DIR"

validate_rel_file() {
    local p="$1"
    [[ -n "$p" && "$p" != /* && "$p" != *..* && "$p" != *[$'\n\r\t']* ]] || return 1
    [[ -f "$p" && ! -L "$p" ]] || return 1
}

if [[ "$MODE" == "diff" ]]; then
    branch_context_env="$OUTPUT_DIR/gather-branch-context.env"
    "$PLUGIN_ROOT/scripts/gather-branch-context.sh" --output-dir "$OUTPUT_DIR" > "$branch_context_env"
    while IFS= read -r line || [[ -n "$line" ]]; do
        emit "$line"
    done < "$branch_context_env"
    emit_kv SCOPE_FILES_COUNT 0
    emit_kv MODE diff
    exit 0
fi

FILE_LIST_FILE="${SCOPE_FILES:-$OUTPUT_DIR/scope-files.txt}"
: > "$FILE_LIST_FILE"

query=$(printf '%s' "$DESCRIPTION_TEXT" | tr -cs '[:alnum:]_./-' '\n' | awk 'length($0) >= 3 { print tolower($0) }' | head -20)
if [[ -n "$query" ]]; then
    while IFS= read -r path; do
        [[ -n "$path" ]] || continue
        lower=$(printf '%s' "$path" | tr '[:upper:]' '[:lower:]')
        matched=false
        while IFS= read -r token; do
            [[ -n "$token" ]] || continue
            case "$lower" in *"$token"*) matched=true ;; esac
        done <<< "$query"
        if [[ "$matched" == "true" ]] && validate_rel_file "$path"; then
            printf '%s\n' "$path"
        fi
    done < <(git ls-files) | sort -u > "$FILE_LIST_FILE"
fi

if [[ ! -s "$FILE_LIST_FILE" && -n "$DESCRIPTION_TEXT" ]]; then
    rg -l --fixed-strings --ignore-case -- "$DESCRIPTION_TEXT" . 2>/dev/null \
        | sed 's#^\./##' \
        | while IFS= read -r p; do validate_rel_file "$p" && printf '%s\n' "$p"; done \
        | sort -u > "$FILE_LIST_FILE" || true
fi

count=$(wc -l < "$FILE_LIST_FILE" | tr -d ' ')
emit_kv DIFF_FILE ""
emit_kv FILE_LIST_FILE "$FILE_LIST_FILE"
emit_kv COMMIT_LOG_FILE ""
emit_kv COMMIT_COUNT 0
emit_kv SCOPE_FILES_COUNT "$count"
emit_kv MODE description
