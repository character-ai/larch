#!/usr/bin/env bash
# decompose-panel-dispatch.sh — fixed 8-slot decomposition panel (4 archetypes x 2 vendors).
# Topology composition: renders prompts + dispatch-with-waterfall
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
LARCH_QUIET_DISABLE=1
export LARCH_QUIET_DISABLE
# shellcheck source=scripts/lib-quiet.sh
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init

APPEND_FAIL_SH="$PLUGIN_ROOT/scripts/append-tool-failure.sh"

usage() {
    larch_err "Usage: decompose-panel-dispatch.sh --design-tmpdir DIR --codex-present true|false --cursor-present true|false --mode plan|feature-only [--plan-file PATH] [--feature-file PATH] [--discussion-round1-file PATH] [--timeout SEC]"
}

DESIGN_TMPDIR=""
CODEX_PRESENT=""
CURSOR_PRESENT=""
MODE=""
PLAN_FILE=""
FEATURE_FILE=""
DISCUSSION_FILE=""
TIMEOUT="1800"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --design-tmpdir) DESIGN_TMPDIR="${2:?}"; shift 2 ;;
        --codex-present) CODEX_PRESENT="${2:?}"; shift 2 ;;
        --cursor-present) CURSOR_PRESENT="${2:?}"; shift 2 ;;
        --mode) MODE="${2:?}"; shift 2 ;;
        --plan-file) PLAN_FILE="${2:?}"; shift 2 ;;
        --feature-file) FEATURE_FILE="${2:?}"; shift 2 ;;
        --discussion-round1-file) DISCUSSION_FILE="${2:?}"; shift 2 ;;
        --timeout) TIMEOUT="${2:?}"; shift 2 ;;
        --help) usage; exit 0 ;;
        *) larch_err "decompose-panel-dispatch.sh: unknown option: $1"; usage; exit 2 ;;
    esac
done

fail() {
    larch_err "decompose-panel-dispatch.sh: $1"
    exit 2
}

[[ -n "$DESIGN_TMPDIR" ]] || fail "--design-tmpdir is required"
[[ "$CODEX_PRESENT" == "true" || "$CODEX_PRESENT" == "false" ]] || fail "--codex-present must be true or false"
[[ "$CURSOR_PRESENT" == "true" || "$CURSOR_PRESENT" == "false" ]] || fail "--cursor-present must be true or false"
[[ "$MODE" == "plan" || "$MODE" == "feature-only" ]] || fail "--mode must be plan or feature-only"
case "$TIMEOUT" in ''|*[!0-9]*|0) fail "--timeout must be a positive integer" ;; esac

DESIGN_TMPDIR=$(cd "$DESIGN_TMPDIR" && pwd -P)
DECOMP_DIR="$DESIGN_TMPDIR/decompose"
mkdir -p "$DECOMP_DIR"

if [[ "$MODE" == "plan" ]]; then
    [[ -n "$PLAN_FILE" ]] || fail "plan mode requires --plan-file"
    [[ -f "$PLAN_FILE" ]] || fail "plan file not found: $PLAN_FILE"
    PRIMARY_INPUT="$PLAN_FILE"
else
    [[ -n "$FEATURE_FILE" ]] || fail "feature-only mode requires --feature-file"
    [[ -f "$FEATURE_FILE" ]] || fail "feature file not found: $FEATURE_FILE"
    PRIMARY_INPUT="$FEATURE_FILE"
fi

if [[ -z "$FEATURE_FILE" ]]; then
    FEATURE_FILE="$DESIGN_TMPDIR/feature-description.txt"
fi
[[ -f "$FEATURE_FILE" ]] || fail "feature-description not found (set --feature-file): $FEATURE_FILE"

_disc_arg="-"
if [[ -n "$DISCUSSION_FILE" ]]; then
    [[ -f "$DISCUSSION_FILE" ]] || fail "discussion file not found: $DISCUSSION_FILE"
    _disc_arg="$DISCUSSION_FILE"
fi

PROMPTS_DIR="$SCRIPT_DIR/decompose-prompts"
COMMON_TAIL="$PROMPTS_DIR/_common-tail.txt"
[[ -f "$COMMON_TAIL" ]] || fail "missing common tail: $COMMON_TAIL"

