#!/usr/bin/env bash
# tally-votes.sh — Orchestrate /review voting and accepted finding output.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
SHARED_DIR="$SCRIPT_DIR/../../shared/scripts"

usage() { echo "Usage: tally-votes.sh --findings-file FILE --review-tmpdir DIR --cursor-available true|false --codex-available true|false --both-down true|false [--output-tally FILE --output-accepted FILE]" >&2; }

FINDINGS_FILE=""
REVIEW_TMPDIR=""
CURSOR_AVAILABLE=""
CODEX_AVAILABLE=""
BOTH_DOWN="false"
SESSION_ENV_PATH=""
OUTPUT_TALLY=""
OUTPUT_ACCEPTED=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --findings-file) FINDINGS_FILE="${2:?--findings-file requires a value}"; shift 2 ;;
        --review-tmpdir) REVIEW_TMPDIR="${2:?--review-tmpdir requires a value}"; shift 2 ;;
        --cursor-available) CURSOR_AVAILABLE="${2:?--cursor-available requires a value}"; shift 2 ;;
        --codex-available) CODEX_AVAILABLE="${2:?--codex-available requires a value}"; shift 2 ;;
        --both-down) BOTH_DOWN="${2:?--both-down requires a value}"; shift 2 ;;
        --session-env-path) SESSION_ENV_PATH="${2:?--session-env-path requires a value}"; shift 2 ;;
        --output-tally) OUTPUT_TALLY="${2:?--output-tally requires a value}"; shift 2 ;;
        --output-accepted) OUTPUT_ACCEPTED="${2:?--output-accepted requires a value}"; shift 2 ;;
        --help) usage; exit 0 ;;
        *) echo "tally-votes.sh: unknown option: $1" >&2; usage; exit 2 ;;
    esac
done

[[ -n "$FINDINGS_FILE" && -f "$FINDINGS_FILE" ]] || { echo "tally-votes.sh: --findings-file must name a file" >&2; exit 2; }
[[ -n "$REVIEW_TMPDIR" ]] || { echo "tally-votes.sh: --review-tmpdir is required" >&2; exit 2; }
mkdir -p "$REVIEW_TMPDIR"
OUTPUT_TALLY="${OUTPUT_TALLY:-$REVIEW_TMPDIR/review-tally.env}"
OUTPUT_ACCEPTED="${OUTPUT_ACCEPTED:-$REVIEW_TMPDIR/accepted-findings.md}"

parse_out=$("$SHARED_DIR/ballot-parse.sh" --ballot-file "$FINDINGS_FILE")
count=$(printf '%s\n' "$parse_out" | awk -F= '$1=="FINDING_COUNT"{print $2}')
count=${count:-0}

: > "$OUTPUT_TALLY"
: > "$OUTPUT_ACCEPTED"
accepted=0
rejected=0

if [[ "$BOTH_DOWN" == "true" ]]; then
    idx=1
    while [[ "$idx" -le "$count" ]]; do
        printf 'FINDING_%s_ACCEPTED=true\n' "$idx" >> "$OUTPUT_TALLY"
        accepted=$((accepted + 1))
        idx=$((idx + 1))
    done
else
    voter_files=()
    [[ -f "$REVIEW_TMPDIR/cursor-votes.txt" ]] && voter_files+=("$REVIEW_TMPDIR/cursor-votes.txt")
    [[ -f "$REVIEW_TMPDIR/codex-votes.txt" ]] && voter_files+=("$REVIEW_TMPDIR/codex-votes.txt")
    if [[ "${#voter_files[@]}" -eq 0 ]]; then
        printf 'FINDING_1 NO\n' > "$REVIEW_TMPDIR/no-votes.txt"
        voter_files+=("$REVIEW_TMPDIR/no-votes.txt")
    fi
    "$SHARED_DIR/tally-vote.sh" --ballot-file "$FINDINGS_FILE" --voter-files "${voter_files[@]}" > "$OUTPUT_TALLY"
    while IFS='=' read -r key value || [[ -n "$key" ]]; do
        case "$key" in
            FINDING_*_ACCEPTED)
                [[ "$value" == "true" ]] && accepted=$((accepted + 1)) || rejected=$((rejected + 1))
                ;;
        esac
    done < "$OUTPUT_TALLY"
fi

awk -v tally="$OUTPUT_TALLY" '
BEGIN {
    while ((getline line < tally) > 0) {
        split(line, kv, "=")
        if (kv[1] ~ /^FINDING_[0-9]+_ACCEPTED$/ && kv[2] == "true") {
            n=kv[1]; sub(/^FINDING_/, "", n); sub(/_ACCEPTED$/, "", n); accepted[n]=1
        }
    }
}
/^### FINDING_[0-9]+:/ {
    current=$0
    n=$0; sub(/^### FINDING_/, "", n); sub(/:.*/, "", n)
    print_block=(n in accepted)
}
print_block { print }
' "$FINDINGS_FILE" > "$OUTPUT_ACCEPTED"

: "$CURSOR_AVAILABLE" "$CODEX_AVAILABLE" "$SESSION_ENV_PATH"
printf 'ACCEPTED_COUNT=%s\n' "$accepted"
printf 'REJECTED_COUNT=%s\n' "$rejected"
printf 'TALLY_FILE=%q\n' "$OUTPUT_TALLY"
printf 'ACCEPTED_FINDINGS_FILE=%q\n' "$OUTPUT_ACCEPTED"
printf 'TALLY_OK=true\n'
