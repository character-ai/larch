#!/usr/bin/env bash
# compose-architecture-sketch.sh — emit a minimal Mermaid architecture sketch.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init

usage() {
    while IFS= read -r line; do larch_err "$line"; done <<'USAGE'
Usage:
  compose-architecture-sketch.sh [--output PATH]
USAGE
}

fail() {
    larch_err "ERROR=$1"
    exit 2
}

OUTPUT=""

while [ $# -gt 0 ]; do
    case "$1" in
        --output)
            OUTPUT="${2:?--output requires a value}"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            usage
            fail "unknown option: $1"
            ;;
    esac
done

# Enumerate changed files against merge-base.
merge_base=$(git merge-base HEAD origin/main 2>/dev/null) || fail "git merge-base failed"
[ -n "$merge_base" ] || fail "could not determine merge-base"

changed_files=$(git diff --name-only "$merge_base..HEAD" 2>/dev/null) || fail "git diff failed"
file_count=$(printf '%s\n' "$changed_files" | grep -c '.' || true)
[ "${file_count:-0}" -gt 0 ] || fail "no changed files relative to origin/main"

# Build the Mermaid sketch.
if [ "$file_count" -eq 1 ]; then
    only_file=$(printf '%s\n' "$changed_files" | head -1)
    basename="${only_file##*/}"
    sketch=$(printf 'flowchart LR\n  A["Edit %s"]' "$basename")
else
    # Group by top-level directory; cap at 3 groups.
    dirs=$(printf '%s\n' "$changed_files" | awk -F/ 'NF>1{print $1} NF==1{print "."}' | sort -u | head -3)
    dir_count=$(printf '%s\n' "$dirs" | grep -c '.' || true)

    if [ "${dir_count:-0}" -eq 1 ]; then
        dir=$(printf '%s\n' "$dirs" | head -1)
        sketch=$(printf 'flowchart LR\n  A["%s/"] --> B["%s files modified"]' "$dir" "$file_count")
    else
        nodes=""
        i=0
        while IFS= read -r dir; do
            [ -n "$dir" ] || continue
            i=$((i + 1))
            nodes="${nodes}  N${i}[\"${dir}/\"]\n"
        done <<< "$dirs"
        sketch=$(printf 'flowchart LR\n%b' "$nodes")
    fi
fi

emit_sketch() {
    local fence='```'
    printf '## Architecture Sketch\n\n%smermaid\n%s\n%s\n' "$fence" "$sketch" "$fence"
}

if [ -n "$OUTPUT" ]; then
    emit_sketch > "$OUTPUT"
else
    emit "$(emit_sketch)"
fi
