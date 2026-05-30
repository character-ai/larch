#!/usr/bin/env bash
# launch-claude-review.sh — Launch Claude as a read-only reviewer subprocess.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
# shellcheck source=scripts/lib-failed-agent-stderr-tail.sh
source "$SCRIPT_DIR/lib-failed-agent-stderr-tail.sh"
larch_quiet_init

usage() {
    larch_err "Usage: launch-claude-review.sh --output <file> (--agent-file <file>|--prompt-file <file>|--prompt <text>) --mode diff|description [--role reviewer|voter] [--context-files <file>...] [context flags]"
}

OUTPUT=""
AGENT_FILE=""
PROMPT_FILE=""
PROMPT=""
MODE=""
DESCRIPTION_TEXT=""
SCOPE_FILES=""
DIFF_FILE=""
COMMIT_COUNT=""
PLAN_FILE=""
FEATURE_FILE=""
EXPLICIT_CONTEXT_FILES=()
TIMEOUT="1800"
TIMING_TASK_KIND="claude-review"
ROLE="reviewer"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --output|--output-file) OUTPUT="${2:?--output requires a value}"; shift 2 ;;
        --agent-file) AGENT_FILE="${2:?--agent-file requires a value}"; shift 2 ;;
        --prompt-file) PROMPT_FILE="${2:?--prompt-file requires a value}"; shift 2 ;;
        --prompt) PROMPT="${2:?--prompt requires a value}"; shift 2 ;;
        --mode) MODE="${2:?--mode requires a value}"; shift 2 ;;
        --role) ROLE="${2:?--role requires a value}"; shift 2 ;;
        --description-text) DESCRIPTION_TEXT="${2:?--description-text requires a value}"; shift 2 ;;
        --scope-files) SCOPE_FILES="${2:?--scope-files requires a value}"; shift 2 ;;
        --diff-file) DIFF_FILE="${2:?--diff-file requires a value}"; shift 2 ;;
        --commit-count) COMMIT_COUNT="${2:?--commit-count requires a value}"; shift 2 ;;
        --plan-file) PLAN_FILE="${2:?--plan-file requires a value}"; shift 2 ;;
        --feature-file) FEATURE_FILE="${2:?--feature-file requires a value}"; shift 2 ;;
        --context-files)
            [[ $# -ge 2 && -n "${2:-}" && "$2" != --* ]] || {
                larch_err "launch-claude-review.sh: --context-files requires a value"
                exit 2
            }
            EXPLICIT_CONTEXT_FILES+=("$2")
            shift 2
            ;;
        --timeout) TIMEOUT="${2:?--timeout requires a value}"; shift 2 ;;
        --timing-task-kind) TIMING_TASK_KIND="${2:?--timing-task-kind requires a value}"; shift 2 ;;
        --help) usage; exit 0 ;;
        *) larch_err "launch-claude-review.sh: unknown option: $1"; usage; exit 2 ;;
    esac
done

[[ "$ROLE" == "reviewer" || "$ROLE" == "voter" ]] || { larch_err "launch-claude-review.sh: --role must be reviewer or voter"; exit 2; }

[[ -n "$OUTPUT" ]] || { larch_err "launch-claude-review.sh: --output is required"; exit 2; }
case "$TIMEOUT" in ''|*[!0-9]*|0) larch_err "launch-claude-review.sh: --timeout must be a positive integer"; exit 2 ;; esac
if (( TIMEOUT > 1800 )); then
    larch_err "launch-claude-review.sh: --timeout ${TIMEOUT}s exceeds subprocess cap; clamping to 1800"
    TIMEOUT=1800
fi

src_count=0
[[ -n "$AGENT_FILE" ]] && src_count=$((src_count + 1))
[[ -n "$PROMPT_FILE" ]] && src_count=$((src_count + 1))
[[ -n "$PROMPT" ]] && src_count=$((src_count + 1))
[[ "$src_count" -eq 1 ]] || { larch_err "launch-claude-review.sh: exactly one of --agent-file, --prompt-file, or --prompt is required"; exit 2; }

mkdir -p "$(dirname "$OUTPUT")"
TEMP_PROMPT=""
SUBPROCESS_STDERR=""
# shellcheck disable=SC2317
cleanup() {
    [[ -n "$TEMP_PROMPT" ]] && rm -f "$TEMP_PROMPT"
    [[ -n "$SUBPROCESS_STDERR" ]] && rm -f "$SUBPROCESS_STDERR"
    return 0
}
trap cleanup EXIT

if [[ -n "$AGENT_FILE" ]]; then
    [[ -n "$MODE" ]] || { larch_err "launch-claude-review.sh: --mode is required with --agent-file"; exit 2; }
    [[ "$ROLE" == "reviewer" ]] || { larch_err "launch-claude-review.sh: --agent-file is only supported with --role reviewer; use --prompt-file or --prompt for voter launches"; exit 2; }
    render_args=(--agent-file "$AGENT_FILE" --mode "$MODE")
    [[ -n "$DESCRIPTION_TEXT" ]] && render_args+=(--description-text "$DESCRIPTION_TEXT")
    [[ -n "$SCOPE_FILES" ]] && render_args+=(--scope-files "$SCOPE_FILES")
    [[ -n "$DIFF_FILE" ]] && render_args+=(--diff-file "$DIFF_FILE")
    [[ -n "$COMMIT_COUNT" ]] && render_args+=(--commit-count "$COMMIT_COUNT")
    [[ -n "$PLAN_FILE" ]] && render_args+=(--plan-file "$PLAN_FILE")
    [[ -n "$FEATURE_FILE" ]] && render_args+=(--feature-file "$FEATURE_FILE")
    TEMP_PROMPT=$(mktemp "$(dirname "$OUTPUT")/claude-review-prompt.XXXXXX")
    "$SCRIPT_DIR/render-specialist-prompt.sh" "${render_args[@]}" > "$TEMP_PROMPT"
    PROMPT_FILE="$TEMP_PROMPT"
