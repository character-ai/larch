#!/usr/bin/env bash
# assess-plan-round.sh — HARD-only plan-quality assessor orchestrator for Step 3.6.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init
larch_quiet_append_done_trap
# shellcheck source=scripts/lib-design-tmpdir.sh
source "$PLUGIN_ROOT/scripts/lib-design-tmpdir.sh"

DESIGN_TMPDIR=""
CODEX_PRESENT=""
CURSOR_PRESENT=""
TIMEOUT="1860"

usage() {
    larch_err "Usage: assess-plan-round.sh --design-tmpdir DIR --codex-present true|false --cursor-present true|false [--timeout SECS]"
}

read_workflow_path() {
    local params="$DESIGN_TMPDIR/run-params.json"
    local parsed=""
    [[ -f "$params" ]] || return 0
    if command -v jq >/dev/null 2>&1; then
        parsed=$(jq -r '.workflow_path // ""' "$params" 2>/dev/null || echo "")
    fi
    if [[ -z "$parsed" ]]; then
        parsed=$(sed -n 's/.*"workflow_path"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$params" | head -1)
    fi
    printf '%s' "$parsed"
}

read_round_cursor() {
    local snap_sh="${LARCH_SNAPSHOT_PLAN_ROUND_SH:-$PLUGIN_ROOT/skills/design/scripts/snapshot-plan-round.sh}"
    local out
    out=$("$snap_sh" read-cursor --design-tmpdir "$DESIGN_TMPDIR")
    ROUND_NUM=1
    while IFS= read -r line || [[ -n "$line" ]]; do
        case "$line" in
            ROUND_CURSOR=*) ROUND_NUM="${line#ROUND_CURSOR=}" ;;
        esac
    done <<<"$out"
}

emit_assessor_kv() {
    local status="$1" verdict="$2" effective="${3:-0}" verdict_file="${4:-}" verdict_env="${5:-}"
    emit_kv ASSESSOR_STATUS "$status"
    emit_kv ASSESSOR_VERDICT "$verdict"
    emit_kv ASSESSOR_VERDICT_FILE "$verdict_file"
    emit_kv ASSESSOR_VERDICT_ENV "$verdict_env"
    emit_kv EFFECTIVE_ASSESSORS "$effective"
    emit_kv ROUND_NUM "$ROUND_NUM"
}

append_warning() {
    local cap="$1" rc="${2:-0}"
    local append_sh="$PLUGIN_ROOT/scripts/append-tool-failure.sh"
    [[ -x "$append_sh" ]] || return 0
    "$append_sh" \
        --log "$DESIGN_TMPDIR/execution-issues.md" \
        --site "design Step 3.6" \
        --tool "assess-plan-round.sh" \
        --exit-code "$rc" \
        --category Warnings \
        --redact \
        --output-file "$cap" \
        >/dev/null 2>&1 || true
}

assessor_path_valid() {
    local candidate="$1" expected_basename="$2" candidate_dir=""
    [[ -n "$candidate" ]] || return 1
    [[ "$(basename "$candidate")" == "$expected_basename" ]] || return 1
    candidate_dir=$(cd "$(dirname "$candidate")" 2>/dev/null && pwd -P) || return 1
    [[ "$candidate_dir" == "$DESIGN_TMPDIR" ]]
}

