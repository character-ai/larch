#!/usr/bin/env bash
# dispatch-plan-voters.sh - Launch /design plan-review voters through waterfall fallback.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init

usage() {
    larch_err "Usage: dispatch-plan-voters.sh --ballot-file FILE --design-tmpdir DIR --codex-available true|false --cursor-available true|false [--session-env-path FILE]"
}

BALLOT_FILE=""
DESIGN_TMPDIR=""
CODEX_AVAILABLE=""
CURSOR_AVAILABLE=""
SESSION_ENV_PATH="${SESSION_ENV_PATH:-}"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --ballot-file) BALLOT_FILE="${2:?--ballot-file requires a value}"; shift 2 ;;
        --design-tmpdir) DESIGN_TMPDIR="${2:?--design-tmpdir requires a value}"; shift 2 ;;
        --codex-available) CODEX_AVAILABLE="${2:?--codex-available requires a value}"; shift 2 ;;
        --cursor-available) CURSOR_AVAILABLE="${2:?--cursor-available requires a value}"; shift 2 ;;
        --session-env-path) SESSION_ENV_PATH="${2:?--session-env-path requires a value}"; shift 2 ;;
        --help) usage; exit 0 ;;
        *) larch_err "dispatch-plan-voters.sh: unknown option: $1"; usage; exit 2 ;;
    esac
done

[[ -n "$BALLOT_FILE" && -f "$BALLOT_FILE" ]] || { larch_err "dispatch-plan-voters.sh: --ballot-file must name a file"; exit 2; }
[[ -n "$DESIGN_TMPDIR" ]] || { larch_err "dispatch-plan-voters.sh: --design-tmpdir is required"; exit 2; }
[[ "$CODEX_AVAILABLE" == "true" || "$CODEX_AVAILABLE" == "false" ]] || { larch_err "dispatch-plan-voters.sh: --codex-available must be true or false"; exit 2; }
[[ "$CURSOR_AVAILABLE" == "true" || "$CURSOR_AVAILABLE" == "false" ]] || { larch_err "dispatch-plan-voters.sh: --cursor-available must be true or false"; exit 2; }
mkdir -p "$DESIGN_TMPDIR"

PLAN_VOTER_PARSE_RATE_RETRY_PREFIX='IMPORTANT: Your previous attempt produced narrative output instead of structured votes. Each line MUST start with the same ballot ID from the ballot (FINDING_N: or OOS_N:) followed by exactly one of YES, NO, or EXONERATE. Do not output any prose, reasoning, or status updates before, between, or after the vote lines. If you need to verify claims, do so silently. Output ONLY vote lines.'