elif [[ -n "$PROMPT" ]]; then
    TEMP_PROMPT=$(mktemp "$(dirname "$OUTPUT")/claude-review-prompt.XXXXXX")
    printf '%s\n' "$PROMPT" > "$TEMP_PROMPT"
    PROMPT_FILE="$TEMP_PROMPT"
fi

ctx_args=()
allow_root_args=()
seen_allow_roots=()
seen_canonical_paths=()
# strict=1: --context-files hard-errors on missing/empty/unreadable; strict=0: implicit flags silent-skip (callers may pass empty).
array_contains() {
    local needle="$1"
    shift || true
    local value
    for value in "$@"; do
        [[ "$value" == "$needle" ]] && return 0
    done
    return 1
}

append_context_file() {
    local path="$1" strict="${2:-0}" dir base canonical
    if [[ "$strict" == "1" ]]; then
        [[ -n "$path" && -f "$path" && -r "$path" ]] || {
            larch_err "launch-claude-review.sh: --context-files path missing or unreadable: $path"
            exit 2
        }
    else
        [[ -n "$path" && -f "$path" ]] || return 0
    fi
    dir=$(cd "$(dirname "$path")" && pwd -P) || dir=""
    base=$(basename "$path")
    if [[ -z "$dir" || -z "$base" ]]; then
        if [[ "$strict" == "1" ]]; then
            larch_err "launch-claude-review.sh: --context-files path missing or unreadable: $path"
            exit 2
        fi
        ctx_args+=(--context-files "$path")
        return 0
    fi
    canonical="$dir/$base"
    array_contains "$canonical" "${seen_canonical_paths[@]+"${seen_canonical_paths[@]}"}" && return 0
    seen_canonical_paths+=("$canonical")
    ctx_args+=(--context-files "$path")
    if ! array_contains "$dir" "${seen_allow_roots[@]+"${seen_allow_roots[@]}"}"; then
        allow_root_args+=(--allow-root "$dir")
        seen_allow_roots+=("$dir")
    fi
}
append_context_file "$DIFF_FILE" 0
append_context_file "$SCOPE_FILES" 0
append_context_file "$PLAN_FILE" 0
append_context_file "$FEATURE_FILE" 0
for explicit_context_file in "${EXPLICIT_CONTEXT_FILES[@]+"${EXPLICIT_CONTEXT_FILES[@]}"}"; do
    append_context_file "$explicit_context_file" 1
done
unset explicit_context_file

rm -f "${OUTPUT}.stderr-tail"
SUBPROCESS_STDERR=$(mktemp "$(dirname "$OUTPUT")/claude-subprocess-stderr.XXXXXX")
set +e
"$SCRIPT_DIR/launch-claude-subprocess.sh" \
    --prompt-file "$PROMPT_FILE" \
    --output-file "$OUTPUT" \
    --timeout "$TIMEOUT" \
    --timing-task-kind "$TIMING_TASK_KIND" \
    ${allow_root_args[@]+"${allow_root_args[@]}"} \
    ${ctx_args[@]+"${ctx_args[@]}"} 2> "$SUBPROCESS_STDERR"
rc=$?
set -e

# launch-claude-subprocess.sh's larch_quiet_init clobbers its FD 4 with its
# own log file, so the subprocess's larch_err output is normally lost in a
# nested invocation. Capture stderr to a temp file and re-emit each line via
# this script's larch_err so validation failures (--prompt-file outside
# allowed roots, context file exceeds N bytes, etc.) reach the caller's
# stderr — used by dispatch-code-voters.sh to surface the specific failing
# check in execution-issues.md Warnings.
_larch_emit_redacted_subprocess_stderr() {
    local src="$1" redact redact_tmpdir pipeline
    [[ -s "$src" ]] || return 1
    redact="$SCRIPT_DIR/redact-secrets.sh"
    redact_tmpdir="$SCRIPT_DIR/redact-tmpdir-paths.sh"
    [[ -x "$redact" ]] || return 1
    if [[ -x "$redact_tmpdir" ]]; then
        pipeline="$redact_tmpdir | $redact"
    else
        pipeline="$redact"
    fi
    # shellcheck disable=SC2090
    eval "cat \"\$src\" | $pipeline" 2>/dev/null | while IFS= read -r _line || [[ -n "$_line" ]]; do
        larch_err "$_line"
    done
    unset _line
    return 0
}

if [[ "$rc" -ne 0 ]]; then
    if [[ ! -s "${OUTPUT}.stderr-tail" ]] && [[ -s "$SUBPROCESS_STDERR" ]]; then
        write_failed_agent_stderr_tail "$SUBPROCESS_STDERR" "$OUTPUT" || true
    fi
    _larch_emit_redacted_subprocess_stderr "$SUBPROCESS_STDERR" || true
    if [[ -s "${OUTPUT}.stderr-tail" ]]; then
        emit_failed_agent_stderr_tail_larch_err "$OUTPUT" || true
    fi
else
    rm -f "${OUTPUT}.stderr-tail"
fi
if [[ "$rc" -eq 0 ]] && [[ -s "$SUBPROCESS_STDERR" ]]; then
    _larch_emit_redacted_subprocess_stderr "$SUBPROCESS_STDERR" || \
        larch_err 'WARN subprocess stderr redaction unavailable'
fi

if [[ ! -f "${OUTPUT}.done" ]]; then
    printf '%s\n' "$rc" > "${OUTPUT}.done"
fi
exit "$rc"
