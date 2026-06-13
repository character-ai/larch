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
# shellcheck source=scripts/lib-quiet.sh
# shellcheck disable=SC1091
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init
# shellcheck source=scripts/lib-design-tmpdir.sh
# shellcheck disable=SC1091
source "$PLUGIN_ROOT/scripts/lib-design-tmpdir.sh"
larch_design_tmpdir_validate "$DESIGN_TMPDIR" || exit $?
[ -n "$OUTCOME" ] || { usage; exit 2; }
if [ "$OUTCOME" = "cancelled-title-filter" ]; then
    MODE_STR="Refused (title-filter)"
fi

[ -n "$MODE_STR" ] || MODE_STR=N/A

# Enum order is file-order (newest entries appended before failed-plan-write);
# SKILL.md Step 0b uses alphabetical-within-cancelled documentation order.
# Both forms accept the same token set.
case "$OUTCOME" in
    approved|approved-partition|cancelled-clarify|cancelled-already-planned|cancelled-reentry-guard|cancelled-title-filter|cancelled-sprawl|cancelled-plan-size|cancelled-decompose|cancelled-outline|failed-plan-write|failed-publish|failed-postplan|failed-clarify|failed-judge-panel|failed-publish-tail|publish-skipped) ;;
    *)
        larch_err "render-final-summary.sh: outcome not in enumeration: $OUTCOME"
        exit 2
        ;;
esac

RUN_ID="${SESSION_ID:-}"
[ -n "$RUN_ID" ] || RUN_ID="unknown"


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
python3 "$PLUGIN_ROOT/python/cli.py" token report --full --format json \
    --output "$DESIGN_TMPDIR/token-report-final.json" 2>"$DESIGN_TMPDIR/token-report-final.stderr.log"
trc=$?
set -e
if [ "$trc" -ne 0 ] || [ ! -s "$DESIGN_TMPDIR/token-report-final.json" ]; then
    : # captured below
    true
fi

set +e
LARCH_TIMING_SKILL=design LARCH_TIMING_LEDGER="$DESIGN_TMPDIR/timing-ledger.tsv" \
    env -u IMPLEMENT_TMPDIR \
    python3 "$PLUGIN_ROOT/python/cli.py" timing report --full --format json \
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
CLAUDE_T=0 CODEX_T=0 CURSOR_T=0 CLAUDE_SUB_T=0
C_IN=0 C_CR=0 C_CW5=0 C_CW1=0 C_OUT=0
D_IN=0 D_CACHED=0 D_OUT=0
U_IN=0 U_CR=0 U_OUT=0
CS_IN=0 CS_CR=0 CS_CW5=0 CS_CW1=0 CS_OUT=0
COST_ARGS=()
_cost_unavailable=false
tok_json="$DESIGN_TMPDIR/token-report-final.json"
stderr_nonempty=false
[ -s "$DESIGN_TMPDIR/token-report-final.stderr.log" ] && stderr_nonempty=true

jq_ok=false
if command -v jq >/dev/null 2>&1 && [ -f "$tok_json" ] && jq -e '.claude.totals' "$tok_json" >/dev/null 2>&1; then
    jq_ok=true
fi