make_prompt_file() {
    local tool="$1"
    local prompt_file="$DESIGN_TMPDIR/${tool}-plan-voter-prompt.txt"
    local plan_voter_yes_exonerate_framing
    plan_voter_yes_exonerate_framing='The YES ↔ EXONERATE boundary requires careful judgment. Both votes accept that the finding is correct and the concern is real. The difference is whether the proposed plan revision is worth shipping in THIS PR:

- Vote YES when: the finding is correct AND the proposed plan revision (or any equivalent revision the implementer would write) materially improves the plan'\''s clarity, completeness, or correctness, AND the revision'\''s complexity is proportionate to the issue'\''s severity. A YES vote is a commitment to revise the plan.

- Vote EXONERATE when: the finding is correct AND the concern is real, BUT one of:
  - The proposed plan revision adds disproportionate complexity for the issue'\''s severity (e.g., a 5-line clarification fix for a 1-line nit; a new mechanism for a one-off edge case).
  - The finding is correct but the plan would already address it implicitly (e.g., reviewer says "missing X" but X is covered by an obvious extension of an already-named contract).
  - The finding is correct but better addressed in a follow-up PR (out-of-PR scope creep).
  - The concern is forward-looking / speculative; valid but not pressing for this PR'\''s correctness.

When in doubt between YES and EXONERATE, prefer EXONERATE. A YES vote should feel like "yes, the plan WILL be worse without this revision." An EXONERATE vote feels like "yes, this is a real concern, but I would not insist on it during a senior code review."

(The YES ↔ NO and NO ↔ EXONERATE boundaries are unchanged: NO means the finding is wrong / a false positive / based on a misreading.)'
    {
        printf 'You are a senior engineer on a voting panel deciding which proposed plan modifications should be accepted.\n'
        printf '%s\n' "$plan_voter_yes_exonerate_framing"
        printf 'Do NOT modify files. Do NOT commit. Do NOT push.\n'
        printf 'Read the ballot from this path: %s\n' "$BALLOT_FILE"
        printf '\nFor each ballot item output exactly one line using the same ID from the ballot:\n'
        printf '  FINDING_N: YES\n'
        printf '  FINDING_N: NO -- one-line reason\n'
        printf '  FINDING_N: EXONERATE -- one-line reason\n'
        printf '  OOS_N: YES\n'
        printf '  OOS_N: NO -- one-line reason\n'
        printf '  OOS_N: EXONERATE -- one-line reason\n'
        printf 'For OOS_N items: YES means file a GitHub issue; NO or EXONERATE means skip.\n'
        printf '\n**Verify silently** — do not produce narrative output, reasoning explanations, or status updates before, between, or after the vote lines. You may read the ballot file and silently inspect the plan or referenced repo files for verification, but do not invoke planning/status tools.\n'
        printf 'You must vote on every item. Do NOT skip any.\n'
        printf '**Output ONLY vote lines.** Lines that do not start with the exact ballot ID from the ballot heading (FINDING_N: or OOS_N:) followed by YES, NO, or EXONERATE are silently ignored.\n'
    } > "$prompt_file"
    printf '%s' "$prompt_file"
}

make_plan_voter_retry_prompt_file() {
    local tool="$1"
    local src_prompt_file="$2"
    local retry_prompt_file="$DESIGN_TMPDIR/${tool}-plan-voter-prompt-retry.txt"
    {
        printf '%s\n\n' "$PLAN_VOTER_PARSE_RATE_RETRY_PREFIX"
        cat "$src_prompt_file"
    } > "$retry_prompt_file"
    printf '%s' "$retry_prompt_file"
}

check_plan_voter_substantive() {
    local voter_path="$1"
    [[ -s "$voter_path" ]] || { printf 'OK\n'; return 0; }
    local vote_count
    vote_count=$(grep -cE '^(FINDING|OOS)_[0-9]+:[[:space:]]*(YES|NO|EXONERATE)([[:space:]-]|$)' "$voter_path" 2>/dev/null || true)
    if [[ "${vote_count:-0}" -gt 0 ]]; then
        printf 'OK\n'
    else
        printf 'NOT_SUBSTANTIVE\n'
    fi
}

manifest="$DESIGN_TMPDIR/plan-voter-slots.ndjson"
codex_prompt=$(make_prompt_file codex)
cursor_prompt=$(make_prompt_file cursor)
VOTER_2_PATH="$DESIGN_TMPDIR/codex-vote-output.txt"
VOTER_3_PATH="$DESIGN_TMPDIR/cursor-vote-output.txt"
{
    printf '{"slot":"voter-2","tool":"codex","output":"%s","prompt_file":"%s"}\n' "$VOTER_2_PATH" "$codex_prompt"
    printf '{"slot":"voter-3","tool":"cursor","output":"%s","prompt_file":"%s"}\n' "$VOTER_3_PATH" "$cursor_prompt"
} > "$manifest"

waterfall_output=$("$PLUGIN_ROOT/scripts/dispatch-with-waterfall.sh" \
    --slots-file "$manifest" \
    --codex-present "$CODEX_AVAILABLE" \
    --cursor-present "$CURSOR_AVAILABLE" \
    --mode description \
    --timeout 1200)

all_outputs=""
all_tools=""
dispatch_ok="true"
while IFS= read -r line || [[ -n "$line" ]]; do
    key="${line%%=*}"
    value="${line#*=}"
    case "$key" in
        ALL_OUTPUT_FILES) all_outputs="$value" ;;
        ALL_OUTPUT_TOOLS) all_tools="$value" ;;
        DISPATCH_OK) dispatch_ok="$value" ;;
        WARN) emit_kv WARN "$value" ;;
    esac
