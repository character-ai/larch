#!/usr/bin/env bash
# launch-codex-exec.sh — Generic auth-wired Codex prompt launcher.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd -P)}"
# shellcheck source=scripts/lib-codex-launcher-common.sh
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib-codex-launcher-common.sh"
# shellcheck source=scripts/lib-validate-meta-path.sh
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib-validate-meta-path.sh"

OUTPUT=""
TIMEOUT=""
PROMPT=""
PROMPT_FILE=""
WORKDIR="$PWD"
SANDBOX="full-auto"
WITH_EFFORT=false
USAGE_LABEL="codex_exec"
TIMING_TASK_KIND="codex-exec"
ADD_DIRS=()

usage() {
    larch_err "Usage: launch-codex-exec.sh --output PATH --timeout SECONDS (--prompt STRING | --prompt-file PATH) [--workdir PATH] [--add-dir PATH]... [--sandbox full-auto|read-only] [--with-effort] [--usage-label LABEL] [--timing-task-kind KIND]"
}

die() {
    larch_err "launch-codex-exec.sh: $1"
    usage
    exit 2
}

write_preflight_bundle() {
    local launcher_exit="$1"
    local failure_reason="$2"
    : > "$OUTPUT" 2>/dev/null || true
    {
        printf 'STATUS=FAILED\n'
        printf 'FAILURE_REASON=%s\n' "$failure_reason"
    } > "${OUTPUT}.diag" 2>/dev/null || true
    {
        printf 'TOOL=codex\n'
        printf 'TIMEOUT=%s\n' "$TIMEOUT"
        printf 'CAPTURE_STDOUT=false\n'
        printf 'OUTPUT_FILE=%s\n' "$OUTPUT"
        printf 'CMD_JSON=[]\n'
    } > "${OUTPUT}.meta" 2>/dev/null || true
    printf '%s\n' "$launcher_exit" > "${OUTPUT}.done" 2>/dev/null || true
    emit_kv LAUNCHER_EXIT "$launcher_exit"
    emit_kv OUTPUT "$OUTPUT"
    exit 0
}

launcher_jq_available() {
    [[ "${LARCH_TEST_FORCE_NO_JQ:-}" == "1" ]] && return 1
    command -v jq >/dev/null 2>&1
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --output) [ $# -ge 2 ] || die "--output requires a value"; OUTPUT=$2; shift 2 ;;
        --timeout) [ $# -ge 2 ] || die "--timeout requires a value"; TIMEOUT=$2; shift 2 ;;
        --prompt) [ $# -ge 2 ] || die "--prompt requires a value"; PROMPT=$2; shift 2 ;;
        --prompt-file) [ $# -ge 2 ] || die "--prompt-file requires a value"; PROMPT_FILE=$2; shift 2 ;;
        --workdir) [ $# -ge 2 ] || die "--workdir requires a value"; WORKDIR=$2; shift 2 ;;
        --add-dir) [ $# -ge 2 ] || die "--add-dir requires a value"; ADD_DIRS+=("$2"); shift 2 ;;
        --sandbox) [ $# -ge 2 ] || die "--sandbox requires a value"; SANDBOX=$2; shift 2 ;;
        --with-effort) WITH_EFFORT=true; shift ;;
        --usage-label) [ $# -ge 2 ] || die "--usage-label requires a value"; USAGE_LABEL=$2; shift 2 ;;
        --timing-task-kind) [ $# -ge 2 ] || die "--timing-task-kind requires a value"; TIMING_TASK_KIND=$2; shift 2 ;;
        --help) usage; exit 0 ;;
        *) die "unknown flag: $1" ;;
    esac
done

