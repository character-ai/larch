#!/usr/bin/env bash
# run-negotiation-round.sh — Run one negotiation round with an external reviewer.
#
# Wraps the Codex stdin-pipe and Cursor agent-prompt negotiation flows
# from the Negotiation Protocol in external-reviewers.md. Removes the
# previous output file before running to ensure fresh results.
#
# Usage:
#   run-negotiation-round.sh --tool codex|cursor --prompt-file <path> --output <path> --workspace <path>
#
# Arguments:
#   --tool        — Which reviewer tool (codex or cursor)
#   --prompt-file — Path to the negotiation prompt file
#   --output      — Path to write the reviewer's response
#   --workspace   — Path to the repository workspace
#
# Outputs (key=value to stdout):
#   RESPONSE_FILE=<path>
#
# Exit codes:
#   0 — success (response written)
#   1 — usage/argument error
#   2 — reviewer command failed
#   3 — cursor_auth_preflight failure
#   other — agent-model-args.sh failure propagated from the helper

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init
# shellcheck source=scripts/lib-external-launcher-common.sh
source "$SCRIPT_DIR/lib-external-launcher-common.sh"

usage() { larch_err "Usage: run-negotiation-round.sh --tool codex|cursor --prompt-file <path> --output <path> --workspace <path>"; }

TOOL=""
PROMPT_FILE=""
OUTPUT_FILE=""
WORKSPACE=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --tool) TOOL="${2:?--tool requires a value}"; shift 2 ;;
        --prompt-file) PROMPT_FILE="${2:?--prompt-file requires a value}"; shift 2 ;;
        --output) OUTPUT_FILE="${2:?--output requires a value}"; shift 2 ;;
        --workspace) WORKSPACE="${2:?--workspace requires a value}"; shift 2 ;;
        --help) usage; exit 0 ;;
        *) larch_err "Unknown option: $1"; usage; exit 1 ;;
    esac
done

if [[ -z "$TOOL" ]] || [[ -z "$PROMPT_FILE" ]] || [[ -z "$OUTPUT_FILE" ]] || [[ -z "$WORKSPACE" ]]; then
    larch_err "ERROR: --tool, --prompt-file, --output, and --workspace are all required"
    usage; exit 1
fi

if [[ ! -f "$PROMPT_FILE" ]]; then
    larch_err "ERROR: prompt file not found: $PROMPT_FILE"
    exit 1
fi

# Remove previous output to ensure fresh results
rm -f "$OUTPUT_FILE"

