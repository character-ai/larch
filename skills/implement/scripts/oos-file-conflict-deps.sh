#!/usr/bin/env bash
# shellcheck shell=bash disable=SC1091,SC2154
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
PARSER="$REPO_ROOT/skills/issue/scripts/parse-input.sh"
REGEX_LIB="$REPO_ROOT/scripts/file-line-regex-lib.sh"

INPUT_FILE=""
OUTPUT_FILE=""
CLUSTER_CAP="${OOS_FILE_CONFLICT_CLUSTER_CAP:-200}"
GLOBAL_CAP="${OOS_FILE_CONFLICT_GLOBAL_CAP:-500}"

if ! [[ "$CLUSTER_CAP" =~ ^[0-9]+$ ]] || (( CLUSTER_CAP <= 0 )); then
    echo "ERROR: OOS_FILE_CONFLICT_CLUSTER_CAP must be a positive integer (got: '$CLUSTER_CAP')" >&2
    exit 2
fi
if ! [[ "$GLOBAL_CAP" =~ ^[0-9]+$ ]] || (( GLOBAL_CAP <= 0 )); then
    echo "ERROR: OOS_FILE_CONFLICT_GLOBAL_CAP must be a positive integer (got: '$GLOBAL_CAP')" >&2
    exit 2
fi

usage() {
    echo "Usage: oos-file-conflict-deps.sh --input-file FILE [--output FILE]" >&2
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --input-file) INPUT_FILE="${2:?--input-file requires a value}"; shift 2 ;;
        --output) OUTPUT_FILE="${2:?--output requires a value}"; shift 2 ;;
        *) echo "Unknown option: $1" >&2; usage; exit 1 ;;
    esac
done

if [[ -z "$INPUT_FILE" || -z "$OUTPUT_FILE" ]]; then
    if [[ -n "$INPUT_FILE" && -z "$OUTPUT_FILE" && -n "${IMPLEMENT_TMPDIR:-}" ]]; then
        OUTPUT_FILE="$IMPLEMENT_TMPDIR/oos-intra-batch-deps.tsv"
    fi
fi
if [[ -z "$INPUT_FILE" || -z "$OUTPUT_FILE" ]]; then
    usage
    exit 1
fi
if [[ ! -f "$INPUT_FILE" ]]; then
    echo "ERROR: input file not found: $INPUT_FILE" >&2
    exit 1
fi
if [[ ! -x "$PARSER" && ! -f "$PARSER" ]]; then
    echo "ERROR: parse-input.sh not found: $PARSER" >&2
    exit 1
fi
if [[ ! -f "$REGEX_LIB" ]]; then
    echo "ERROR: file-line-regex-lib.sh not found: $REGEX_LIB" >&2
    exit 1
fi

# shellcheck source=../../../scripts/file-line-regex-lib.sh
source "$REGEX_LIB"

TMPDIR_ROOT="${TMPDIR:-/tmp}"
WORK_DIR="$(mktemp -d "$TMPDIR_ROOT/oos-file-conflict-deps.XXXXXX")"
OUTPUT_TMP="$OUTPUT_FILE.tmp"
trap 'rm -rf "$WORK_DIR"; rm -f "$OUTPUT_TMP"' EXIT

parse_out="$WORK_DIR/parse.out"
parse_dir="$WORK_DIR/parsed"
if ! bash "$PARSER" --input-file "$INPUT_FILE" --output-dir "$parse_dir" > "$parse_out"; then
    echo "ERROR: parse-input.sh failed for OOS batch" >&2
    exit 1
fi

items_total="$(awk -F= '$1 == "ITEMS_TOTAL" { print $2 }' "$parse_out" | tail -1)"
if ! [[ "$items_total" =~ ^[0-9]+$ ]]; then
    echo "ERROR: parse-input.sh did not emit a numeric ITEMS_TOTAL" >&2
    exit 1
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
    [[ "$path" != *":"* ]] || return 1
    [[ "$path" =~ ^[A-Za-z0-9_./-]+$ ]] || return 1
}