if [ "$jq_ok" = true ]; then
    read -r CLAUDE_T CODEX_T CURSOR_T CLAUDE_SUB_T < <(jq -r '[.claude.totals.total // 0, (.codex.totals.total // 0), (.cursor.totals.total // 0), (.claude_sub.totals.total // 0)] | @tsv' "$tok_json" 2>/dev/null || printf '0\t0\t0\t0\n')
    if jq -e '.BUCKETS_claude' "$tok_json" >/dev/null 2>&1; then
        read -r C_IN C_CR C_CW5 C_CW1 C_OUT < <(jq -r '[.BUCKETS_claude.input, .BUCKETS_claude.cache_read, .BUCKETS_claude.cache_create_5m, .BUCKETS_claude.cache_create_1h, .BUCKETS_claude.output] | @tsv' "$tok_json" 2>/dev/null || printf '0\t0\t0\t0\t0\n')
        read -r D_IN D_CACHED D_OUT < <(jq -r '[.BUCKETS_codex.input, .BUCKETS_codex.cached_input, .BUCKETS_codex.output] | @tsv' "$tok_json" 2>/dev/null || printf '0\t0\t0\n')
        read -r U_IN U_CR U_OUT < <(jq -r '[.BUCKETS_cursor.input, .BUCKETS_cursor.cache_read, .BUCKETS_cursor.output] | @tsv' "$tok_json" 2>/dev/null || printf '0\t0\t0\n')
        read -r CS_IN CS_CR CS_CW5 CS_CW1 CS_OUT < <(jq -r '[.BUCKETS_claude_sub.input, .BUCKETS_claude_sub.cache_read, .BUCKETS_claude_sub.cache_create_5m, .BUCKETS_claude_sub.cache_create_1h, .BUCKETS_claude_sub.output] | @tsv' "$tok_json" 2>/dev/null || printf '0\t0\t0\t0\t0\n')
    fi
    sum_b=$((C_IN + C_CR + C_CW5 + C_CW1 + C_OUT + D_IN + D_CACHED + D_OUT + U_IN + U_CR + U_OUT + CS_IN + CS_CR + CS_CW5 + CS_CW1 + CS_OUT))
    total_t=$((CLAUDE_T + CODEX_T + CURSOR_T + CLAUDE_SUB_T))
    if [ "$sum_b" -eq 0 ] && [ "$total_t" -eq 0 ]; then
        _cost_unavailable=true
        if [ "$stderr_nonempty" = true ] && [ ! -f "$DESIGN_TMPDIR/token-report-final.failure.log" ]; then
            cp "$DESIGN_TMPDIR/token-report-final.stderr.log" "$DESIGN_TMPDIR/token-report-final.failure.log" 2>/dev/null || true
        fi
        if [ "$stderr_nonempty" = true ]; then
            python3 "$PLUGIN_ROOT/python/cli.py" run-log append-failure \
                --log "$DESIGN_TMPDIR/execution-issues.md" \
                --site "design final summary" \
                --tool "python3 python/cli.py token report" \
                --exit-code "${trc:-1}" \
                --category Warnings \
                --redact \
                --output-file "$DESIGN_TMPDIR/token-report-final.failure.log" \
                >/dev/null 2>&1 || true
        fi
    elif [ "$sum_b" -eq 0 ]; then
        COST_ARGS=(
            --claude-tokens "$CLAUDE_T"
            --codex-tokens "$CODEX_T"
            --cursor-tokens "$CURSOR_T"
            --claude-sub-tokens "$CLAUDE_SUB_T"
        )
    else
        COST_ARGS=(
            --claude-tokens "$CLAUDE_T"
            --codex-tokens "$CODEX_T"
            --cursor-tokens "$CURSOR_T"
            --claude-sub-tokens "$CLAUDE_SUB_T"
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
            --claude-sub-input-tokens "$CS_IN"
            --claude-sub-cache-read-tokens "$CS_CR"
            --claude-sub-cache-write-5m-tokens "$CS_CW5"
            --claude-sub-cache-write-1h-tokens "$CS_CW1"
            --claude-sub-output-tokens "$CS_OUT"
        )
    fi
else
    _cost_unavailable=true
    if [ "$stderr_nonempty" = true ] || [ "$trc" -ne 0 ]; then
        : >"$DESIGN_TMPDIR/token-report-final.failure.log" 2>/dev/null || true
        if [ -s "$DESIGN_TMPDIR/token-report-final.stderr.log" ]; then
            cat "$DESIGN_TMPDIR/token-report-final.stderr.log" >>"$DESIGN_TMPDIR/token-report-final.failure.log" 2>/dev/null || true
        fi
        python3 "$PLUGIN_ROOT/python/cli.py" run-log append-failure \
            --log "$DESIGN_TMPDIR/execution-issues.md" \
            --site "design final summary" \
            --tool "python3 python/cli.py token report" \
            --exit-code "${trc:-1}" \
            --category Warnings \
            --redact \
            --output-file "$DESIGN_TMPDIR/token-report-final.failure.log" \
            >/dev/null 2>&1 || true
    fi
fi

if [ -z "$DURATION" ]; then
    if [ ! -f "$DESIGN_TMPDIR/timing-report-final.json" ] || [ "${tmrc:-0}" -ne 0 ]; then
        : >"$DESIGN_TMPDIR/timing-report-final.failure.log" 2>/dev/null || true
        if [ -s "$DESIGN_TMPDIR/timing-report-final.stderr.log" ]; then
            cat "$DESIGN_TMPDIR/timing-report-final.stderr.log" >>"$DESIGN_TMPDIR/timing-report-final.failure.log" 2>/dev/null || true
        fi
        python3 "$PLUGIN_ROOT/python/cli.py" run-log append-failure \
            --log "$DESIGN_TMPDIR/execution-issues.md" \
            --site "design final summary" \
            --tool "python3 python/cli.py timing report" \
            --exit-code "${tmrc:-1}" \
            --category Warnings \
            --redact \
            --output-file "$DESIGN_TMPDIR/timing-report-final.failure.log" \
            >/dev/null 2>&1 || true
    fi
