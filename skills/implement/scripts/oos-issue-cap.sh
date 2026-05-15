#!/usr/bin/env bash
# shellcheck shell=bash disable=SC1091,SC2016,SC2034,SC2154
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
PARSER="$REPO_ROOT/skills/issue/scripts/parse-input.sh"
REGEX_LIB="$REPO_ROOT/scripts/file-line-regex-lib.sh"
EXCERPT_HELPER="$SCRIPT_DIR/oos-issue-cap-excerpt.py"
WARNING_STRING='**⚠ /implement: oos-issue-cap helper failed (exit <N>) — OOS batch NOT filed; review accepted-OOS Descriptions and re-run with corrected env, or have the items filed manually**'

INPUT_FILE=""
OUTPUT_FILE=""
OUTPUT_PROVIDED=0
ISSUES_CAP="${OOS_ISSUES_PER_RUN_CAP-5}"
EXCERPT_MAX="${OOS_ISSUE_CAP_EXCERPT_MAX-200}"

if ! [[ "$ISSUES_CAP" =~ ^[0-9]+$ ]] || (( ISSUES_CAP <= 0 )); then
    larch_err "ERROR: OOS_ISSUES_PER_RUN_CAP must be a positive integer (got: '$ISSUES_CAP')"
    exit 2
fi
if ! [[ "$EXCERPT_MAX" =~ ^[0-9]+$ ]] || (( EXCERPT_MAX <= 0 )); then
    larch_err "ERROR: OOS_ISSUE_CAP_EXCERPT_MAX must be a positive integer (got: '$EXCERPT_MAX')"
    exit 2
fi

usage() {
    larch_err "Usage: oos-issue-cap.sh --input-file FILE [--output FILE]"
    larch_err "  When --output is omitted, the helper rewrites --input-file in place"
    larch_err "  (via a same-directory tmp + mv for atomicity)."
    larch_err "  Input must be OOS-shaped: every item must begin with '### OOS_<digits>:'."
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --input-file) INPUT_FILE="${2:?--input-file requires a value}"; shift 2 ;;
        --output) OUTPUT_FILE="${2:?--output requires a value}"; OUTPUT_PROVIDED=1; shift 2 ;;
        *) larch_err "Unknown option: $1"; usage; exit 1 ;;
    esac
done

if [[ -z "$INPUT_FILE" ]]; then
    usage
    exit 1
fi
if [[ -z "$OUTPUT_FILE" ]]; then
    OUTPUT_FILE="$INPUT_FILE"
elif [[ "$OUTPUT_PROVIDED" == 1 ]]; then
    INPUT_REAL="$(cd "$(dirname "$INPUT_FILE")" 2>/dev/null && printf '%s/%s' "$(pwd -P)" "$(basename "$INPUT_FILE")" || printf '%s' "$INPUT_FILE")"
    OUTPUT_REAL="$(cd "$(dirname "$OUTPUT_FILE")" 2>/dev/null && printf '%s/%s' "$(pwd -P)" "$(basename "$OUTPUT_FILE")" || printf '%s' "$OUTPUT_FILE")"
    if [[ "$INPUT_REAL" == "$OUTPUT_REAL" ]]; then
        larch_err "ERROR: --input-file and --output resolve to the same path: $INPUT_REAL"
        larch_err "       Omit --output to rewrite the input file in place (atomic via tmp+mv)."
        exit 1
    fi
fi

WORK_DIR=""
OUTPUT_TMP="$OUTPUT_FILE.tmp"
SUCCESS=0
cleanup_on_exit() {
    local rc=$?
    if [[ -n "$WORK_DIR" ]]; then
        rm -rf "$WORK_DIR" 2>/dev/null || true
    fi
    rm -f "$OUTPUT_TMP" "$OUTPUT_TMP.renumber" 2>/dev/null || true
    if (( SUCCESS == 0 && OUTPUT_PROVIDED == 1 )); then
        rm -f "$OUTPUT_FILE" 2>/dev/null || true
    fi
    exit "$rc"
}
trap cleanup_on_exit EXIT

if [[ ! -f "$INPUT_FILE" ]]; then
    larch_err "ERROR: input file not found: $INPUT_FILE"
    exit 1