write_record() {
    local records_file="$1" candidate="$2"
    local path="$candidate"
    local start="" end="" whole="1"

    if [[ "$candidate" =~ ^(.+):([0-9]+)(-([0-9]+))?$ ]]; then
        path="${BASH_REMATCH[1]}"
        start="${BASH_REMATCH[2]}"
        end="${BASH_REMATCH[4]:-$start}"
        if (( start > 0 && end > 0 && start <= end )); then
            whole="0"
        else
            start=""
            end=""
            whole="1"
        fi
    fi

    path="${path#./}"
    path_is_safe "$path" || return 0
    printf '%s\t%s\t%s\t%s\n' "$path" "$start" "$end" "$whole" >> "$records_file"
}

extract_records() {
    local body_file="$1" records_file="$2"
    : > "$records_file"

    local normalized_body="$WORK_DIR/body-normalized.txt"
    # Strip leading `./`, then replace common adjacency separators (comma, semicolon)
    # with newlines so grep -Eoh's consumed left/right boundaries do not swallow the
    # neighbor's anchor, which would silently drop the second path in `a.sh,b.sh`.
    sed -E -e 's#(^|[^A-Za-z0-9])\./#\1#g' -e 's#[,;]#\
#g' "$body_file" > "$normalized_body"

    grep -Eoh "$__filelinelib_any_re|$__filelinelib_extensionless_re" "$normalized_body" 2>/dev/null \
        | while IFS= read -r raw; do
            candidate="$(clean_match "$raw")"
            [[ -n "$candidate" ]] || continue
            write_record "$records_file" "$candidate"
        done || true

    sort -u "$records_file" -o "$records_file"
}

for ((i = 1; i <= items_total; i++)); do
    records_file="$WORK_DIR/item-$i.records"
    : > "$records_file"
    if grep -q "^ITEM_${i}_MALFORMED=true$" "$parse_out"; then
        continue
    fi
    body_file="$(awk -F= -v key="ITEM_${i}_BODY_FILE" '$1 == key { print substr($0, length(key) + 2) }' "$parse_out" | tail -1)"
    if [[ -n "$body_file" && -f "$body_file" ]]; then
        extract_records "$body_file" "$records_file"
    fi
done

has_whole_file() {
    local records_file="$1" path="$2"
    awk -F'\t' -v p="$path" '$1 == p && $4 == "1" { found=1 } END { exit found ? 0 : 1 }' "$records_file"
}

ranges_overlap() {
    local a_start="$1" a_end="$2" b_start="$3" b_end="$4"
    (( a_start > b_end || b_start > a_end )) && return 1
    return 0
}

path_conflicts() {
    local i="$1" j="$2" path="$3"
    local left="$WORK_DIR/item-$i.records"
    local right="$WORK_DIR/item-$j.records"

    if has_whole_file "$left" "$path" || has_whole_file "$right" "$path"; then
        return 0
    fi

    while IFS=$'\t' read -r _ l_start l_end l_whole; do
        [[ "$l_whole" == "0" ]] || continue
        while IFS=$'\t' read -r _ r_start r_end r_whole; do
            [[ "$r_whole" == "0" ]] || continue
            if ranges_overlap "$l_start" "$l_end" "$r_start" "$r_end"; then
                return 0
            fi
        done < <(awk -F'\t' -v p="$path" '$1 == p { print }' "$right")
    done < <(awk -F'\t' -v p="$path" '$1 == p { print }' "$left")

    return 1
}

parent_file="$WORK_DIR/parents"
: > "$parent_file"
for ((i = 1; i <= items_total; i++)); do
    printf '%s\t%s\n' "$i" "$i" >> "$parent_file"
done

find_parent() {
    local node="$1" parent
    parent="$(awk -F'\t' -v n="$node" '$1 == n { print $2 }' "$parent_file")"
    while [[ "$parent" != "$node" ]]; do
        node="$parent"
        parent="$(awk -F'\t' -v n="$node" '$1 == n { print $2 }' "$parent_file")"
    done
    printf '%s\n' "$parent"
}

set_parent() {
    local node="$1" parent="$2"
    awk -F'\t' -v n="$node" -v p="$parent" 'BEGIN { OFS="\t" } $1 == n { $2=p } { print }' "$parent_file" > "$parent_file.tmp"
    mv "$parent_file.tmp" "$parent_file"
}

