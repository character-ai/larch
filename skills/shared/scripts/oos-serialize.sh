#!/usr/bin/env bash
# oos-serialize.sh — Serialize accepted out-of-scope review observations.

set -euo pipefail

usage() { echo "Usage: oos-serialize.sh --findings-file FILE --output-file FILE [--session-env-path FILE]" >&2; }

FINDINGS_FILE=""
OUTPUT_FILE=""
SESSION_ENV_PATH=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --findings-file) FINDINGS_FILE="${2:?--findings-file requires a value}"; shift 2 ;;
        --output-file) OUTPUT_FILE="${2:?--output-file requires a value}"; shift 2 ;;
        --session-env-path) SESSION_ENV_PATH="${2:?--session-env-path requires a value}"; shift 2 ;;
        --help) usage; exit 0 ;;
        *) echo "oos-serialize.sh: unknown option: $1" >&2; usage; exit 2 ;;
    esac
done

[[ -n "$FINDINGS_FILE" && -f "$FINDINGS_FILE" ]] || { echo "oos-serialize.sh: --findings-file must name a file" >&2; exit 2; }
[[ -n "$OUTPUT_FILE" ]] || { echo "oos-serialize.sh: --output-file is required" >&2; exit 2; }
mkdir -p "$(dirname "$OUTPUT_FILE")"

awk '
# is_security_tagged: returns 1 when at least one UNFENCED occurrence of the
# canonical token (case-insensitive, optional whitespace around =) exists.
# Fenced = inside inline backtick or triple-backtick region. Per SECURITY.md.
function is_security_tagged(line,    lower, i, fenced, c, result) {
    lower = tolower(line)
    # Check triple-backtick fencing on this line.
    fenced = (line ~ /^[ \t]*```/)
    if (fenced) return 0
    # Scan for the token; skip occurrences inside inline backtick spans.
    result = 0
    i = 1
    in_backtick = 0
    while (i <= length(lower)) {
        c = substr(lower, i, 1)
        if (c == "`") { in_backtick = !in_backtick; i++; continue }
        if (!in_backtick && substr(lower, i) ~ /^focus-area[ \t]*=[ \t]*security/) {
            result = 1
            break
        }
        i++
    }
    return result
}
BEGIN { in_block=0; block=""; security=0; oos=0; in_fence=0 }
function flush() {
    if (!in_block) return
    if (oos && security) held++
    else if (oos) { print block; accepted++ }
}
/^### FINDING_[0-9]+:/ {
    flush()
    in_block=1
    in_fence=0
    block=$0 "\n"
    security=is_security_tagged($0)
    oos=($0 ~ /\[OUT_OF_SCOPE\]/ || $0 ~ /\[OOS\]/)
    next
}
in_block {
    block=block $0 "\n"
    # Track triple-backtick fence regions.
    if ($0 ~ /^[ \t]*```/) in_fence = !in_fence
    if (!in_fence && is_security_tagged($0)) security=1
    if ($0 ~ /\[OUT_OF_SCOPE\]/ || $0 ~ /\[OOS\]/) oos=1
}
END { flush(); printf("OOS_ACCEPTED=%d\nOOS_HELD_SECURITY=%d\n", accepted + 0, held + 0) > "/dev/stderr" }
' "$FINDINGS_FILE" > "$OUTPUT_FILE" 2> "$OUTPUT_FILE.env"

cat "$OUTPUT_FILE.env"
rm -f "$OUTPUT_FILE.env"
: "$SESSION_ENV_PATH"
