#!/usr/bin/env bash
# dispatch-plan-review-panel.sh — Render + dispatch /design plan-review (static + dynamic slots).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
LARCH_QUIET_DISABLE=1
export LARCH_QUIET_DISABLE
# shellcheck source=scripts/lib-quiet.sh
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init

usage() {
    larch_err "Usage: dispatch-plan-review-panel.sh --design-tmpdir DIR --codex-present true|false --cursor-present true|false --plan-file PATH [--feature-file PATH] [--timeout SEC] [--competition-notice-file PATH]"
}

DESIGN_TMPDIR=""
CODEX_PRESENT=""
CURSOR_PRESENT=""
PLAN_FILE=""
FEATURE_FILE=""
TIMEOUT="1800"
COMPETITION_NOTICE_FILE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --design-tmpdir) DESIGN_TMPDIR="${2:?}"; shift 2 ;;
        --codex-present) CODEX_PRESENT="${2:?}"; shift 2 ;;
        --cursor-present) CURSOR_PRESENT="${2:?}"; shift 2 ;;
        --plan-file) PLAN_FILE="${2:?}"; shift 2 ;;
        --feature-file) FEATURE_FILE="${2:?}"; shift 2 ;;
        --timeout) TIMEOUT="${2:?}"; shift 2 ;;
        --competition-notice-file) COMPETITION_NOTICE_FILE="${2:?}"; shift 2 ;;
        --help) usage; exit 0 ;;
        *) larch_err "dispatch-plan-review-panel.sh: unknown option: $1"; usage; exit 2 ;;
    esac
done

fail() {
    larch_err "dispatch-plan-review-panel.sh: $1"
    exit 2
}

[[ -n "$DESIGN_TMPDIR" ]] || fail "--design-tmpdir is required"
[[ "$CODEX_PRESENT" == "true" || "$CODEX_PRESENT" == "false" ]] || fail "--codex-present must be true or false"
[[ "$CURSOR_PRESENT" == "true" || "$CURSOR_PRESENT" == "false" ]] || fail "--cursor-present must be true or false"
[[ -n "$PLAN_FILE" ]] || fail "--plan-file is required"
[[ -f "$PLAN_FILE" ]] || fail "plan file not found: $PLAN_FILE"
case "$TIMEOUT" in ''|*[!0-9]*|0) fail "--timeout must be a positive integer" ;; esac

DESIGN_TMPDIR=$(cd "$DESIGN_TMPDIR" && pwd -P)

append_shared_prompt_tail() {
    local plan_path="$1"
    bash "${PLUGIN_ROOT}/skills/design/scripts/render-plan-review-prompt.sh" \
        --archetype arch --vendor cursor --plan-file "$plan_path" | tail -n +2
}

write_dynamic_prompt() {
    local slug="$1" plan_path="$2" body_file="$3" out="$4"
    {
        printf '%s\n' "You are a supplementary plan-review specialist (dynamic archetype \`${slug}\`). The static /design panel already covers Arch, Edge, Innovation, Pragmatic, and Requirements (Cursor + Codex). Apply the same evidence discipline: compare the written plan to current repository state. Focus directive:"
        printf '\n'
        cat "$body_file"
        printf '\n'
        append_shared_prompt_tail "$plan_path"
    } >"$out"
}

_manifest="$DESIGN_TMPDIR/plan-review-slots.ndjson"
_scout_manifest="$DESIGN_TMPDIR/scout-plan-manifest.json"
: >"$_manifest"

for _archetype in arch edge innovation pragmatic requirements; do
    bash "${PLUGIN_ROOT}/skills/design/scripts/render-plan-review-prompt.sh" \
        --archetype "$_archetype" --vendor cursor --plan-file "$PLAN_FILE" \
        >"$DESIGN_TMPDIR/render-plan-cursor-${_archetype}.prompt"
    bash "${PLUGIN_ROOT}/skills/design/scripts/render-plan-review-prompt.sh" \
        --archetype "$_archetype" --vendor codex --plan-file "$PLAN_FILE" \
        >"$DESIGN_TMPDIR/render-plan-codex-${_archetype}.prompt"
done

for _archetype in arch edge innovation pragmatic requirements; do
    printf '{"slot":"cursor-plan-%s","tool":"cursor","output":"%s","prompt_file":"%s"}\n' \
        "$_archetype" \
        "$DESIGN_TMPDIR/cursor-plan-${_archetype}-output.txt" \
        "$DESIGN_TMPDIR/render-plan-cursor-${_archetype}.prompt" >>"$_manifest"
    printf '{"slot":"codex-plan-%s","tool":"codex","output":"%s","prompt_file":"%s"}\n' \
        "$_archetype" \
        "$DESIGN_TMPDIR/codex-primary-plan-${_archetype}-output.txt" \
        "$DESIGN_TMPDIR/render-plan-codex-${_archetype}.prompt" >>"$_manifest"
done

