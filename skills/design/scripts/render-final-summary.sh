#!/usr/bin/env bash
# render-final-summary.sh — /design terminal summary: gather artifacts, render-run-summary, upsert.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"

usage() {
    printf '%s\n' "Usage: render-final-summary.sh --outcome <o> --mode <m> [--repo R] [--pre-publish-only | --post-publish-only]" >&2
    printf '%s\n' "Requires env: DESIGN_TMPDIR, SESSION_ID, ISSUE_NUMBER (may be empty)." >&2
}

OUTCOME=""
MODE_STR=""
REPO_OPT=""
PHASE="post" # post = print + upsert + file; pre = file only

while [ $# -gt 0 ]; do
    case "$1" in
        --outcome) [ $# -ge 2 ] || { usage; exit 2; }; OUTCOME=$2; shift 2 ;;
        --mode) [ $# -ge 2 ] || { usage; exit 2; }; MODE_STR=$2; shift 2 ;;
        --repo) [ $# -ge 2 ] || { usage; exit 2; }; REPO_OPT=$2; shift 2 ;;
        --pre-publish-only) PHASE=pre; shift ;;
        --post-publish-only) PHASE=post; shift ;;
        -h|--help) usage; exit 0 ;;
        *) usage; exit 2 ;;
    esac
done

[ -n "${DESIGN_TMPDIR:-}" ] || { printf '%s\n' "render-final-summary.sh: DESIGN_TMPDIR unset" >&2; exit 2; }
[ -d "$DESIGN_TMPDIR" ] || { printf '%s\n' "render-final-summary.sh: DESIGN_TMPDIR not a directory" >&2; exit 2; }
[ -n "$OUTCOME" ] || { usage; exit 2; }
[ -n "$MODE_STR" ] || { usage; exit 2; }

case "$OUTCOME" in
    approved|cancelled-clarify|cancelled-already-planned|cancelled-tier-gate|cancelled-sprawl|cancelled-plan-size-hard|failed-plan-write) ;;
    *)
        printf '%s\n' "render-final-summary.sh: outcome not in enumeration: $OUTCOME" >&2
        exit 2
        ;;
esac

RUN_ID="${SESSION_ID:-}"
[ -n "$RUN_ID" ] || RUN_ID="unknown"

WORKFLOW_PATH="unknown"
if [ -f "$DESIGN_TMPDIR/run-params.json" ] && command -v jq >/dev/null 2>&1; then
    WORKFLOW_PATH=$(jq -r '.workflow_path // "unknown"' "$DESIGN_TMPDIR/run-params.json" 2>/dev/null || echo unknown)
fi

ISSUE="${ISSUE_NUMBER:-}"
[ -n "$ISSUE" ] || ISSUE=""

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

REPO="${REPO_OPT:-}"
ISSUE_URL="N/A"
if [ -n "$ISSUE" ] && [ "$ISSUE" != "0" ]; then
    ISSUE_URL=$(issue_url_from_repo "$REPO" "$ISSUE" || echo "N/A")
fi

# --- Token + timing JSON (best-effort) ---
rm -f "$DESIGN_TMPDIR/token-report-final.json" "$DESIGN_TMPDIR/token-report-final.stderr.log" \
    "$DESIGN_TMPDIR/timing-report-final.json" "$DESIGN_TMPDIR/timing-report-final.stderr.log" 2>/dev/null || true
set +e
export DESIGN_TMPDIR
export IMPLEMENT_TMPDIR="${IMPLEMENT_TMPDIR:-}"
"$PLUGIN_ROOT/scripts/token-report.sh" --full --format json \
    --output "$DESIGN_TMPDIR/token-report-final.json" 2>"$DESIGN_TMPDIR/token-report-final.stderr.log"
trc=$?
set -e
if [ "$trc" -ne 0 ] || [ ! -s "$DESIGN_TMPDIR/token-report-final.json" ]; then
    : # captured below
    true
fi

set +e
LARCH_TIMING_SKILL=design \
    "$PLUGIN_ROOT/scripts/timing-report.sh" --full --format json \
    --output "$DESIGN_TMPDIR/timing-report-final.json" 2>"$DESIGN_TMPDIR/timing-report-final.stderr.log"