fi

# --- execution-issues.md: exec vs warnings (FINDING_13) ---
EXEC_ISSUES=0
WARNINGS=0
refresh_issue_counts() {
    EXEC_ISSUES=0
    WARNINGS=0
    ex_file="$DESIGN_TMPDIR/execution-issues.md"
    if [ -f "$ex_file" ] && [ -s "$ex_file" ]; then
        _issue_counts=$(python3 - "$ex_file" 2>/dev/null <<'PY'
import sys

section = 0
fenced = False
exec_issues = 0
warnings = 0

try:
    with open(sys.argv[1], "r", encoding="utf-8", errors="replace") as handle:
        for raw_line in handle:
            line = raw_line.rstrip("\r\n")
            stripped = line.strip()

            if stripped == chr(96) * 3:
                fenced = not fenced
                continue
            if fenced:
                continue

            if stripped in ("### Tool Failures", "### External Reviewer Issues"):
                section = 1
                continue
            if stripped == "### Warnings":
                section = 2
                continue
            if stripped.startswith("### "):
                section = 0
                continue

            if line.startswith("- **"):
                if section == 1:
                    exec_issues += 1
                elif section == 2:
                    warnings += 1
except OSError:
    pass

print(exec_issues, warnings)
PY
        ) || _issue_counts="0 0"
        _exec_issue_count=0
        _warning_count=0
        read -r _exec_issue_count _warning_count _count_extra <<EOF_COUNTS
$_issue_counts
EOF_COUNTS
        case "$_exec_issue_count" in "" | *[!0123456789]*) EXEC_ISSUES=0 ;; *) EXEC_ISSUES="$_exec_issue_count" ;; esac
        case "$_warning_count" in "" | *[!0123456789]*) WARNINGS=0 ;; *) WARNINGS="$_warning_count" ;; esac
    fi
}

BLOCKED_POLLING_ATTEMPTS=0
read_bg_poll_guard_denials() {
    local count_file="$DESIGN_TMPDIR/bg-poll-guard-denials.count" value
    [ -f "$count_file" ] && [ ! -L "$count_file" ] || return 0
    value=$(awk 'NR==1 { print; exit }' "$count_file" 2>/dev/null || printf '0')
    case "$value" in ''|*[!0-9]*) value=0 ;; esac
    BLOCKED_POLLING_ATTEMPTS=$value
}

record_bg_poll_guard_warning() {
    [ "${BLOCKED_POLLING_ATTEMPTS:-0}" -gt 0 ] 2>/dev/null || return 0
    [ ! -f "$DESIGN_TMPDIR/.bg-poll-guard-warning-recorded" ] || return 0
    local warn_file="$DESIGN_TMPDIR/bg-poll-guard-warning.log"
    printf 'Blocked polling attempts: %s\n' "$BLOCKED_POLLING_ATTEMPTS" >"$warn_file" 2>/dev/null || return 0
    if python3 "$PLUGIN_ROOT/python/cli.py" run-log append-failure \
        --log "$DESIGN_TMPDIR/execution-issues.md" \
        --site "design immediate-background wait" \
        --tool "hook-bg-poll-guard.sh" \
        --exit-code 0 \
        --category Warnings \
        --redact \
        --output-file "$warn_file" \
        >/dev/null 2>&1; then
        : >"$DESIGN_TMPDIR/.bg-poll-guard-warning-recorded" 2>/dev/null || true
    fi
}

read_bg_poll_guard_denials
record_bg_poll_guard_warning
refresh_issue_counts

# --- Plan review line ---
PLAN_LINE="0 findings"
apf="$DESIGN_TMPDIR/accepted-plan-findings-all.md"
if [ ! -s "$apf" ]; then
    apf="$DESIGN_TMPDIR/accepted-plan-findings.md"
