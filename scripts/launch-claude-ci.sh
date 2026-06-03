#!/usr/bin/env bash
# launch-claude-ci.sh — Launch Claude Code CLI for /implement CI-fix subwork (write-capable).
# Sibling to launch-cursor-ci.sh / launch-codex-ci.sh; unlike launch-claude-subprocess.sh,
# this path does NOT inject the read-only reviewer preamble.
#
# LAUNCHER_FAILURE_* canonical token pin (grep tests; classifier emits): none health other auth quota binary-missing health-probe timeout parse refusal unknown

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init
# shellcheck source=scripts/lib-external-launcher-common.sh
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib-external-launcher-common.sh"

ROLE=""
OUTPUT=""
RUN_ID=""
REPO=""
PLAN_FILE=""
CONFLICT_FILES=""
FAILURE_LOG=""
TIMEOUT="1800"
TIMING_TASK_KIND="claude-ci-fix"
MODEL="claude-sonnet-4-6"

usage() {
    larch_err "Usage: launch-claude-ci.sh --role fix|resolve-conflict --output PATH --run-id ID --repo OWNER/REPO [--plan-file PATH] [--conflict-files CSV] [--failure-log PATH] [--timeout SECONDS] [--timing-task-kind KIND] [--model MODEL]"
}

die() {
    larch_err "launch-claude-ci.sh: $1"
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
        --model) [ $# -ge 2 ] || die "--model requires a value"; MODEL=$2; shift 2 ;;
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
    if [[ "$ROLE" != "resolve-conflict" ]]; then
        die "--conflict-files is only valid with --role resolve-conflict"
    fi
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

PROMPT="You are a write-capable implementer fixing larch /implement CI subwork. You MAY edit files in this repository. You are NOT a read-only reviewer.

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

PROMPT_FILE="${OUTPUT}.prompt"
printf '%s' "$PROMPT" > "$PROMPT_FILE"

if ! command -v claude >/dev/null 2>&1; then
    LAUNCHER_EXIT=127
    : > "${OUTPUT}.token-record" 2>/dev/null || true
    emit_kv LAUNCHER_EXIT "$LAUNCHER_EXIT"
    external_classify_launch_failure "$LAUNCHER_EXIT" "/dev/null" "unclassified" 0 "claude" ""
    emit_kv OUTPUT "$OUTPUT"
    emit_kv TOKEN_RECORD "${OUTPUT}.token-record"
    larch_err "launch-claude-ci.sh: claude CLI not found in PATH"
    exit 1
fi

START_S=$(date +%s)
LAUNCHER_EXIT=0
if command -v timeout >/dev/null 2>&1; then
    if timeout "$TIMEOUT" claude --model "$MODEL" --print < "$PROMPT_FILE" > "${OUTPUT}.tmp.$$" 2> "${OUTPUT}.stderr.$$"; then
        LAUNCHER_EXIT=0
    else
        LAUNCHER_EXIT=$?
    fi
else
    if claude --model "$MODEL" --print < "$PROMPT_FILE" > "${OUTPUT}.tmp.$$" 2> "${OUTPUT}.stderr.$$"; then
        LAUNCHER_EXIT=0
    else
        LAUNCHER_EXIT=$?
    fi
fi
mv "${OUTPUT}.tmp.$$" "$OUTPUT" 2>/dev/null || true
mv "${OUTPUT}.stderr.$$" "${OUTPUT}.stderr" 2>/dev/null || true

END_S=$(date +%s)
"$PLUGIN_ROOT/scripts/timing-ledger.sh" record-vendor-task \
    --vendor claude \
    --task-kind "$TIMING_TASK_KIND" \
    --start-s "$START_S" \
    --end-s "$END_S" \
    --output "$OUTPUT" \
    --exit-code "$LAUNCHER_EXIT" \
    --status "$([ "$LAUNCHER_EXIT" -eq 0 ] && echo complete || echo signal)" >/dev/null 2>&1 || true

if (( LAUNCHER_EXIT != 0 )); then
    append_launch_failure "CI $ROLE" "claude-ci" "$LAUNCHER_EXIT" "${OUTPUT}.stderr" "" ""
fi

if [[ -s "$OUTPUT" ]]; then
    _tok=$(wc -w < "$OUTPUT" | tr -d '[:space:]')
    printf 'TOOL=claude\nTOTAL=%s\nRAW=claude_ci_fix\n' "${_tok:-0}" > "${OUTPUT}.token-record"
fi

emit_kv LAUNCHER_EXIT "$LAUNCHER_EXIT"
_AUTH_VERDICT=$(external_auth_verdict "claude" "${OUTPUT}.stderr"; true)
_AUTH_VERDICT=${_AUTH_VERDICT//$'\n'/}
external_classify_launch_failure "$LAUNCHER_EXIT" "${OUTPUT}.stderr" "$_AUTH_VERDICT" 1 "claude" "$OUTPUT"
emit_kv OUTPUT "$OUTPUT"
emit_kv TOKEN_RECORD "${OUTPUT}.token-record"
exit 0
