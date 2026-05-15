#!/usr/bin/env bash
# review-and-fix.sh — Enumerate accepted findings or run one /implement review round.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init

usage() {
    larch_err "Usage:"
    larch_err "  review-and-fix.sh --findings-file FILE --review-tmpdir DIR [--session-env-path FILE]"
    larch_err "  review-and-fix.sh --implement-tmpdir DIR --mode diff --panel simple|hard --round-num N [context flags]"
}

FINDINGS_FILE=""
REVIEW_TMPDIR=""
SESSION_ENV_PATH=""
CALL_FIXER_SH="${REVIEW_AND_FIX_CALL_FIXER_SH:-$SCRIPT_DIR/call-fixer.sh}"
REVIEW_CORE_SH="${REVIEW_AND_FIX_REVIEW_CORE_SH:-$PLUGIN_ROOT/skills/review/scripts/review-core.sh}"
IMPLEMENT_TMPDIR=""
PANEL=""
MODE=""
DIFF_FILE=""
COMMIT_COUNT="0"
PLAN_FILE=""
FEATURE_FILE=""
RUN_ID=""
ROUND_NUM="1"
CODEX_AVAILABLE="${CODEX_AVAILABLE:-}"
CURSOR_AVAILABLE="${CURSOR_AVAILABLE:-}"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --findings-file) FINDINGS_FILE="${2:?--findings-file requires a value}"; shift 2 ;;
        --review-tmpdir) REVIEW_TMPDIR="${2:?--review-tmpdir requires a value}"; shift 2 ;;
        --session-env-path) SESSION_ENV_PATH="${2:?--session-env-path requires a value}"; shift 2 ;;
        --implement-tmpdir) IMPLEMENT_TMPDIR="${2:?--implement-tmpdir requires a value}"; shift 2 ;;
        --panel) PANEL="${2:?--panel requires a value}"; shift 2 ;;
        --mode) MODE="${2:?--mode requires a value}"; shift 2 ;;
        --diff-file) DIFF_FILE="${2:?--diff-file requires a value}"; shift 2 ;;
        --commit-count) COMMIT_COUNT="${2:?--commit-count requires a value}"; shift 2 ;;
        --plan-file) PLAN_FILE="${2:?--plan-file requires a value}"; shift 2 ;;
        --feature-file) FEATURE_FILE="${2:?--feature-file requires a value}"; shift 2 ;;
        --run-id) RUN_ID="${2:?--run-id requires a value}"; shift 2 ;;
        --round-num) ROUND_NUM="${2:?--round-num requires a value}"; shift 2 ;;
        --codex-available) CODEX_AVAILABLE="${2:?--codex-available requires a value}"; shift 2 ;;
        --cursor-available) CURSOR_AVAILABLE="${2:?--cursor-available requires a value}"; shift 2 ;;
        --help) usage; exit 0 ;;
        *) echo "review-and-fix.sh: unknown option: $1" >&2; usage; exit 2 ;;
    esac
done

kv_get() {
    local file="$1" key="$2"
    awk -F= -v key="$key" '$1 == key { sub(/^[^=]*=/, ""); print; exit }' "$file" 2>/dev/null || true
}

session_get() {
    local key="$1" default_value="${2:-}"
    if [[ -n "$SESSION_ENV_PATH" && -f "$SESSION_ENV_PATH" && -x "$PLUGIN_ROOT/scripts/read-session-env-key.sh" ]]; then
        "$PLUGIN_ROOT/scripts/read-session-env-key.sh" --file "$SESSION_ENV_PATH" --key "$key" --default "$default_value"
    else
        printf '%s\n' "$default_value"
    fi
}

enumerate_findings() {
    [[ -f "$FINDINGS_FILE" ]] || { larch_err "review-and-fix.sh: --findings-file must name a file"; exit 2; }
    [[ -n "$REVIEW_TMPDIR" ]] || { larch_err "review-and-fix.sh: --review-tmpdir is required"; exit 2; }
    mkdir -p "$REVIEW_TMPDIR"
    : "$SESSION_ENV_PATH"

    if [[ ! -s "$FINDINGS_FILE" ]] || ! grep -Eq '^### FINDING_[0-9]+:' "$FINDINGS_FILE"; then
        emit_kv REVIEW_AND_FIX_STATUS no-findings
        emit_kv FIX_COUNT 0
        return 0
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
}

