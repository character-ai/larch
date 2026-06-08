#!/usr/bin/env bash
# render-findings-view.sh — Render a dropped markdown view from review-findings-full.jsonl.
# Usage: render-findings-view.sh <run-dir> [accepted|rejected|oos|all]
# Outputs the requested view to stdout. Exits 1 when the jsonl is absent.

set -euo pipefail

usage() {
    printf 'Usage: render-findings-view.sh <larch-logs/implement/RUN_ID/> [accepted|rejected|oos|all]\n' >&2
    exit 1
}

[ $# -ge 1 ] || usage
RUN_DIR="$1"
VIEW="${2:-all}"

JSONL="$RUN_DIR/review-findings-full.jsonl"
if [ ! -f "$JSONL" ]; then
    printf 'render-findings-view.sh: review-findings-full.jsonl not found in %s\n' "$RUN_DIR" >&2
    exit 1
fi

case "$VIEW" in
    accepted|rejected|oos|all) ;;
    *) printf 'render-findings-view.sh: unknown view %s (accepted|rejected|oos|all)\n' "$VIEW" >&2; exit 1 ;;
esac

# Build jq outcome filter
if [ "$VIEW" = "all" ]; then
    OUTCOME_FILTER='true'
elif [ "$VIEW" = "oos" ]; then
    OUTCOME_FILTER='.outcome == "out_of_scope"'
else
    OUTCOME_FILTER=".outcome == \"$VIEW\""
fi

command -v jq >/dev/null 2>&1 || { printf 'render-findings-view.sh: jq is required\n' >&2; exit 1; }

jq -r --arg view "$VIEW" "
select($OUTCOME_FILTER) |
\"### FINDING (\" + .outcome + \") round-\" + (.round_num | tostring) + \"\\n\" +
(.prose_body // \"(no prose body)\") + \"\\n\"
" "$JSONL"
