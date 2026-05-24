#!/usr/bin/env bash
# Shared helpers for voter parse-rate diagnostics and substantive vote-line checks.
# Sourced from dispatch-code-voters.sh and dispatch-plan-voters.sh.

# Directory containing launch-claude-review.sh / launch-review.sh (repo scripts/).
# shellcheck disable=SC2034
SCRIPT_DIR_VPR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"

# Retry preambles (code-review vs plan-review ballots).
VOTER_PARSE_RATE_RETRY_PREFIX_CODE='IMPORTANT: Your previous attempt produced narrative output instead of structured votes. Each line MUST start with FINDING_N: followed by exactly one of YES, NO, or EXONERATE. Do not output any prose, reasoning, or status updates before, between, or after the vote lines. If you need to verify claims, do so silently. Output ONLY vote lines.'

VOTER_PARSE_RATE_RETRY_PREFIX_PLAN='IMPORTANT: Your previous attempt produced narrative output instead of structured votes. Each line MUST start with the same ballot ID from the ballot (FINDING_N: or OOS_N:) followed by exactly one of YES, NO, or EXONERATE. Do not output any prose, reasoning, or status updates before, between, or after the vote lines. If you need to verify claims, do so silently. Output ONLY vote lines.'

voter_parse_rate_diag_path() {
    local voter_path="$1"
    case "$voter_path" in
        *.txt) printf '%s\n' "${voter_path%.txt}-parse-rate-diag.txt" ;;
        *) printf '%s-parse-rate-diag.txt\n' "$voter_path" ;;
    esac
}

voter_output_sha256() {
    local voter_path="$1"
    [[ -f "$voter_path" ]] || return 1
    shasum -a 256 "$voter_path" | awk '{print $1}'
}

voter_parse_rate_diag_matches_output() {
    local diag_file="$1" voter_path="$2" recorded_path recorded_sha actual_sha
    [[ -f "$diag_file" && -f "$voter_path" ]] || return 1

    recorded_path=$(
        awk 'index($0, "voter_file=") == 1 { print substr($0, 12); exit }' "$diag_file"
    )
    recorded_sha=$(
        awk 'index($0, "voter_sha256=") == 1 { print substr($0, 14); exit }' "$diag_file"
    )
    [[ -n "$recorded_path" && -n "$recorded_sha" ]] || return 1

    actual_sha="$(voter_output_sha256 "$voter_path")" || return 1
    [[ "$recorded_path" == "$voter_path" && "$recorded_sha" == "$actual_sha" ]]
}

parse_rate_check_tool_label() {
    local voter_tool="$1"
    case "$voter_tool" in
        claude) printf 'launch-claude-review.sh (voter parse-rate check)\n' ;;
        codex|cursor) printf 'launch-review.sh --tool %s (voter parse-rate check)\n' "$voter_tool" ;;
        *) printf 'voter parse-rate check (%s)\n' "$voter_tool" ;;
    esac
}

is_harness_review_path() {
    local path="$1"
    case "$path" in
        */test-dispatch-code-voters.*|\
        */test-dispatch-plan-voters.*|\
        */test-plan-review-loop.*|\
        */test-collect-*|\
        */test-check-*|\
        */test-tally-*)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

