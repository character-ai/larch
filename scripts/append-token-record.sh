#!/usr/bin/env bash
# append-token-record.sh — Normalize CI launcher token sidecars.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init

INPUT=""
TMPDIR_ARG=""

usage() {
    larch_err "Usage: append-token-record.sh --input PATH --tmpdir PATH"
}

die() {
    larch_err "append-token-record.sh: $1"
    usage
    exit 2
}

while [ $# -gt 0 ]; do
    case "$1" in
        --input) [ $# -ge 2 ] || die "--input requires a value"; INPUT=$2; shift 2 ;;
        --tmpdir) [ $# -ge 2 ] || die "--tmpdir requires a value"; TMPDIR_ARG=$2; shift 2 ;;
        --help) usage; exit 0 ;;
        *) die "unknown flag: $1" ;;
    esac
done

[ -n "$TMPDIR_ARG" ] || die "--tmpdir is required"
[ -d "$TMPDIR_ARG" ] || die "--tmpdir must exist"

if [ -z "$INPUT" ]; then
    exit 0
fi

if [ ! -s "$INPUT" ]; then
    if [ ! -e "$TMPDIR_ARG/execution-issues.md" ]; then
        larch_err "append-token-record.sh: token sidecar absent: $INPUT"
    fi
    exit 0
fi

kv() {
    awk -F= -v k="$1" '$1 == k {print substr($0, index($0, "=") + 1); found=1} END {if (!found) print ""}' "$INPUT" | tail -n 1
}

TOOL=$(kv TOOL)
TOTAL=$(kv TOTAL)
RAW=$(kv RAW)
INPUT_TOKENS=$(kv INPUT)
OUTPUT_TOKENS=$(kv OUTPUT)
CACHE_READ=$(kv CACHE_READ)
CACHE_CREATE=$(kv CACHE_CREATE)

case "$TOOL" in codex|cursor) ;; *) TOOL=unknown ;; esac
case "$TOTAL" in ''|*[!0-9]*) TOTAL=0 ;; esac
case "$INPUT_TOKENS" in ''|*[!0-9]*) INPUT_TOKENS=0 ;; esac
case "$OUTPUT_TOKENS" in ''|*[!0-9]*) OUTPUT_TOKENS=0 ;; esac
case "$CACHE_READ" in ''|*[!0-9]*) CACHE_READ=0 ;; esac
case "$CACHE_CREATE" in ''|*[!0-9]*) CACHE_CREATE=0 ;; esac
[ -n "$RAW" ] || RAW="${TOOL}_ci_fix"

OUT="$TMPDIR_ARG/token-report.ndjson"
if command -v jq >/dev/null 2>&1; then
    jq -cn \
        --arg tool "$TOOL" \
        --arg raw "$RAW" \
        --argjson input "$INPUT_TOKENS" \
        --argjson output "$OUTPUT_TOKENS" \
        --argjson cache_read "$CACHE_READ" \
        --argjson cache_create "$CACHE_CREATE" \
        --argjson total "$TOTAL" \
        '{tool:$tool, raw:$raw, input:$input, output:$output, cache_read:$cache_read, cache_create:$cache_create, total:$total}' >> "$OUT"
else
    printf '{"tool":"%s","raw":"%s","input":%s,"output":%s,"cache_read":%s,"cache_create":%s,"total":%s}\n' \
        "$TOOL" "$RAW" "$INPUT_TOKENS" "$OUTPUT_TOKENS" "$CACHE_READ" "$CACHE_CREATE" "$TOTAL" >> "$OUT"
fi
