#!/usr/bin/env bash
# collect-findings.sh — Collect reviewer outputs and write ballot findings.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"

usage() { echo "Usage: collect-findings.sh --mode diff|description --findings-file FILE --oos-file FILE [--external-output-files FILE...] [--claude-output-files FILE...] [--timeout SECONDS]" >&2; }

MODE=""
TIMEOUT="1860"
SESSION_ENV_PATH=""
FINDINGS_FILE=""
OOS_FILE=""
EXTERNAL_OUTPUT_FILES=()
CLAUDE_OUTPUT_FILES=()
EXTERNAL_COUNT=0
CLAUDE_COUNT=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --external-output-files) shift; while [[ $# -gt 0 && "$1" != --* ]]; do EXTERNAL_OUTPUT_FILES+=("$1"); EXTERNAL_COUNT=$((EXTERNAL_COUNT + 1)); shift; done ;;
        --claude-output-files) shift; while [[ $# -gt 0 && "$1" != --* ]]; do CLAUDE_OUTPUT_FILES+=("$1"); CLAUDE_COUNT=$((CLAUDE_COUNT + 1)); shift; done ;;
        --mode) MODE="${2:?--mode requires a value}"; shift 2 ;;
        --timeout) TIMEOUT="${2:?--timeout requires a value}"; shift 2 ;;
        --session-env-path) SESSION_ENV_PATH="${2:?--session-env-path requires a value}"; shift 2 ;;
        --findings-file) FINDINGS_FILE="${2:?--findings-file requires a value}"; shift 2 ;;
        --oos-file) OOS_FILE="${2:?--oos-file requires a value}"; shift 2 ;;
        --help) usage; exit 0 ;;
        *) echo "collect-findings.sh: unknown option: $1" >&2; usage; exit 2 ;;
    esac
done

[[ "$MODE" == "diff" || "$MODE" == "description" ]] || { echo "collect-findings.sh: --mode must be diff or description" >&2; exit 2; }
[[ -n "$FINDINGS_FILE" ]] || { echo "collect-findings.sh: --findings-file is required" >&2; exit 2; }
[[ -n "$OOS_FILE" ]] || { echo "collect-findings.sh: --oos-file is required" >&2; exit 2; }
mkdir -p "$(dirname "$FINDINGS_FILE")" "$(dirname "$OOS_FILE")"

collector_out=""
if [[ "$EXTERNAL_COUNT" -gt 0 ]]; then
    # Pin: collect-agent-results.sh --timeout 1860 --substantive-validation --validation-mode
    args=(--timeout "$TIMEOUT" --substantive-validation --validation-mode)
    [[ -n "$SESSION_ENV_PATH" ]] && args+=(--write-health "${SESSION_ENV_PATH}.health")
    collector_out=$("$PLUGIN_ROOT/scripts/collect-agent-results.sh" "${args[@]}" "${EXTERNAL_OUTPUT_FILES[@]}")
fi

if [[ "$CLAUDE_COUNT" -gt 0 ]]; then
    sentinels=()
    for f in "${CLAUDE_OUTPUT_FILES[@]}"; do sentinels+=("${f}.done"); done
    WAIT_FOR_REVIEWERS_POLL_INTERVAL="${WAIT_FOR_REVIEWERS_POLL_INTERVAL:-1}" "$PLUGIN_ROOT/scripts/wait-for-reviewers.sh" --timeout "$TIMEOUT" "${sentinels[@]}" >/dev/null
fi

DIRTY_DETECTED=false
for f in "${EXTERNAL_OUTPUT_FILES[@]+"${EXTERNAL_OUTPUT_FILES[@]}"}" "${CLAUDE_OUTPUT_FILES[@]+"${CLAUDE_OUTPUT_FILES[@]}"}"; do
    sidecar="${f}.dirty-tree"
    if [[ ! -s "$sidecar" ]] || ! grep -Fq 'STATUS=clean' "$sidecar"; then
        DIRTY_DETECTED=true
    fi
done

tmp=$(mktemp "${TMPDIR:-/tmp}/review-findings.XXXXXX") || exit 1
trap 'rm -f "$tmp"' EXIT

parse_output() {
    local file="$1" label="$2"
    [[ -s "$file" ]] || return 0
    if grep -Fxq 'NO_ISSUES_FOUND' "$file"; then
        return 0
    fi
    if [[ "$MODE" == "description" ]]; then
        # In description mode, parse dual-list output with ### In-Scope Findings and ### Out-of-Scope Observations; missing one header is fail-open.
        if grep -Fq '### Out-of-Scope Observations' "$file"; then
            :
        fi
    else
        # In diff mode, preserve single-list output by treating the entire output as in-scope findings.
        :
    fi
    awk -v label="$label" -v mode="$MODE" '
    BEGIN { oos=0; body=""; title="" }
    function flush() {
        if (body != "") {
            gsub(/^[[:space:]]+|[[:space:]]+$/, "", body)
            prefix=oos ? "[OUT_OF_SCOPE] " : ""
            printf("%s%s\t%s\t%s\n", prefix, title == "" ? "Reviewer finding" : title, label, body)
        }
        body=""; title=""
    }
    /^### Out-of-Scope Observations/ { flush(); oos=1; next }
    /^### In-Scope Findings/ { flush(); oos=0; next }
    /^[-*] / || /^[0-9]+\./ {
        flush()
        title=$0
        sub(/^[-*][[:space:]]*/, "", title)
        sub(/^[0-9]+\.[[:space:]]*/, "", title)
        body=$0
        next
    }
    NF { body = body "\n" $0 }
    END { flush() }
    ' "$file"
}

for f in "${EXTERNAL_OUTPUT_FILES[@]+"${EXTERNAL_OUTPUT_FILES[@]}"}" "${CLAUDE_OUTPUT_FILES[@]+"${CLAUDE_OUTPUT_FILES[@]}"}"; do
    parse_output "$f" "$(basename "$f")" >> "$tmp"
done

sort -u "$tmp" > "$tmp.sorted"
: > "$FINDINGS_FILE"
: > "$OOS_FILE"
count=0
oos_count=0
while IFS=$'\t' read -r title label body || [[ -n "${title:-}" ]]; do
    [[ -n "$title" ]] || continue
    count=$((count + 1))
    {
        printf '### FINDING_%s: %s\n' "$count" "$title"
        printf -- '- **Reviewer**: %s\n' "$label"
        printf -- '- **Concern**: %s\n' "$body"
        printf -- '- **Suggested revision**: Address the concern above.\n\n'
    } >> "$FINDINGS_FILE"
    if [[ "$title" == \[OUT_OF_SCOPE\]* ]]; then
        oos_count=$((oos_count + 1))
        printf '### FINDING_%s: %s\n%s\n\n' "$count" "$title" "$body" >> "$OOS_FILE"
    fi
done < "$tmp.sorted"

printf '%s\n' "$collector_out" > "$(dirname "$FINDINGS_FILE")/collector-results.env"
printf 'FINDINGS_COUNT=%s\n' "$count"
printf 'OOS_COUNT=%s\n' "$oos_count"
printf 'DIRTY_DETECTED=%s\n' "$DIRTY_DETECTED"
printf 'COLLECT_OK=true\n'
