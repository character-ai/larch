#!/usr/bin/env bash
# render-run-summary.sh — shared markdown run-summary block (implement + fix-issue).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd -P)}"
TOKEN_COST_SH="$SCRIPT_DIR/token-cost.sh"

emit_diag() {
    if [ "${LARCH_QUIET_PID:-}" = "$$" ]; then
        printf '%s\n' "$*" >&4
    else
        printf '%s\n' "$*" >&2
    fi
}

emit_body_line() {
    if [ "${LARCH_QUIET_PID:-}" = "$$" ]; then
        printf '%s\n' "$*" >&3
    else
        printf '%s\n' "$*"
    fi
}

usage() {
    emit_diag "Usage: render-run-summary.sh --skill implement|fix-issue ... (see render-run-summary.md)"
}

SKILL=""
OUTCOME=""
RUN_ID=""
MODE_STR=""
WORKFLOW_PATH=""
DURATION=""
CLAUDE_TOKENS=0
CODEX_TOKENS=0
CURSOR_TOKENS=0
ISSUE_NUMBER=""
ISSUE_URL=""
PR_NUMBER=""
PR_URL=""
PLAN_REVIEW_LINE=""
CODE_REVIEW_LINE=""
OOS_COUNT=0
OOS_URLS=""
EXEC_ISSUES=0
WARNINGS=0
RUN_LOGS_PATH=""
NOTE_LINES_FILE=""
PRINT_STDOUT=false
OUTPUT_FILE=""

while [ $# -gt 0 ]; do
    case "$1" in
        --skill) [ $# -ge 2 ] || { usage; exit 2; }; SKILL=$2; shift 2 ;;
        --outcome) [ $# -ge 2 ] || { usage; exit 2; }; OUTCOME=$2; shift 2 ;;
        --run-id) [ $# -ge 2 ] || { usage; exit 2; }; RUN_ID=$2; shift 2 ;;
        --mode) [ $# -ge 2 ] || { usage; exit 2; }; MODE_STR=$2; shift 2 ;;
        --workflow-path) [ $# -ge 2 ] || { usage; exit 2; }; WORKFLOW_PATH=$2; shift 2 ;;
        --duration) [ $# -ge 2 ] || { usage; exit 2; }; DURATION=$2; shift 2 ;;
        --claude-tokens) [ $# -ge 2 ] || { usage; exit 2; }; CLAUDE_TOKENS=$2; shift 2 ;;
        --codex-tokens) [ $# -ge 2 ] || { usage; exit 2; }; CODEX_TOKENS=$2; shift 2 ;;
        --cursor-tokens) [ $# -ge 2 ] || { usage; exit 2; }; CURSOR_TOKENS=$2; shift 2 ;;
        --issue-number) [ $# -ge 2 ] || { usage; exit 2; }; ISSUE_NUMBER=$2; shift 2 ;;
        --issue-url) [ $# -ge 2 ] || { usage; exit 2; }; ISSUE_URL=$2; shift 2 ;;
        --pr-number) [ $# -ge 2 ] || { usage; exit 2; }; PR_NUMBER=$2; shift 2 ;;
        --pr-url) [ $# -ge 2 ] || { usage; exit 2; }; PR_URL=$2; shift 2 ;;
        --plan-review-line) [ $# -ge 2 ] || { usage; exit 2; }; PLAN_REVIEW_LINE=$2; shift 2 ;;
        --code-review-line) [ $# -ge 2 ] || { usage; exit 2; }; CODE_REVIEW_LINE=$2; shift 2 ;;
        --oos-count) [ $# -ge 2 ] || { usage; exit 2; }; OOS_COUNT=$2; shift 2 ;;
        --oos-urls) [ $# -ge 2 ] || { usage; exit 2; }; OOS_URLS=$2; shift 2 ;;
        --exec-issues) [ $# -ge 2 ] || { usage; exit 2; }; EXEC_ISSUES=$2; shift 2 ;;
        --warnings) [ $# -ge 2 ] || { usage; exit 2; }; WARNINGS=$2; shift 2 ;;
        --run-logs-path) [ $# -ge 2 ] || { usage; exit 2; }; RUN_LOGS_PATH=$2; shift 2 ;;
        --note-lines-file) [ $# -ge 2 ] || { usage; exit 2; }; NOTE_LINES_FILE=$2; shift 2 ;;
        --print-stdout) PRINT_STDOUT=true; shift ;;
        --output-file) [ $# -ge 2 ] || { usage; exit 2; }; OUTPUT_FILE=$2; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) usage; exit 2 ;;
    esac
done

[ -n "$SKILL" ] || { usage; exit 2; }
[ -n "$OUTCOME" ] || { usage; exit 2; }
[ -n "$RUN_ID" ] || { usage; exit 2; }

case "$SKILL" in implement|fix-issue) ;; *) usage; exit 2 ;; esac

na() { [ -z "$1" ] && printf 'N/A\n' || printf '%s\n' "$1"; }

tok_k() {
    awk -v n="${1:-0}" 'BEGIN {
      if (n == "") n = 0
      printf "%d\n", int((n+500)/1000)
    }'
}

ct=$(tok_k "$((CLAUDE_TOKENS + CODEX_TOKENS + CURSOR_TOKENS))")
ck=$(tok_k "$CLAUDE_TOKENS")
dk=$(tok_k "$CODEX_TOKENS")
uk=$(tok_k "$CURSOR_TOKENS")

cost_lines=""
if [ -x "$TOKEN_COST_SH" ]; then
    cost_lines=$("$TOKEN_COST_SH" \
        --claude-tokens "$CLAUDE_TOKENS" \
        --codex-tokens "$CODEX_TOKENS" \
        --cursor-tokens "$CURSOR_TOKENS" 2>/dev/null || true)
