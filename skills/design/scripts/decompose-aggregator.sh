#!/usr/bin/env bash
# decompose-aggregator.sh — merge eight decomposition panel outputs into one partition proposal.
# Topology composition: single-slot merge of eight proposals
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
LARCH_QUIET_DISABLE=1
export LARCH_QUIET_DISABLE
# shellcheck source=scripts/lib-quiet.sh
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init

usage() {
    larch_err "Usage: decompose-aggregator.sh --design-tmpdir DIR --panel-outputs-file PATH --codex-present true|false --cursor-present true|false --output PATH [--timeout SEC]"
}

DESIGN_TMPDIR=""
PANEL_OUTPUTS=""
CODEX_PRESENT=""
CURSOR_PRESENT=""
OUT_PATH=""
TIMEOUT="1800"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --design-tmpdir) DESIGN_TMPDIR="${2:?}"; shift 2 ;;
        --panel-outputs-file) PANEL_OUTPUTS="${2:?}"; shift 2 ;;
        --codex-present) CODEX_PRESENT="${2:?}"; shift 2 ;;
        --cursor-present) CURSOR_PRESENT="${2:?}"; shift 2 ;;
        --output) OUT_PATH="${2:?}"; shift 2 ;;
        --timeout) TIMEOUT="${2:?}"; shift 2 ;;
        --help) usage; exit 0 ;;
        *) larch_err "decompose-aggregator.sh: unknown option: $1"; usage; exit 2 ;;
    esac
done

fail() {
    larch_err "decompose-aggregator.sh: $1"
    exit 2
}

[[ -n "$DESIGN_TMPDIR" ]] || fail "--design-tmpdir is required"
[[ -f "$PANEL_OUTPUTS" ]] || fail "--panel-outputs-file must exist"
[[ -n "$OUT_PATH" ]] || fail "--output is required"
[[ "$CODEX_PRESENT" == "true" || "$CODEX_PRESENT" == "false" ]] || fail "--codex-present must be true or false"
[[ "$CURSOR_PRESENT" == "true" || "$CURSOR_PRESENT" == "false" ]] || fail "--cursor-present must be true or false"
case "$TIMEOUT" in ''|*[!0-9]*|0) fail "--timeout must be a positive integer" ;; esac

DESIGN_TMPDIR=$(cd "$DESIGN_TMPDIR" && pwd -P)
DECOMP_DIR="$DESIGN_TMPDIR/decompose"
mkdir -p "$DECOMP_DIR"

COMBINED="$DECOMP_DIR/combined-proposals.txt"
: >"$COMBINED"
while IFS= read -r row || [[ -n "$row" ]]; do
    [[ -n "$row" ]] || continue
    _op=$(printf '%s' "$row" | jq -r '.output // empty')
    _arch=$(printf '%s' "$row" | jq -r '.archetype // empty')
    _vendor=$(printf '%s' "$row" | jq -r '.vendor // empty')
    {
        printf '\n## Panel output (%s / %s)\n\n' "$_arch" "$_vendor"
        if [[ -f "$_op" ]]; then
            cat "$_op"
        else
            printf '(missing file: %s)\n' "$_op"
        fi
        printf '\n'
    } >>"$COMBINED"
done <"$PANEL_OUTPUTS"

FEATURE_FILE="$DESIGN_TMPDIR/feature-description.txt"
[[ -f "$FEATURE_FILE" ]] || fail "missing $FEATURE_FILE for aggregator context"

MERGE_PROMPT="$DECOMP_DIR/aggregator-partition-merge.prompt"
{
    cat <<'HDR'
You are the decomposition aggregator. Below are eight independent partition proposals from external reviewers (four archetypes × two vendors).

Task: produce **one** canonical merged partition that best satisfies the independently-mergeable constraint (acyclic blocker graph) while minimizing unnecessary coupling.

HDR
    cat "$COMBINED"
    cat <<'TAIL'

Output **only** Markdown matching this schema (first heading must be detectable):

## Recommendation
split | no-split

## Pieces (only when Recommendation is split)

### Piece 1: <short title>
- Scope: <files / behaviors covered>
- Dependencies: none | blocked-by Piece N
- Diff_lines estimate: <integer>
- Why independently mergeable: <prose>

### Piece 2: ...

TAIL
} >"$MERGE_PROMPT"

AGG_OUT="$DECOMP_DIR/aggregator-raw-output.txt"
_slots="$DECOMP_DIR/aggregator-slots.ndjson"
jq -nc \
    --arg slot decompose-aggregator \
    --arg tool cursor \
    --arg output "$AGG_OUT" \
    --arg prompt_file "$MERGE_PROMPT" \
    '{slot:$slot,tool:$tool,output:$output,prompt_file:$prompt_file}' >"$_slots"

WATERFALL_SH="${DECOMPOSE_AGGREGATE_WATERFALL_SH:-$PLUGIN_ROOT/scripts/dispatch-with-waterfall.sh}"

set +e
_agg_out=$("$WATERFALL_SH" \
    --slots-file "$_slots" \
    --codex-present "$CODEX_PRESENT" \
    --cursor-present "$CURSOR_PRESENT" \
    --mode description \
    --feature-file "$FEATURE_FILE" \
    --timeout "$TIMEOUT")
_agg_rc=$?
set -e

DISPATCH_OK=""
ALL_OUTPUT_FILES_PATH=""
while IFS= read -r _line || [[ -n "$_line" ]]; do
    [[ -n "$_line" ]] || continue
    _key="${_line%%=*}"
    _value="${_line#*=}"
    case "$_key" in
        DISPATCH_OK) DISPATCH_OK="$_value" ;;
        ALL_OUTPUT_FILES_PATH) ALL_OUTPUT_FILES_PATH="$_value" ;;
    esac
done <<<"$_agg_out"

final_out="$AGG_OUT"
if [[ -n "$ALL_OUTPUT_FILES_PATH" && -f "$ALL_OUTPUT_FILES_PATH" ]]; then
    read -r final_out <"$ALL_OUTPUT_FILES_PATH" || true
fi

AGGREGATOR_STATUS="failed"
if [[ "$_agg_rc" == 0 && "${DISPATCH_OK:-false}" == "true" && -f "$final_out" ]]; then
    if grep -Eq '^[[:space:]]*## Recommendation' "$final_out"; then
        cp -f "$final_out" "$OUT_PATH"
        AGGREGATOR_STATUS="ok"
    fi
fi

emit_kv AGGREGATOR_STATUS "$AGGREGATOR_STATUS"
if [[ "$AGGREGATOR_STATUS" == "ok" ]]; then
    emit_kv AGGREGATOR_OUTPUT "$OUT_PATH"
fi
exit 0
