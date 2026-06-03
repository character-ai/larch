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
# shellcheck source=scripts/lib-design-tmpdir.sh
source "$PLUGIN_ROOT/scripts/lib-design-tmpdir.sh"

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

larch_design_tmpdir_validate "$DESIGN_TMPDIR" || exit $?

DESIGN_TMPDIR=$(cd "$DESIGN_TMPDIR" && pwd -P)

append_shared_prompt_tail() {
    local plan_path="$1"
    bash "${PLUGIN_ROOT}/skills/design/scripts/render-plan-review-prompt.sh" \
        --archetype arch --vendor cursor --plan-file "$plan_path" --design-tmpdir "$DESIGN_TMPDIR" | tail -n +2
}

write_dynamic_prompt() {
    local slug="$1" plan_path="$2" body_file="$3" out="$4"
    local vendor_note=""
    if [[ "$CODEX_PRESENT" == "true" && "$CURSOR_PRESENT" == "true" ]]; then
        vendor_note=" (Cursor + Codex)"
    elif [[ "$CURSOR_PRESENT" == "true" ]]; then
        vendor_note=" (Cursor)"
    elif [[ "$CODEX_PRESENT" == "true" ]]; then
        vendor_note=" (Codex)"
    fi
    {
        printf '%s\n' "You are a supplementary plan-review specialist (dynamic archetype \`${slug}\`). The static /design panel already covers Arch, Edge, Innovation, Pragmatic, and Requirements${vendor_note}. Apply the same evidence discipline: compare the written plan to current repository state. Focus directive:"
        printf '\n'
        cat "$body_file"
        printf '\n'
        append_shared_prompt_tail "$plan_path"
    } >"$out"
}

_manifest="$DESIGN_TMPDIR/plan-review-slots.ndjson"
_scout_manifest="$DESIGN_TMPDIR/scout-plan-manifest.json"
: >"$_manifest"

waterfall_extra=()
if [[ -n "$COMPETITION_NOTICE_FILE" && -f "$COMPETITION_NOTICE_FILE" ]]; then
    waterfall_extra+=(--competition-notice --competition-notice-file "$COMPETITION_NOTICE_FILE")
fi
if [[ -n "$FEATURE_FILE" && -f "$FEATURE_FILE" ]]; then
    waterfall_extra+=(--feature-file "$FEATURE_FILE")
fi

DISPATCH_WATERFALL_SH="${DISPATCH_PLAN_REVIEW_WATERFALL_SH:-$PLUGIN_ROOT/scripts/dispatch-with-waterfall.sh}"

