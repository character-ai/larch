#!/usr/bin/env bash
# write-final-report.sh — final run summary for /implement (rich block + upsert).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
# shellcheck source=scripts/run-log-terminal-outcomes.inc.bash
# shellcheck disable=SC1091
source "$PLUGIN_ROOT/scripts/run-log-terminal-outcomes.inc.bash"
# shellcheck source=scripts/lib-quiet.sh
# shellcheck disable=SC1091
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init

emit_kv_out() {
    if [ "${PRINT_STDOUT:-false}" = true ]; then
        larch_errf '%s=%s\n' "$1" "${2-}"
    else
        emit_kv "$1" "${2-}"
    fi
}

usage() {
    larch_err "Usage: write-final-report.sh --implement-tmpdir PATH [--comment-only] [--print-stdout]"
}

fail_usage() {
    usage
    emit_kv_out COMMENT_URL ""
    emit_kv_out STATUS failed
    emit_kv_out ERROR "$1"
    exit 2
}

read_kv() {
    local key=$1 file=$2
    [ -f "$file" ] || return 0
    awk -v k="$key" 'BEGIN{p=k"="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$file" 2>/dev/null
}

issue_url_from_repo() {
    local repo="$1" num="$2"
    [ -n "$repo" ] || return 1
    [ -n "$num" ] || return 1
    [ "$num" = "0" ] && return 1
    case "$repo" in
        */*) printf 'https://github.com/%s/issues/%s\n' "$repo" "$num" ;;
        *) return 1 ;;
    esac
}

IMPLEMENT_TMPDIR=""
COMMENT_ONLY=false
PRINT_STDOUT=false
export PRINT_STDOUT

while [ $# -gt 0 ]; do
    case "$1" in
        --implement-tmpdir) [ $# -ge 2 ] || fail_usage "--implement-tmpdir requires a value"; IMPLEMENT_TMPDIR=$2; shift 2 ;;
        --comment-only) COMMENT_ONLY=true; shift ;;
        --print-stdout) PRINT_STDOUT=true; shift ;;
        --help) usage; exit 0 ;;
        *) fail_usage "unknown option: $1" ;;
    esac
done

[ -n "$IMPLEMENT_TMPDIR" ] || fail_usage "--implement-tmpdir is required"
[ -d "$IMPLEMENT_TMPDIR" ] || fail_usage "--implement-tmpdir not found"

PARENT_ISSUE="$IMPLEMENT_TMPDIR/parent-issue.md"
SESSION_ENV="$IMPLEMENT_TMPDIR/session-env.sh"
SHIP_PR_STATE="$IMPLEMENT_TMPDIR/ship-pr-state.sh"
FINALIZE_STATE="$IMPLEMENT_TMPDIR/finalize-state.sh"
RUN_FLAGS="$IMPLEMENT_TMPDIR/run-flags.sh"

ISSUE="$(read_kv ISSUE_NUMBER "$PARENT_ISSUE")"; [ -n "$ISSUE" ] || ISSUE="0"
RUN_ID="$(read_kv RUN_ID "$PARENT_ISSUE")"
[ -n "$RUN_ID" ] || RUN_ID="$(tr -d '\r\n' < "$IMPLEMENT_TMPDIR/session-id" 2>/dev/null || true)"
case "$RUN_ID" in
    */*|*'..'*) emit_kv_out COMMENT_URL ""
                emit_kv_out STATUS failed
                emit_kv_out ERROR "invalid RUN_ID (path-traversal characters rejected)"
                exit 1 ;;
esac

PR_URL="$(read_kv PR_URL "$SHIP_PR_STATE")"; [ -n "$PR_URL" ] || PR_URL="N/A"
PR_NUMBER="$(read_kv PR_NUMBER "$SHIP_PR_STATE")"; [ -n "$PR_NUMBER" ] || PR_NUMBER=""
STALL_TRACKING="$(read_kv STALL_TRACKING "$SHIP_PR_STATE")"; [ -n "$STALL_TRACKING" ] || STALL_TRACKING="false"
MERGE_RESULT="$(read_kv MERGE_RESULT "$SHIP_PR_STATE")"
MERGE="$(read_kv MERGE "$SHIP_PR_STATE")"; [ -n "$MERGE" ] || MERGE=""
DRAFT="$(read_kv DRAFT "$SHIP_PR_STATE")"; [ -n "$DRAFT" ] || DRAFT="false"
FORKED_TARGET="$(read_kv FORKED_TARGET "$SHIP_PR_STATE")"; [ -n "$FORKED_TARGET" ] || FORKED_TARGET="false"