write_default_verdict_artifacts() {
    local verdict_file="$DESIGN_TMPDIR/assessor-verdict-round-${ROUND_NUM}.txt"
    local verdict_env="${verdict_file}.env"
    mkdir -p "$(dirname "$verdict_file")"
    printf 'NOT_WORSE\n' >"$verdict_file"
    {
        printf 'ASSESSOR_VERDICT=not-worse\n'
        printf 'BETTER_VOTES=0\n'
        printf 'WORSE_VOTES=0\n'
        printf 'TIE_VOTES=0\n'
        printf 'EFFECTIVE_ASSESSORS=0\n'
        printf 'DEGRADED_DEFAULT_OPEN=true\n'
        printf 'QUALIFICATIONS_SUMMARY=Plan-quality assessor panel degraded; no WORSE-majority verdict available.\n'
    } >"$verdict_env"
    emit_assessor_kv degraded-default-open not-worse 0 "$verdict_file" "$verdict_env"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --design-tmpdir) DESIGN_TMPDIR="${2:?}"; shift 2 ;;
        --codex-present) CODEX_PRESENT="${2:?}"; shift 2 ;;
        --cursor-present) CURSOR_PRESENT="${2:?}"; shift 2 ;;
        --timeout) TIMEOUT="${2:?}"; shift 2 ;;
        --help) usage; exit 0 ;;
        *) larch_err "assess-plan-round.sh: unknown option: $1"; usage; exit 2 ;;
    esac
done

[[ -n "$DESIGN_TMPDIR" ]] || { usage; exit 2; }
larch_design_tmpdir_validate "$DESIGN_TMPDIR" || exit $?
mkdir -p "$DESIGN_TMPDIR"
DESIGN_TMPDIR=$(cd "$DESIGN_TMPDIR" && pwd -P)
ROUND_NUM=1

workflow_path="$(read_workflow_path)"
if [[ "$workflow_path" != "HARD" ]]; then
    emit "⏩ assessor: workflow_path=${workflow_path:-<unset>}; skipped"
    emit_assessor_kv skipped skipped 0 "" ""
    exit 0
fi

read_round_cursor
if (( ROUND_NUM < 2 )); then
    emit "⏩ assessor: round ${ROUND_NUM}; no previous plan; skipped"
    emit_assessor_kv skipped skipped 0 "" ""
    exit 0
fi

plan_original="$DESIGN_TMPDIR/plan.txt-original"
plan_prev="$DESIGN_TMPDIR/plan-after-round-$((ROUND_NUM - 1)).txt"
plan_current="$DESIGN_TMPDIR/plan.txt"
feature_file="${IMPLEMENT_TMPDIR:-$DESIGN_TMPDIR}/feature-description.txt"

for missing in "$plan_original" "$plan_prev" "$plan_current" "$feature_file"; do
    if [[ ! -f "$missing" ]]; then
        emit "**⚠ assessor: missing input snapshot ($missing); skipped"
        cap=$(mktemp "${TMPDIR:-/tmp}/assessor-missing.XXXXXX")
        printf '%s\n' "missing=$missing" >"$cap"
        append_warning "$cap" 0
        rm -f "$cap"
        emit_assessor_kv missing-snapshot skipped 0 "" ""
        exit 0
    fi
done

rm -f \
    "$DESIGN_TMPDIR/claude-plan-assessor-round-${ROUND_NUM}.txt" \
    "$DESIGN_TMPDIR/codex-plan-assessor-round-${ROUND_NUM}.txt" \
    "$DESIGN_TMPDIR/cursor-plan-assessor-round-${ROUND_NUM}.txt" \
    "$DESIGN_TMPDIR/claude-plan-assessor-round-${ROUND_NUM}.txt.diag" \
    "$DESIGN_TMPDIR/codex-plan-assessor-round-${ROUND_NUM}.txt.diag" \
    "$DESIGN_TMPDIR/cursor-plan-assessor-round-${ROUND_NUM}.txt.diag" \
    "$DESIGN_TMPDIR/claude-plan-assessor-round-${ROUND_NUM}.txt.json" \
    "$DESIGN_TMPDIR/codex-plan-assessor-round-${ROUND_NUM}.txt.json" \
    "$DESIGN_TMPDIR/cursor-plan-assessor-round-${ROUND_NUM}.txt.json" \
    "$DESIGN_TMPDIR/assessor-verdict-round-${ROUND_NUM}.txt" \
    "$DESIGN_TMPDIR/assessor-verdict-round-${ROUND_NUM}.env" \
    2>/dev/null || true