if [[ "$CODEX_PRESENT" == "false" && "$CURSOR_PRESENT" == "false" ]]; then
    _panel_paths="$DESIGN_TMPDIR/plan-review-panel-paths.txt"
    _generic_output="$DESIGN_TMPDIR/claude-plan-generic-output.txt"
    _generic_prompt="$DESIGN_TMPDIR/claude-plan-generic.prompt"
    {
        printf '%s\n' "You are a combined plan-review panel applying all five standard archetype lenses in a single pass. Address each lens below, then follow the shared output contract."
        printf '\n'
        for _archetype in arch edge innovation pragmatic requirements; do
            _role_render=$(bash "${PLUGIN_ROOT}/skills/design/scripts/render-plan-review-prompt.sh" \
                --archetype "$_archetype" --vendor cursor --plan-file "$PLAN_FILE" --design-tmpdir "$DESIGN_TMPDIR")
            _role_line="${_role_render%%$'\n'*}"
            printf '%s\n\n' "$_role_line"
        done
        append_shared_prompt_tail "$PLAN_FILE"
    } >"$_generic_prompt"
    _generic_first_line_ere='^[[:space:]]*(schema_version|\{"no_issues_found|\{"schema_version)'
    set +e
    "$PLUGIN_ROOT/scripts/launch-claude-review.sh" \
        --output "$_generic_output" \
        --prompt-file "$_generic_prompt" \
        --mode description \
        --model claude-opus-4-7 \
        --timeout "$TIMEOUT" \
        --timing-task-kind claude-plan-generic \
        "${waterfall_extra[@]+"${waterfall_extra[@]}"}" >/dev/null 2>"${_generic_output}.launch-stderr"
    _generic_rc=$?
    set -e
    [[ -f "${_generic_output}.done" ]] || printf '%s\n' "$_generic_rc" >"${_generic_output}.done"
    _generic_dispatch_ok=false
    _generic_degraded=true
    _generic_has_output=false
    if [[ "$_generic_rc" -eq 0 && -s "$_generic_output" ]]; then
        _generic_has_output=true
        printf '%s\n' "$_generic_output" >"$_panel_paths"
        _generic_first=$(
            awk 'NF { print; exit }' "$_generic_output" 2>/dev/null || true
        )
        if [[ -n "$_generic_first" ]] && printf '%s\n' "$_generic_first" | grep -Eq -- "$_generic_first_line_ere"; then
            if [[ -x "$PLUGIN_ROOT/scripts/validate-research-output.sh" ]] && \
                "$PLUGIN_ROOT/scripts/validate-research-output.sh" \
                    --structured-reviewer-mode \
                    --write-structured "${_generic_output}.tsv" \
                    "$_generic_output" >/dev/null 2>&1; then
                _generic_dispatch_ok=true
                _generic_degraded=false
            else
                emit_kv WARN "plan-review-panel: generic Claude reviewer passed the first-line gate but failed structured validation (degraded)"
            fi
        else
            # #3392: a non-empty generic reviewer response that fails the
            # first-line format gate (e.g. leads with a preamble) must be
            # observable, not just collapsed into DISPATCH_OK=false. Surface the
            # offending first line so a format-miss is distinguishable from an
            # empty/failed reviewer.
            _generic_first_snip=$(printf '%s' "${_generic_first:-<empty>}" | LC_ALL=C tr -d '\r\n\t' | cut -c1-160)
            emit_kv WARN "plan-review-panel: generic Claude reviewer failed the first-line format gate (degraded) — first line: ${_generic_first_snip}"
        fi
    fi
    if [[ "$_generic_has_output" != true ]]; then
        : >"$_panel_paths"
    fi
    emit_kv DISPATCH_OK "$_generic_dispatch_ok"
    emit_kv FALLBACK_COUNT 0
    emit_kv COMBINED_FALLBACK_COUNT 0
    emit_kv STATIC_DISPATCH_OK "$_generic_dispatch_ok"
    emit_kv DYNAMIC_SLOT_COUNT 0
    emit_kv DEGRADED_ROUND "$_generic_degraded"
    emit_kv PANEL_PATHS_FILE "$_panel_paths"
    exit 0
fi

for _archetype in arch edge innovation pragmatic requirements; do
    if [[ "$CURSOR_PRESENT" == "true" ]]; then
        bash "${PLUGIN_ROOT}/skills/design/scripts/render-plan-review-prompt.sh" \
            --archetype "$_archetype" --vendor cursor --plan-file "$PLAN_FILE" --design-tmpdir "$DESIGN_TMPDIR" \
            >"$DESIGN_TMPDIR/render-plan-cursor-${_archetype}.prompt"
    fi
    if [[ "$CODEX_PRESENT" == "true" ]]; then
        bash "${PLUGIN_ROOT}/skills/design/scripts/render-plan-review-prompt.sh" \
            --archetype "$_archetype" --vendor codex --plan-file "$PLAN_FILE" --design-tmpdir "$DESIGN_TMPDIR" \
            >"$DESIGN_TMPDIR/render-plan-codex-${_archetype}.prompt"
    fi
done

for _archetype in arch edge innovation pragmatic requirements; do
    if [[ "$CURSOR_PRESENT" == "true" ]]; then
        jq -nc \
            --arg slot "cursor-plan-${_archetype}" \
            --arg tool cursor \
            --arg output "$DESIGN_TMPDIR/cursor-plan-${_archetype}-output.txt" \
            --arg prompt_file "$DESIGN_TMPDIR/render-plan-cursor-${_archetype}.prompt" \
            '{slot:$slot,tool:$tool,output:$output,prompt_file:$prompt_file}' >>"$_manifest"
    fi
    if [[ "$CODEX_PRESENT" == "true" ]]; then
        jq -nc \
            --arg slot "codex-plan-${_archetype}" \
            --arg tool codex \
            --arg output "$DESIGN_TMPDIR/codex-primary-plan-${_archetype}-output.txt" \
            --arg prompt_file "$DESIGN_TMPDIR/render-plan-codex-${_archetype}.prompt" \
            '{slot:$slot,tool:$tool,output:$output,prompt_file:$prompt_file}' >>"$_manifest"
    fi
done