fi
filter_gate_b_skipped_findings() {
    local accepted_file="$1" rejected_file="$2" out_file="$3"
    python3 - "$accepted_file" "$rejected_file" "$out_file" <<'PY'
import re
import sys
from pathlib import Path

accepted_path, rejected_path, out_path = map(Path, sys.argv[1:4])
reason = "rejected by user during one-by-one review"

def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""

def blocks(text: str, prefix: str):
    pattern = rf"(?ms)^### {prefix}_[0-9]+:.*?(?=^### |\Z)"
    return [m.group(0).strip() for m in re.finditer(pattern, text)]

def normalize(block: str) -> str:
    lines = [line.rstrip() for line in block.strip().splitlines() if reason not in line]
    return "\n".join(lines).strip()

skipped = {normalize(block) for block in blocks(read(rejected_path), "FINDING") if reason in block}
accepted = [block for block in blocks(read(accepted_path), "FINDING") if normalize(block) not in skipped]
body = "\n\n".join(accepted)
if body:
    body += "\n\n"
out_path.write_text(body, encoding="utf-8")
PY
}
if [ -s "$apf" ] && [ -s "$DESIGN_TMPDIR/rejected-findings.md" ] \
    && grep -Fq 'rejected by user during one-by-one review' "$DESIGN_TMPDIR/rejected-findings.md" 2>/dev/null; then
    _filtered_apf="$DESIGN_TMPDIR/.final-summary-accepted-plan-findings.md"
    if filter_gate_b_skipped_findings "$apf" "$DESIGN_TMPDIR/rejected-findings.md" "$_filtered_apf" 2>/dev/null; then
        apf="$_filtered_apf"
    fi
fi
oaf="$DESIGN_TMPDIR/oos-accepted-design.md"
if { [ ! -f "$apf" ] || [ ! -s "$apf" ]; } && { [ ! -f "$oaf" ] || [ ! -s "$oaf" ]; }; then
    PLAN_LINE="0 findings"
else
    plan_review_count_inputs=()
    [ -s "$apf" ] && plan_review_count_inputs+=("$apf")
    [ -s "$oaf" ] && plan_review_count_inputs+=("$oaf")
    read -r acnt xc yc zc wc < <(awk '
          function bump(fa,   a) {
            a = tolower(fa)
            gsub(/^[[:space:]]+|[[:space:]]+$/, "", a)
            if (a == "security") { cx++; return }
            if (a == "correctness" || a == "risk-integration") { hy++; return }
            if (a == "architecture" || a == "code-quality") { md++; return }
            lw++
          }
          BEGIN { cx=0; hy=0; md=0; lw=0; inf=0; total=0 }
          FNR == 1 { inf=0 }
          /^### (FINDING_|OOS_)[0-9]/ { inf=1; total++; next }
          inf && /^- \*\*Focus area\*\*:[[:space:]]*/ {
            sub(/^- \*\*Focus area\*\*:[[:space:]]*/, "")
            bump($0)
            inf=0
            next
          }
          /^### / { inf=0 }
          END {
            n = cx+hy+md+lw
            if (n < total) { lw += (total - n); n = total }
            print n, cx+0, hy+0, md+0, lw+0
          }
    ' "${plan_review_count_inputs[@]}" 2>/dev/null || echo "0 0 0 0 0")
    if [ "${acnt:-0}" -eq 0 ] 2>/dev/null; then
        PLAN_LINE="0 findings"
    else
        PLAN_LINE="${acnt} accepted (${xc} critical / ${yc} high / ${zc} medium / ${wc} low)"
    fi
fi

# --- OOS filed ---
OOS_COUNT=0
OOS_URLS=""
if [ -f "$DESIGN_TMPDIR/oos-issues-created.md" ] && [ -s "$DESIGN_TMPDIR/oos-issues-created.md" ]; then
    OOS_COUNT=$(grep -chE 'https://github.com[^[:space:])>]+' "$DESIGN_TMPDIR/oos-issues-created.md" 2>/dev/null | head -1 || echo 0)
    case "$OOS_COUNT" in ''|*[!0-9]*) OOS_COUNT=0 ;; esac
    OOS_URLS=$(grep -hoE 'https://github.com[^"[:space:])>]+' "$DESIGN_TMPDIR/oos-issues-created.md" 2>/dev/null | sort -u | paste -sd, - || true)
elif [ -f "$DESIGN_TMPDIR/oos-issue-sentinel" ]; then
    _sent_created=$(awk -F= '$1=="ISSUES_CREATED"{print $2; exit}' \
        "$DESIGN_TMPDIR/oos-issue-sentinel" 2>/dev/null || echo 0)
    _sent_failed=$(awk -F= '$1=="ISSUES_FAILED"{print $2; exit}' \
        "$DESIGN_TMPDIR/oos-issue-sentinel" 2>/dev/null || echo 0)
    case "$_sent_created" in ''|*[!0-9]*) _sent_created=0 ;; esac
    case "$_sent_failed" in ''|*[!0-9]*) _sent_failed=0 ;; esac
    if [ "$_sent_created" -gt 0 ] && [ "$_sent_failed" -eq 0 ]; then
        OOS_COUNT="$_sent_created"
        OOS_URLS="(URLs unavailable — annotate step was skipped)"
    fi