write_summary_json() {
    local output="$1" tmp="$1.tmp.$$"
    local status="$2" core_status="$3" round="$4" accepted="$5" rejected="$6" rounds_completed="$7" approved="$8" round_dir="$9" oos_jsonl="${10}" oos_markdown="${11}"
    jq -n \
        --arg status "$status" \
        --arg core_status "$core_status" \
        --argjson round_num "$round" \
        --argjson rounds_completed "$rounds_completed" \
        --argjson accepted_count "$accepted" \
        --argjson rejected_count "$rejected" \
        --arg approved_fixes_file "$approved" \
        --arg review_round_dir "$round_dir" \
        --arg accumulated_oos_file "$oos_jsonl" \
        --arg accumulated_oos_markdown_file "$oos_markdown" \
        '{
            schema_version: 1,
            status: $status,
            review_core_status: $core_status,
            round_num: $round_num,
            rounds_completed: $rounds_completed,
            accepted_count: $accepted_count,
            rejected_count: $rejected_count,
            approved_fixes_file: $approved_fixes_file,
            review_round_dir: $review_round_dir,
            accumulated_oos_file: $accumulated_oos_file,
            accumulated_oos_markdown_file: $accumulated_oos_markdown_file
        }' > "$tmp"
    mv -f "$tmp" "$output"
}