tmrc=$?
set -e
if [ "$tmrc" -ne 0 ] || [ ! -s "$DESIGN_TMPDIR/timing-report-final.json" ]; then
    true
fi

# --- Duration ---
DURATION=""
if [ -f "$DESIGN_TMPDIR/timing-report-final.json" ] && command -v jq >/dev/null 2>&1; then
    DURATION=$(jq -r 'if .total_hms then .total_hms elif .total_seconds then (.total_seconds | tostring + "s") else empty end' \
        "$DESIGN_TMPDIR/timing-report-final.json" 2>/dev/null || true)
fi

# --- Token buckets + cost-unavailable (FINDING_12) ---
CLAUDE_T=0 CODEX_T=0 CURSOR_T=0
C_IN=0 C_CR=0 C_CW5=0 C_CW1=0 C_OUT=0
D_IN=0 D_CACHED=0 D_OUT=0
U_IN=0 U_CR=0 U_OUT=0
COST_ARGS=()
tok_json="$DESIGN_TMPDIR/token-report-final.json"
stderr_nonempty=false
[ -s "$DESIGN_TMPDIR/token-report-final.stderr.log" ] && stderr_nonempty=true

jq_ok=false
if command -v jq >/dev/null 2>&1 && [ -f "$tok_json" ] && jq -e '.claude.totals' "$tok_json" >/dev/null 2>&1; then
    jq_ok=true
fi

if [ "$jq_ok" = true ]; then
    read -r CLAUDE_T CODEX_T CURSOR_T < <(jq -r '[.claude.totals.total // 0, (.codex.totals.total // 0), (.cursor.totals.total // 0)] | @tsv' "$tok_json" 2>/dev/null || printf '0\t0\t0\n')
    if jq -e '.BUCKETS_claude' "$tok_json" >/dev/null 2>&1; then
        read -r C_IN C_CR C_CW5 C_CW1 C_OUT < <(jq -r '[.BUCKETS_claude.input, .BUCKETS_claude.cache_read, .BUCKETS_claude.cache_create_5m, .BUCKETS_claude.cache_create_1h, .BUCKETS_claude.output] | @tsv' "$tok_json" 2>/dev/null || printf '0\t0\t0\t0\t0\n')
        read -r D_IN D_CACHED D_OUT < <(jq -r '[.BUCKETS_codex.input, .BUCKETS_codex.cached_input, .BUCKETS_codex.output] | @tsv' "$tok_json" 2>/dev/null || printf '0\t0\t0\n')
        read -r U_IN U_CR U_OUT < <(jq -r '[.BUCKETS_cursor.input, .BUCKETS_cursor.cache_read, .BUCKETS_cursor.output] | @tsv' "$tok_json" 2>/dev/null || printf '0\t0\t0\n')
    fi
    sum_b=$((C_IN + C_CR + C_CW5 + C_CW1 + C_OUT + D_IN + D_CACHED + D_OUT + U_IN + U_CR + U_OUT))
    if [ "$sum_b" -eq 0 ] && [ "$stderr_nonempty" = true ]; then
        COST_ARGS=()
        if [ ! -f "$DESIGN_TMPDIR/token-report-final.failure.log" ]; then
            cp "$DESIGN_TMPDIR/token-report-final.stderr.log" "$DESIGN_TMPDIR/token-report-final.failure.log" 2>/dev/null || true
        fi
        "$PLUGIN_ROOT/scripts/append-tool-failure.sh" \
            --log "$DESIGN_TMPDIR/execution-issues.md" \
            --site "design final summary" \
            --tool "token-report.sh" \
            --exit-code "${trc:-1}" \
            --category Warnings \
            --output-file "$DESIGN_TMPDIR/token-report-final.failure.log" \
            >/dev/null 2>&1 || true
    else
        COST_ARGS=(
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
else
    COST_ARGS=()
    if [ "$stderr_nonempty" = true ] || [ "$trc" -ne 0 ]; then
        : >"$DESIGN_TMPDIR/token-report-final.failure.log" 2>/dev/null || true
        if [ -s "$DESIGN_TMPDIR/token-report-final.stderr.log" ]; then
            cat "$DESIGN_TMPDIR/token-report-final.stderr.log" >>"$DESIGN_TMPDIR/token-report-final.failure.log" 2>/dev/null || true
        fi
        "$PLUGIN_ROOT/scripts/append-tool-failure.sh" \
            --log "$DESIGN_TMPDIR/execution-issues.md" \
            --site "design final summary" \
            --tool "token-report.sh" \
            --exit-code "${trc:-1}" \
            --category Warnings \
            --output-file "$DESIGN_TMPDIR/token-report-final.failure.log" \
            >/dev/null 2>&1 || true
    fi
fi

if [ -z "$DURATION" ]; then
    if [ ! -f "$DESIGN_TMPDIR/timing-report-final.json" ] || [ "$tmrc" -ne 0 ]; then
        : >"$DESIGN_TMPDIR/timing-report-final.failure.log" 2>/dev/null || true
        if [ -s "$DESIGN_TMPDIR/timing-report-final.stderr.log" ]; then
            cat "$DESIGN_TMPDIR/timing-report-final.stderr.log" >>"$DESIGN_TMPDIR/timing-report-final.failure.log" 2>/dev/null || true
        fi
        "$PLUGIN_ROOT/scripts/append-tool-failure.sh" \
            --log "$DESIGN_TMPDIR/execution-issues.md" \
            --site "design final summary" \
            --tool "timing-report.sh" \
            --exit-code "${tmrc:-1}" \
            --category Warnings \
            --output-file "$DESIGN_TMPDIR/timing-report-final.failure.log" \
            >/dev/null 2>&1 || true
    fi
fi

# --- execution-issues.md: exec vs warnings (FINDING_13) ---
EXEC_ISSUES=0
WARNINGS=0
ex_file="$DESIGN_TMPDIR/execution-issues.md"
if [ -f "$ex_file" ] && [ -s "$ex_file" ]; then
    read -r EXEC_ISSUES WARNINGS < <(awk '
      /^### Tool Failures$/ { sec=1; next }
      /^### External Reviewer Issues$/ { sec=1; next }
      /^### Warnings$/ { sec=2; next }
      /^### / { sec=0; next }
      /^\*\*Step / {
        if (sec == 1) ex++
        if (sec == 2) wa++
        next
      }
      END { print ex+0, wa+0 }
    ' "$ex_file")
fi

# --- Plan review line ---
PLAN_LINE="0 findings"
if [ ! -f "$DESIGN_TMPDIR/voting-tally.md" ]; then
    case "$MODE_STR" in *--trivial*|*trivial*) PLAN_LINE="skipped (trivial)" ;; *) PLAN_LINE="0 findings" ;; esac