union_nodes() {
    local left="$1" right="$2" lroot rroot keep drop
    lroot="$(find_parent "$left")"
    rroot="$(find_parent "$right")"
    [[ "$lroot" == "$rroot" ]] && return
    if (( lroot < rroot )); then
        keep="$lroot"
        drop="$rroot"
    else
        keep="$rroot"
        drop="$lroot"
    fi
    for ((n = 1; n <= items_total; n++)); do
        if [[ "$(find_parent "$n")" == "$drop" ]]; then
            set_parent "$n" "$keep"
        fi
    done
}

candidate_edges="$WORK_DIR/candidate-edges.tsv"
: > "$candidate_edges"

for ((i = 1; i <= items_total; i++)); do
    for ((j = i + 1; j <= items_total; j++)); do
        left_paths="$WORK_DIR/item-$i.paths"
        right_paths="$WORK_DIR/item-$j.paths"
        shared_paths="$WORK_DIR/shared-$i-$j.paths"
        cut -f1 "$WORK_DIR/item-$i.records" | sort -u > "$left_paths"
        cut -f1 "$WORK_DIR/item-$j.records" | sort -u > "$right_paths"
        comm -12 "$left_paths" "$right_paths" > "$shared_paths"
        while IFS= read -r path; do
            [[ -n "$path" ]] || continue
            if path_conflicts "$i" "$j" "$path"; then
                printf '%s\t%s\t%s\n' "$i" "$j" "$(basename "$path")" >> "$candidate_edges"
                union_nodes "$i" "$j"
                break
            fi
        done < "$shared_paths"
    done
done

component_nodes="$WORK_DIR/component-nodes.tsv"
: > "$component_nodes"
for ((i = 1; i <= items_total; i++)); do
    root="$(find_parent "$i")"
    printf '%s\t%s\n' "$root" "$i" >> "$component_nodes"
done

planned_edges="$WORK_DIR/planned-edges.tsv"
: > "$planned_edges"

cut -f1 "$component_nodes" | sort -n -u | while IFS= read -r root; do
    [[ -n "$root" ]] || continue
    nodes_file="$WORK_DIR/nodes-$root"
    awk -F'\t' -v r="$root" '$1 == r { print $2 }' "$component_nodes" | sort -n > "$nodes_file"
    node_count="$(wc -l < "$nodes_file" | tr -d ' ')"
    (( node_count >= 2 )) || continue
    cluster_edges="$(awk -F'\t' -v r="$root" '
        NR == FNR { root_by_node[$2]=$1; next }
        root_by_node[$1] == r && root_by_node[$2] == r { count++ }
        END { print count + 0 }
    ' "$component_nodes" "$candidate_edges")"
    if (( cluster_edges > CLUSTER_CAP )); then
        basename_hint="$(awk -F'\t' -v r="$root" '
            NR == FNR { root_by_node[$2]=$1; next }
            root_by_node[$1] == r && root_by_node[$2] == r { print $3; exit }
        ' "$component_nodes" "$candidate_edges")"
        echo "**⚠ /implement: oos-file-conflict-deps cluster size $node_count on ${basename_hint:-unknown} exceeded $CLUSTER_CAP all-pairs rows; emitting chain (lower robustness under SCC pruning).**" >&2
        previous=""
        while IFS= read -r node; do
            if [[ -n "$previous" ]]; then
                printf '%s\t%s\n' "$previous" "$node" >> "$planned_edges"
            fi
            previous="$node"
        done < "$nodes_file"
    else
        awk -F'\t' -v r="$root" '
            NR == FNR { root_by_node[$2]=$1; next }
            root_by_node[$1] == r && root_by_node[$2] == r { print $1 "\t" $2 }
        ' "$component_nodes" "$candidate_edges" >> "$planned_edges"
    fi
done

sort -n -k1,1 -k2,2 "$planned_edges" -o "$planned_edges"
row_count="$(wc -l < "$planned_edges" | tr -d ' ')"
if (( row_count > GLOBAL_CAP )); then
    rm -f "$OUTPUT_TMP" "$OUTPUT_FILE"
    echo "ERROR: oos-file-conflict-deps would emit $row_count rows, exceeding the $GLOBAL_CAP-row --intra-batch-deps-file cap; split the OOS batch" >&2
    exit 1
fi

cp "$planned_edges" "$OUTPUT_TMP"
mv "$OUTPUT_TMP" "$OUTPUT_FILE"
trap 'rm -rf "$WORK_DIR"' EXIT