if [[ -s "$_scout_manifest" ]] && jq -e '.archetypes | type == "array"' "$_scout_manifest" >/dev/null 2>&1; then
    while IFS= read -r row || [[ -n "$row" ]]; do
        [[ -n "$row" ]] || continue
        _slug=$(printf '%s' "$row" | jq -r '.name // empty')
        [[ -n "$_slug" ]] || continue
        _body_tmp=$(mktemp "${DESIGN_TMPDIR}/dyn-body.XXXXXX")
        printf '%s' "$row" | jq -r '.prompt_body // empty' >"$_body_tmp"
        if [[ "$CURSOR_PRESENT" == "true" ]]; then
            write_dynamic_prompt "$_slug" "$PLAN_FILE" "$_body_tmp" "$DESIGN_TMPDIR/render-plan-cursor-dyn-${_slug}.prompt"
        fi
        if [[ "$CODEX_PRESENT" == "true" ]]; then
            write_dynamic_prompt "$_slug" "$PLAN_FILE" "$_body_tmp" "$DESIGN_TMPDIR/render-plan-codex-dyn-${_slug}.prompt"
        fi
        rm -f "$_body_tmp"
        if [[ "$CURSOR_PRESENT" == "true" ]]; then
            jq -nc \
                --arg slot "dyn-cursor-plan-${_slug}" \
                --arg tool cursor \
                --arg output "$DESIGN_TMPDIR/cursor-plan-dyn-${_slug}-output.txt" \
                --arg prompt_file "$DESIGN_TMPDIR/render-plan-cursor-dyn-${_slug}.prompt" \
                '{slot:$slot,tool:$tool,output:$output,prompt_file:$prompt_file}' >>"$_manifest"
        fi
        if [[ "$CODEX_PRESENT" == "true" ]]; then
            jq -nc \
                --arg slot "dyn-codex-plan-${_slug}" \
                --arg tool codex \
                --arg output "$DESIGN_TMPDIR/codex-primary-plan-dyn-${_slug}-output.txt" \
                --arg prompt_file "$DESIGN_TMPDIR/render-plan-codex-dyn-${_slug}.prompt" \
                '{slot:$slot,tool:$tool,output:$output,prompt_file:$prompt_file}' >>"$_manifest"
        fi
    done < <(jq -c '.archetypes[]?' "$_scout_manifest")
fi

slot_count=0
while IFS= read -r _row || [[ -n "$_row" ]]; do
    [[ -n "$_row" ]] || continue
    slot_count=$((slot_count + 1))
done <"$_manifest"

_dispatch_out=$("$DISPATCH_WATERFALL_SH" \
    --slots-file "$_manifest" \
    --codex-present "$CODEX_PRESENT" \
    --cursor-present "$CURSOR_PRESENT" \
    --mode description \
    --plan-file "$PLAN_FILE" \
    --no-fallback \
    --require-first-line-pattern '^[[:space:]]*(schema_version|\{"no_issues_found)' \
    --timeout "$TIMEOUT" \
    "${waterfall_extra[@]+"${waterfall_extra[@]}"}")

DISPATCH_OK=""
FALLBACK_COUNT=""
COMBINED_FALLBACK_COUNT=""
STATIC_DISPATCH_OK=""
ALL_OUTPUT_FILES_PATH=""
ALL_SLOTS_DROPPED=""

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
        ALL_SLOTS_DROPPED) ALL_SLOTS_DROPPED="$_value" ;;
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
case "$COMBINED_FALLBACK_COUNT" in ''|*[!0-9]*) COMBINED_FALLBACK_COUNT="$FALLBACK_COUNT" ;; esac
DEGRADED_ROUND=false
[[ "${STATIC_DISPATCH_OK:-true}" == "false" ]] && DEGRADED_ROUND=true
if (( 10#$COMBINED_FALLBACK_COUNT > floor_half )); then
    DEGRADED_ROUND=true
fi
_paths_sidecar="${ALL_OUTPUT_FILES_PATH:-${_manifest}.output-files}"
_succeeded_paths=0
if [[ -f "$_paths_sidecar" ]]; then
    while IFS= read -r _pp || [[ -n "$_pp" ]]; do
        [[ -n "$_pp" ]] && _succeeded_paths=$((_succeeded_paths + 1))
    done <"$_paths_sidecar"
fi
if (( slot_count > 0 && _succeeded_paths < slot_count )); then
    DEGRADED_ROUND=true
fi
[[ "$ALL_SLOTS_DROPPED" == "true" ]] && DEGRADED_ROUND=true

printf '%s\n' "$_dispatch_out"
emit_kv DYNAMIC_SLOT_COUNT "$dyn_slots"
emit_kv DEGRADED_ROUND "$DEGRADED_ROUND"
emit_kv PANEL_PATHS_FILE "${ALL_OUTPUT_FILES_PATH:-${_manifest}.output-files}"
exit 0
