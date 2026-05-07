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

usage() { echo "Usage: run-negotiation-round.sh --tool codex|cursor --prompt-file <path> --output <path> --workspace <path>" >&2; }

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
        *) echo "Unknown option: $1" >&2; usage; exit 1 ;;
    esac
done

if [[ -z "$TOOL" ]] || [[ -z "$PROMPT_FILE" ]] || [[ -z "$OUTPUT_FILE" ]] || [[ -z "$WORKSPACE" ]]; then
    echo "ERROR: --tool, --prompt-file, --output, and --workspace are all required" >&2
    usage; exit 1
fi

if [[ ! -f "$PROMPT_FILE" ]]; then
    echo "ERROR: prompt file not found: $PROMPT_FILE" >&2
    exit 1
fi

# Remove previous output to ensure fresh results
rm -f "$OUTPUT_FILE"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

case "$TOOL" in
    codex)
        CODEX_MODEL_ARGS_TMP=$(mktemp)
        if "$SCRIPT_DIR/agent-model-args.sh" --tool codex > "$CODEX_MODEL_ARGS_TMP"; then
            :
        else
            rc=$?
            rm -f "$CODEX_MODEL_ARGS_TMP"
            exit "$rc"
        fi
        CODEX_MODEL_ARGS=()
        while IFS= read -r arg; do
            CODEX_MODEL_ARGS+=("$arg")
        done < "$CODEX_MODEL_ARGS_TMP"
        rm -f "$CODEX_MODEL_ARGS_TMP"
        codex exec --full-auto -C "$WORKSPACE" ${CODEX_MODEL_ARGS[@]+"${CODEX_MODEL_ARGS[@]}"} \
            --output-last-message "$OUTPUT_FILE" - < "$PROMPT_FILE" 2>&1
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
            echo "RESPONSE_FILE=$OUTPUT_FILE"
            exit 3
        fi
        CURSOR_AUTH_ARGS=()
        cursor_auth_argv
        cursor agent -p --force --trust ${CURSOR_MODEL_ARGS[@]+"${CURSOR_MODEL_ARGS[@]}"} ${CURSOR_AUTH_ARGS[@]+"${CURSOR_AUTH_ARGS[@]}"} --workspace "$WORKSPACE" \
            "$("$SCRIPT_DIR/cursor-wrap-prompt.sh" "Read the negotiation prompt from $PROMPT_FILE and respond to it.")" \
            > "$OUTPUT_FILE" 2>&1
        ;;
    *)
        echo "ERROR: --tool must be 'codex' or 'cursor' (got: $TOOL)" >&2
        exit 1
        ;;
esac

EXIT_CODE=$?
if [[ $EXIT_CODE -ne 0 ]]; then
    echo "RESPONSE_FILE=$OUTPUT_FILE"
    exit 2
fi

echo "RESPONSE_FILE=$OUTPUT_FILE"