render_prompt() {
    local archetype="$1" out="$2"
    local arch_file="$PROMPTS_DIR/${archetype}.txt"
    [[ -f "$arch_file" ]] || fail "missing archetype template: $arch_file"
    python3 - "$arch_file" "$COMMON_TAIL" "$PRIMARY_INPUT" "$_disc_arg" "$out" <<'PY'
import pathlib
import sys

arch_p, common_p, primary_p, disc_arg, out_p = sys.argv[1:6]
arch = pathlib.Path(arch_p).read_text(encoding="utf-8")
common = pathlib.Path(common_p).read_text(encoding="utf-8")


def read_text(path: str) -> str:
    p = pathlib.Path(path)
    if not p.is_file():
        return ""
    return p.read_text(encoding="utf-8")


primary = read_text(primary_p)
if not primary.strip():
    primary = "(empty primary input file)\n"

if disc_arg == "-":
    disc_body = "(none — discussion-round1 artifact not passed or absent.)\n"
else:
    dpath = pathlib.Path(disc_arg)
    disc_body = dpath.read_text(encoding="utf-8") if dpath.is_file() else "(discussion path not readable)\n"

plan_or_feature_block = "## Primary input\n\n" + primary.strip() + "\n\n"
discussion_block = "## Discussion round 1\n\n" + disc_body.strip() + "\n\n"

full = arch.replace("{COMMON_TAIL}", common)
full = full.replace("{PLAN_OR_FEATURE_BLOCK}", plan_or_feature_block)
full = full.replace("{DISCUSSION_BLOCK}", discussion_block)
pathlib.Path(out_p).write_text(full, encoding="utf-8")
PY
}

_manifest="$DECOMP_DIR/decompose-slots.ndjson"
: >"$_manifest"

_archetypes=(decomposition-specialist dependency-analyst scope-minimalist risk-isolation)
for _a in "${_archetypes[@]}"; do
    render_prompt "$_a" "$DECOMP_DIR/render-decomp-cursor-${_a}.prompt"
    render_prompt "$_a" "$DECOMP_DIR/render-decomp-codex-${_a}.prompt"
    jq -nc \
        --arg slot "decomp-cursor-${_a}" \
        --arg tool cursor \
        --arg output "$DECOMP_DIR/decomp-cursor-${_a}-output.txt" \
        --arg prompt_file "$DECOMP_DIR/render-decomp-cursor-${_a}.prompt" \
        --arg fallback_group "decomp-${_a}" \
        '{slot:$slot,tool:$tool,output:$output,prompt_file:$prompt_file,fallback_group:$fallback_group}' >>"$_manifest"
    jq -nc \
        --arg slot "decomp-codex-${_a}" \
        --arg tool codex \
        --arg output "$DECOMP_DIR/decomp-codex-${_a}-output.txt" \
        --arg prompt_file "$DECOMP_DIR/render-decomp-codex-${_a}.prompt" \
        --arg fallback_group "decomp-${_a}" \
        '{slot:$slot,tool:$tool,output:$output,prompt_file:$prompt_file,fallback_group:$fallback_group}' >>"$_manifest"
done

WATERFALL_SH="${DECOMPOSE_PANEL_WATERFALL_SH:-$PLUGIN_ROOT/scripts/dispatch-with-waterfall.sh}"

_wf_extra=(--feature-file "$FEATURE_FILE" --timeout "$TIMEOUT")
if [[ "$MODE" == "plan" ]]; then
    _wf_extra+=(--plan-file "$PLAN_FILE")
fi

set +e
unset LARCH_PAIRED_PID_FILE
_dispatch_out=$("$WATERFALL_SH" \
    --slots-file "$_manifest" \
    --codex-present "$CODEX_PRESENT" \
    --cursor-present "$CURSOR_PRESENT" \
    --mode description \
    --require-result-pattern '^[[:space:]]*## Recommendation' \
    "${_wf_extra[@]}")
_wf_rc=$?
set -e

if [[ "$_wf_rc" != 0 ]]; then
    _cap="$DECOMP_DIR/decompose-waterfall-failure.log"
    printf '%s\n' "$_dispatch_out" >"$_cap"
    if [[ -x "$APPEND_FAIL_SH" ]]; then
        set +e
        bash "$APPEND_FAIL_SH" \
            --log "$DESIGN_TMPDIR/execution-issues.md" \
            --site "design Step 2b.5 decompose panel" \
            --tool "dispatch-with-waterfall.sh" \
            --exit-code "$_wf_rc" \
            --category "External Reviewer Issues" \
            --output-file "$_cap" \
            --redact || true
        set -e
    fi
fi

DISPATCH_OK=""
FALLBACK_COUNT=""
COMBINED_FALLBACK_COUNT=""
STATIC_DISPATCH_OK=""
ALL_OUTPUT_FILES_PATH=""