else
    cost_lines=$("$PLUGIN_ROOT/scripts/token-cost.sh" \
        --claude-tokens "$CLAUDE_TOKENS" \
        --codex-tokens "$CODEX_TOKENS" \
        --cursor-tokens "$CURSOR_TOKENS" 2>/dev/null || true)
fi

read_cost() {
    local key=$1 v
    v=$(printf '%s\n' "$cost_lines" | awk -F= -v k="$key" '$1==k{print $2; exit}')
    [ -n "$v" ] && printf '%s\n' "$v" || printf 'N/A\n'
}

tc=$(read_cost TOTAL_COST)
cc=$(read_cost CLAUDE_COST)
dc=$(read_cost CODEX_COST)
uc=$(read_cost CURSOR_COST)

fmt_usd() {
    case "$1" in N/A|"") printf 'N/A' ;; *) printf '$%s' "$1" ;; esac
}

cost_bullet() {
    local tc_disp
    case "$tc" in N/A|"") tc_disp="N/A" ;; *) tc_disp="~$(fmt_usd "$tc")" ;; esac
    printf 'TOTAL %s — Claude %s, Codex %s, Cursor %s' \
        "$tc_disp" "$(fmt_usd "$cc")" "$(fmt_usd "$dc")" "$(fmt_usd "$uc")"
}

mode_disp=$(na "$MODE_STR")
path_disp=$(na "$WORKFLOW_PATH")
dur_disp=$(na "$DURATION")

iss_disp="N/A"
if [ -n "$ISSUE_NUMBER" ] && [ "$ISSUE_NUMBER" != "0" ]; then
    if [ -n "$ISSUE_URL" ] && [ "$ISSUE_URL" != "N/A" ]; then
        iss_disp="#${ISSUE_NUMBER} — ${ISSUE_URL}"
    else
        iss_disp="#${ISSUE_NUMBER}"
    fi
fi

pr_disp="N/A"
if [ -n "$PR_NUMBER" ] && [ "$PR_NUMBER" != "0" ]; then
    if [ -n "$PR_URL" ] && [ "$PR_URL" != "N/A" ]; then
        pr_disp="#${PR_NUMBER} — ${PR_URL}"
    else
        pr_disp="#${PR_NUMBER}"
    fi
fi

plan_disp="${PLAN_REVIEW_LINE:-N/A}"
code_disp="${CODE_REVIEW_LINE:-N/A}"

oos_disp="0"
case "$OOS_COUNT" in ''|*[!0-9]*) oos_disp="0" ;; 0) oos_disp="0" ;; *)
    if [ -n "$OOS_URLS" ] && [ "$OOS_URLS" != "N/A" ]; then
        oos_disp="${OOS_COUNT} — ${OOS_URLS}"
    else
        oos_disp="$OOS_COUNT"
    fi
    ;;
esac

ex_disp=$(na "${EXEC_ISSUES:-0}")
warn_disp=$(na "${WARNINGS:-0}")

run_logs_disp=$(na "$RUN_LOGS_PATH")
if [ "$run_logs_disp" = "N/A" ] && [ -n "$RUN_ID" ]; then
    run_logs_disp="larch-logs/${SKILL}/${RUN_ID}/"
fi

tmp_out="$(mktemp "${TMPDIR:-/tmp}/render-run-summary.XXXXXX")"
# shellcheck disable=SC2317 # EXIT trap invokes cleanup on early exit paths
cleanup() { rm -f "$tmp_out"; }
trap cleanup EXIT

{
    printf '## /%s run %s — %s\n\n' "$SKILL" "$RUN_ID" "$OUTCOME"
    case "$OUTCOME" in bailed*|stalled) printf -- '- **Outcome**: %s\n' "$OUTCOME" ;; esac
    printf -- '- **Mode**: %s\n' "$mode_disp"
    printf -- '- **Path**: %s\n' "$path_disp"
    printf -- '- **Duration**: %s\n' "$dur_disp"
    printf -- '- **Tokens**: %sk total — Claude %sk, Codex %sk, Cursor %sk\n' "$ct" "$ck" "$dk" "$uk"
    printf -- '- **Cost**: %s\n' "$(cost_bullet)"
    printf -- '- **Issue**: %s\n' "$iss_disp"
    if [ "$pr_disp" != "N/A" ]; then
        printf -- '- **PR**: %s\n' "$pr_disp"
    fi
    printf -- '- **Plan review**: %s\n' "$plan_disp"
    printf -- '- **Code review**: %s\n' "$code_disp"
    printf -- '- **OOS filed**: %s\n' "$oos_disp"
    printf -- '- **Exec issues**: %s\n' "$ex_disp"
    printf -- '- **Warnings**: %s\n' "$warn_disp"
    printf -- "- **Run logs**: \`%s\`\n\n" "$run_logs_disp"
    printf '%s\n' '<!-- larch:run-summary v=1 -->'
} > "$tmp_out"

if [ -n "$NOTE_LINES_FILE" ] && [ -f "$NOTE_LINES_FILE" ]; then
    printf '\n' >> "$tmp_out"
    cat "$NOTE_LINES_FILE" >> "$tmp_out"
fi

if [ -n "$OUTPUT_FILE" ]; then
    mkdir -p "$(dirname "$OUTPUT_FILE")"
    cp "$tmp_out" "$OUTPUT_FILE"
    final_path="$OUTPUT_FILE"
else
    final_path="$tmp_out"
fi

if [ "$PRINT_STDOUT" = true ]; then
    while IFS= read -r line || [ -n "$line" ]; do
        emit_body_line "$line"
    done < "$tmp_out"
fi

emit_diag "STATUS=ok"
emit_diag "OUTPUT_FILE=$final_path"

trap - EXIT
rm -f "$tmp_out"
exit 0
