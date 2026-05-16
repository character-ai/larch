#!/usr/bin/env bash
# scrub-submodule-paths.sh - Drop accepted findings that target submodules.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init

usage() {
    larch_err "Usage: scrub-submodule-paths.sh --input FILE --output FILE --log FILE"
}

INPUT=""
OUTPUT=""
LOG_FILE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --input) INPUT="${2:?--input requires a value}"; shift 2 ;;
        --output) OUTPUT="${2:?--output requires a value}"; shift 2 ;;
        --log) LOG_FILE="${2:?--log requires a value}"; shift 2 ;;
        --help) usage; exit 0 ;;
        *) larch_err "scrub-submodule-paths.sh: unknown option: $1"; usage; exit 2 ;;
    esac
done

[[ -n "$INPUT" && -f "$INPUT" && ! -L "$INPUT" ]] || {
    emit_kv SCRUB_OK false
    larch_err "scrub-submodule-paths.sh: --input must name a regular file"
    exit 2
}
[[ -n "$OUTPUT" ]] || { larch_err "scrub-submodule-paths.sh: --output is required"; exit 2; }
[[ -n "$LOG_FILE" ]] || { larch_err "scrub-submodule-paths.sh: --log is required"; exit 2; }
mkdir -p "$(dirname "$OUTPUT")" "$(dirname "$LOG_FILE")"

submodules_file=$(mktemp "${TMPDIR:-/tmp}/larch-submodules.XXXXXX")
paths_file=$(mktemp "${TMPDIR:-/tmp}/larch-finding-paths.XXXXXX")
tmp_output="${OUTPUT}.tmp.$$"
tmp_log="${LOG_FILE}.tmp.$$"
cleanup() {
    rm -f "$submodules_file" "$paths_file" "$tmp_output" "$tmp_log"
}
trap cleanup EXIT

if [[ -f .gitmodules ]]; then
    git config -f .gitmodules --get-regexp '^[^.]+\.path$' 2>/dev/null | awk '{print $2}' >> "$submodules_file" || true
    if [[ ! -s "$submodules_file" ]]; then
        sed -n 's/^[[:space:]]*path[[:space:]]*=[[:space:]]*//p' .gitmodules >> "$submodules_file" || true
    fi
fi
git submodule foreach --quiet "echo \$sm_path" 2>/dev/null >> "$submodules_file" || true
awk 'NF && !seen[$0]++ { print }' "$submodules_file" > "${submodules_file}.dedup"
mv "${submodules_file}.dedup" "$submodules_file"

is_under_submodule() {
    local candidate="$1" submodule_path
    [[ -n "$candidate" ]] || return 1
    while IFS= read -r submodule_path || [[ -n "$submodule_path" ]]; do
        [[ -n "$submodule_path" ]] || continue
        case "$candidate" in
            "$submodule_path"|"$submodule_path"/*) return 0 ;;
        esac
    done < "$submodules_file"
    return 1
}

extract_paths() {
    local block_file="$1"
    {
        awk '
            index($0, "- **Location**:") == 1 || index($0, "- **File**:") == 1 {
                sub("^- \\*\\*(Location|File)\\*\\*: ?", "")
                print
            }
        ' "$block_file"
        grep -Eo '([A-Za-z0-9._/-]+\.(sh|py|md|json|ts|tsx|js|jsx|yml|yaml|txt))(:[0-9]+)?' "$block_file" || true
    } | sed \
        -e 's/^[`"'"'"'(<[]*//' \
        -e 's/[`"'"'"'),>\].;:]*$//' \
        -e 's/:[0-9][0-9]*$//' \
        | awk 'NF && $0 !~ /^\// && $0 !~ /\.\./ && !seen[$0]++ { print }'
}

: > "$tmp_output"
: > "$tmp_log"
scrub_count=0
block_file=$(mktemp "${TMPDIR:-/tmp}/larch-finding-block.XXXXXX")
trap 'cleanup; rm -f "$block_file"' EXIT

flush_block() {
    local finding_id="$1" candidate
    [[ -s "$block_file" ]] || return 0
    : > "$paths_file"
    extract_paths "$block_file" > "$paths_file"
    while IFS= read -r candidate || [[ -n "$candidate" ]]; do
        [[ -n "$candidate" ]] || continue
        if is_under_submodule "$candidate"; then
            scrub_count=$((scrub_count + 1))
            printf '%s | %s | reason=under-submodule\n' "${finding_id:-UNKNOWN}" "$candidate" >> "$tmp_log"
            : > "$block_file"
            return 0
        fi
    done < "$paths_file"
    cat "$block_file" >> "$tmp_output"
    : > "$block_file"
}

current_id=""
while IFS= read -r line || [[ -n "$line" ]]; do
    if [[ "$line" =~ ^###[[:space:]](FINDING_[0-9]+): ]]; then
        flush_block "$current_id"
        current_id="${BASH_REMATCH[1]}"
    fi
    printf '%s\n' "$line" >> "$block_file"
done < "$INPUT"
flush_block "$current_id"

mv -f "$tmp_output" "$OUTPUT"
mv -f "$tmp_log" "$LOG_FILE"

emit_kv SCRUB_COUNT "$scrub_count"
emit_kv SCRUB_OK true
