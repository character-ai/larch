#!/usr/bin/env bash
# launch-cursor-review.sh — Launch a Cursor agent review with automatic model
# args and prompt wrapping.
#
# Absorbs the command-substitution chain (agent-model-args.sh + cursor-wrap-prompt.sh
# + optionally render-specialist-prompt.sh) so SKILL.md Bash blocks are simple
# script invocations that don't trigger Claude Code permission prompts.
#
# Two modes:
#   Generic:    --prompt "review text..."
#   Specialist: --agent-file agents/reviewer-X.md --mode diff|description
#               [--description-text TEXT] [--scope-files PATH] [--competition-notice]
#
# Usage:
#   launch-cursor-review.sh --output FILE --timeout SECS --prompt "PROMPT"
#   launch-cursor-review.sh --output FILE --timeout SECS \
#       --agent-file FILE --mode diff|description [--description-text T] [--scope-files F] [--competition-notice]
#
# Output: same stdout as run-external-agent.sh (no additional output).
#
# Exit codes: passed through from run-external-agent.sh.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd -P)}"

OUTPUT=""
TIMEOUT=""
PROMPT=""
AGENT_FILE=""
MODE=""
DESCRIPTION_TEXT=""
SCOPE_FILES=""
COMPETITION_NOTICE=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --output) OUTPUT="${2:?--output requires a value}"; shift 2 ;;
        --timeout) TIMEOUT="${2:?--timeout requires a value}"; shift 2 ;;
        --prompt) PROMPT="${2:?--prompt requires a value}"; shift 2 ;;
        --agent-file) AGENT_FILE="${2:?--agent-file requires a value}"; shift 2 ;;
        --mode) MODE="${2:?--mode requires a value}"; shift 2 ;;
        --description-text) DESCRIPTION_TEXT="${2:?--description-text requires a value}"; shift 2 ;;
        --scope-files) SCOPE_FILES="${2:?--scope-files requires a value}"; shift 2 ;;
        --competition-notice) COMPETITION_NOTICE=true; shift ;;
        *) echo "launch-cursor-review.sh: unknown flag: $1" >&2; exit 2 ;;
    esac
done

if [[ -z "$OUTPUT" ]]; then
    echo "launch-cursor-review.sh: --output is required" >&2; exit 2
fi
if [[ -z "$TIMEOUT" ]]; then
    echo "launch-cursor-review.sh: --timeout is required" >&2; exit 2
fi

if [[ -n "$AGENT_FILE" ]]; then
    RENDER_ARGS=(--agent-file "$AGENT_FILE" --mode "$MODE")
    [[ -n "$DESCRIPTION_TEXT" ]] && RENDER_ARGS+=(--description-text "$DESCRIPTION_TEXT")
    [[ -n "$SCOPE_FILES" ]] && RENDER_ARGS+=(--scope-files "$SCOPE_FILES")
    [[ "$COMPETITION_NOTICE" == "true" ]] && RENDER_ARGS+=(--competition-notice)
    PROMPT=$("$SCRIPT_DIR/render-specialist-prompt.sh" "${RENDER_ARGS[@]}")
elif [[ -z "$PROMPT" ]]; then
    echo "launch-cursor-review.sh: either --prompt or --agent-file is required" >&2; exit 2
fi

MODEL_ARGS=$("$SCRIPT_DIR/agent-model-args.sh" --tool cursor --with-effort)
WRAPPED_PROMPT=$("$SCRIPT_DIR/cursor-wrap-prompt.sh" "$PROMPT")
RUN_EXTERNAL="$SCRIPT_DIR/run-external-agent.sh"
SIDECAR="${OUTPUT}.sidecar"

# shellcheck disable=SC2086
EXIT_CODE=0
if : > "$SIDECAR" 2>/dev/null; then
    # shellcheck disable=SC2086
    "$RUN_EXTERNAL" \
        --tool cursor \
        --output "$OUTPUT" \
        --timeout "$TIMEOUT" \
        --capture-stdout-only \
        -- \
        cursor agent -p --force --trust \
        --output-format json \
        $MODEL_ARGS \
        --workspace "$PWD" \
        "$WRAPPED_PROMPT" \
        2>>"$SIDECAR" || EXIT_CODE=$?
else
    SIDECAR=/dev/null
    # shellcheck disable=SC2086
    "$RUN_EXTERNAL" \
        --tool cursor \
        --output "$OUTPUT" \
        --timeout "$TIMEOUT" \
        --capture-stdout-only \
        -- \
        cursor agent -p --force --trust \
        --output-format json \
        $MODEL_ARGS \
        --workspace "$PWD" \
        "$WRAPPED_PROMPT" \
        2>/dev/null || EXIT_CODE=$?
fi

# Atomic-or-bust JSON-extraction pattern: keep $OUTPUT pointing at usable
# bytes for downstream collectors at every step. The previous shape
# (`mv $OUTPUT $OUTPUT.json` then guarded jq) destroyed $OUTPUT before
# proving the jq extraction would succeed — if jq was missing or extraction
# failed, $OUTPUT ended up empty/missing while the only copy of the run
# output sat unreachable at $OUTPUT.json. Fix:
#   1. Copy (not move) bytes to $OUTPUT.json sidecar.
#   2. Try to extract .result via jq into a temp file.
#   3. ONLY install the temp file over $OUTPUT after jq succeeds with
#      non-empty content — else leave the original bytes at $OUTPUT
#      unchanged so collectors still see prose.
if [[ -s "$OUTPUT" ]]; then
    cp "$OUTPUT" "${OUTPUT}.json" 2>/dev/null || true
    if command -v jq >/dev/null 2>&1 && [[ -s "${OUTPUT}.json" ]]; then
        EXTRACT_TMP="${OUTPUT}.extract.$$"
        if jq -re '.result // ""' "${OUTPUT}.json" > "$EXTRACT_TMP" 2>/dev/null && [[ -s "$EXTRACT_TMP" ]]; then
            mv "$EXTRACT_TMP" "$OUTPUT"
        else
            rm -f "$EXTRACT_TMP"
            # jq missing, JSON malformed, or empty .result — leave $OUTPUT as
            # raw JSON bytes; collectors that prefer prose will see literal
            # JSON, which is still bounded content and not an empty file.
        fi
        read -r INP OUT CR CW < <(jq -r '.usage // {} | "\(.inputTokens // 0) \(.outputTokens // 0) \(.cacheReadTokens // 0) \(.cacheWriteTokens // 0)"' "${OUTPUT}.json" 2>/dev/null || echo "0 0 0 0")
        if [[ "$INP" =~ ^[0-9]+$ && "$OUT" =~ ^[0-9]+$ && "$CR" =~ ^[0-9]+$ && "$CW" =~ ^[0-9]+$ ]]; then
            TOT=$((INP + OUT + CR + CW))
            "$PLUGIN_ROOT/scripts/token-ledger.sh" record-vendor cursor input="$INP" output="$OUT" cache_read="$CR" cache_create="$CW" total="$TOT" raw="cursor_review" >/dev/null 2>&1 || true
        fi
    fi
fi

exit "$EXIT_CODE"