DESIGN_ONLY_DONE="$(read_kv DESIGN_ONLY_DONE "$FINALIZE_STATE")"; [ -n "$DESIGN_ONLY_DONE" ] || DESIGN_ONLY_DONE="false"
BAIL_USER="$(read_kv BAIL_NEEDS_USER_INPUT "$FINALIZE_STATE")"; [ -n "$BAIL_USER" ] || BAIL_USER="false"
if [ "$STALL_TRACKING" = "false" ] && [ -f "$FINALIZE_STATE" ]; then
    STALL_TRACKING="$(read_kv STALL_TRACKING "$FINALIZE_STATE")"
    [ -n "$STALL_TRACKING" ] || STALL_TRACKING="false"
fi

REPO="$(read_kv REPO "$SESSION_ENV")"
REPO_UNAV="$(read_kv REPO_UNAVAILABLE "$SESSION_ENV")"; [ -n "$REPO_UNAV" ] || REPO_UNAV="false"

NO_ISSUES="$(read_kv NO_ISSUES "$RUN_FLAGS")"; [ -n "$NO_ISSUES" ] || NO_ISSUES="false"
WORKFLOW_PATH="$(read_kv WORKFLOW_PATH "$RUN_FLAGS")"
[ -n "$WORKFLOW_PATH" ] || WORKFLOW_PATH="$(read_kv POST_PLAN_WORKFLOW_PATH "$SESSION_ENV")"
[ -n "$WORKFLOW_PATH" ] || WORKFLOW_PATH="N/A"

UPSTREAM_ISSUE="$(read_kv UPSTREAM_DESIGN_ISSUE "$SESSION_ENV")"

run_dir="$IMPLEMENT_TMPDIR/larch-logs/implement/$RUN_ID"
mkdir -p "$run_dir" || {
    emit_kv_out COMMENT_URL ""
    emit_kv_out STATUS failed
    emit_kv_out ERROR "could not create run log directory"
    exit 1
}

ISSUE_URL="$(read_kv ISSUE_URL "$PARENT_ISSUE")"
[ -n "$ISSUE_URL" ] || ISSUE_URL=""
if [ -z "$ISSUE_URL" ] || [ "$ISSUE_URL" = "N/A" ]; then
    ISSUE_URL=$(issue_url_from_repo "$REPO" "$ISSUE" || true)
fi

# --- Outcome ---
OUTCOME=""
if [ "$STALL_TRACKING" = "true" ]; then
    OUTCOME="stalled"
elif [ "$FORKED_TARGET" = "true" ]; then
    OUTCOME="forked-dry-run"
elif [ "$DESIGN_ONLY_DONE" = "true" ]; then
    OUTCOME="design-only"
elif [ "$MERGE_RESULT" = "merged" ] || [ "$MERGE_RESULT" = "admin_merged" ]; then
    OUTCOME="merged"
elif [ "$MERGE_RESULT" = "already_merged" ]; then
    OUTCOME="force-merged-externally"
elif [ -n "$PR_NUMBER" ] && [ "$PR_NUMBER" != "0" ] && [ "$DRAFT" = "true" ]; then
    OUTCOME="pr-created-draft"
elif [ -n "$PR_NUMBER" ] && [ "$PR_NUMBER" != "0" ] && [ "$DRAFT" = "false" ] && [ "$MERGE" = "false" ]; then
    OUTCOME="pr-created"
fi
if [ -z "$OUTCOME" ]; then
    OUTCOME="bailed"
fi

if [ "$BAIL_USER" = "true" ] && [ "$OUTCOME" = "bailed" ]; then
    OUTCOME="bailed-needs-user-input"
fi

# --- Mode flags (display) ---
mode_parts=()
[ "$NO_ISSUES" = "true" ] && mode_parts+=("--no-issues")
[ "$DESIGN_ONLY_DONE" = "true" ] && mode_parts+=("--design-only")
[ "$DRAFT" = "true" ] && mode_parts+=("--draft")
[ "$FORKED_TARGET" = "true" ] && mode_parts+=("--forked")
[ "$REPO_UNAV" = "true" ] && mode_parts+=("--repo-unavailable")
mode_str="N/A"
if [ "${#mode_parts[@]}" -gt 0 ]; then
    mode_str=$(IFS=', '; echo "${mode_parts[*]}")
