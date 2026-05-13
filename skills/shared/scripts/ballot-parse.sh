#!/usr/bin/env bash
# ballot-parse.sh — Parse review ballot finding blocks.

set -euo pipefail

usage() { echo "Usage: ballot-parse.sh --ballot-file FILE" >&2; }

BALLOT_FILE=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --ballot-file) BALLOT_FILE="${2:?--ballot-file requires a value}"; shift 2 ;;
        --help) usage; exit 0 ;;
        *) echo "ballot-parse.sh: unknown option: $1" >&2; usage; exit 2 ;;
    esac
done

[[ -n "$BALLOT_FILE" && -f "$BALLOT_FILE" ]] || { echo "ballot-parse.sh: --ballot-file must name a file" >&2; exit 2; }

awk '
function emit() {
    if (idx > 0) {
        gsub(/^[[:space:]]+|[[:space:]]+$/, "", concern)
        printf("FINDING_%d_TITLE=%s\n", idx, title)
        printf("FINDING_%d_CONCERN=%s\n", idx, concern)
        printf("FINDING_%d_OOS=%s\n", idx, oos)
    }
}
/^### FINDING_[0-9]+:/ {
    emit()
    idx++
    title=$0
    sub(/^### FINDING_[0-9]+:[[:space:]]*/, "", title)
    concern=""
    oos="false"
    if (title ~ /^\[OUT_OF_SCOPE\]/ || title ~ /^\[OOS\]/) oos="true"
    next
}
idx > 0 {
    if ($0 ~ /^- \*\*Concern\*\*:/) {
        line=$0
        sub(/^- \*\*Concern\*\*:[[:space:]]*/, "", line)
        concern=line
    } else if (concern != "" && $0 !~ /^- \*\*/) {
        concern=concern " " $0
    }
    if ($0 ~ /\[OUT_OF_SCOPE\]/ || $0 ~ /\[OOS\]/) oos="true"
}
END {
    emit()
    printf("FINDING_COUNT=%d\n", idx + 0)
}
' "$BALLOT_FILE"
