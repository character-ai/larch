#!/usr/bin/env bash
# scoreboard.sh — Render a reviewer competition scoreboard.

set -euo pipefail

usage() { echo "Usage: scoreboard.sh --tally-file FILE --reviewer-labels CSV --output-file FILE" >&2; }

TALLY_FILE=""
LABELS=""
OUTPUT_FILE=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --tally-file) TALLY_FILE="${2:?--tally-file requires a value}"; shift 2 ;;
        --reviewer-labels) LABELS="${2:?--reviewer-labels requires a value}"; shift 2 ;;
        --output-file) OUTPUT_FILE="${2:?--output-file requires a value}"; shift 2 ;;
        --help) usage; exit 0 ;;
        *) echo "scoreboard.sh: unknown option: $1" >&2; usage; exit 2 ;;
    esac
done

[[ -n "$OUTPUT_FILE" ]] || { echo "scoreboard.sh: --output-file is required" >&2; exit 2; }
mkdir -p "$(dirname "$OUTPUT_FILE")"

{
    printf '| Reviewer | Score |\n'
    printf '|---|---:|\n'
    old_ifs=$IFS
    IFS=,
    for label in $LABELS; do
        label=$(printf '%s' "$label" | sed 's/^ *//; s/ *$//')
        [[ -n "$label" ]] || continue
        score=0
        if [[ -n "$TALLY_FILE" && -f "$TALLY_FILE" ]]; then
            score=$(awk -v label="$label" '$0 ~ "REVIEWER=" label " " && $0 ~ /ACCEPTED=true/ { n++ } END { print n + 0 }' "$TALLY_FILE")
        fi
        printf '| %s | %s |\n' "$label" "$score"
    done
    IFS=$old_ifs
} > "$OUTPUT_FILE"

printf 'SCOREBOARD_FILE=%q\n' "$OUTPUT_FILE"
