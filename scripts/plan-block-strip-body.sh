#!/usr/bin/env bash
# plan-block-strip-body.sh — remove an embedded larch:plan block from body text.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init

MARK_START='^[[:space:]]*<!--[[:space:]]+larch:plan:start[[:space:]]+-->[[:space:]]*$'
MARK_END='^[[:space:]]*<!--[[:space:]]+larch:plan:end[[:space:]]+-->[[:space:]]*$'

usage() {
    while IFS= read -r line; do larch_err "$line"; done <<'USAGE'
Usage: plan-block-strip-body.sh [--file <path>] [--output <path>]
USAGE
}

IN_PATH=""
OUT_PATH=""
while [ $# -gt 0 ]; do
    case "$1" in
        --file) IN_PATH="${2:?}"; shift 2 ;;
        --output) OUT_PATH="${2:?}"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) larch_err "plan-block-strip-body.sh: unknown option: $1"; usage; exit 1 ;;
    esac
done

BODY_TMP=$(mktemp "${TMPDIR:-/tmp}/plan-block-strip-body.XXXXXX")
OUT_TMP=""
cleanup() {
    rm -f "$BODY_TMP"
    if [ -n "$OUT_TMP" ]; then rm -f "$OUT_TMP"; fi
}
trap cleanup EXIT

if [ -n "$IN_PATH" ]; then
    cat "$IN_PATH" > "$BODY_TMP"
else
    cat > "$BODY_TMP"
fi

start_count=$(grep -c -E "$MARK_START" "$BODY_TMP" 2>/dev/null) || start_count=0
end_count=$(grep -c -E "$MARK_END" "$BODY_TMP" 2>/dev/null) || end_count=0

emit_malformed() {
    if [ -n "$OUT_PATH" ]; then : > "$OUT_PATH"; fi
    emit_kv MALFORMED "$1"
    exit 1
}

if [ "$start_count" -eq 0 ] && [ "$end_count" -eq 0 ]; then
    if [ -n "$OUT_PATH" ]; then
        cp "$BODY_TMP" "$OUT_PATH"
    else
        cat "$BODY_TMP"
    fi
    exit 0
fi

if [ "$start_count" -gt 1 ]; then emit_malformed "multiple-start"; fi
if [ "$end_count" -gt 1 ]; then emit_malformed "multiple-end"; fi
if [ "$start_count" -eq 1 ] && [ "$end_count" -eq 0 ]; then emit_malformed "start-without-end"; fi
if [ "$start_count" -eq 0 ] && [ "$end_count" -eq 1 ]; then emit_malformed "end-without-start"; fi

start_line=$(grep -n -E "$MARK_START" "$BODY_TMP" | head -1 | cut -d: -f1)
end_line=$(grep -n -E "$MARK_END" "$BODY_TMP" | head -1 | cut -d: -f1)
if [ "$end_line" -lt "$start_line" ]; then emit_malformed "end-before-start"; fi

if [ -n "$OUT_PATH" ]; then
    OUT_TMP=$(mktemp "${TMPDIR:-/tmp}/plan-block-strip-out.XXXXXX")
    awk -v s="$start_line" -v e="$end_line" 'NR < s || NR > e' "$BODY_TMP" > "$OUT_TMP"
    mv -f "$OUT_TMP" "$OUT_PATH"
    OUT_TMP=""
else
    awk -v s="$start_line" -v e="$end_line" 'NR < s || NR > e' "$BODY_TMP"
fi
