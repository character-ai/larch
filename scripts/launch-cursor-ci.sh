#!/usr/bin/env bash
# launch-cursor-ci.sh — Launch Cursor for /implement CI-fix subwork.
#
# Stall monitoring and stall JSON sidecars are implemented in
# scripts/lib-cursor-launcher-common.sh (cursor_launcher_run_stall_monitor,
# cursor_launcher_emit_cursor_ci_stall_json_sidecar); triage stall behavior there.

# LAUNCHER_FAILURE_* canonical token pin (grep tests; classifier emits): none health other auth quota binary-missing health-probe timeout parse refusal unknown

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd -P)}"
# shellcheck source=scripts/lib-cursor-launcher-common.sh
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib-cursor-launcher-common.sh"

ROLE=""
OUTPUT=""
RUN_ID=""
REPO=""
PLAN_FILE=""
CONFLICT_FILES=""
FAILURE_LOG=""
TIMEOUT="1800"
TIMING_TASK_KIND="cursor-ci-fix"

usage() {
    larch_err "Usage: launch-cursor-ci.sh --role fix|resolve-conflict --output PATH --run-id ID --repo OWNER/REPO [--plan-file PATH] [--conflict-files CSV] [--failure-log PATH] [--timeout SECONDS]"
}

die() {
    larch_err "launch-cursor-ci.sh: $1"
    usage
    exit 2
}

append_launch_failure() {
    local site="$1" tool_label="$2" rc="$3" diag_file="$4" verdict="${5:-}" retry_count="${6:-}"
    [[ -x "$PLUGIN_ROOT/scripts/append-tool-failure.sh" ]] || return 0
    [[ -n "${IMPLEMENT_TMPDIR:-}" ]] || return 0
    local _args=()
    [[ -n "$verdict" ]] && _args+=(--verdict "$verdict")
    [[ -n "$retry_count" ]] && _args+=(--retry-count "$retry_count")
    "$PLUGIN_ROOT/scripts/append-tool-failure.sh" \
        --log "${IMPLEMENT_TMPDIR}/execution-issues.md" \
        --site "$site" --tool "$tool_label" --exit-code "$rc" \
        --category "Tool Failures" --output-file "$diag_file" \
        "${_args[@]}" --redact >/dev/null 2>&1 || true
}

while [ $# -gt 0 ]; do
    case "$1" in
        --role) [ $# -ge 2 ] || die "--role requires a value"; ROLE=$2; shift 2 ;;
        --output) [ $# -ge 2 ] || die "--output requires a value"; OUTPUT=$2; shift 2 ;;
        --run-id) [ $# -ge 2 ] || die "--run-id requires a value"; RUN_ID=$2; shift 2 ;;
        --repo) [ $# -ge 2 ] || die "--repo requires a value"; REPO=$2; shift 2 ;;
        --plan-file) [ $# -ge 2 ] || die "--plan-file requires a value"; PLAN_FILE=$2; shift 2 ;;
        --conflict-files) [ $# -ge 2 ] || die "--conflict-files requires a value"; CONFLICT_FILES=$2; shift 2 ;;
        --failure-log) [ $# -ge 2 ] || die "--failure-log requires a value"; FAILURE_LOG=$2; shift 2 ;;
        --timeout) [ $# -ge 2 ] || die "--timeout requires a value"; TIMEOUT=$2; shift 2 ;;
        --timing-task-kind) [ $# -ge 2 ] || die "--timing-task-kind requires a value"; TIMING_TASK_KIND=$2; shift 2 ;;
        --help) usage; exit 0 ;;
        *) die "unknown flag: $1" ;;
    esac
done