should_suppress_parse_rate_issue_append() {
    local voter_path="$1" base_tmp="${2:?}"
    [[ "$voter_path" == "$base_tmp"/* ]] || return 1
    is_harness_review_path "$base_tmp" || is_harness_review_path "$voter_path"
}

# Globals (callers set before invoking substantive checks):
#   LARCH_VPR_BALLOT_FILE — path to ballot markdown
#   LARCH_VPR_ID_GRAMMAR — finding-only | finding-oos
#   LARCH_VPR_REVIEW_TMPDIR — session tmpdir for diagnostics / retry prompts
#   LARCH_VPR_PLUGIN_ROOT — plugin root for append-tool-failure.sh
# Optional:
#   SESSION_ENV_PATH, IMPLEMENT_TMPDIR — execution-issues log resolution

check_voter_parse_rate() {
    local voter_path="$1" voter_tool="$2" slot_num="${3:-}" log_mode="${4:-log}"
    local ballot_file="${LARCH_VPR_BALLOT_FILE:?LARCH_VPR_BALLOT_FILE must be set}"
    local id_grammar="${LARCH_VPR_ID_GRAMMAR:-finding-only}"
    local base_tmp="${LARCH_VPR_REVIEW_TMPDIR:?LARCH_VPR_REVIEW_TMPDIR must be set}"
    local plugin_root="${LARCH_VPR_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-}}"
    local diag_file
    diag_file="$(voter_parse_rate_diag_path "$voter_path")"
    [[ -s "$voter_path" ]] || { printf 'PARSE_RATE_STATUS=OK\n'; return 0; }
    local ids_count judge_error_count
    if [[ "$id_grammar" == "finding-oos" ]]; then
        ids_count=$(grep -cE '^### (FINDING_[0-9]+|OOS_[0-9]+):' "$ballot_file" 2>/dev/null || true)
    else
        ids_count=$(grep -cE '^### (FINDING_[0-9]+):' "$ballot_file" 2>/dev/null || true)
    fi
    ids_count="${ids_count:-0}"
    [[ "$ids_count" -gt 0 ]] || { printf 'PARSE_RATE_STATUS=OK\n'; return 0; }
    judge_error_count=0
    local id_line one
    while IFS= read -r id_line || [[ -n "$id_line" ]]; do
        [[ -z "$id_line" ]] && continue
        one=$(
            awk -v id="$id_line" '
              BEGIN { result="JUDGE_ERROR" }
              {
                upper=toupper($0)
                prefix="^" toupper(id) ":[[:space:]]*"
                if (upper ~ (prefix "(YES|NO|EXONERATE)([[:space:]-]|$)")) {
                    rest=upper; sub(prefix, "", rest)
                    if (rest ~ /^YES([[:space:]-]|$)/) result="YES"
                    else if (rest ~ /^NO([[:space:]-]|$)/) result="NO"
                    else if (rest ~ /^EXONERATE([[:space:]-]|$)/) result="EXONERATE"
                }
              }
              END { print result }
            ' "$voter_path"
        )
        [[ "$one" == "JUDGE_ERROR" ]] && judge_error_count=$((judge_error_count + 1))
    done < <(
        if [[ "$id_grammar" == "finding-oos" ]]; then
            grep -oE '^### (FINDING|OOS)_[0-9]+:' "$ballot_file" 2>/dev/null || true
        else
            grep -oE '^### FINDING_[0-9]+:' "$ballot_file" 2>/dev/null || true
        fi | awk '{ sub(/^### /, "", $0); sub(/:$/, "", $0); print }'
    )
    # >=80% JUDGE_ERROR threshold
    if awk -v n="$judge_error_count" -v t="$ids_count" 'BEGIN { exit (n / t >= 0.8) ? 0 : 1 }'; then
        {
            [[ -n "$slot_num" ]] && printf 'slot=%s\n' "$slot_num"
            printf 'voter_tool=%s\n' "$voter_tool"
            printf 'judge_error_count=%s\n' "$judge_error_count"
            printf 'total_findings=%s\n' "$ids_count"
            printf 'voter_file=%s\n' "$voter_path"
            printf 'voter_sha256=%s\n' "$(voter_output_sha256 "$voter_path")"
            printf -- '--- first 200 bytes of voter output ---\n'
            head -c 200 "$voter_path" 2>/dev/null || true
            printf '\n'
        } > "$diag_file" || true
        if [[ "$log_mode" == "log" ]]; then
            larch_err "**⚠ Voter ${voter_tool}: ${judge_error_count}/${ids_count} findings returned JUDGE_ERROR — voter likely produced prose without FINDING_N: VOTE lines. Check voter output at ${voter_path}.**"
            _issues_log="${LARCH_EXECUTION_ISSUES_LOG:-}"
            [[ -z "$_issues_log" && -n "${SESSION_ENV_PATH:-}" ]] && _issues_log="$(dirname "$SESSION_ENV_PATH")/execution-issues.md"
            [[ -z "$_issues_log" && -n "${IMPLEMENT_TMPDIR:-}" ]] && _issues_log="$IMPLEMENT_TMPDIR/execution-issues.md"
            [[ -z "$_issues_log" ]] && _issues_log="$base_tmp/execution-issues.md"
            _parse_site="${LARCH_VPR_DISPATCH_LABEL:-dispatch-code-voters.sh} ${voter_tool}"
            if ! should_suppress_parse_rate_issue_append "$voter_path" "$base_tmp" && [[ -x "$plugin_root/scripts/append-tool-failure.sh" ]]; then
                "$plugin_root/scripts/append-tool-failure.sh" \
                    --log "$_issues_log" \
                    --site "$_parse_site" \
                    --tool "$(parse_rate_check_tool_label "$voter_tool")" \
                    --exit-code 0 \
                    --status-label "warning" \
                    --category Warnings \
                    --output-file "$diag_file" \
                    --redact >/dev/null 2>&1 || true
            fi
            unset _issues_log _parse_site
        fi
        printf 'PARSE_RATE_STATUS=NOT_SUBSTANTIVE\n'
    else
        rm -f "$diag_file"
        printf 'PARSE_RATE_STATUS=OK\n'
    fi
}

parse_rate_status_from_output() {
    awk -F= '$1=="PARSE_RATE_STATUS" { print $2; found=1 } END { if (!found) print "OK" }'
}

make_voter_retry_prompt_file() {
    local label="$1"
    local src_prompt_file="$2"
    local review_tmpdir="${LARCH_VPR_REVIEW_TMPDIR:?}"
    local kind="${LARCH_VPR_RETRY_PREFIX_KIND:-code}"
    local prefix retry_prompt_file
    case "$kind" in
        plan) prefix="$VOTER_PARSE_RATE_RETRY_PREFIX_PLAN" ;;
        *) prefix="$VOTER_PARSE_RATE_RETRY_PREFIX_CODE" ;;
    esac
    retry_prompt_file="$review_tmpdir/${label}-vote-prompt-retry.txt"
    {
        printf '%s\n\n' "$prefix"
        cat "$src_prompt_file"
    } > "$retry_prompt_file"
    printf '%s' "$retry_prompt_file"
}

launch_voter_retry() {
    local voter_tool="$1" retry_output="$2" retry_prompt="$3" timing_task="$4"
    local mode="${LARCH_VPR_LAUNCH_MODE:-description}"
    set +e
    case "$voter_tool" in
        claude)
            "$SCRIPT_DIR_VPR/launch-claude-review.sh" \
                --output "$retry_output" \
                --prompt-file "$retry_prompt" \
                --mode "$mode" \
                --role voter \
                --timeout 1200 \
                --timing-task-kind "$timing_task" \
                "${LARCH_VPR_CTX[@]+"${LARCH_VPR_CTX[@]}"}" >/dev/null 2> "${retry_output}.launcher-stderr"
            ;;
        codex|cursor)
            "$SCRIPT_DIR_VPR/launch-review.sh" \
                --tool "$voter_tool" \
                --output "$retry_output" \
                --prompt-file "$retry_prompt" \
                --mode "$mode" \
                --timeout 1200 \
                --timing-task-kind "$timing_task" \
                "${LARCH_VPR_CTX[@]+"${LARCH_VPR_CTX[@]}"}" >/dev/null 2> "${retry_output}.launcher-stderr"
            ;;
        *)
            larch_err "launch_voter_retry: unknown voter retry tool: $voter_tool"
            return 2
            ;;
    esac
    local rc=$?
    set -e
    [[ -f "${retry_output}.done" ]] || printf '%s\n' "$rc" > "${retry_output}.done"
    return "$rc"
}

check_and_retry_voter_parse_rate() {
    local slot_num="$1" voter_path="$2" voter_tool="$3" prompt_file="$4"
    local status retry_prompt retry_output retry_rc retry_status diag_file retry_diag_file first_pass_sidecar
    diag_file="$(voter_parse_rate_diag_path "$voter_path")"
    case "$voter_path" in
        *.txt) first_pass_sidecar="${voter_path%.txt}-first-pass.txt" ;;
        *) first_pass_sidecar="${voter_path}-first-pass" ;;
    esac
    status=$(check_voter_parse_rate "$voter_path" "$voter_tool" "$slot_num" silent | parse_rate_status_from_output)
    [[ "$status" == "NOT_SUBSTANTIVE" ]] || { printf '%s\n' "$status"; return 0; }

    retry_prompt=$(make_voter_retry_prompt_file "$voter_tool" "$prompt_file")
    case "$voter_path" in
        *.txt) retry_output="${voter_path%.txt}-parse-retry.txt" ;;
        *) retry_output="${voter_path}-parse-retry" ;;
    esac
    retry_diag_file="$(voter_parse_rate_diag_path "$retry_output")"
    rm -f "$retry_output" "${retry_output}.done" "${retry_output}.launcher-stderr"

    set +e
    launch_voter_retry "$voter_tool" "$retry_output" "$retry_prompt" "${voter_tool}-voter-${slot_num}-parse-retry"
    retry_rc=$?
    set -e
    if [[ "$retry_rc" -eq 0 && -s "$retry_output" ]]; then
        retry_status=$(check_voter_parse_rate "$retry_output" "$voter_tool" "$slot_num" silent | parse_rate_status_from_output)
        if [[ "$retry_status" == "OK" ]]; then
            rm -f "$first_pass_sidecar" || true
            if cp "$voter_path" "$first_pass_sidecar" 2>/dev/null; then
                { emit_breadcrumb "voter-${voter_tool}: first-pass content preserved at $(basename "$first_pass_sidecar") (parse-rate retry succeeded)"; } >&2
            else
                larch_err "check_and_retry_voter_parse_rate: warning: failed to preserve first-pass voter output at $first_pass_sidecar after parse-rate retry succeeded"
            fi
            mv "$retry_output" "$voter_path"
            if [[ -f "${retry_output}.done" ]]; then
                mv "${retry_output}.done" "${voter_path}.done"
            else
                printf '0\n' > "${voter_path}.done"
            fi
            rm -f "$diag_file" "$retry_diag_file" "${retry_output}.launcher-stderr"
            printf 'OK\n'
            return 0
        fi
    fi

    rm -f "$retry_output" "${retry_output}.done" "${retry_output}.launcher-stderr" "$retry_diag_file"
    check_voter_parse_rate "$voter_path" "$voter_tool" "$slot_num" log | parse_rate_status_from_output
}