bc_dir="$DESIGN_TMPDIR/breadcrumbs"
mkdir -p "$bc_dir"
export LARCH_BREADCRUMB_STREAM="$bc_dir/assessor-round-${ROUND_NUM}.ndjson"
export LARCH_DONE_SENTINEL="$bc_dir/assessor-round-${ROUND_NUM}.done"
export LARCH_STATUS_FILE="$bc_dir/assessor-round-${ROUND_NUM}.status"
export LARCH_QUIET_LOG_FILE="$bc_dir/assessor-round-${ROUND_NUM}.quiet.log"
DISPATCH_KV_FILE="$bc_dir/assessor-round-${ROUND_NUM}.dispatch.kv"
export LARCH_BREADCRUMBS_SURFACED_FILE="$bc_dir/assessor-round-${ROUND_NUM}.surfaced"
export LARCH_PAIRED_PID_FILE="$bc_dir/assessor-round-${ROUND_NUM}.paired.pid"
rm -f "$DISPATCH_KV_FILE"

DISPATCH_SH="${LARCH_DISPATCH_PLAN_ASSESSORS_SH:-$PLUGIN_ROOT/skills/design/scripts/dispatch-plan-assessors.sh}"
MONITOR_SH="${LARCH_BREADCRUMB_MONITOR_SH:-$PLUGIN_ROOT/scripts/breadcrumb-monitor.sh}"

set +e
"$DISPATCH_SH" \
    --design-tmpdir "$DESIGN_TMPDIR" \
    --round-num "$ROUND_NUM" \
    --plan-original "$plan_original" \
    --plan-prev "$plan_prev" \
    --plan-current "$plan_current" \
    --feature-file "$feature_file" \
    --codex-present "$CODEX_PRESENT" \
    --cursor-present "$CURSOR_PRESENT" \
    --timeout "$TIMEOUT" \
    >"$DISPATCH_KV_FILE" 2>"$LARCH_QUIET_LOG_FILE" &
dispatch_pid=$!
monitor_rc=0
"$MONITOR_SH" \
    --stream "$LARCH_BREADCRUMB_STREAM" \
    --done-sentinel "$LARCH_DONE_SENTINEL" \
    --status-file "$LARCH_STATUS_FILE" \
    --quiet-log "$LARCH_QUIET_LOG_FILE" \
    --surfaced-sentinel "$LARCH_BREADCRUMBS_SURFACED_FILE" \
    --paired-pid-file "$LARCH_PAIRED_PID_FILE" \
    || monitor_rc=$?
wait "$dispatch_pid"
dispatch_rc=$?
set -e

dispatch_out=""
[[ -f "$DISPATCH_KV_FILE" ]] && dispatch_out=$(cat "$DISPATCH_KV_FILE" 2>/dev/null || true)

DISPATCH_OK=false
CLAUDE_ASSESSOR_PATH="$DESIGN_TMPDIR/claude-plan-assessor-round-${ROUND_NUM}.txt"
CODEX_ASSESSOR_PATH="$DESIGN_TMPDIR/codex-plan-assessor-round-${ROUND_NUM}.txt"
CURSOR_ASSESSOR_PATH="$DESIGN_TMPDIR/cursor-plan-assessor-round-${ROUND_NUM}.txt"
while IFS= read -r line || [[ -n "$line" ]]; do
    key="${line%%=*}"
    value="${line#*=}"
    case "$key" in
        DISPATCH_OK) DISPATCH_OK="$value" ;;
        CLAUDE_ASSESSOR_PATH) CLAUDE_ASSESSOR_PATH="$value" ;;
        CODEX_ASSESSOR_PATH) CODEX_ASSESSOR_PATH="$value" ;;
        CURSOR_ASSESSOR_PATH) CURSOR_ASSESSOR_PATH="$value" ;;
    esac
done <<<"$dispatch_out"

if ! assessor_path_valid "$CLAUDE_ASSESSOR_PATH" "claude-plan-assessor-round-${ROUND_NUM}.txt" || \
   ! assessor_path_valid "$CODEX_ASSESSOR_PATH" "codex-plan-assessor-round-${ROUND_NUM}.txt" || \
   ! assessor_path_valid "$CURSOR_ASSESSOR_PATH" "cursor-plan-assessor-round-${ROUND_NUM}.txt"; then
    DISPATCH_OK=false