fi

# --- Tokens ---
CLAUDE_T=0 CODEX_T=0 CURSOR_T=0
C_IN=0 C_CR=0 C_CW5=0 C_CW1=0 C_OUT=0
D_IN=0 D_CACHED=0 D_OUT=0
U_IN=0 U_CR=0 U_OUT=0
TOKEN_JSON=""
TOKEN_DATA_AVAILABLE=false
TOKEN_REPORT_CORRUPT_ZERO=false
TOKEN_REPORT_CORRUPT_ZERO_WARNING='**⚠ token-report.json appears corrupt; reporting Cost: N/A**'
for cand in "$run_dir/token-report.json" "$IMPLEMENT_TMPDIR/token-report-rendered.json"; do
    [ -f "$cand" ] && TOKEN_JSON="$cand" && break
done
if [ -z "$TOKEN_JSON" ] || [ ! -f "$TOKEN_JSON" ]; then
    tr_json="$IMPLEMENT_TMPDIR/token-report-truth.json"
    if IMPLEMENT_TMPDIR="$IMPLEMENT_TMPDIR" LARCH_TOKEN_SESSION_ID="${LARCH_TOKEN_SESSION_ID:-}" \
        "$PLUGIN_ROOT/scripts/token-report.sh" --full --format json --output "$tr_json" 2>/dev/null && [ -f "$tr_json" ]; then
        TOKEN_JSON="$tr_json"
    fi