fi

RUN_LOGS_PATH="N/A"
if [ -n "$RUN_ID" ] && [ "$RUN_ID" != "unknown" ] && [ "$OUTCOME" != "failed-publish" ] && [ "$OUTCOME" != "publish-skipped" ]; then
    RUN_LOGS_PATH="larch-logs/design/${RUN_ID}/"
fi

valid_log_pr_number() {
    local value="$1"
    [[ "$value" =~ ^[1-9][0-9]*$ ]]
}

valid_log_pr_url() {
    local value="$1"
    [[ "$value" =~ ^https://github[.]com/[A-Za-z0-9._-]+/[A-Za-z0-9._-]+/pull/[1-9][0-9]*([/?#].*)?$ ]]
}

valid_log_recovery_branch() {
    local value="$1"
    [[ "$value" =~ ^[A-Za-z0-9._/-]+$ ]] || return 1
    git check-ref-format --branch "$value" >/dev/null 2>&1
}

sanitize_failed_publish_notes() {
    [[ -z "${DESIGN_LOG_PR_NUMBER:-}" ]] || valid_log_pr_number "$DESIGN_LOG_PR_NUMBER" || DESIGN_LOG_PR_NUMBER=""
    [[ -z "${DESIGN_LOG_PR_URL:-}" ]] || valid_log_pr_url "$DESIGN_LOG_PR_URL" || DESIGN_LOG_PR_URL=""
    [[ -z "${DESIGN_LOG_RECOVERY_BRANCH:-}" ]] || valid_log_recovery_branch "$DESIGN_LOG_RECOVERY_BRANCH" || DESIGN_LOG_RECOVERY_BRANCH=""
}

append_failed_publish_notes() {
    local out="$1"
    sanitize_failed_publish_notes
    if [ -n "${DESIGN_LOG_RECOVERY_BRANCH:-}" ]; then
        printf '%s\n' "- **Log recovery branch**: \`$DESIGN_LOG_RECOVERY_BRANCH\`" >>"$out"
    fi
    if [ -n "${DESIGN_LOG_PR_NUMBER:-}" ] || [ -n "${DESIGN_LOG_PR_URL:-}" ]; then
        if [ -n "${DESIGN_LOG_PR_NUMBER:-}" ] && [ -n "${DESIGN_LOG_PR_URL:-}" ]; then
            printf -- '- **Log flush PR**: #%s — %s\n' "$DESIGN_LOG_PR_NUMBER" "$DESIGN_LOG_PR_URL" >>"$out"
        elif [ -n "${DESIGN_LOG_PR_NUMBER:-}" ]; then
            printf -- '- **Log flush PR**: #%s\n' "$DESIGN_LOG_PR_NUMBER" >>"$out"
        else
            printf -- '- **Log flush PR**: %s\n' "$DESIGN_LOG_PR_URL" >>"$out"
        fi
    fi
    if [ "${DESIGNED_ADMISSION_READY:-false}" = true ] || { [ "${RENAMED:-}" = true ] && { [ "${UPSERT_RAN:-false}" != true ] || [ "${UPSERT_STATUS:-}" = ok ]; }; }; then
        printf -- '- **Publish recovery**: design logs did not finish publishing and the issue is [DESIGNED]; retry log publish from the preserved design tmpdir before starting /implement when the session may contain secrets.\n' >>"$out"
    elif { [ "${RENAMED:-}" = true ] || { [ "${RENAMED:-}" = false ] && [ "${NEW_TITLE#"[DESIGNED] "}" != "$NEW_TITLE" ]; }; } && [ "${UPSERT_RAN:-false}" = true ] && [ "${UPSERT_STATUS:-}" != ok ]; then
        printf -- "%s\n" "- **Publish recovery**: design logs did not finish publishing and the issue title is [DESIGNED], but the diagram comment was not confirmed; verify or repair \`larch:diagrams\` before starting /implement, then retry logs manually from the preserved design tmpdir." >>"$out"
    else
        printf -- '- **Publish recovery**: design logs did not finish publishing and the [DESIGNED] rename was not confirmed; fix the issue title before /implement, then retry logs manually from the preserved design tmpdir.\n' >>"$out"
    fi
}

invoke_render() {
    local out_file="$DESIGN_TMPDIR/final-summary.md"
    local render_cost_args=()
    local note_file="$DESIGN_TMPDIR/final-summary-notes.md"
    local note_args=()
    if [ "$_cost_unavailable" = true ]; then
        render_cost_args=(--cost-unavailable)
    else
        render_cost_args=(${COST_ARGS[@]+"${COST_ARGS[@]}"})
    fi
    if [ "$OUTCOME" = "cancelled-outline" ]; then
        printf '%s\n' '- **Cancel site**: Step 1d.7 outline gate' >"$note_file"
        note_args=(--note-lines-file "$note_file")
    elif [ "$OUTCOME" = "failed-publish" ]; then
        : >"$note_file"
        append_failed_publish_notes "$note_file"
        note_args=(--note-lines-file "$note_file")
    elif [ "$OUTCOME" = "publish-skipped" ]; then
        printf '%s\n' '- **Publish**: skipped — no SESSION_ID / run-log; the plan was written to the issue.' >"$note_file"
        note_args=(--note-lines-file "$note_file")
    else
        if rm -f "$note_file" 2>/dev/null; then
            note_args=()
        elif [ ! -e "$note_file" ]; then
            note_args=()
        else
            note_args=(--note-lines-file "$note_file")
        fi
    fi
    local _rpd_out="$DESIGN_TMPDIR/review-phase-detail.md"
    rm -f "$_rpd_out" 2>/dev/null || true
    local _rounds_root=""
    if [ -d "$DESIGN_TMPDIR/plan-review" ]; then
        _rounds_root="$DESIGN_TMPDIR/plan-review"
    elif mkdir -p "$DESIGN_TMPDIR/plan-review" 2>/dev/null; then
        _rounds_root="$DESIGN_TMPDIR/plan-review"
    fi
    if [ -n "$_rounds_root" ] && [ -d "$_rounds_root" ] && [ -r "$_rounds_root" ] && [ -x "$_rounds_root" ]; then
        local _rfj="$DESIGN_TMPDIR/review-findings-full.jsonl"
        rm -f "$_rfj" 2>/dev/null || true
        if ! "$PLUGIN_ROOT/scripts/compose-review-findings.sh" \
            --design-artifacts-dir "$DESIGN_TMPDIR" \
            --issue "${ISSUE:-0}" \
            --output "$_rfj" >/dev/null 2>/dev/null; then
            : >"$_rfj"
        fi

        local _rpd_token_ledger="" _rpd_tl
        for _rpd_tl in "$DESIGN_TMPDIR"/larch-tokens-*.jsonl; do
            [ -f "$_rpd_tl" ] && _rpd_token_ledger="$_rpd_tl" && break
        done

        local _rpd_args=(
            --rounds-root "$_rounds_root"
            --findings-file "$_rfj"
            --timing-ledger "$DESIGN_TMPDIR/timing-ledger.tsv"
            --skill design
            --output "$_rpd_out"
        )
        [ -n "$_rpd_token_ledger" ] && _rpd_args+=(--token-ledger "$_rpd_token_ledger")

        if ! "$PLUGIN_ROOT/scripts/render-review-phase-detail.sh" "${_rpd_args[@]}" 2>/dev/null; then
            : >"$_rpd_out"
        fi
    fi
    if [ "${BLOCKED_POLLING_ATTEMPTS:-0}" -gt 0 ] 2>/dev/null; then
        [ -f "$note_file" ] || : >"$note_file"
        printf '%s\n' "- **Blocked polling attempts**: $BLOCKED_POLLING_ATTEMPTS" >>"$note_file"
        note_args=(--note-lines-file "$note_file")
    fi
    if [ -s "$_rpd_out" ]; then
        [ -f "$note_file" ] || : >"$note_file"
        printf '\n' >>"$note_file"
        cat "$_rpd_out" >>"$note_file"
        note_args=(--note-lines-file "$note_file")
    fi
    local _rr_args=(
        --skill design
        --outcome "$OUTCOME"
        --run-id "$RUN_ID"
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
    # Bash 3.2 + nounset requires the safe-empty array idiom; see BASH_AUTHORING.md §3.
    "$PLUGIN_ROOT/scripts/render-run-summary.sh" "${_rr_args[@]}" ${render_cost_args[@]+"${render_cost_args[@]}"} ${note_args[@]+"${note_args[@]}"}
}

append_render_warning() {
    local rc=$1 output_file=$2
    RENDER_WARNING_RECORDED=false
    command -v python3 >/dev/null 2>&1 || return 0
    [ -f "$output_file" ] || : >"$output_file"
    if python3 "$PLUGIN_ROOT/python/cli.py" run-log append-failure \
        --log "$DESIGN_TMPDIR/execution-issues.md" \
        --site "design final summary" \
        --tool "render-run-summary.sh" \
        --exit-code "$rc" \
        --category Warnings \
        --redact \
        --output-file "$output_file" \
        >/dev/null 2>&1; then
        RENDER_WARNING_RECORDED=true
    fi
    refresh_issue_counts
}

compose_self_fallback() {
    local out_file="$DESIGN_TMPDIR/final-summary.md"
    local banner='**⚠ Degraded fallback — full renderer failed; warning recorded in execution issues.**'
    if [ "${RENDER_WARNING_RECORDED:-false}" != "true" ]; then
        banner='**⚠ Degraded fallback — full renderer failed; warning could not be recorded in execution issues.**'
    fi
    {
        printf '## /design run %s — %s\n\n' "$RUN_ID" "$OUTCOME"
        printf '%s\n\n' "$banner"
        case "$OUTCOME" in bailed*|stalled|cancelled-*|failed-*|publish-skipped) printf -- '- **Outcome**: %s\n' "$OUTCOME" ;; esac
        printf -- '- **Duration**: %s\n' "${DURATION:-N/A}"
        printf -- '- **Cost**: N/A\n'
        if [ -n "$ISSUE" ] && [ "$ISSUE" != "0" ]; then
            if [ -n "$ISSUE_URL" ] && [ "$ISSUE_URL" != "N/A" ]; then
                printf -- '- **Issue**: #%s — %s\n' "$ISSUE" "$ISSUE_URL"
            else
                printf -- '- **Issue**: #%s\n' "$ISSUE"
            fi
        else
            printf -- '- **Issue**: N/A\n'
        fi
        printf -- '- **Plan review**: %s\n' "${PLAN_LINE:-N/A}"
        if [ "${OOS_COUNT:-0}" != "0" ] && [ -n "${OOS_URLS:-}" ] && [ "${OOS_URLS:-}" != "N/A" ]; then
            printf -- '- **OOS filed**: %s — %s\n' "$OOS_COUNT" "$OOS_URLS"
        else
            printf -- '- **OOS filed**: %s\n' "${OOS_COUNT:-0}"
        fi
        printf -- '- **Exec issues**: %s\n' "${EXEC_ISSUES:-0}"
        printf -- '- **Warnings**: %s\n' "${WARNINGS:-0}"
        printf -- "- **Run logs**: \`%s\`\n\n" "${RUN_LOGS_PATH:-N/A}"
        printf '%s\n' '<!-- larch:run-summary v=1 -->'
        printf '%s\n' '<!-- larch:final-summary-fallback v1 -->'
        if [ "$OUTCOME" = "failed-publish" ]; then
            append_failed_publish_notes /dev/stdout
        elif [ "$OUTCOME" = "publish-skipped" ]; then
            printf '%s\n' '- **Publish**: skipped — no SESSION_ID / run-log; the plan was written to the issue.'
        fi
        if [ "$OUTCOME" = "cancelled-outline" ]; then
            printf '%s\n' '- **Cancel site**: Step 1d.7 outline gate'
        fi
        if [ "${BLOCKED_POLLING_ATTEMPTS:-0}" -gt 0 ] 2>/dev/null; then
            printf '%s\n' "- **Blocked polling attempts**: $BLOCKED_POLLING_ATTEMPTS"
        fi
    } > "$out_file"
}

summary_has_usable_cost() {
    local file=$1
    [ -s "$file" ] || return 1
    grep -Fq -- '- **Cost**:' "$file" 2>/dev/null || return 1
    ! grep -Fq -- '- **Cost**: N/A' "$file" 2>/dev/null
}

summary_cost_line() {
    local file=$1
    [ -f "$file" ] || return 1
    grep -F -- '- **Cost**:' "$file" 2>/dev/null | head -1
}

summary_cost_is_na_or_missing() {
    local file=$1 cost_line
    cost_line="$(summary_cost_line "$file" || true)"
    [ -z "$cost_line" ] && return 0
    [ "$cost_line" = '- **Cost**: N/A' ]
}

restore_preserved_cost_line() {
    local summary_file=$1 preserved_cost_line=$2
    [ -n "$preserved_cost_line" ] || return 0
    awk -v cost_line="$preserved_cost_line" '
        /^- \*\*Cost\*\*:/ && !done {
            print cost_line
            done = 1
            next
        }
        { print }
    ' "$summary_file" > "${summary_file}.tmp"
    mv "${summary_file}.tmp" "$summary_file"
}



run_design_failure_report_gate() {
    [ "$PHASE" = post ] || return 0
    local helper="$PLUGIN_ROOT/skills/design/scripts/design-failure-report.sh"
    local out_file="$DESIGN_TMPDIR/design-failure-report.stdout.log"
    local err_file="$DESIGN_TMPDIR/design-failure-report.stderr.log"
    [ -x "$helper" ] || return 0
    set +e
    "$helper" --design-tmpdir "$DESIGN_TMPDIR" --outcome "$OUTCOME" ${REPO:+--repo "$REPO"} ${ISSUE:+--issue "$ISSUE"} ${RUN_ID:+--run-id "$RUN_ID"} >"$out_file" 2>"$err_file"
    local gate_rc=$?
    set -e
    if [ "$gate_rc" -ne 0 ]; then
        python3 "$PLUGIN_ROOT/python/cli.py" run-log append-failure \
            --log "$DESIGN_TMPDIR/execution-issues.md" \
            --site "design failure report gate" \
            --tool "design-failure-report.sh" \
            --exit-code "$gate_rc" \
            --category Warnings \
            --redact \
            --output-file "$err_file" \
            >/dev/null 2>&1 || true
        refresh_issue_counts
    fi
}

print_report_gate_sidecars() {
    local sidecar
    for sidecar in "$DESIGN_TMPDIR/design-failure-chat-print.md" "$DESIGN_TMPDIR/design-failure-operator-action-chat.md"; do
        [ -s "$sidecar" ] || continue
        while IFS= read -r line || [ -n "$line" ]; do
            if [ "${LARCH_QUIET_PID:-}" = "$$" ]; then
                printf '%s\n' "$line" >&3
            else
                printf '%s\n' "$line"
            fi
        done <"$sidecar"
    done
}

render_or_fallback() {
    local err_file="$DESIGN_TMPDIR/render-final-summary.stderr.log"
    local summary_file="$DESIGN_TMPDIR/final-summary.md"
    local preserved_cost_line=""
    if [ "$PHASE" = post ] && summary_has_usable_cost "$summary_file"; then
        preserved_cost_line="$(summary_cost_line "$summary_file" || true)"
    fi
    set +e
    invoke_render 2>"$err_file"
    local rr=$?
    set -e
    if [ "$rr" -ne 0 ] || [ ! -s "$summary_file" ]; then
        append_render_warning "${rr:-1}" "$err_file"
        compose_self_fallback
        restore_preserved_cost_line "$summary_file" "$preserved_cost_line"
    elif [ "$PHASE" = post ] && [ -n "$preserved_cost_line" ] && summary_cost_is_na_or_missing "$summary_file"; then
        restore_preserved_cost_line "$summary_file" "$preserved_cost_line"
    fi

}

if [ "$PHASE" = pre ]; then
    render_or_fallback
    exit 0
fi

# post phase: run the report gate, render to file, then print the resolved file exactly once.
run_design_failure_report_gate
render_or_fallback
while IFS= read -r line || [ -n "$line" ]; do
    if [ "${LARCH_QUIET_PID:-}" = "$$" ]; then
        printf '%s\n' "$line" >&3
    else
        printf '%s\n' "$line"
    fi
done < "$DESIGN_TMPDIR/final-summary.md"
print_report_gate_sidecars

if [ -n "$ISSUE" ] && [ "$ISSUE" != "0" ] && [ -s "$DESIGN_TMPDIR/final-summary.md" ]; then
    marker="<!-- larch:final-summary v1 runid=${RUN_ID} -->"
    set +e
    ups_err="$(mktemp "${TMPDIR:-/tmp}/rfs-ups-err.XXXXXX")"
    if [ -n "$REPO" ]; then
        python3 "$PLUGIN_ROOT/python/cli.py" tracking-issue upsert-summary \
            --issue "$ISSUE" \
            --marker "$marker" \
            --content-file "$DESIGN_TMPDIR/final-summary.md" \
            --repo "$REPO" 2>"$ups_err"
    else
        python3 "$PLUGIN_ROOT/python/cli.py" tracking-issue upsert-summary \
            --issue "$ISSUE" \
            --marker "$marker" \
            --content-file "$DESIGN_TMPDIR/final-summary.md" 2>"$ups_err"
    fi
    ups_rc=$?
    set -e
    if [ "$ups_rc" -ne 0 ]; then
        python3 "$PLUGIN_ROOT/python/cli.py" run-log append-failure \
            --log "$DESIGN_TMPDIR/execution-issues.md" \
            --site "design Step 5" \
            --tool "python3 python/cli.py tracking-issue upsert-summary" \
            --exit-code "$ups_rc" \
            --category Warnings \
            --redact \
            --output-file "$ups_err" \
            >/dev/null 2>&1 || true
    fi
    rm -f "$ups_err"
fi

exit 0