[ -n "$OUTPUT" ] || die "--output is required"
[ -n "$TIMEOUT" ] || die "--timeout is required"
case "$TIMEOUT" in ''|*[!0-9]*|0) die "--timeout must be a positive integer" ;; esac
case "$OUTPUT" in /*) ;; *) die "--output must be an absolute path" ;; esac
validate_meta_scalar_path --output "$OUTPUT" || exit 2

if [[ -n "$PROMPT" && -n "$PROMPT_FILE" ]]; then
    die "exactly one of --prompt or --prompt-file is required, not both"
fi
if [[ -z "$PROMPT" && -z "$PROMPT_FILE" ]]; then
    die "exactly one of --prompt or --prompt-file is required"
fi
if [[ -n "$PROMPT_FILE" ]]; then
    [[ -f "$PROMPT_FILE" ]] || die "--prompt-file not found: $PROMPT_FILE"
    PROMPT=$(cat "$PROMPT_FILE")
fi

case "$SANDBOX" in full-auto|read-only) ;; *) die "--sandbox must be full-auto or read-only" ;; esac
[[ -d "$WORKDIR" ]] || die "--workdir is not a directory: $WORKDIR"

if [[ ${#ADD_DIRS[@]} -eq 0 ]]; then
    ADD_DIRS=("$WORKDIR")
fi

PROMPT_FILE_SIDECAR="${OUTPUT}.prompt"
printf '%s' "$PROMPT" > "$PROMPT_FILE_SIDECAR"

MODEL_ARGS_TMP=""
CODEX_HOME_DIR=""
trap 'rm -f "${MODEL_ARGS_TMP:-}"; rm -rf "${CODEX_HOME_DIR:-}"' EXIT

CODEX_HOME_DIR=$(mktemp -d "${TMPDIR:-/tmp}/larch-codex-exec-home-XXXXXX")
if [[ -f ~/.codex/config.toml ]]; then
    cp ~/.codex/config.toml "$CODEX_HOME_DIR/config.toml"
fi

AUTH_PREP_RC=0
external_prepare_codex_auth "$CODEX_HOME_DIR" || AUTH_PREP_RC=$?
if (( AUTH_PREP_RC != 0 )); then
    if external_codex_env_key_enabled; then
        _auth_failure_reason="codex OPENAI_API_KEY auth setup failed (exit $AUTH_PREP_RC)"
    else
        _auth_failure_reason="codex auth setup failed (exit $AUTH_PREP_RC)"
    fi
    write_preflight_bundle "$AUTH_PREP_RC" "$_auth_failure_reason"
fi

MODEL_ARGS_TMP=$(mktemp)
MODEL_ARGS_ERR=$(mktemp)
MODEL_ARGS_RC=0
_model_args_flags=(--tool codex)
[[ "$WITH_EFFORT" == true ]] && _model_args_flags+=(--with-effort)
"$SCRIPT_DIR/agent-model-args.sh" "${_model_args_flags[@]}" > "$MODEL_ARGS_TMP" 2> "$MODEL_ARGS_ERR" || MODEL_ARGS_RC=$?
if [[ "$MODEL_ARGS_RC" -ne 0 ]]; then
    _ma_reason=$(head -1 "$MODEL_ARGS_ERR" 2>/dev/null | tr '\n' ' ')
    rm -f "$MODEL_ARGS_ERR"
    write_preflight_bundle "$MODEL_ARGS_RC" "agent-model-args.sh failed (exit $MODEL_ARGS_RC): ${_ma_reason:-unknown}"
fi
rm -f "$MODEL_ARGS_ERR"
MODEL_ARGS=()
while IFS= read -r arg; do
    MODEL_ARGS+=("$arg")
done < "$MODEL_ARGS_TMP"

PROJECT_KEY=${WORKDIR//\\/\\\\}
PROJECT_KEY=${PROJECT_KEY//\"/\\\"}
TRUST_CONFIG_ARG="projects.\"$PROJECT_KEY\".trust_level=\"trusted\""
CODEX_AUTH_ARGS=()
external_codex_auth_config_args CODEX_AUTH_ARGS

TIMING_START_S=$(date +%s)
LAUNCHER_EXIT=0
SIDECAR_LOG="${OUTPUT}.sidecar"
CODEX_EVENTS="${OUTPUT}.events.jsonl"
: > "${OUTPUT}.token-record" 2>/dev/null || true
MAX_AUTH_RETRIES=${LARCH_EXTERNAL_AUTH_RETRIES:-5}
case "$MAX_AUTH_RETRIES" in ''|*[!0-9]*|0) MAX_AUTH_RETRIES=5 ;; esac
HOLD=${LARCH_EXTERNAL_SERIAL_LOCK_DELAY:-0.5}

SANDBOX_ARGS=()
case "$SANDBOX" in
    full-auto) SANDBOX_ARGS=(--full-auto) ;;
    read-only) SANDBOX_ARGS=(--sandbox read-only) ;;
esac

ADD_DIR_ARGS=()
for _add_dir in "${ADD_DIRS[@]}"; do
    ADD_DIR_ARGS+=(--add-dir "$_add_dir")
done

AUTH_ATTEMPT=1
while (( AUTH_ATTEMPT <= MAX_AUTH_RETRIES )); do
    _SERIAL_LOCK=""
    external_serial_lock_acquire _SERIAL_LOCK "codex"
    external_serial_lock_release_after "$_SERIAL_LOCK" "$HOLD"
    LAUNCHER_EXIT=0
    rm -f "$CODEX_EVENTS"
    (
        cd "$WORKDIR" || exit 1
        CODEX_HOME="$CODEX_HOME_DIR" RUN_EXTERNAL_AGENT_INNER_SENTINEL_SUFFIX=.inner.done \
            "$SCRIPT_DIR/run-external-agent.sh" \
            --tool codex \
            --output "$OUTPUT" \
            --timeout "$TIMEOUT" \
            -- \
            codex exec "${SANDBOX_ARGS[@]}" -C "$WORKDIR" \
            "${ADD_DIR_ARGS[@]+"${ADD_DIR_ARGS[@]}"}" \
            ${MODEL_ARGS[@]+"${MODEL_ARGS[@]}"} \
            -c "$TRUST_CONFIG_ARG" \
            ${CODEX_AUTH_ARGS[@]+"${CODEX_AUTH_ARGS[@]}"} \
            --output-last-message "$OUTPUT" \
            --json \
            -- \
            "$PROMPT" \
            >"$CODEX_EVENTS" 2>"$SIDECAR_LOG"
    ) || LAUNCHER_EXIT=$?
    if (( LAUNCHER_EXIT != 0 && AUTH_ATTEMPT < MAX_AUTH_RETRIES )) && external_is_auth_failure "codex" "$SIDECAR_LOG"; then
        AUTH_ATTEMPT=$((AUTH_ATTEMPT + 1))
        : > "$SIDECAR_LOG" 2>/dev/null || true
        continue
    fi
    break
done

if (( LAUNCHER_EXIT != 0 )); then
    external_launcher_mirror_quota_from_events "$CODEX_EVENTS" "$SIDECAR_LOG"
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

if [[ ! -s "$CODEX_EVENTS" ]]; then
    printf '{}\n' > "$CODEX_EVENTS"
fi

codex_launcher_record_usage_from_events "$PLUGIN_ROOT" "$CODEX_EVENTS" "$SIDECAR_LOG" "$USAGE_LABEL" "${OUTPUT}.token-record"

_add_dirs_json="[]"
if [[ ${#ADD_DIRS[@]} -gt 0 ]]; then
    if launcher_jq_available; then
        _add_dirs_json=$(printf '%s\n' "${ADD_DIRS[@]}" | jq -R . | jq -s -c .)
    elif ! _add_dirs_json=$(json_array_from_args "${ADD_DIRS[@]}"); then
        larch_err "launch-codex-exec.sh: failed to serialize --add-dir metadata without jq; retry metadata will fall back to workdir only"
        _add_dirs_json=$(json_array_from_args "$WORKDIR") || _add_dirs_json="[]"
    fi
fi
codex_launcher_append_codex_exec_outer_meta \
    "${OUTPUT}.meta" \
    "$SCRIPT_DIR/launch-codex-exec.sh" \
    "$PROMPT_FILE_SIDECAR" \
    "$WORKDIR" \
    "$SANDBOX" \
    "$WITH_EFFORT" \
    "$USAGE_LABEL" \
    "$TIMING_TASK_KIND" \
    "$_add_dirs_json"

codex_launcher_promote_inner_done "$OUTPUT"

emit_kv LAUNCHER_EXIT "$LAUNCHER_EXIT"
emit_kv OUTPUT "$OUTPUT"
exit 0