fi
if [[ ! -r "$INPUT_FILE" ]]; then
    larch_err "ERROR: input file not readable: $INPUT_FILE"
    exit 1
fi
if [[ ! -f "$PARSER" ]]; then
    larch_err "ERROR: parse-input.sh not found: $PARSER"
    exit 1
fi
if [[ ! -f "$REGEX_LIB" ]]; then
    larch_err "ERROR: file-line-regex-lib.sh not found: $REGEX_LIB"
    exit 1
fi
if [[ ! -f "$EXCERPT_HELPER" ]]; then
    larch_err "ERROR: oos-issue-cap-excerpt.py not found: $EXCERPT_HELPER"
    exit 1
fi

# shellcheck source=../../../scripts/file-line-regex-lib.sh
source "$REGEX_LIB"

TMPDIR_ROOT="${TMPDIR:-/tmp}"
WORK_DIR="$(mktemp -d "$TMPDIR_ROOT/oos-issue-cap.XXXXXX")"

if [[ ! -s "$INPUT_FILE" ]]; then
    cp "$INPUT_FILE" "$OUTPUT_TMP"
    mv "$OUTPUT_TMP" "$OUTPUT_FILE"
    SUCCESS=1
    exit 0
fi

parse_out="$WORK_DIR/parse.out"
parse_dir="$WORK_DIR/parsed"
if ! bash "$PARSER" --input-file "$INPUT_FILE" --output-dir "$parse_dir" > "$parse_out"; then
    larch_err "ERROR: parse-input.sh failed"
    exit 1
fi

items_total="$(awk -F= '$1 == "ITEMS_TOTAL" { print $2 }' "$parse_out" | tail -1)"
if ! [[ "$items_total" =~ ^[0-9]+$ ]]; then
    larch_err "ERROR: parse-input.sh did not emit a numeric ITEMS_TOTAL"
    exit 1
fi

if (( items_total > 0 )); then
    if ! grep -Eq '^### OOS_[0-9]+:' "$INPUT_FILE"; then
        larch_err "ERROR: input is not OOS-shaped (no '### OOS_<N>:' headings); oos-issue-cap.sh accepts only post-combine OOS batches"
        exit 1
    fi
fi

oos_heading_count="$(awk '/^### OOS_[0-9]+:/ { c++ } END { print c+0 }' "$INPUT_FILE")"
if (( items_total != oos_heading_count )); then
    larch_err "ERROR: ITEMS_TOTAL ($items_total) != raw '### OOS_<N>:' heading count ($oos_heading_count); refusing to compact a batch the parser disagrees with"
    exit 1
fi

if (( items_total <= ISSUES_CAP )); then
    cp "$INPUT_FILE" "$OUTPUT_TMP"
    mv "$OUTPUT_TMP" "$OUTPUT_FILE"
    SUCCESS=1
    exit 0
fi

clean_match() {
    local raw="$1"
    printf '%s\n' "$raw" \
        | sed -E 's/^[^A-Za-z.]+//; s/[^A-Za-z0-9_./:-]+$//; s#^\./##'
}