if [[ -s "$_scout_manifest" ]] && jq -e '.archetypes | type == "array"' "$_scout_manifest" >/dev/null 2>&1; then
    while IFS= read -r row || [[ -n "$row" ]]; do
        [[ -n "$row" ]] || continue
        _slug=$(printf '%s' "$row" | jq -r '.name // empty')
        [[ -n "$_slug" ]] || continue
        _body_tmp=$(mktemp "${DESIGN_TMPDIR}/dyn-body.XXXXXX")
        printf '%s' "$row" | jq -r '.prompt_body // empty' >"$_body_tmp"
        write_dynamic_prompt "$_slug" "$PLAN_FILE" "$_body_tmp" "$DESIGN_TMPDIR/render-plan-cursor-dyn-${_slug}.prompt"
        write_dynamic_prompt "$_slug" "$PLAN_FILE" "$_body_tmp" "$DESIGN_TMPDIR/render-plan-codex-dyn-${_slug}.prompt"
        rm -f "$_body_tmp"
        printf '{"slot":"dyn-cursor-plan-%s","tool":"cursor","output":"%s","prompt_file":"%s"}\n' \
            "$_slug" \
            "$DESIGN_TMPDIR/cursor-plan-dyn-${_slug}-output.txt" \
            "$DESIGN_TMPDIR/render-plan-cursor-dyn-${_slug}.prompt" >>"$_manifest"
        printf '{"slot":"dyn-codex-plan-%s","tool":"codex","output":"%s","prompt_file":"%s"}\n' \
            "$_slug" \
            "$DESIGN_TMPDIR/codex-primary-plan-dyn-${_slug}-output.txt" \
            "$DESIGN_TMPDIR/render-plan-codex-dyn-${_slug}.prompt" >>"$_manifest"
    done < <(jq -c '.archetypes[]?' "$_scout_manifest")
fi

slot_count=0
while IFS= read -r _row || [[ -n "$_row" ]]; do
    [[ -n "$_row" ]] || continue
    slot_count=$((slot_count + 1))
done <"$_manifest"

waterfall_extra=()
if [[ -n "$COMPETITION_NOTICE_FILE" && -f "$COMPETITION_NOTICE_FILE" ]]; then
    waterfall_extra+=(--competition-notice --competition-notice-file "$COMPETITION_NOTICE_FILE")
fi
if [[ -n "$FEATURE_FILE" && -f "$FEATURE_FILE" ]]; then
    waterfall_extra+=(--feature-file "$FEATURE_FILE")
fi

DISPATCH_WATERFALL_SH="${DISPATCH_PLAN_REVIEW_WATERFALL_SH:-$PLUGIN_ROOT/scripts/dispatch-with-waterfall.sh}"

_dispatch_out=$("$DISPATCH_WATERFALL_SH" \
    --slots-file "$_manifest" \
    --codex-present "$CODEX_PRESENT" \
    --cursor-present "$CURSOR_PRESENT" \
    --mode description \
    --plan-file "$PLAN_FILE" \
    --timeout "$TIMEOUT" \
    "${waterfall_extra[@]+"${waterfall_extra[@]}"}")

DISPATCH_OK=""
FALLBACK_COUNT=""
STATIC_DISPATCH_OK=""
ALL_OUTPUT_FILES_PATH=""

while IFS= read -r _line || [[ -n "$_line" ]]; do
    [[ -n "$_line" ]] || continue
    _key="${_line%%=*}"
    _value="${_line#*=}"
    case "$_key" in
        DISPATCH_OK) DISPATCH_OK="$_value" ;;
        FALLBACK_COUNT) FALLBACK_COUNT="$_value" ;;
        STATIC_DISPATCH_OK) STATIC_DISPATCH_OK="$_value" ;;
        ALL_OUTPUT_FILES_PATH) ALL_OUTPUT_FILES_PATH="$_value" ;;
        WARN) emit_kv WARN "$_value" ;;
    esac
done <<<"$_dispatch_out"

: "${DISPATCH_OK:-}"

dyn_slots=0
while IFS= read -r _row2 || [[ -n "$_row2" ]]; do
    [[ -n "$_row2" ]] || continue
    case "$(printf '%s' "$_row2" | jq -r '.slot // empty')" in
        dyn-*) dyn_slots=$((dyn_slots + 1)) ;;
    esac
done <"$_manifest"

floor_half=$((slot_count / 2))
case "$FALLBACK_COUNT" in ''|*[!0-9]*) FALLBACK_COUNT=0 ;; esac
DEGRADED_ROUND=false
[[ "${STATIC_DISPATCH_OK:-true}" == "false" ]] && DEGRADED_ROUND=true
if (( 10#$FALLBACK_COUNT > floor_half )); then
    DEGRADED_ROUND=true
fi

printf '%s\n' "$_dispatch_out"
emit_kv DYNAMIC_SLOT_COUNT "$dyn_slots"
emit_kv DEGRADED_ROUND "$DEGRADED_ROUND"
emit_kv PANEL_PATHS_FILE "${ALL_OUTPUT_FILES_PATH:-${_manifest}.output-files}"
exit 0