fi

if [[ "$monitor_rc" -ne 0 ]]; then
    cap=$(mktemp "${TMPDIR:-/tmp}/assessor-monitor.XXXXXX")
    {
        printf 'monitor_rc=%s\n' "$monitor_rc"
        [[ -f "$LARCH_QUIET_LOG_FILE" ]] && cat "$LARCH_QUIET_LOG_FILE"
    } >"$cap"
    append_warning "$cap" "$monitor_rc"
    rm -f "$cap"
fi

if [[ "$DISPATCH_OK" != "true" || "$dispatch_rc" -ne 0 ]]; then
    cap=$(mktemp "${TMPDIR:-/tmp}/assessor-dispatch.XXXXXX")
    {
        printf 'dispatch_rc=%s\n' "${dispatch_rc:-1}"
        printf 'monitor_rc=%s\n' "${monitor_rc:-0}"
        printf '%s\n' "$dispatch_out"
        [[ -f "$LARCH_QUIET_LOG_FILE" ]] && cat "$LARCH_QUIET_LOG_FILE"
    } >"$cap"
    append_warning "$cap" "${dispatch_rc:-1}"
    rm -f "$cap"
    write_default_verdict_artifacts
    exit 0
fi

verdict_file="$DESIGN_TMPDIR/assessor-verdict-round-${ROUND_NUM}.txt"
TALLY_SH="${LARCH_TALLY_PLAN_ASSESSOR_SH:-$PLUGIN_ROOT/skills/design/scripts/tally-plan-assessor.sh}"
set +e
tally_out=$("$TALLY_SH" \
    --design-tmpdir "$DESIGN_TMPDIR" \
    --round-num "$ROUND_NUM" \
    --claude-output "$CLAUDE_ASSESSOR_PATH" \
    --cursor-output "$CURSOR_ASSESSOR_PATH" \
    --codex-output "$CODEX_ASSESSOR_PATH" \
    --output "$verdict_file" 2>&1)
tally_rc=$?
set -e
if [[ "$tally_rc" -ne 0 ]]; then
    cap=$(mktemp "${TMPDIR:-/tmp}/assessor-tally.XXXXXX")
    printf '%s\n' "$tally_out" >"$cap"
    append_warning "$cap" "$tally_rc"
    rm -f "$cap"
    write_default_verdict_artifacts
    exit 0
fi

ASSESSOR_VERDICT=""
EFFECTIVE_ASSESSORS=0
VERDICT_ENV="${verdict_file}.env"
while IFS= read -r line || [[ -n "$line" ]]; do
    case "$line" in
        ASSESSOR_VERDICT=*) ASSESSOR_VERDICT="${line#ASSESSOR_VERDICT=}" ;;
        EFFECTIVE_ASSESSORS=*) EFFECTIVE_ASSESSORS="${line#EFFECTIVE_ASSESSORS=}" ;;
    esac
done <<<"$tally_out"

if [[ -z "$ASSESSOR_VERDICT" && -f "$VERDICT_ENV" ]]; then
    ASSESSOR_VERDICT=$(grep -E '^ASSESSOR_VERDICT=' "$VERDICT_ENV" 2>/dev/null | head -1 | cut -d= -f2- || true)
    EFFECTIVE_ASSESSORS=$(grep -E '^EFFECTIVE_ASSESSORS=' "$VERDICT_ENV" 2>/dev/null | head -1 | cut -d= -f2- || echo 0)
fi

status=ok
[[ "${EFFECTIVE_ASSESSORS:-0}" == "0" ]] && status=degraded-default-open
emit_assessor_kv "$status" "${ASSESSOR_VERDICT:-not-worse}" "${EFFECTIVE_ASSESSORS:-0}" "$verdict_file" "$VERDICT_ENV"
exit 0