path_is_safe() {
    local path="$1"
    [[ -n "$path" ]] || return 1
    [[ "$path" != /* ]] || return 1
    [[ "$path" != -* ]] || return 1
    [[ "$path" != *".."* ]] || return 1
    [[ "$path" =~ ^[A-Za-z0-9_./:-]+$ ]] || return 1
}

extract_file_refs() {
    local body_file="$1" matches_file="$WORK_DIR/matches.txt" refs_file="$WORK_DIR/refs.txt"
    : > "$refs_file"

    local grep_status=0
    grep -Eoh "$__filelinelib_any_re|$__filelinelib_extensionless_re" "$body_file" > "$matches_file" 2>/dev/null || grep_status=$?
    if (( grep_status > 1 )); then
        larch_err "ERROR: grep failed scanning $body_file (exit $grep_status)"
        return "$grep_status"
    fi

    while IFS= read -r raw; do
        [[ -n "$raw" ]] || continue
        local candidate path
        candidate="$(clean_match "$raw")"
        [[ -n "$candidate" ]] || continue
        path="$candidate"
        if [[ "$candidate" =~ ^(.+):[0-9]+(-[0-9]+)?$ ]]; then
            path="${BASH_REMATCH[1]}"
        fi
        path="${path#./}"
        path_is_safe "$path" || continue
        printf '%s\n' "$candidate" >> "$refs_file"
    done < "$matches_file"

    sort -u "$refs_file" | tr '\n' ' ' | sed -E 's/ +$//'
}

normalize_title() {
    local title="$1"
    printf '%s' "$title" \
        | tr -d '\000-\010\013\014\016-\037\177' \
        | tr '\r\n\t' '   ' \
        | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//; s/^[*_#`]+[[:space:]]*//; s/[*`]+//g; s/[[:space:]]+/ /g'
}

normalize_excerpt() {
    local excerpt="$1"
    printf '%s' "$excerpt" \
        | tr -d '\000-\010\013\014\016-\037\177' \
        | tr '\r\n\t' '   ' \
        | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//; s/^[*_#`]+[[:space:]]*//; s/[[:space:]]+/ /g'
}

keep=$(( ISSUES_CAP - 1 ))
surplus=$(( items_total - keep ))
heading_table="$WORK_DIR/heading-table.tsv"
awk '/^### OOS_[0-9]+:/ { idx++; print idx "\t" NR }' "$INPUT_FILE" > "$heading_table"

: > "$OUTPUT_TMP"
if (( keep > 0 )); then
    keep_plus_one_line="$(awk -F'\t' -v k=$((keep + 1)) '$1 == k { print $2 }' "$heading_table")"
    if [[ -z "$keep_plus_one_line" ]]; then
        larch_err "ERROR: heading table missing entry for item $((keep + 1))"
        exit 1
    fi
    end_of_keep=$(( keep_plus_one_line - 1 ))
    if (( end_of_keep >= 1 )); then
        awk -v end="$end_of_keep" 'NR<=end' "$INPUT_FILE" >> "$OUTPUT_TMP"
    fi
fi

{
    printf '### OOS_%d: Aggregated rollup of %d capped OOS items\n' "$ISSUES_CAP" "$surplus"
    printf -- '- **Description**: Cap %d (OOS_ISSUES_PER_RUN_CAP) exceeded; the following %d items were rolled up by skills/implement/scripts/oos-issue-cap.sh:\n' "$ISSUES_CAP" "$surplus"
    for ((i = keep + 1; i <= items_total; i++)); do
        title="$(awk -F= -v key="ITEM_${i}_TITLE" '$1 == key { print substr($0, length(key) + 2) }' "$parse_out" | tail -1)"
        body_file="$(awk -F= -v key="ITEM_${i}_BODY_FILE" '$1 == key { print substr($0, length(key) + 2) }' "$parse_out" | tail -1)"
        title_clean="$(normalize_title "${title:-(no title)}")"
        [[ -n "$title_clean" ]] || title_clean="(no title)"

        if [[ -n "$body_file" && -f "$body_file" && -s "$body_file" ]]; then
            excerpt="$(python3 "$EXCERPT_HELPER" "$body_file" "$EXCERPT_MAX")"
            excerpt_clean="$(normalize_excerpt "$excerpt")"
            file_refs_clean="$(extract_file_refs "$body_file")"
        else
            excerpt_clean="(malformed item — body unavailable)"
            file_refs_clean=""
        fi

        if [[ -n "$file_refs_clean" ]]; then
            printf -- '  - **%s**: %s [Files: %s]\n' "$title_clean" "$excerpt_clean" "$file_refs_clean"
        else
            printf -- '  - **%s**: %s\n' "$title_clean" "$excerpt_clean"
        fi
    done
    printf -- '- **Reviewer**: Combined: capped per-run rollup\n'
    printf -- '- **Vote tally**: N/A — capped rollup of %d entries\n' "$surplus"
    printf -- '- **Phase**: implement\n\n'
} >> "$OUTPUT_TMP"

awk '
    BEGIN { idx = 0 }
    /^### OOS_[0-9]+:/ {
        idx++
        sub(/^### OOS_[0-9]+:/, "### OOS_" idx ":")
    }
    { print }
' "$OUTPUT_TMP" > "$WORK_DIR/renumber"
mv "$WORK_DIR/renumber" "$OUTPUT_TMP"

mv "$OUTPUT_TMP" "$OUTPUT_FILE"
SUCCESS=1