else
    apf="$DESIGN_TMPDIR/accepted-plan-findings.md"
    oaf="$DESIGN_TMPDIR/oos-accepted-design.md"
    if { [ ! -f "$apf" ] || [ ! -s "$apf" ]; } && { [ ! -f "$oaf" ] || [ ! -s "$oaf" ]; }; then
        PLAN_LINE="0 findings"
    else
        read -r acnt xc yc zc wc < <(awk '
          function bump(fa,   a) {
            a = tolower(fa)
            gsub(/^[[:space:]]+|[[:space:]]+$/, "", a)
            if (a == "security") { cx++; return }
            if (a == "correctness" || a == "risk-integration") { hy++; return }
            if (a == "architecture" || a == "code-quality") { md++; return }
            lw++
          }
          BEGIN { cx=0; hy=0; md=0; lw=0; inf=0 }
          FNR == 1 { inf=0 }
          /^### (FINDING_|OOS_)/ { inf=1; next }
          inf && /^- focus-area[[:space:]]*=[[:space:]]*/ {
            sub(/^- focus-area[[:space:]]*=[[:space:]]*/, "")
            bump($0)
            inf=0
            next
          }
          /^### / { inf=0 }
          END {
            n = cx+hy+md+lw
            print n, cx+0, hy+0, md+0, lw+0
          }
        ' "$apf" "$oaf" 2>/dev/null || echo "0 0 0 0 0")
        if [ "${acnt:-0}" -eq 0 ] 2>/dev/null; then
            PLAN_LINE="0 findings"
        else
            PLAN_LINE="${acnt} accepted (${xc} critical / ${yc} high / ${zc} medium / ${wc} low)"
        fi
    fi
fi

# --- OOS filed ---
OOS_COUNT=0
OOS_URLS=""
if [ -f "$DESIGN_TMPDIR/oos-issues-created.md" ] && [ -s "$DESIGN_TMPDIR/oos-issues-created.md" ]; then
    OOS_COUNT=$(grep -chE 'https://github.com[^[:space:])>]+' "$DESIGN_TMPDIR/oos-issues-created.md" 2>/dev/null | head -1 || echo 0)
    case "$OOS_COUNT" in ''|*[!0-9]*) OOS_COUNT=0 ;; esac
    OOS_URLS=$(grep -hoE 'https://github.com[^"[:space:])>]+' "$DESIGN_TMPDIR/oos-issues-created.md" 2>/dev/null | sort -u | paste -sd, - || true)
