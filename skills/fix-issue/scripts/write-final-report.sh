#!/usr/bin/env bash
# write-final-report.sh — /fix-issue terminal run summary (parallel to /implement).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
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

usage() {
    larch_err "Usage: write-final-report.sh [--fix-issue-tmpdir PATH] [--print-stdout] [--outcome X] [--issue-number N] [--duration D] [--claude-tokens N] [--codex-tokens N] [--cursor-tokens N] [--repo R]"
}

FIX_TMP="${FIX_ISSUE_TMPDIR:-}"
PRINT_STDOUT=false
OUTCOME=""
ISSUE=""
DURATION="N/A"
CLAUDE_T=0
CODEX_T=0
CURSOR_T=0
REPO_ARG=""
export PRINT_STDOUT

while [ $# -gt 0 ]; do
    case "$1" in
        --fix-issue-tmpdir) FIX_TMP="${2:?}"; shift 2 ;;
        --print-stdout) PRINT_STDOUT=true; shift ;;
        --outcome) OUTCOME="${2:?}"; shift 2 ;;
        --issue-number) ISSUE="${2:?}"; shift 2 ;;
        --duration) DURATION="${2:?}"; shift 2 ;;
        --claude-tokens) CLAUDE_T="${2:?}"; shift 2 ;;
        --codex-tokens) CODEX_T="${2:?}"; shift 2 ;;
        --cursor-tokens) CURSOR_T="${2:?}"; shift 2 ;;
        --repo) REPO_ARG="${2:?}"; shift 2 ;;
        --help) usage; exit 0 ;;
        *) usage; exit 2 ;;
    esac
done

STATE=""
PR_NUMBER=""
PR_URL="N/A"
[ -n "$FIX_TMP" ] && STATE="$FIX_TMP/final-report-state.sh"

if [ -f "$STATE" ]; then
    [ -n "$ISSUE" ] || ISSUE="$(read_kv ISSUE_NUMBER "$STATE")"
    [ -n "$OUTCOME" ] || OUTCOME="$(read_kv OUTCOME "$STATE")"
    [ -n "$REPO_ARG" ] || REPO_ARG="$(read_kv REPO "$FIX_TMP/session-env.sh")"
    PR_NUMBER="$(read_kv PR_NUMBER "$STATE")"
    PR_URL="$(read_kv PR_URL "$STATE")"
else
    PR_NUMBER="${PR_NUMBER:-}"
    PR_URL="${PR_URL:-N/A}"
fi

[ -n "$ISSUE" ] || ISSUE="0"
[ -n "$OUTCOME" ] || OUTCOME="bailed-implement-failed"
[ -n "$REPO_ARG" ] || REPO_ARG=""

RUN_ID="fix-issue"
if [ -n "$FIX_TMP" ] && [ -f "$FIX_TMP/session-id" ]; then
    RUN_ID=$(tr -d '\r\n' < "$FIX_TMP/session-id" 2>/dev/null || echo fix-issue)
fi

ISSUE_URL=$(issue_url_from_repo "$REPO_ARG" "$ISSUE" || true)

skip_upsert=false
case "$OUTCOME" in
    pr-merged|pr-open|no-candidate|lock-failed|bailed-implement-failed|bailed-adopted-issue-closed) skip_upsert=true ;;
esac

mode_str="/fix-issue"
path_str="N/A"
plan_line="N/A"
code_line="N/A"
oos_count=0
oos_urls=""
exec_n=0
warn_n=0
run_logs="N/A"

body_tmp="$(mktemp "${TMPDIR:-/tmp}/fix-wfr-body.XXXXXX")"
trap 'rm -f "$body_tmp"' EXIT

set +e
"$PLUGIN_ROOT/scripts/render-run-summary.sh" \
    --skill fix-issue \
    --outcome "$OUTCOME" \
    --run-id "$RUN_ID" \
    --mode "$mode_str" \
    --workflow-path "$path_str" \
    --duration "$DURATION" \
    --claude-tokens "$CLAUDE_T" \
    --codex-tokens "$CODEX_T" \
    --cursor-tokens "$CURSOR_T" \
    --issue-number "$ISSUE" \
    --issue-url "${ISSUE_URL:-N/A}" \
    --pr-number "${PR_NUMBER:-0}" \
    --pr-url "${PR_URL:-N/A}" \
    --plan-review-line "$plan_line" \
    --code-review-line "$code_line" \
    --oos-count "$oos_count" \
    --oos-urls "$oos_urls" \
    --exec-issues "$exec_n" \
    --warnings "$warn_n" \
    --run-logs-path "$run_logs" \
    --output-file "$body_tmp" >/dev/null
rr=$?
set -e

if [ "$rr" -ne 0 ] || [ ! -s "$body_tmp" ]; then
    {
        printf '## /fix-issue run %s — %s\n\n' "$RUN_ID" "$OUTCOME"
        printf '%s\n' "- **Outcome**: $OUTCOME (summary render degraded)"
        printf '%s\n' '<!-- larch:run-summary v=1 -->'
    } > "$body_tmp"
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

if [ "$skip_upsert" = true ] || [ "$ISSUE" = "0" ]; then
    emit_kv_out COMMENT_URL ""
    emit_kv_out STATUS skipped
    emit_kv_out REASON "fix-issue-summary-not-posted"
    exit 0
fi

case "$ISSUE" in *[!0-9]*|"") emit_kv_out COMMENT_URL ""; emit_kv_out STATUS failed; emit_kv_out ERROR "ISSUE_NUMBER must be numeric"; exit 1 ;; esac

summary_tmp="$(mktemp "${TMPDIR:-/tmp}/fix-wfr-summary.XXXXXX")"
cp "$body_tmp" "$summary_tmp"
trap 'rm -f "$body_tmp" "$summary_tmp"' EXIT

args=(upsert-summary --issue "$ISSUE" --marker "<!-- larch:fix-issue:final-summary v=1 -->" --content-file "$summary_tmp")
[ -z "$REPO_ARG" ] || args+=(--repo "$REPO_ARG")
_adj_tmp="${FIX_TMP:-${TMPDIR:-/tmp}}"
outf="$_adj_tmp/write-final-report-fix-$$.out"
errf="$_adj_tmp/write-final-report-fix-$$.err"
mkdir -p "$(dirname "$outf")" 2>/dev/null || true
if "$PLUGIN_ROOT/scripts/tracking-issue-summary.sh" "${args[@]}" >"$outf" 2>"$errf"; then
    emit_kv_out COMMENT_URL "$(awk -F= '$1=="COMMENT_URL"{print substr($0,index($0,"=")+1); exit}' "$outf")"
    emit_kv_out STATUS ok
    exit 0
fi

emit_kv_out COMMENT_URL ""
emit_kv_out STATUS failed
emit_kv_out ERROR "$(tr '\n' ' ' < "$errf" 2>/dev/null | head -c 500)"
exit 1