done <<< "$waterfall_output"

read -r -a outputs_arr <<< "$all_outputs"
read -r -a tools_arr <<< "$all_tools"

VOTER_2_PATH="${outputs_arr[0]:-}"
VOTER_3_PATH="${outputs_arr[1]:-}"
VOTER_2_TOOL="${tools_arr[0]:-codex}"
VOTER_3_TOOL="${tools_arr[1]:-cursor}"
VOTER_2_STATUS="launched"
VOTER_3_STATUS="launched"
[[ "$VOTER_2_TOOL" == "claude" ]] && VOTER_2_STATUS="fallback"
[[ "$VOTER_3_TOOL" == "claude" ]] && VOTER_3_STATUS="fallback"
[[ -s "$VOTER_2_PATH" ]] || VOTER_2_STATUS="failed"
[[ -s "$VOTER_3_PATH" ]] || VOTER_3_STATUS="failed"

# Parse-rate retry: if a voter produced output but no valid vote lines, retry once
# with the preamble-prepended prompt via a single-slot waterfall re-dispatch.
retry_voter() {
    local slot_num="$1" voter_path_var="$2" voter_tool="$3" orig_prompt="$4"
    local voter_path="${!voter_path_var}"
    [[ -s "$voter_path" ]] || return 0
    local rate_status
    rate_status=$(check_plan_voter_substantive "$voter_path")
    [[ "$rate_status" == "NOT_SUBSTANTIVE" ]] || return 0

    local first_pass_sidecar retry_output retry_prompt retry_manifest
    case "$voter_path" in
        *.txt) first_pass_sidecar="${voter_path%.txt}-first-pass.txt"
               retry_output="${voter_path%.txt}-parse-retry.txt" ;;
        *)     first_pass_sidecar="${voter_path}-first-pass"
               retry_output="${voter_path}-parse-retry" ;;
    esac
    retry_prompt=$(make_plan_voter_retry_prompt_file "$voter_tool" "$orig_prompt")
    if [[ "$voter_tool" == "claude" ]]; then
        if ! "$PLUGIN_ROOT/scripts/launch-claude-review.sh" \
            --output "$retry_output" \
            --prompt-file "$retry_prompt" \
            --mode description \
            --role voter \
            --timeout 1200 >/dev/null 2>&1; then
            emit_kv WARN "plan-voter retry failed for slot $slot_num via claude"
            return 0
        fi
    else
        local retry_waterfall_output retry_all_outputs retry_dispatch_ok
        local retry_key retry_value retry_actual_output
        retry_manifest="$DESIGN_TMPDIR/plan-voter-retry-slot${slot_num}.ndjson"
        printf '{"slot":"voter-%s-retry","tool":"%s","output":"%s","prompt_file":"%s"}\n' \
            "$slot_num" "$voter_tool" "$retry_output" "$retry_prompt" > "$retry_manifest"
        if ! retry_waterfall_output=$("$PLUGIN_ROOT/scripts/dispatch-with-waterfall.sh" \
            --slots-file "$retry_manifest" \
            --codex-present "$CODEX_AVAILABLE" \
            --cursor-present "$CURSOR_AVAILABLE" \
            --mode description \
            --timeout 1200 2>/dev/null); then
            emit_kv WARN "plan-voter retry failed for slot $slot_num via $voter_tool"
            return 0
        fi
        retry_all_outputs=""
        retry_dispatch_ok="true"
        while IFS= read -r line || [[ -n "$line" ]]; do
            retry_key="${line%%=*}"
            retry_value="${line#*=}"
            case "$retry_key" in
                ALL_OUTPUT_FILES) retry_all_outputs="$retry_value" ;;
                DISPATCH_OK) retry_dispatch_ok="$retry_value" ;;
                WARN) emit_kv WARN "$retry_value" ;;
            esac
        done <<< "$retry_waterfall_output"
        read -r -a retry_outputs_arr <<< "$retry_all_outputs"
        retry_actual_output="${retry_outputs_arr[0]:-$retry_output}"
        retry_output="$retry_actual_output"
        if [[ "$retry_dispatch_ok" != "true" && ! -s "$retry_output" ]]; then
            emit_kv WARN "plan-voter retry produced no usable waterfall output for slot $slot_num"
            return 0
        fi
    fi
    if [[ ! -s "$retry_output" ]]; then
        emit_kv WARN "plan-voter retry produced no output for slot $slot_num"
        return 0
    fi
    if [[ -s "$retry_output" ]]; then
        local retry_rate_status
        retry_rate_status=$(check_plan_voter_substantive "$retry_output")
        if [[ "$retry_rate_status" == "OK" ]]; then
            cp "$voter_path" "$first_pass_sidecar" 2>/dev/null || true
            mv "$retry_output" "$voter_path"
        fi
    fi
}
retry_voter 2 VOTER_2_PATH "$VOTER_2_TOOL" "$codex_prompt"
retry_voter 3 VOTER_3_PATH "$VOTER_3_TOOL" "$cursor_prompt"

