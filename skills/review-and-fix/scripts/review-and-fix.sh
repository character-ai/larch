#!/usr/bin/env bash
# review-and-fix.sh — Enumerate accepted findings for main-agent fixes.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init

usage() {
    echo "Usage: review-and-fix.sh --findings-file FILE --review-tmpdir DIR [--session-env-path FILE]" >&2
}

FINDINGS_FILE=""
REVIEW_TMPDIR=""
SESSION_ENV_PATH=""
CALL_FIXER_SH="${REVIEW_AND_FIX_CALL_FIXER_SH:-$SCRIPT_DIR/call-fixer.sh}"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --findings-file) FINDINGS_FILE="${2:?--findings-file requires a value}"; shift 2 ;;
        --review-tmpdir) REVIEW_TMPDIR="${2:?--review-tmpdir requires a value}"; shift 2 ;;
        --session-env-path) SESSION_ENV_PATH="${2:?--session-env-path requires a value}"; shift 2 ;;
        --help) usage; exit 0 ;;
        *) echo "review-and-fix.sh: unknown option: $1" >&2; usage; exit 2 ;;
    esac
done

[[ -f "$FINDINGS_FILE" ]] || { echo "review-and-fix.sh: --findings-file must name a file" >&2; exit 2; }
[[ -n "$REVIEW_TMPDIR" ]] || { echo "review-and-fix.sh: --review-tmpdir is required" >&2; exit 2; }
mkdir -p "$REVIEW_TMPDIR"
: "$SESSION_ENV_PATH"

if [[ ! -s "$FINDINGS_FILE" ]] || ! grep -Eq '^### FINDING_[0-9]+:' "$FINDINGS_FILE"; then
    emit_kv REVIEW_AND_FIX_STATUS no-findings
    emit_kv FIX_COUNT 0
    exit 0
fi

ids_file="$REVIEW_TMPDIR/review-and-fix-finding-ids.txt"
grep -E '^### FINDING_[0-9]+:' "$FINDINGS_FILE" | sed 's/^### \(FINDING_[0-9][0-9]*\):.*/\1/' > "$ids_file"

count=0
while IFS= read -r id || [[ -n "$id" ]]; do
    [[ -n "$id" ]] || continue
    count=$((count + 1))
    emit_kv FINDING_ID "$id"
    "$CALL_FIXER_SH" --finding-file "$FINDINGS_FILE" --finding-id "$id" --review-tmpdir "$REVIEW_TMPDIR" > "$REVIEW_TMPDIR/${id}.fixer.env"
done < "$ids_file"

emit_kv REVIEW_AND_FIX_STATUS complete
emit_kv FIX_COUNT "$count"
emit_kv FINDING_IDS_FILE "$ids_file"