fi
if [ -n "$TOKEN_JSON" ] && [ -f "$TOKEN_JSON" ] && command -v jq >/dev/null 2>&1 && jq -e '.claude.totals' "$TOKEN_JSON" >/dev/null 2>&1; then
    read -r CLAUDE_T CODEX_T CURSOR_T < <(jq -r '[.claude.totals.total // 0, (.codex.totals.total // 0), (.cursor.totals.total // 0)] | @tsv' "$TOKEN_JSON" 2>/dev/null || printf '0\t0\t0\n')
    TOKEN_CODEX_PRESENT=false
    TOKEN_CURSOR_PRESENT=false
    jq -e '.codex' "$TOKEN_JSON" >/dev/null 2>&1 && TOKEN_CODEX_PRESENT=true
    jq -e '.cursor' "$TOKEN_JSON" >/dev/null 2>&1 && TOKEN_CURSOR_PRESENT=true
    # guard against silent zero costs
    if jq -e --argjson codex_present "$TOKEN_CODEX_PRESENT" --argjson cursor_present "$TOKEN_CURSOR_PRESENT" '
      (.claude.totals? != null)
      and ((.claude.totals.total // 0) == 0)
      and (if $codex_present then ((.codex.totals.total // 0) == 0) else true end)
      and (if $cursor_present then ((.cursor.totals.total // 0) == 0) else true end)
      and ($codex_present or $cursor_present)
    ' "$TOKEN_JSON" >/dev/null 2>&1; then
        TOKEN_REPORT_CORRUPT_ZERO=true
        larch_err "$TOKEN_REPORT_CORRUPT_ZERO_WARNING"
    fi
    if jq -e '.BUCKETS_claude' "$TOKEN_JSON" >/dev/null 2>&1; then
        read -r C_IN C_CR C_CW5 C_CW1 C_OUT < <(jq -r '[.BUCKETS_claude.input, .BUCKETS_claude.cache_read, .BUCKETS_claude.cache_create_5m, .BUCKETS_claude.cache_create_1h, .BUCKETS_claude.output] | @tsv' "$TOKEN_JSON" 2>/dev/null || printf '0\t0\t0\t0\t0\n')
        read -r D_IN D_CACHED D_OUT < <(jq -r '[.BUCKETS_codex.input, .BUCKETS_codex.cached_input, .BUCKETS_codex.output] | @tsv' "$TOKEN_JSON" 2>/dev/null || printf '0\t0\t0\n')
        read -r U_IN U_CR U_OUT < <(jq -r '[.BUCKETS_cursor.input, .BUCKETS_cursor.cache_read, .BUCKETS_cursor.output] | @tsv' "$TOKEN_JSON" 2>/dev/null || printf '0\t0\t0\n')
    fi
    sum_b=$((C_IN + C_CR + C_CW5 + C_CW1 + C_OUT + D_IN + D_CACHED + D_OUT + U_IN + U_CR + U_OUT))
    total_t=$((CLAUDE_T + CODEX_T + CURSOR_T))
    if [ "$TOKEN_REPORT_CORRUPT_ZERO" != true ] && { [ "$sum_b" -ne 0 ] || [ "$total_t" -ne 0 ]; }; then
        TOKEN_DATA_AVAILABLE=true
    fi
fi

# --- Duration ---
DURATION="N/A"
if [ -f "$run_dir/timing-report.json" ]; then
    DURATION=$(jq -r 'if .total_hms then .total_hms elif .total_seconds then (.total_seconds | tostring + "s") else "N/A" end' "$run_dir/timing-report.json" 2>/dev/null || echo N/A)
fi

# --- Plan / code review lines ---
PLAN_LINE="N/A"
if [ -f "$run_dir/plan-review-tally.json" ]; then
    read -r pa pr _ < <(jq -r '[.accepted_count // 0, .rejected_count // 0, .mode // ""] | @tsv' "$run_dir/plan-review-tally.json" 2>/dev/null || printf '0\t0\t\n')
    tot=$((pa + pr))
    if [ "$tot" -gt 0 ] 2>/dev/null; then
        PLAN_LINE="${pa}/${tot} accepted"
    fi
fi

CODE_LINE="N/A"
if [ -f "$run_dir/code-review-tally.json" ]; then
    read -r ca cr < <(jq -r '[.accepted_count // 0, .rejected_count // 0] | @tsv' "$run_dir/code-review-tally.json" 2>/dev/null || printf '0\t0\n')
    ctot=$((ca + cr))
    if [ "$ctot" -gt 0 ] 2>/dev/null; then
        CODE_LINE="${ca}/${ctot} accepted"
    fi
fi

# --- OOS ---
OOS_COUNT=0
OOS_URLS=""
if [ -f "$run_dir/oos-issues.ndjson" ]; then
    OOS_COUNT=$(wc -l < "$run_dir/oos-issues.ndjson" | tr -d ' ')
    OOS_URLS=$(grep -hoE 'https://github.com[^"[:space:])>]+' "$run_dir/oos-issues.ndjson" 2>/dev/null | sort -u | paste -sd, - || true)
fi

# --- Execution issues / warnings ---
EXEC_N=0 WARN_N=0

RUN_LOGS_DISP="larch-logs/implement/${RUN_ID}/"

refresh_issue_counts() {
    EXEC_N=0
    WARN_N=0
    if [ -f "$IMPLEMENT_TMPDIR/execution-issues.md" ] && [ -s "$IMPLEMENT_TMPDIR/execution-issues.md" ]; then
        read -r md_exec md_warn < <(awk '
          /^### Tool Failures$/ { sec=1; next }
          /^### External Reviewer Issues$/ { sec=1; next }
          /^### Warnings$/ { sec=2; next }
          /^### / { sec=0; next }
          /^- \*\*[^*].*\*\*:?([[:space:]].*)?$/ {
            if (sec == 1) ex++
            if (sec == 2) wa++
            next
          }
          END { print ex+0, wa+0 }
        ' "$IMPLEMENT_TMPDIR/execution-issues.md")
        EXEC_N=$md_exec
        WARN_N=$md_warn
    elif [ -f "$run_dir/execution-issues.ndjson" ] && command -v jq >/dev/null 2>&1; then
        local ndjson_body nd_exec nd_warn
        ndjson_body="$(mktemp "${TMPDIR:-/tmp}/wfr-execution-issues.XXXXXX")"
        jq -r '.body // empty' "$run_dir/execution-issues.ndjson" 2>/dev/null >"$ndjson_body" || true
        if grep -Eq '^### (Tool Failures|External Reviewer Issues|Warnings)$' "$ndjson_body"; then
            read -r nd_exec nd_warn < <(awk '
              /^### Tool Failures$/ { sec=1; next }
              /^### External Reviewer Issues$/ { sec=1; next }
              /^### Warnings$/ { sec=2; next }
              /^### / { sec=0; next }
              /^- \*\*[^*].*\*\*:?([[:space:]].*)?$/ {
                if (sec == 1) ex++
                if (sec == 2) wa++
                next
              }
              END { print ex+0, wa+0 }
            ' "$ndjson_body")
            EXEC_N=${nd_exec:-0}
            WARN_N=${nd_warn:-0}
        else
            read -r nd_exec nd_warn < <(jq -rs '
              . as $rows
              | [
                  ($rows | map(select(.category == "Tool Failures" or .category == "External Reviewer Issues")) | length),
                  ($rows | map(select(.category == "Warnings")) | length)
                ] | @tsv
            ' "$run_dir/execution-issues.ndjson" 2>/dev/null || printf '0\t0\n')
            EXEC_N=${nd_exec:-0}
            WARN_N=${nd_warn:-0}
        fi
        rm -f "$ndjson_body"
    elif [ -f "$run_dir/execution-issues.ndjson" ]; then
        EXEC_N=$(( \
            $(grep -c '"category":"Tool Failures"' "$run_dir/execution-issues.ndjson" 2>/dev/null || echo 0) + \
            $(grep -c '"category":"External Reviewer Issues"' "$run_dir/execution-issues.ndjson" 2>/dev/null || echo 0) \
        ))
        WARN_N=$(grep -c '"category":"Warnings"' "$run_dir/execution-issues.ndjson" 2>/dev/null || echo 0)
        case "$EXEC_N" in *[!0-9]*) EXEC_N=0 ;; esac
        case "$WARN_N" in *[!0-9]*) WARN_N=0 ;; esac
    fi
}

redact_output_file_in_place() {
    local output_file=${1:-}
    local redacted_tmp
    [ -n "$output_file" ] || return 0
    [ -f "$output_file" ] || return 0
    [ -x "$PLUGIN_ROOT/scripts/redact-secrets.sh" ] || return 0
    redacted_tmp="$(mktemp "${TMPDIR:-/tmp}/wfr-redacted.XXXXXX")" || return 0
    if "$PLUGIN_ROOT/scripts/redact-secrets.sh" <"$output_file" >"$redacted_tmp"; then
        mv "$redacted_tmp" "$output_file"
    else
        rm -f "$redacted_tmp"
    fi
}

append_render_warning() {
    local site=$1 tool=$2 rc=$3 output_file=$4
    [ -x "$PLUGIN_ROOT/scripts/append-tool-failure.sh" ] || return 0
    [ -f "$output_file" ] || : >"$output_file"
    "$PLUGIN_ROOT/scripts/append-tool-failure.sh" \
        --log "$IMPLEMENT_TMPDIR/execution-issues.md" \
        --site "$site" \
        --tool "$tool" \
        --exit-code "$rc" \
        --category Warnings \
        --redact \
        --output-file "$output_file" \
        >/dev/null 2>&1 || true
    refresh_issue_counts
}

# --- Note lines (after sentinel in body — appended by render via note file) ---
notes_tmp="$(mktemp "${TMPDIR:-/tmp}/wfr-notes.XXXXXX")"
{
    if [ "$OUTCOME" = "forked-dry-run" ]; then
        printf '%s\n' "## Fork CI Dry-Run Complete"
        printf '%s\n' "- Fork PR: ${PR_URL}"
        printf '%s\n' "- Actions must be enabled on the fork for CI to run."
        printf '%s\n' "- Repository secrets are not available on fork runs."
        printf '%s\n' "- \`github.repository\` guards may skip jobs that expect upstream."
        printf '%s\n' "- Green on the fork does not guarantee green on upstream."
        printf '%s\n' "- \`FORK_CI_NO_CHECKS=true\` means no CI signal was observed."
        printf '\n'
    fi
    if [ "$DESIGN_ONLY_DONE" = "true" ] && [ "$NO_ISSUES" = "true" ]; then
        printf '%s\n' "**Note:** \`--design-only --no-issues\` was set — no tracking issue was opened."
    elif [ "$DESIGN_ONLY_DONE" = "true" ]; then
        printf '%s\n' "**Note:** \`--design-only\` was set — no PR was created; see tracking summaries for plan artifacts."
    fi
    if [ "$DRAFT" = "true" ] && [ -n "$PR_NUMBER" ] && [ "$PR_NUMBER" != "0" ]; then
        printf '%s\n' "**Note:** \`--draft\` was set — mark the PR ready and merge manually when ready."
    fi
    if [ "$MERGE" = "false" ] && [ "$DRAFT" = "false" ] && [ -n "$PR_NUMBER" ] && [ "$PR_NUMBER" != "0" ]; then
        printf '%s\n' "**Note:** \`--merge\` was not set — merge the PR manually when ready."
    fi
    if [ -n "$UPSTREAM_ISSUE" ]; then
        printf '%s\n' "**Note:** You may include \`Closes #${UPSTREAM_ISSUE}\` in the upstream PR body when you compose it manually."
    fi
    if [ "$TOKEN_REPORT_CORRUPT_ZERO" = true ]; then
        printf '%s\n' "$TOKEN_REPORT_CORRUPT_ZERO_WARNING"
    fi
    if [ "$FORKED_TARGET" = "true" ]; then
        any_oos=false
        for f in "$IMPLEMENT_TMPDIR/oos-accepted-main-agent.md" "$IMPLEMENT_TMPDIR/oos-accepted-design.md" "$IMPLEMENT_TMPDIR/oos-accepted-review.md"; do
            [ -s "$f" ] && any_oos=true && break
        done
        if [ "$any_oos" = true ]; then
            printf '%s\n' "## Out-of-Scope Observations (fork mode — not filed)"
            for f in "$IMPLEMENT_TMPDIR/oos-accepted-main-agent.md" "$IMPLEMENT_TMPDIR/oos-accepted-design.md" "$IMPLEMENT_TMPDIR/oos-accepted-review.md"; do
                [ -s "$f" ] || continue
                printf '%s\n' "- See \`$(basename "$f")\` in the session tmpdir for accepted OOS text (not filed upstream in fork dry-run)."
            done
        fi
    fi
} > "$notes_tmp"
# Drop note file if only whitespace / empty meaningful lines
if ! grep -q '[^[:space:]]' "$notes_tmp" 2>/dev/null; then
    rm -f "$notes_tmp"
    notes_tmp=""
fi

summary="$IMPLEMENT_TMPDIR/summary-final.md"
body_tmp="$(mktemp "${TMPDIR:-/tmp}/wfr-body.XXXXXX")"
trap 'rm -f "$body_tmp" "${notes_tmp:-}"' EXIT

run_body_render() {
    local nf="${1-}"
    local force_cost_unavailable="${2:-false}"
    local cost_args=()
    local note_args=()
    if [ "$force_cost_unavailable" = true ] || [ "$TOKEN_DATA_AVAILABLE" != true ]; then
        cost_args=(--cost-unavailable)
    else
        cost_args=(
            --claude-tokens "$CLAUDE_T"
            --codex-tokens "$CODEX_T"
            --cursor-tokens "$CURSOR_T"
            --claude-input-tokens "$C_IN"
            --claude-cache-read-tokens "$C_CR"
            --claude-cache-write-5m-tokens "$C_CW5"
            --claude-cache-write-1h-tokens "$C_CW1"
            --claude-output-tokens "$C_OUT"
            --codex-input-tokens "$D_IN"
            --codex-cached-input-tokens "$D_CACHED"
            --codex-output-tokens "$D_OUT"
            --cursor-input-tokens "$U_IN"
            --cursor-cache-read-tokens "$U_CR"
            --cursor-output-tokens "$U_OUT"
        )
    fi
    if [ -n "$nf" ] && [ -f "$nf" ]; then
        note_args=(--note-lines-file "$nf")
    fi
    "$PLUGIN_ROOT/scripts/render-run-summary.sh" \
        --skill implement \
        --outcome "$OUTCOME" \
        --run-id "$RUN_ID" \
        --mode "$mode_str" \
        --workflow-path "$WORKFLOW_PATH" \
        --duration "$DURATION" \
        "${cost_args[@]}" \
        --issue-number "$ISSUE" \
        --issue-url "${ISSUE_URL:-N/A}" \
        --pr-number "${PR_NUMBER:-0}" \
        --pr-url "$PR_URL" \
        --plan-review-line "$PLAN_LINE" \
        --code-review-line "$CODE_LINE" \
        --oos-count "$OOS_COUNT" \
        --oos-urls "${OOS_URLS:-}" \
        --exec-issues "$EXEC_N" \
        --warnings "$WARN_N" \
        --run-logs-path "$RUN_LOGS_DISP" \
        "${note_args[@]+"${note_args[@]}"}" \
        --output-file "$body_tmp" >/dev/null
}

compose_self_fallback() {
    {
        printf '## /implement run %s — %s\n\n' "$RUN_ID" "$OUTCOME"
        printf '%s\n\n' '**⚠ Degraded fallback — full renderer failed; warning recorded in execution issues.**'
        case "$OUTCOME" in bailed*|stalled|cancelled-*|failed-*) printf -- '- **Outcome**: %s\n' "$OUTCOME" ;; esac
        printf -- '- **Mode**: %s\n' "${mode_str:-N/A}"
        printf -- '- **Path**: %s\n' "${WORKFLOW_PATH:-N/A}"
        printf -- '- **Duration**: %s\n' "${DURATION:-N/A}"
        printf -- '- **Cost**: N/A\n'
        if [ -n "$ISSUE" ] && [ "$ISSUE" != "0" ]; then
            if [ -n "${ISSUE_URL:-}" ] && [ "${ISSUE_URL:-N/A}" != "N/A" ]; then
                printf -- '- **Issue**: #%s — %s\n' "$ISSUE" "$ISSUE_URL"
            else
                printf -- '- **Issue**: #%s\n' "$ISSUE"
            fi
        else
            printf -- '- **Issue**: N/A\n'
        fi
        if [ -n "${PR_NUMBER:-}" ] && [ "${PR_NUMBER:-0}" != "0" ]; then
            if [ -n "$PR_URL" ] && [ "$PR_URL" != "N/A" ]; then
                printf -- '- **PR**: #%s — %s\n' "$PR_NUMBER" "$PR_URL"
            else
                printf -- '- **PR**: #%s\n' "$PR_NUMBER"
            fi
        fi
        printf -- '- **Plan review**: %s\n' "${PLAN_LINE:-N/A}"
        printf -- '- **Code review**: %s\n' "${CODE_LINE:-N/A}"
        if [ "${OOS_COUNT:-0}" != "0" ] && [ -n "${OOS_URLS:-}" ] && [ "${OOS_URLS:-}" != "N/A" ]; then
            printf -- '- **OOS filed**: %s — %s\n' "$OOS_COUNT" "$OOS_URLS"
        else
            printf -- '- **OOS filed**: %s\n' "${OOS_COUNT:-0}"
        fi
        printf -- '- **Exec issues**: %s\n' "${EXEC_N:-0}"
        printf -- '- **Warnings**: %s\n' "${WARN_N:-0}"
        printf -- "- **Run logs**: \`%s\`\n\n" "${RUN_LOGS_DISP:-N/A}"
        printf '%s\n' '<!-- larch:run-summary v=1 -->'
        printf '%s\n' '<!-- larch:final-summary-fallback v1 -->'
    } > "$body_tmp"
    if [ -n "${notes_tmp:-}" ] && [ -f "$notes_tmp" ]; then
        printf '\n' >> "$body_tmp"
        cat "$notes_tmp" >> "$body_tmp"
    fi
}

set +e
refresh_issue_counts
run_body_render "${notes_tmp}"
rr=$?
set -e

if [ "$rr" -ne 0 ] || [ ! -s "$body_tmp" ]; then
    primary_err="$IMPLEMENT_TMPDIR/wfr-primary-render-failed.log"
    printf 'render-run-summary.sh failed or produced an empty body (exit %s)\n' "$rr" > "$primary_err"
    append_render_warning "implement final summary" "render-run-summary.sh" "${rr:-1}" "$primary_err"
    set +e
    run_body_render "${notes_tmp}" true 2>"$IMPLEMENT_TMPDIR/wfr-fallback-stage1.log"
    rr2=$?
    set -e
    if [ "$rr2" -ne 0 ] || [ ! -s "$body_tmp" ]; then
        redact_output_file_in_place "$IMPLEMENT_TMPDIR/wfr-fallback-stage1.log"
        append_render_warning "implement final summary fallback" "render-run-summary.sh --cost-unavailable" "${rr2:-1}" "$IMPLEMENT_TMPDIR/wfr-fallback-stage1.log"
        rm -f "$IMPLEMENT_TMPDIR/wfr-fallback-stage1.log"
        compose_self_fallback
    else
        rm -f "$IMPLEMENT_TMPDIR/wfr-fallback-stage1.log"
    fi
fi

cp "$body_tmp" "$summary" || {
    emit_kv_out COMMENT_URL ""
    emit_kv_out STATUS failed
    emit_kv_out ERROR "could not write summary"
    exit 1
}
if [ "$COMMENT_ONLY" != "true" ]; then
    cp "$body_tmp" "$run_dir/final-summary.md" 2>/dev/null || true
    # Terminal non-merge outcomes: persist explicit steps_ran.*=false for steps that
    # clearly did not run so audit required-file tooling is not fooled by `{}`.
    mf_impl="$run_dir/manifest.json"
    bail_steps_ran=false
    if [[ "$OUTCOME" =~ $RUN_LOG_TERMINAL_OUTCOME_NAME_EREGEX ]]; then
        bail_steps_ran=true
    fi
    if [ "$bail_steps_ran" = true ] && [ -f "$mf_impl" ]; then
        mf_fields=()
        if [ ! -f "$run_dir/run-statistics.md" ] && [ ! -f "$run_dir/oos-issues.ndjson" ]; then
            mf_fields+=(--field "steps_ran.step9a1=false")
        fi
        if [ ! -f "$run_dir/version-bump-reasoning.md" ]; then
            mf_fields+=(--field "steps_ran.step8=false")
        fi
        if ! {
            [ -f "$run_dir/token-report.json" ] ||
                [ -f "$run_dir/timing-report.json" ] ||
                [ -f "$run_dir/execution-issues.ndjson" ] ||
                [ -f "$run_dir/session-transcript.jsonl" ]
        }; then
            mf_fields+=(--field "steps_ran.step7a=false")
        fi
        if [ "${#mf_fields[@]}" -gt 0 ]; then
            if ! "$PLUGIN_ROOT/scripts/larch-log.sh" manifest \
                --log-root "$IMPLEMENT_TMPDIR/larch-logs" \
                --skill implement \
                --run-id "$RUN_ID" \
                "${mf_fields[@]}"; then
                emit_kv_out COMMENT_URL ""
                emit_kv_out STATUS failed
                emit_kv_out ERROR "larch-log.sh manifest steps_ran update failed"
                exit 1
            fi
        fi
    fi
fi

if [ "$PRINT_STDOUT" = true ]; then
    while IFS= read -r line || [ -n "$line" ]; do
        if [ "${LARCH_QUIET_PID:-}" = "$$" ]; then
            printf '%s\n' "$line" >&3
        else
            printf '%s\n' "$line"
        fi
    done < "$body_tmp"
fi

if [ "$ISSUE" = "0" ]; then
    emit_kv_out COMMENT_URL ""
    emit_kv_out STATUS skipped
    emit_kv_out REASON "issue-not-set"
    exit 0
fi

case "$ISSUE" in *[!0-9]*|"") emit_kv_out COMMENT_URL ""; emit_kv_out STATUS failed; emit_kv_out ERROR "ISSUE_NUMBER must be numeric"; exit 1 ;; esac

if [ "$REPO_UNAV" = "true" ]; then
    emit_kv_out COMMENT_URL ""
    emit_kv_out STATUS skipped
    emit_kv_out REASON "repo-unavailable"
    exit 0
fi

args=(upsert-summary --issue "$ISSUE" --marker "<!-- larch:final-summary v1 runid=$RUN_ID -->" --content-file "$summary")
[ -z "$REPO" ] || args+=(--repo "$REPO")
out_file="$IMPLEMENT_TMPDIR/write-final-report.out"
err_file="$IMPLEMENT_TMPDIR/write-final-report.err"
if "$PLUGIN_ROOT/scripts/tracking-issue-summary.sh" "${args[@]}" >"$out_file" 2>"$err_file"; then
    emit_kv_out COMMENT_URL "$(awk -F= '$1=="COMMENT_URL"{print substr($0,index($0,"=")+1); exit}' "$out_file")"
    emit_kv_out STATUS ok
    exit 0
fi

emit_kv_out COMMENT_URL ""
emit_kv_out STATUS failed
emit_kv_out ERROR "$(tr '\n' ' ' < "$err_file" | head -c 500)"
exit 1
