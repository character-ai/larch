#!/usr/bin/env bash
# launch-codex-ci.sh — Launch Codex for /implement CI-fix subwork.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd -P)}"
# shellcheck source=scripts/lib-codex-launcher-common.sh
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib-codex-launcher-common.sh"

ROLE=""
OUTPUT=""
RUN_ID=""
REPO=""
PLAN_FILE=""
CONFLICT_FILES=""
TIMEOUT="1800"
TIMING_TASK_KIND="codex-ci-fix"

usage() {
    larch_err "Usage: launch-codex-ci.sh --role fix|resolve-conflict|bump-classify|changelog-draft --output PATH --run-id ID --repo OWNER/REPO [--plan-file PATH] [--conflict-files CSV] [--timeout SECONDS]"
}

die() {
    larch_err "launch-codex-ci.sh: $1"
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
        --timeout) [ $# -ge 2 ] || die "--timeout requires a value"; TIMEOUT=$2; shift 2 ;;
        --timing-task-kind) [ $# -ge 2 ] || die "--timing-task-kind requires a value"; TIMING_TASK_KIND=$2; shift 2 ;;
        --help) usage; exit 0 ;;
        *) die "unknown flag: $1" ;;
    esac
done

case "$ROLE" in fix|resolve-conflict|bump-classify|changelog-draft) ;; *) die "--role must be fix, resolve-conflict, bump-classify, or changelog-draft" ;; esac
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

PROMPT="You are fixing larch /implement CI subwork.

Role: $ROLE
Repository: $REPO
Failed run id: $RUN_ID
Working directory: $PWD
$PLAN_CONTEXT
$CONFLICT_CONTEXT

Inspect the repository and CI logs as needed. Make only the minimal changes required for this role. Do not rewrite history. Do not edit submodules. Leave a concise summary in the final answer."
PROMPT_FILE="${OUTPUT}.prompt"
printf '%s' "$PROMPT" > "$PROMPT_FILE"

MODEL_ARGS_TMP=$(mktemp)
CODEX_HOME_DIR=$(mktemp -d /tmp/larch-codex-ci-home-XXXXXX)
trap 'rm -f "$MODEL_ARGS_TMP"; rm -rf "$CODEX_HOME_DIR"' EXIT
"$SCRIPT_DIR/agent-model-args.sh" --tool codex --with-effort > "$MODEL_ARGS_TMP"
MODEL_ARGS=()
while IFS= read -r arg; do
    MODEL_ARGS+=("$arg")
done < "$MODEL_ARGS_TMP"
if [ -f ~/.codex/auth.json ]; then
    ln -sf "$(cd ~/.codex && pwd)/auth.json" "$CODEX_HOME_DIR/auth.json"
fi
PROJECT_KEY=${PWD//\\/\\\\}
PROJECT_KEY=${PROJECT_KEY//\"/\\\"}
TRUST_CONFIG_ARG="projects.\"$PROJECT_KEY\".trust_level=\"trusted\""

TIMING_START_S=$(date +%s)
LAUNCHER_EXIT=0
SIDECAR_LOG="${OUTPUT}.sidecar"
MAX_AUTH_RETRIES=${LARCH_EXTERNAL_AUTH_RETRIES:-5}
case "$MAX_AUTH_RETRIES" in ''|*[!0-9]*|0) MAX_AUTH_RETRIES=5 ;; esac
HOLD=${LARCH_EXTERNAL_SERIAL_LOCK_DELAY:-0.5}
AUTH_ATTEMPT=1
while (( AUTH_ATTEMPT <= MAX_AUTH_RETRIES )); do
    _SERIAL_LOCK=""
    external_serial_lock_acquire _SERIAL_LOCK "codex"
    external_serial_lock_release_after "$_SERIAL_LOCK" "$HOLD"
    LAUNCHER_EXIT=0
    CODEX_HOME="$CODEX_HOME_DIR" "$SCRIPT_DIR/run-external-agent.sh" \
        --tool codex \
        --output "$OUTPUT" \
        --timeout "$TIMEOUT" \
        -- \
        codex exec --full-auto -C "$PWD" \
        ${MODEL_ARGS[@]+"${MODEL_ARGS[@]}"} \
        -c "$TRUST_CONFIG_ARG" \
        --output-last-message "$OUTPUT" \
        -- \
        "$PROMPT" >"$SIDECAR_LOG" 2>&1 || LAUNCHER_EXIT=$?
    if (( LAUNCHER_EXIT != 0 && AUTH_ATTEMPT < MAX_AUTH_RETRIES )) && external_is_auth_failure "codex" "$SIDECAR_LOG"; then
        AUTH_ATTEMPT=$((AUTH_ATTEMPT + 1))
        : > "$SIDECAR_LOG" 2>/dev/null || true
        continue
    fi
    break
done

if (( LAUNCHER_EXIT != 0 )); then
    _AUTH_VERDICT=$(external_auth_verdict "codex" "$SIDECAR_LOG")
    [[ "$_AUTH_VERDICT" == "auth" ]] && _VERDICT="auth-retries-exhausted" || _VERDICT="$_AUTH_VERDICT"
    append_launch_failure "CI $ROLE" "codex-ci" "$LAUNCHER_EXIT" "$SIDECAR_LOG" "$_VERDICT" "$AUTH_ATTEMPT"
fi

END_S=$(date +%s)
"$PLUGIN_ROOT/scripts/timing-ledger.sh" record-vendor-task \
    --vendor codex \
    --task-kind "$TIMING_TASK_KIND" \
    --start-s "$TIMING_START_S" \
    --end-s "$END_S" \
    --output "$OUTPUT" \
    --exit-code "$LAUNCHER_EXIT" \
    --status "$([ "$LAUNCHER_EXIT" -eq 0 ] && echo complete || echo signal)" >/dev/null 2>&1 || true

TOKENS=$(awk '/^tokens used$/ { getline n; gsub(",","",n); last=n } END { print last }' "${OUTPUT}.diag" "$OUTPUT" "$SIDECAR_LOG" 2>/dev/null || true)
if [[ "$TOKENS" =~ ^[0-9]+$ ]]; then
    printf 'TOOL=codex\nTOTAL=%s\nRAW=codex_ci_fix\n' "$TOKENS" > "${OUTPUT}.token-record"
fi

emit_kv LAUNCHER_EXIT "$LAUNCHER_EXIT"
emit_kv OUTPUT "$OUTPUT"
emit_kv TOKEN_RECORD "${OUTPUT}.token-record"
exit 0