case "$TOOL" in
    codex)
        codex_events="${OUTPUT_FILE%.txt}.events.jsonl"
        codex_sidecar="${OUTPUT_FILE%.txt}.sidecar"
        codex_home=""
        CODEX_MODEL_ARGS_TMP=""
        _negotiation_codex_cleanup() {
            rm -f "${CODEX_MODEL_ARGS_TMP:-}"
            rm -rf "${codex_home:-}"
        }
        codex_home=$(mktemp -d "${TMPDIR:-/tmp}/larch-codex-negotiation-home-XXXXXX")
        trap '_negotiation_codex_cleanup' EXIT
        if [[ -f ~/.codex/config.toml ]]; then
            if ! cp ~/.codex/config.toml "$codex_home/config.toml"; then
                _negotiation_codex_cleanup
                emit_kv RESPONSE_FILE "$OUTPUT_FILE"
                exit 2
            fi
        fi
        if ! external_prepare_codex_auth "$codex_home"; then
            _negotiation_codex_cleanup
            emit_kv RESPONSE_FILE "$OUTPUT_FILE"
            exit 2
        fi
        CODEX_MODEL_ARGS_TMP=$(mktemp)
        if "$SCRIPT_DIR/agent-model-args.sh" --tool codex > "$CODEX_MODEL_ARGS_TMP"; then
            :
        else
            rc=$?
            _negotiation_codex_cleanup
            exit "$rc"
        fi
        CODEX_MODEL_ARGS=()
        while IFS= read -r arg; do
            CODEX_MODEL_ARGS+=("$arg")
        done < "$CODEX_MODEL_ARGS_TMP"
        rm -f "$CODEX_MODEL_ARGS_TMP"
        CODEX_MODEL_ARGS_TMP=""
        project_key=${WORKSPACE//\\/\\\\}
        project_key=${project_key//\"/\\\"}
        trust_config_arg="projects.\"$project_key\".trust_level=\"trusted\""
        CODEX_AUTH_ARGS=()
        external_codex_auth_config_args CODEX_AUTH_ARGS
        _SERIAL_LOCK=""
        if ! external_serial_lock_acquire _SERIAL_LOCK "codex"; then
            _negotiation_codex_cleanup
            emit_kv RESPONSE_FILE "$OUTPUT_FILE"
            exit 2
        fi
        external_serial_lock_release_after "$_SERIAL_LOCK" "${LARCH_EXTERNAL_SERIAL_LOCK_DELAY:-0.5}"
        rm -f "$codex_events" "$codex_sidecar"
        codex_rc=0
        CODEX_HOME="$codex_home" codex exec --full-auto -C "$WORKSPACE" ${CODEX_MODEL_ARGS[@]+"${CODEX_MODEL_ARGS[@]}"} -c "$trust_config_arg" ${CODEX_AUTH_ARGS[@]+"${CODEX_AUTH_ARGS[@]}"} --output-last-message "$OUTPUT_FILE" --json -- - < "$PROMPT_FILE" >"$codex_events" 2>"$codex_sidecar" || codex_rc=$? # lint-codex-exec-auth: ok inline stdin-pipe dispatch; auth wired per check-reviewers.sh:211-245
        if [[ "$codex_rc" -ne 0 ]]; then
            external_launcher_mirror_quota_from_events "$codex_events" "$codex_sidecar"
        fi
        external_launcher_record_usage_from_events "$PLUGIN_ROOT" "$codex_events" "$codex_sidecar" "codex_negotiation" || true
        _negotiation_codex_cleanup
        if [[ "$codex_rc" -ne 0 ]]; then
            emit_kv RESPONSE_FILE "$OUTPUT_FILE"
            exit 2
        fi
        ;;
    cursor)
        CURSOR_MODEL_ARGS_TMP=$(mktemp)
        if "$SCRIPT_DIR/agent-model-args.sh" --tool cursor > "$CURSOR_MODEL_ARGS_TMP"; then
            :
        else
            rc=$?
            rm -f "$CURSOR_MODEL_ARGS_TMP"
            exit "$rc"
        fi
        CURSOR_MODEL_ARGS=()
        while IFS= read -r arg; do
            CURSOR_MODEL_ARGS+=("$arg")
        done < "$CURSOR_MODEL_ARGS_TMP"
        rm -f "$CURSOR_MODEL_ARGS_TMP"
        # Source the Cursor auth helper and run preflight before launching.
        # No sentinel collector here (negotiation is foreground-synchronous),
        # so direct exit 3 on preflight failure is the distinct auth contract.
        # Emit RESPONSE_FILE= on the preflight-failure path so the stdout
        # envelope is symmetric with the exit-2 reviewer-command-failed path
        # (callers can `grep RESPONSE_FILE=` regardless of failure class).
        # shellcheck source=scripts/lib-cursor-auth.sh
        # shellcheck disable=SC1091
        . "$SCRIPT_DIR/lib-cursor-auth.sh"
        if ! cursor_auth_preflight; then
            emit_kv RESPONSE_FILE "$OUTPUT_FILE"
            exit 3
        fi
        cursor_auth_export_env
        _SERIAL_LOCK=""
        external_serial_lock_acquire _SERIAL_LOCK "cursor"
        external_serial_lock_release_after "$_SERIAL_LOCK" "${LARCH_EXTERNAL_SERIAL_LOCK_DELAY:-0.5}"
        cursor agent -p --force --trust ${CURSOR_MODEL_ARGS[@]+"${CURSOR_MODEL_ARGS[@]}"} --workspace "$WORKSPACE" \
            "$("$SCRIPT_DIR/cursor-wrap-prompt.sh" "Read the negotiation prompt from $PROMPT_FILE and respond to it.")" \
            > "$OUTPUT_FILE" 2>&1
        ;;
    *)
        larch_err "ERROR: --tool must be 'codex' or 'cursor' (got: $TOOL)"
        exit 1
        ;;
esac

EXIT_CODE=$?
if [[ $EXIT_CODE -ne 0 ]]; then
    emit_kv RESPONSE_FILE "$OUTPUT_FILE"
    exit 2
fi

emit_kv RESPONSE_FILE "$OUTPUT_FILE"