fi

RUN_LOGS_PATH="N/A"
if [ -n "$RUN_ID" ] && [ "$RUN_ID" != "unknown" ]; then
    RUN_LOGS_PATH="larch-logs/design/${RUN_ID}/"
fi

invoke_render() {
    local print_stdout=$1
    local out_file="$DESIGN_TMPDIR/final-summary.md"
    local print_arg=()
    if [ "$print_stdout" = true ]; then
        print_arg=(--print-stdout)
    fi
    _rr_args=(
        --skill design
        --outcome "$OUTCOME"
        --run-id "$RUN_ID"
        --mode "$MODE_STR"
        --workflow-path "$WORKFLOW_PATH"
        --duration "$DURATION"
        --issue-number "$ISSUE"
        --issue-url "$ISSUE_URL"
        --pr-number 0
        --pr-url "N/A"
        --plan-review-line "$PLAN_LINE"
        --code-review-line "N/A"
        --oos-count "$OOS_COUNT"
        --oos-urls "${OOS_URLS:-}"
        --exec-issues "$EXEC_ISSUES"
        --warnings "$WARNINGS"
        --run-logs-path "$RUN_LOGS_PATH"
        --output-file "$out_file"
    )
    if [ "${#COST_ARGS[@]}" -eq 0 ]; then
        "$PLUGIN_ROOT/scripts/render-run-summary.sh" "${_rr_args[@]}" "${print_arg[@]+"${print_arg[@]}"}"
    else
        "$PLUGIN_ROOT/scripts/render-run-summary.sh" "${_rr_args[@]}" "${COST_ARGS[@]}" "${print_arg[@]+"${print_arg[@]}"}"
    fi
}

if [ "$PHASE" = pre ]; then
    invoke_render false
    exit 0
fi

# post phase: render to file and print body to stdout (same bytes as file per render-run-summary contract)
invoke_render true

if [ -n "$ISSUE" ] && [ "$ISSUE" != "0" ] && [ -s "$DESIGN_TMPDIR/final-summary.md" ]; then
    marker="<!-- larch:final-summary v1 runid=${RUN_ID} -->"
    set +e
    ups_err="$(mktemp "${TMPDIR:-/tmp}/rfs-ups-err.XXXXXX")"
    if [ -n "$REPO" ]; then
        "$PLUGIN_ROOT/scripts/tracking-issue-summary.sh" upsert-summary \
            --issue "$ISSUE" \
            --marker "$marker" \
            --content-file "$DESIGN_TMPDIR/final-summary.md" \
            --repo "$REPO" 2>"$ups_err"
    else
        "$PLUGIN_ROOT/scripts/tracking-issue-summary.sh" upsert-summary \
            --issue "$ISSUE" \
            --marker "$marker" \
            --content-file "$DESIGN_TMPDIR/final-summary.md" 2>"$ups_err"
    fi
    ups_rc=$?
    set -e
    if [ "$ups_rc" -ne 0 ]; then
        "$PLUGIN_ROOT/scripts/append-tool-failure.sh" \
            --log "$DESIGN_TMPDIR/execution-issues.md" \
            --site "design Step 5" \
            --tool "tracking-issue-summary.sh upsert-summary" \
            --exit-code "$ups_rc" \
            --category Warnings \
            --output-file "$ups_err" \
            >/dev/null 2>&1 || true
    fi
    rm -f "$ups_err"
fi

exit 0
