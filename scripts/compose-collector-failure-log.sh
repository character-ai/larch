#!/usr/bin/env bash
# compose-collector-failure-log.sh — compose a guaranteed-non-empty failure log
# from a collect-agent-results.sh collector record + reviewer output sidecars.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init

REVIEWER_FILE=""
STRUCTURED_RECORD=""
OUTPUT=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --reviewer-file)
            [[ $# -ge 2 ]] || { larch_err "--reviewer-file requires a value"; exit 2; }
            REVIEWER_FILE="$2"; shift 2 ;;
        --structured-record)
            [[ $# -ge 2 ]] || { larch_err "--structured-record requires a value"; exit 2; }
            STRUCTURED_RECORD="$2"; shift 2 ;;
        --output)
            [[ $# -ge 2 ]] || { larch_err "--output requires a value"; exit 2; }
            OUTPUT="$2"; shift 2 ;;
        *)
            larch_err "compose-collector-failure-log.sh: unknown flag: $1"; exit 2 ;;
    esac
done

[[ -n "$STRUCTURED_RECORD" ]] || { larch_err "--structured-record is required and non-empty"; exit 2; }
[[ -n "$OUTPUT" ]] || { larch_err "--output is required"; exit 2; }
[[ -d "$(dirname "$OUTPUT")" ]] || { larch_err "--output parent directory missing: $(dirname "$OUTPUT")"; exit 2; }

dump_section() {
    local header="$1" path="$2"
    printf '## %s\n\n' "$header"
    if [[ -z "$path" ]]; then
        printf '(no path provided)\n\n'
    elif [[ ! -e "$path" ]]; then
        printf '(file missing: %s)\n\n' "$path"
    elif [[ ! -s "$path" ]]; then
        printf '(empty: %s)\n\n' "$path"
    else
        cat "$path"
        printf '\n'
    fi
}

TMP=$(mktemp "$(dirname "$OUTPUT")/.compose-collector-failure-log.XXXXXX")
{
    printf '## Structured collector record\n\n'
    printf '%s\n\n' "$STRUCTURED_RECORD"
    dump_section "Reviewer output ($REVIEWER_FILE)" "$REVIEWER_FILE"
    if [[ -n "$REVIEWER_FILE" ]]; then
        dump_section "Reviewer stderr (${REVIEWER_FILE}.diag)" "${REVIEWER_FILE}.diag"
        dump_section "Failed-agent stderr tail (${REVIEWER_FILE}.stderr-tail)" "${REVIEWER_FILE}.stderr-tail"
        dump_section "Launcher stderr (${REVIEWER_FILE}.launch-stderr)" "${REVIEWER_FILE}.launch-stderr"
    fi
} > "$TMP"
mv "$TMP" "$OUTPUT"
