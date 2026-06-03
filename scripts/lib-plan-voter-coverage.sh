#!/usr/bin/env bash
# Plan-review-specific helpers for voter coverage accounting and status KV emission.
# The interleaved KV order in plan_voter_coverage_emit_status_block is a binding
# contract for plan-review stdout parsers; do not reuse from code-review dispatch.

# shellcheck source=scripts/lib-quiet.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/lib-quiet.sh"

plan_voter_coverage_compute_effective_judges() {
    local effective_judges=0
    local slot_record status path parse_rate_status

    if [[ $# -gt 0 ]]; then
        for slot_record in "$@"; do
            IFS=$'\t' read -r status path parse_rate_status <<< "$slot_record"
            [[ "$status" != "failed" && "$parse_rate_status" != "NOT_SUBSTANTIVE" && -s "$path" ]] && effective_judges=$((effective_judges + 1))
        done
    else
        while IFS= read -r slot_record || [[ -n "$slot_record" ]]; do
            IFS=$'\t' read -r status path parse_rate_status <<< "$slot_record"
            [[ "$status" != "failed" && "$parse_rate_status" != "NOT_SUBSTANTIVE" && -s "$path" ]] && effective_judges=$((effective_judges + 1))
        done
    fi

    printf '%s\n' "$effective_judges"
}

plan_voter_coverage_emit_degraded_warning_if_needed() {
    local effective_judges="${1:?effective_judges is required}"
    local expected_judges="${2:?expected_judges is required}"
    # Optional single-line cause note appended to the banner so a usage-limit /
    # quota degradation is not silently attributed to a generic failure (#3378).
    local reason_note="${3:-}"
    local warn_msg

    if (( effective_judges < expected_judges )); then
        warn_msg="**⚠ Degraded plan-review panel: ${effective_judges}/${expected_judges} effective judges produced substantive vote output.**"
        [[ -n "$reason_note" ]] && warn_msg="${warn_msg} ${reason_note}"
        larch_err "$warn_msg"
        emit_kv DEGRADED_PANEL_WARNING "$warn_msg"
    fi
}

plan_voter_coverage_emit_status_block() {
    local voter_1_path="${1:?voter_1_path is required}"
    local voter_1_tool="${2:?voter_1_tool is required}"
    local voter_1_status="${3:?voter_1_status is required}"
    local voter_1_parse_rate_status="${4:?voter_1_parse_rate_status is required}"
    local voter_2_path="${5-}"
    local voter_2_tool="${6:?voter_2_tool is required}"
    local voter_2_status="${7:?voter_2_status is required}"
    local voter_2_parse_rate_status="${8:?voter_2_parse_rate_status is required}"
    local voter_3_path="${9-}"
    local voter_3_tool="${10:?voter_3_tool is required}"
    local voter_3_status="${11:?voter_3_status is required}"
    local voter_3_parse_rate_status="${12:?voter_3_parse_rate_status is required}"
    local plan_voter_paths_file="${13:?plan_voter_paths_file is required}"

    emit_kv VOTER_1_PATH "$voter_1_path"
    emit_kv VOTER_1_TOOL "$voter_1_tool"
    emit_kv VOTER_1_STATUS "$voter_1_status"
    emit_kv VOTER_1_PARSE_RATE_STATUS "$voter_1_parse_rate_status"
    emit_kv VOTER_2_PATH "$voter_2_path"
    emit_kv VOTER_3_PATH "$voter_3_path"
    [[ -s "$plan_voter_paths_file" ]] && emit_kv VOTER_PATHS_FILE "$plan_voter_paths_file"
    emit_kv VOTER_2_TOOL "$voter_2_tool"
    emit_kv VOTER_3_TOOL "$voter_3_tool"
    emit_kv VOTER_2_STATUS "$voter_2_status"
    emit_kv VOTER_3_STATUS "$voter_3_status"
    emit_kv VOTER_2_PARSE_RATE_STATUS "$voter_2_parse_rate_status"
    emit_kv VOTER_3_PARSE_RATE_STATUS "$voter_3_parse_rate_status"
}