run_implement_round() {
    [[ "$MODE" == "diff" ]] || { larch_err "review-and-fix.sh: orchestrator mode currently requires --mode diff"; exit 2; }
    [[ "$PANEL" == "simple" || "$PANEL" == "hard" ]] || { larch_err "review-and-fix.sh: --panel must be simple or hard"; exit 2; }
    case "$ROUND_NUM" in ''|*[!0-9]*) larch_err "review-and-fix.sh: --round-num must be a positive integer"; exit 2 ;; esac
    (( 10#$ROUND_NUM > 0 )) || { larch_err "review-and-fix.sh: --round-num must be a positive integer"; exit 2; }
    round_num_dec=$((10#$ROUND_NUM))
    [[ -n "$IMPLEMENT_TMPDIR" && -d "$IMPLEMENT_TMPDIR" && ! -L "$IMPLEMENT_TMPDIR" ]] || { larch_err "review-and-fix.sh: --implement-tmpdir must name a directory"; exit 2; }
    [[ -n "$SESSION_ENV_PATH" ]] || SESSION_ENV_PATH="$IMPLEMENT_TMPDIR/session-env.sh"
    [[ -x "$REVIEW_CORE_SH" ]] || { larch_err "review-and-fix.sh: review-core.sh not executable: $REVIEW_CORE_SH"; exit 2; }
    [[ -x "$CALL_FIXER_SH" ]] || { larch_err "review-and-fix.sh: call-fixer.sh not executable: $CALL_FIXER_SH"; exit 2; }
    command -v jq >/dev/null 2>&1 || { larch_err "review-and-fix.sh: jq is required"; exit 2; }

    if [[ "$CODEX_AVAILABLE" != "true" && "$CODEX_AVAILABLE" != "false" ]]; then
        codex_healthy=$(session_get CODEX_HEALTHY false)
        CODEX_AVAILABLE="$codex_healthy"
    fi
    if [[ "$CURSOR_AVAILABLE" != "true" && "$CURSOR_AVAILABLE" != "false" ]]; then
        cursor_healthy=$(session_get CURSOR_HEALTHY false)
        CURSOR_AVAILABLE="$cursor_healthy"
    fi

    round_dir="$IMPLEMENT_TMPDIR/round-${round_num_dec}"
    mkdir -p "$round_dir"
    if (( round_num_dec == 1 )) && [[ -x "$PLUGIN_ROOT/scripts/snapshot-untracked.sh" ]]; then
        "$PLUGIN_ROOT/scripts/snapshot-untracked.sh" --output "$IMPLEMENT_TMPDIR/pre-review-untracked.txt"
    fi
    core_out="$round_dir/review-core.env"
    core_args=(
        --mode "$MODE"
        --output-dir "$round_dir"
        --session-env-path "$SESSION_ENV_PATH"
        --codex-available "$CODEX_AVAILABLE"
        --cursor-available "$CURSOR_AVAILABLE"
        --panel "$PANEL"
        --round-num "$round_num_dec"
    )
    [[ -n "$DIFF_FILE" ]] && core_args+=(--diff-file "$DIFF_FILE")
    [[ -n "$COMMIT_COUNT" ]] && core_args+=(--commit-count "$COMMIT_COUNT")
    [[ -n "$PLAN_FILE" ]] && core_args+=(--plan-file "$PLAN_FILE")
    [[ -n "$FEATURE_FILE" ]] && core_args+=(--feature-file "$FEATURE_FILE")
    [[ -n "$RUN_ID" ]] && core_args+=(--run-id "$RUN_ID")

    IMPLEMENT_TMPDIR="$IMPLEMENT_TMPDIR" "$REVIEW_CORE_SH" "${core_args[@]}" > "$core_out"

    core_status=$(kv_get "$core_out" REVIEW_CORE_STATUS)
    accepted_count=$(kv_get "$core_out" ACCEPTED_COUNT)
    rejected_count=$(kv_get "$core_out" REJECTED_COUNT)
    accepted_file=$(kv_get "$core_out" ACCEPTED_FINDINGS_FILE)
    rejected_file=$(kv_get "$core_out" REJECTED_FINDINGS_FILE)
    accepted_count="${accepted_count:-0}"
    rejected_count="${rejected_count:-0}"
    core_status="${core_status:-unknown}"
    accepted_file="${accepted_file:-$round_dir/accepted-findings.md}"
    rejected_file="${rejected_file:-$round_dir/rejected-findings.md}"

    oos_jsonl="$IMPLEMENT_TMPDIR/accumulated-oos.jsonl"
    oos_markdown="$IMPLEMENT_TMPDIR/accumulated-oos.md"
    round_oos="$round_dir/oos-accepted-review.md"
    if [[ -s "$round_oos" ]]; then
        jq -Rn --argjson round "$round_num_dec" --rawfile body "$round_oos" \
            '{round: $round, source: "code-review", body: $body}' >> "$oos_jsonl"
        [[ -s "$oos_markdown" ]] && printf '\n' >> "$oos_markdown"
        cat "$round_oos" >> "$oos_markdown"
        cp "$oos_markdown" "$IMPLEMENT_TMPDIR/oos-accepted-review.md" 2>/dev/null || true
    fi

    if [[ -f "$rejected_file" ]]; then
        cp "$rejected_file" "$IMPLEMENT_TMPDIR/rejected-findings.md" 2>/dev/null || true
    fi

    fix_count=0
    if [[ "$accepted_count" -gt 0 && -s "$accepted_file" ]]; then
        # Filter OOS findings — they go to Step 9a.1, not to the fixer.
        in_scope_file="$round_dir/accepted-in-scope-findings.md"
        awk '/^### FINDING_[0-9]+: \[OUT_OF_SCOPE\]/{skip=1} /^### FINDING_[0-9]+:/ && !/\[OUT_OF_SCOPE\]/{skip=0} !skip{print}' \
            "$accepted_file" > "$in_scope_file" || true
        if [[ -s "$in_scope_file" ]] && grep -Eq '^### FINDING_[0-9]+:' "$in_scope_file"; then
            FINDINGS_FILE="$in_scope_file"
            REVIEW_TMPDIR="$round_dir"
            # emit_kv uses FD3 (lib-quiet.sh); capture it, not stdout.
            enumerate_findings 3>>"$round_dir/review-and-fix-enumeration.env"
            fix_count=$(kv_get "$round_dir/review-and-fix-enumeration.env" FIX_COUNT)
            fix_count="${fix_count:-0}"
        fi
    fi

    prior_summary="$IMPLEMENT_TMPDIR/review-and-fix-summary.json"
    prior_accepted=0
    prior_rejected=0
    if [[ -f "$prior_summary" ]] && jq -e '.schema_version == 1' "$prior_summary" >/dev/null 2>&1; then
        prior_rounds=$(jq -r '.rounds_completed // 0' "$prior_summary")
        if [[ "$prior_rounds" =~ ^[0-9]+$ ]] && (( 10#$prior_rounds < round_num_dec )); then
            prior_accepted=$(jq -r '.accepted_count // 0' "$prior_summary")
            prior_rejected=$(jq -r '.rejected_count // 0' "$prior_summary")
        fi
    fi
    total_accepted=$((prior_accepted + accepted_count))
    total_rejected=$((prior_rejected + rejected_count))

    status="complete"
    exit_code=0
    case "$core_status" in
        wholesale-rejected)
            status="wholesale-rejected"
            exit_code=2
            ;;
        fix-required|cap-reached)
            if [[ "$accepted_count" -gt 0 ]]; then
                status="fix-required"
                exit_code=3
            fi
            ;;
        zero-findings|ok)
            status="complete"
            ;;
        *)
            status="$core_status"
            ;;
    esac

    write_summary_json "$prior_summary" "$status" "$core_status" "$round_num_dec" "$total_accepted" "$total_rejected" "$round_num_dec" "$accepted_file" "$round_dir" "$oos_jsonl" "$oos_markdown"

    emit_kv REVIEW_AND_FIX_STATUS "$status"
    emit_kv REVIEW_CORE_STATUS "$core_status"
    emit_kv ROUND_NUM "$round_num_dec"
    emit_kv ACCEPTED_COUNT "$accepted_count"
    emit_kv REJECTED_COUNT "$rejected_count"
    emit_kv FIX_COUNT "$fix_count"
    emit_kv APPROVED_FIXES_FILE "$accepted_file"
    emit_kv REJECTED_FINDINGS_FILE "$rejected_file"
    emit_kv REVIEW_ROUND_DIR "$round_dir"
    emit_kv REVIEW_AND_FIX_SUMMARY_FILE "$prior_summary"
    emit_kv ACCUMULATED_OOS_FILE "$oos_jsonl"
    exit "$exit_code"
}

if [[ -n "$IMPLEMENT_TMPDIR" ]]; then
    run_implement_round
fi

[[ -f "$FINDINGS_FILE" ]] || { larch_err "review-and-fix.sh: --findings-file must name a file"; exit 2; }
enumerate_findings