if [[ "$VOTER_2_STATUS" != "failed" ]]; then
    voter_2_rate_status=$(check_plan_voter_substantive "$VOTER_2_PATH")
    if [[ "$voter_2_rate_status" == "NOT_SUBSTANTIVE" ]]; then
        emit_kv WARN "plan-voter slot 2 remained narrative-only after retry; excluding from external judge count"
        VOTER_2_STATUS="failed"
    fi
fi
if [[ "$VOTER_3_STATUS" != "failed" ]]; then
    voter_3_rate_status=$(check_plan_voter_substantive "$VOTER_3_PATH")
    if [[ "$voter_3_rate_status" == "NOT_SUBSTANTIVE" ]]; then
        emit_kv WARN "plan-voter slot 3 remained narrative-only after retry; excluding from external judge count"
        VOTER_3_STATUS="failed"
    fi
fi

external_judges=0
[[ "$VOTER_2_STATUS" != "failed" && -s "$VOTER_2_PATH" ]] && external_judges=$((external_judges + 1))
[[ "$VOTER_3_STATUS" != "failed" && -s "$VOTER_3_PATH" ]] && external_judges=$((external_judges + 1))
if (( external_judges < 2 )); then
    _warn_msg="**⚠ Plan-review external voter degradation: ${external_judges}/2 voter slots produced substantive vote output. Voter 1 (Claude) must compensate.**"
    larch_err "$_warn_msg"
    emit_kv DEGRADED_PANEL_WARNING "$_warn_msg"
fi

plan_voter_paths_file="$DESIGN_TMPDIR/plan-voter-paths.txt"
pv_tmp=$(mktemp "${DESIGN_TMPDIR}/.plan-voter-paths.XXXXXX")
if [[ "$VOTER_2_STATUS" != "failed" && -n "$VOTER_2_PATH" ]]; then
    printf '%s\n' "$VOTER_2_PATH" >> "$pv_tmp"
fi
if [[ "$VOTER_3_STATUS" != "failed" && -n "$VOTER_3_PATH" ]]; then
    printf '%s\n' "$VOTER_3_PATH" >> "$pv_tmp"
fi
mv -f "$pv_tmp" "$plan_voter_paths_file"

emit_kv VOTER_2_PATH "$VOTER_2_PATH"
emit_kv VOTER_3_PATH "$VOTER_3_PATH"
[[ -s "$plan_voter_paths_file" ]] && emit_kv VOTER_PATHS_FILE "$plan_voter_paths_file"
emit_kv VOTER_2_TOOL "$VOTER_2_TOOL"
emit_kv VOTER_3_TOOL "$VOTER_3_TOOL"
emit_kv VOTER_2_STATUS "$VOTER_2_STATUS"
emit_kv VOTER_3_STATUS "$VOTER_3_STATUS"
emit_kv DISPATCH_OK "$dispatch_ok"