while IFS= read -r _line || [[ -n "$_line" ]]; do
    [[ -n "$_line" ]] || continue
    _key="${_line%%=*}"
    _value="${_line#*=}"
    case "$_key" in
        DISPATCH_OK) DISPATCH_OK="$_value" ;;
        FALLBACK_COUNT) FALLBACK_COUNT="$_value" ;;
        COMBINED_FALLBACK_COUNT) COMBINED_FALLBACK_COUNT="$_value" ;;
        STATIC_DISPATCH_OK) STATIC_DISPATCH_OK="$_value" ;;
        ALL_OUTPUT_FILES_PATH) ALL_OUTPUT_FILES_PATH="$_value" ;;
        WARN) emit_kv WARN "$_value" ;;
    esac
done <<<"$_dispatch_out"

: "${DISPATCH_OK:-}"
: "${FALLBACK_COUNT:-0}"
: "${STATIC_DISPATCH_OK:-true}"
: "${ALL_OUTPUT_FILES_PATH:-}"

floor_half=$((8 / 2))
case "$FALLBACK_COUNT" in ''|*[!0-9]*) FALLBACK_COUNT=0 ;; esac
case "$COMBINED_FALLBACK_COUNT" in ''|*[!0-9]*) COMBINED_FALLBACK_COUNT="$FALLBACK_COUNT" ;; esac
DEGRADED_PANEL=false
[[ "${STATIC_DISPATCH_OK:-true}" == "false" ]] && DEGRADED_PANEL=true
if (( 10#$COMBINED_FALLBACK_COUNT > floor_half )); then
    DEGRADED_PANEL=true
fi

usable=0
_panel_rows="$DECOMP_DIR/panel-outputs.ndjson"
: >"$_panel_rows"

# Read the dispatcher's resolved paths (one per slot, manifest order) so panel
# rows reflect phase-2/phase-3 fallback files instead of the original manifest
# phase-1 path. Bash 3.2-compatible: no mapfile/readarray.
_resolved_paths=()
if [[ -n "$ALL_OUTPUT_FILES_PATH" && -f "$ALL_OUTPUT_FILES_PATH" ]]; then
    while IFS= read -r _rp_line || [[ -n "$_rp_line" ]]; do
        _resolved_paths+=("$_rp_line")
    done <"$ALL_OUTPUT_FILES_PATH"
fi

_i=0
_warned_missing_paths=false
while IFS= read -r row || [[ -n "$row" ]]; do
    [[ -n "$row" ]] || continue
    _slot=$(printf '%s' "$row" | jq -r '.slot // empty')
    _tool=$(printf '%s' "$row" | jq -r '.tool // empty')
    _outp=$(printf '%s' "$row" | jq -r '.output // empty')
    _arch="${_slot#decomp-cursor-}"
    _arch="${_arch#decomp-codex-}"
    if (( ${#_resolved_paths[@]} > 0 )); then
        _outp_resolved="${_resolved_paths[$_i]:-$_outp}"
    else
        if [[ "$_warned_missing_paths" != true ]]; then
            larch_err "decompose-panel-dispatch.sh: ALL_OUTPUT_FILES_PATH empty or missing; falling back to manifest paths for panel-outputs rows"
            _warned_missing_paths=true
        fi
        _outp_resolved="$_outp"
    fi
    _status="missing"
    if [[ -f "$_outp_resolved" ]] && grep -Eq '^[[:space:]]*## Recommendation' "$_outp_resolved"; then
        _status="ok"
        usable=$((usable + 1))
    elif [[ -f "$_outp_resolved" ]]; then
        _status="unparsed"
    fi
    jq -nc \
        --arg archetype "$_arch" \
        --arg vendor "$_tool" \
        --arg output "$_outp_resolved" \
        --arg status "$_status" \
        '{archetype:$archetype,vendor:$vendor,output:$output,status:$status}' >>"$_panel_rows"
    _i=$((_i + 1))
done <"$_manifest"

PANEL_STATUS="ok"
if (( usable == 0 )); then
    PANEL_STATUS="panel-failed"
elif [[ "$DEGRADED_PANEL" == true ]]; then
    PANEL_STATUS="degraded"
fi

if [[ "$_wf_rc" != 0 ]]; then
    DEGRADED_PANEL=true
    if (( usable > 0 )) && [[ "$PANEL_STATUS" == "ok" ]]; then
        PANEL_STATUS="degraded"
    fi
fi

printf '%s\n' "$_dispatch_out"
emit_kv PANEL_OUTPUTS_FILE "$_panel_rows"
emit_kv DEGRADED_PANEL "$DEGRADED_PANEL"
emit_kv PANEL_STATUS "$PANEL_STATUS"
exit 0