case "$ROLE" in fix|resolve-conflict) ;; *) die "--role must be fix or resolve-conflict" ;; esac
[ -n "$OUTPUT" ] || die "--output is required"
[ -n "$RUN_ID" ] || die "--run-id is required"
[ -n "$REPO" ] || die "--repo is required"
case "$TIMEOUT" in ''|*[!0-9]*|0) die "--timeout must be a positive integer" ;; esac
case "$OUTPUT" in /*) ;; *) die "--output must be an absolute path" ;; esac
case "$PLAN_FILE" in /*) ;; "") ;; *) die "--plan-file must be an absolute path" ;; esac
case "$OUTPUT" in *[!A-Za-z0-9._/-]*) die "--output contains unsupported characters" ;; esac
if [[ -n "$CONFLICT_FILES" ]]; then
    if [[ "$CONFLICT_FILES" == *..* || "$CONFLICT_FILES" == /* ]]; then
        die "--conflict-files must be repo-relative comma-separated paths (no .. or absolute paths)"
    fi
    larch_validate_vendor_conflict_csv "$CONFLICT_FILES" || die "invalid --conflict-files"
fi

if [[ -n "$FAILURE_LOG" ]]; then
    case "$FAILURE_LOG" in /*) ;; *) die "--failure-log must be an absolute path" ;; esac
    [[ -n "${IMPLEMENT_TMPDIR:-}" ]] || die "--failure-log requires IMPLEMENT_TMPDIR in the environment"
    case "$FAILURE_LOG" in
        "$IMPLEMENT_TMPDIR"/*) ;;
        *) die "--failure-log must live under IMPLEMENT_TMPDIR" ;;
    esac
    [[ -f "$FAILURE_LOG" ]] || die "--failure-log must name an existing file"
fi

STALL_THRESHOLD=${LARCH_CURSOR_CI_STALL_THRESHOLD:-180}
case "$STALL_THRESHOLD" in ''|*[!0-9]*|0) STALL_THRESHOLD=180 ;; esac
STALL_CHANNEL=""
case "$ROLE" in
    fix) STALL_CHANNEL=stdout ;;
    resolve-conflict) STALL_CHANNEL="tree:${PWD}" ;;
esac

MODEL_ARGS=()
cursor_launcher_load_model_args
cursor_launcher_setup_auth_argv

PLAN_CONTEXT=""
if [ -n "$PLAN_FILE" ] && [ -f "$PLAN_FILE" ]; then
    PLAN_CONTEXT="
Design plan (do not revert or undo the work it describes):
$(cat "$PLAN_FILE")"
fi

CONFLICT_CONTEXT=""
if [ "$ROLE" = "resolve-conflict" ] && [ -n "$CONFLICT_FILES" ]; then
    CONFLICT_CONTEXT="
Still-conflicted paths (repo-relative). Resolve each path, stage with git add, then finish the in-progress rebase with: GIT_EDITOR=true git rebase --continue

<<<CONFLICT_PATHS>>>
$CONFLICT_FILES
<<<END_CONFLICT_PATHS>>>"
fi

FAILURE_CONTEXT=""
if [[ -n "$FAILURE_LOG" && -f "$FAILURE_LOG" ]]; then
    if ! _fl_snippet=$(head -c 4096 "$FAILURE_LOG" | "$SCRIPT_DIR/redact-secrets.sh" 2>/dev/null); then
        _fl_snippet="[failure log excerpt omitted: redaction unavailable]"
    fi
    FAILURE_CONTEXT="
<<<FAILURE_LOG_EXCERPT>>>
${_fl_snippet}
<<<END_FAILURE_LOG>>>
"
fi

LARCH_PATTERNS=""
if [[ "$ROLE" == "fix" ]]; then
    _ci_fix_patterns="${PLUGIN_ROOT}/skills/shared/ci-fix-failure-patterns.md"
    if [[ -f "$_ci_fix_patterns" ]]; then
        LARCH_PATTERNS="
Larch-specific failure patterns (apply when relevant to the failure log):
$(cat "$_ci_fix_patterns")
"
    fi
fi

LOCAL_REPRO=""
if [[ "$ROLE" == "fix" ]]; then
    LOCAL_REPRO="
Local reproduction invariant: reproduce the failure locally with the same commands shown in the logs (or scripts/relevant-checks.sh / the failing harness), confirm the failure, apply your fix, then re-run the same commands and confirm they pass. Summarize the commands you ran in your final answer."
fi

PROMPT="You are fixing larch /implement CI subwork.

Role: $ROLE
Repository: $REPO
Failed run id: $RUN_ID
Working directory: $PWD
$PLAN_CONTEXT
$CONFLICT_CONTEXT
$FAILURE_CONTEXT
$LARCH_PATTERNS
$LOCAL_REPRO

Inspect the repository and CI logs as needed. Make only the minimal changes required for this role. Do not rewrite history. Do not edit submodules. Leave a concise summary in the final answer."
WRAPPED_PROMPT=$("$SCRIPT_DIR/cursor-wrap-prompt.sh" "$PROMPT")
PROMPT_FILE="${OUTPUT}.prompt"
printf '%s' "$PROMPT" > "$PROMPT_FILE"

TIMING_START_S=$(date +%s)
LAUNCHER_EXIT=0
unset CURSOR_CONFIG_DIR_TMP CURSOR_CONFIG_DIR
cursor_launcher_setup_private_config_dir
# shellcheck disable=SC2154 # CURSOR_CONFIG_DIR_TMP set by cursor_launcher_setup_private_config_dir.
trap 'cursor_launcher_cleanup_private_config_dir' EXIT
MAX_AUTH_RETRIES=${LARCH_EXTERNAL_AUTH_RETRIES:-5}
case "$MAX_AUTH_RETRIES" in ''|*[!0-9]*|0) MAX_AUTH_RETRIES=5 ;; esac
HOLD=${LARCH_EXTERNAL_SERIAL_LOCK_DELAY:-0.5}
if ! command -v cursor >/dev/null 2>&1; then
    LAUNCHER_EXIT=127
    : > "${OUTPUT}.token-record" 2>/dev/null || true
    emit_kv LAUNCHER_EXIT "$LAUNCHER_EXIT"
    external_classify_launch_failure "$LAUNCHER_EXIT" "/dev/null" "unclassified" 0 "cursor" ""
    emit_kv OUTPUT "$OUTPUT"
    emit_kv TOKEN_RECORD "${OUTPUT}.token-record"
    larch_err "launch-cursor-ci.sh: cursor CLI not found in PATH"
    exit 1
fi
AUTH_ATTEMPT=1
while (( AUTH_ATTEMPT <= MAX_AUTH_RETRIES )); do
    _SERIAL_LOCK=""
    external_serial_lock_acquire _SERIAL_LOCK "cursor"
    external_serial_lock_release_after "$_SERIAL_LOCK" "$HOLD"
    LAUNCHER_EXIT=0
    RUN_EXTERNAL_AGENT_INNER_SENTINEL_SUFFIX=.inner.done \
    "$SCRIPT_DIR/run-external-agent.sh" \
        --tool cursor \
        --output "$OUTPUT" \
        --timeout "$TIMEOUT" \
        --capture-stdout-only \
        -- \
        cursor agent -p --force --trust \
        --output-format json \
        ${MODEL_ARGS[@]+"${MODEL_ARGS[@]}"} \
        --workspace "$PWD" \
        "$WRAPPED_PROMPT" &
    _REA_PID=$!
    cursor_launcher_run_stall_monitor "$STALL_CHANNEL" "$OUTPUT" "$STALL_THRESHOLD" "${OUTPUT}.diag" "$_REA_PID" || true
    wait "$_REA_PID" && LAUNCHER_EXIT=0 || LAUNCHER_EXIT=$?
    if (( LAUNCHER_EXIT != 0 && AUTH_ATTEMPT < MAX_AUTH_RETRIES )) && external_is_auth_failure "cursor" "${OUTPUT}.diag"; then
        AUTH_ATTEMPT=$((AUTH_ATTEMPT + 1))
        : > "${OUTPUT}.diag" 2>/dev/null || true
        continue
    fi
    break
done
cursor_launcher_cleanup_private_config_dir

if (( LAUNCHER_EXIT != 0 )); then
    _AUTH_VERDICT=$(external_auth_verdict "cursor" "${OUTPUT}.diag")
    [[ "$_AUTH_VERDICT" == "auth" ]] && _VERDICT="auth-retries-exhausted" || _VERDICT="$_AUTH_VERDICT"
    append_launch_failure "CI $ROLE" "cursor-ci" "$LAUNCHER_EXIT" "${OUTPUT}.diag" "$_VERDICT" "$AUTH_ATTEMPT"
fi

cursor_launcher_append_outer_meta "${OUTPUT}.meta" "$SCRIPT_DIR/launch-cursor-ci.sh" "$PROMPT_FILE" "$PWD" "" ""
cursor_launcher_promote_inner_done "$OUTPUT"

END_S=$(date +%s)
"$PLUGIN_ROOT/scripts/timing-ledger.sh" record-vendor-task \
    --vendor cursor \
    --task-kind "$TIMING_TASK_KIND" \
    --start-s "$TIMING_START_S" \
    --end-s "$END_S" \
    --output "$OUTPUT" \
    --exit-code "$LAUNCHER_EXIT" \
    --status "$([ "$LAUNCHER_EXIT" -eq 0 ] && echo complete || echo signal)" >/dev/null 2>&1 || true

if command -v jq >/dev/null 2>&1 && [ -f "$OUTPUT" ]; then
    read -r INP OUT CR CW < <(jq -r '.usage // {} | "\(.inputTokens // 0) \(.outputTokens // 0) \(.cacheReadTokens // 0) \(.cacheWriteTokens // 0)"' "$OUTPUT" 2>/dev/null || echo "0 0 0 0") || true
    if [[ "$INP" =~ ^[0-9]+$ && "$OUT" =~ ^[0-9]+$ && "$CR" =~ ^[0-9]+$ && "$CW" =~ ^[0-9]+$ ]]; then
        TOTAL=$((INP + OUT + CR + CW))
        printf 'TOOL=cursor\nINPUT=%s\nOUTPUT=%s\nCACHE_READ=%s\nCACHE_CREATE=%s\nTOTAL=%s\nRAW=cursor_ci_fix\n' \
            "$INP" "$OUT" "$CR" "$CW" "$TOTAL" > "${OUTPUT}.token-record"
    fi
fi

emit_kv LAUNCHER_EXIT "$LAUNCHER_EXIT"
_AUTH_VERDICT=$(external_auth_verdict "cursor" "${OUTPUT}.diag"; true)
_AUTH_VERDICT=${_AUTH_VERDICT//$'\n'/}
external_classify_launch_failure "$LAUNCHER_EXIT" "${OUTPUT}.diag" "$_AUTH_VERDICT" 1 "cursor" "$OUTPUT"
emit_kv OUTPUT "$OUTPUT"
emit_kv TOKEN_RECORD "${OUTPUT}.token-record"
exit 0
