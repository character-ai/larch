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
PROMPT_FILE=""
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
        --prompt-file) PROMPT_FILE="${2:?--prompt-file requires a value}"; shift 2 ;;
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

# shellcheck source=scripts/lib-validate-meta-path.sh
source "$SCRIPT_DIR/lib-validate-meta-path.sh"
validate_meta_scalar_path --output "$OUTPUT" || exit 1
case "$TIMEOUT" in
    ''|*[!0-9]*) echo "launch-cursor-review.sh: --timeout must be a positive integer" >&2; exit 2 ;;
esac
# Reject zero-padded zero values (e.g., 00, 000) that would pass the digit-only
# case above but fail the wrapper's arithmetic floor check at run-external-agent.sh
# AFTER the launcher has installed its EXIT trap and written sidecars. Keeps
# validate-before-side-effects intact (per FINDING_5 of the design plan review)
# and matches the floor used by launch-cursor-implement.sh / launch-gemini-review.sh.
if (( 10#$TIMEOUT < 1 )); then
    echo "launch-cursor-review.sh: --timeout must be >= 1" >&2
    exit 2
fi

_src_count=0
[[ -n "$PROMPT" ]] && _src_count=$((_src_count + 1))
[[ -n "$AGENT_FILE" ]] && _src_count=$((_src_count + 1))
[[ -n "$PROMPT_FILE" ]] && _src_count=$((_src_count + 1))
if [[ "$_src_count" -gt 1 ]]; then
    echo "launch-cursor-review.sh: --prompt, --agent-file, and --prompt-file are mutually exclusive" >&2
    exit 2
fi
if [[ "$_src_count" -eq 0 ]]; then
    echo "launch-cursor-review.sh: one of --prompt, --agent-file, --prompt-file is required" >&2
    exit 2
fi

WRAPPER_PID=""
# shellcheck disable=SC2329,SC2317  # body invoked indirectly by the EXIT trap below.
_publish_done_on_exit() {
    # The shell exit status is fixed at trap entry; this trap only publishes sidecars.
    if [[ -z "$OUTPUT" || -f "${OUTPUT}.done" ]]; then
        return
    fi
    if [[ -n "$WRAPPER_PID" ]] && kill -0 "$WRAPPER_PID" 2>/dev/null; then
        kill "$WRAPPER_PID" 2>/dev/null || true
        wait "$WRAPPER_PID" 2>/dev/null || true
    fi
    if [[ -f "${OUTPUT}.inner.done" ]]; then
        mv -f "${OUTPUT}.inner.done" "${OUTPUT}.done" 2>/dev/null || true
    else
        echo "99" > "${OUTPUT}.done" 2>/dev/null || true
    fi
    return 0
}
trap _publish_done_on_exit EXIT

if [[ -n "$PROMPT_FILE" ]]; then
    if ! PROMPT=$({ cat -- "$PROMPT_FILE"; _cat_status=$?; printf X; exit "$_cat_status"; }); then
        echo "launch-cursor-review.sh: failed to read --prompt-file $PROMPT_FILE" >&2
        exit 1
    fi
    PROMPT=${PROMPT%X}
fi

if [[ -n "$AGENT_FILE" ]]; then
    RENDER_ARGS=(--agent-file "$AGENT_FILE" --mode "$MODE")
    [[ -n "$DESCRIPTION_TEXT" ]] && RENDER_ARGS+=(--description-text "$DESCRIPTION_TEXT")
    [[ -n "$SCOPE_FILES" ]] && RENDER_ARGS+=(--scope-files "$SCOPE_FILES")
    [[ "$COMPETITION_NOTICE" == "true" ]] && RENDER_ARGS+=(--competition-notice)
    PROMPT=$("$SCRIPT_DIR/render-specialist-prompt.sh" "${RENDER_ARGS[@]}")
fi

MODEL_ARGS=$("$SCRIPT_DIR/agent-model-args.sh" --tool cursor --with-effort)
WRAPPED_PROMPT=$({ "$SCRIPT_DIR/cursor-wrap-prompt.sh" "$PROMPT"; _wrap_status=$?; printf X; exit "$_wrap_status"; })
WRAPPED_PROMPT=${WRAPPED_PROMPT%X}
RUN_EXTERNAL="$SCRIPT_DIR/run-external-agent.sh"
SIDECAR="${OUTPUT}.sidecar"
PROMPT_FILE_SIDECAR="${OUTPUT}.prompt"
printf '%s' "$PROMPT" > "$PROMPT_FILE_SIDECAR"

# shellcheck disable=SC2086
EXIT_CODE=0
if : > "$SIDECAR" 2>/dev/null; then
    _STDERR_TARGET="$SIDECAR"
else
    SIDECAR=/dev/null
    _STDERR_TARGET=/dev/null
fi

# shellcheck disable=SC2086
RUN_EXTERNAL_AGENT_INNER_SENTINEL_SUFFIX=.inner.done \
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
        2>>"$_STDERR_TARGET" &
WRAPPER_PID=$!
wait "$WRAPPER_PID" && EXIT_CODE=0 || EXIT_CODE=$?

if [[ -f "${OUTPUT}.meta" ]]; then
    {
        printf 'OUTER_LAUNCHER=%s\n' "$SCRIPT_DIR/launch-cursor-review.sh"
        printf 'OUTER_LAUNCHER_PROMPT_FILE=%s\n' "$PROMPT_FILE_SIDECAR"
        printf 'OUTER_LAUNCHER_WORKDIR=%s\n' "$PWD"
    } >> "${OUTPUT}.meta"
fi

# Test-only deterministic hook (FINDING_1 of /review round 1 hardening): the
# legacy `eval "$LARCH_TEST_TRAP_AFTER_INNER_DONE"` was an env-var → arbitrary-
# shell channel in shipped runtime code. Replaced with a strictly-gated
# source-file pattern that requires:
#   1. LARCH_ALLOW_TEST_HOOKS=1 (exact match; production callers must NOT set this).
#   2. LARCH_TEST_TRAP_AFTER_INNER_DONE_FILE points at a regular non-symlink file
#      that the test harness wrote under its own tmpdir.
# A production attacker would need to set TWO env vars AND control a writable
# filesystem path the launcher will source, which is a much higher bar than
# leaking one env var. The harness still controls deterministic post-wrapper
# trap behavior by writing shell snippets to a path inside its session tmpdir.
# The legacy env var name (LARCH_TEST_TRAP_AFTER_INNER_DONE without _FILE) is
# intentionally NOT honored — silent fallback would defeat the gating.
if [[ "${LARCH_ALLOW_TEST_HOOKS:-}" == "1" && -n "${LARCH_TEST_TRAP_AFTER_INNER_DONE_FILE:-}" ]]; then
    if [[ -f "$LARCH_TEST_TRAP_AFTER_INNER_DONE_FILE" && ! -L "$LARCH_TEST_TRAP_AFTER_INNER_DONE_FILE" ]]; then
        # shellcheck source=/dev/null
        source "$LARCH_TEST_TRAP_AFTER_INNER_DONE_FILE"
    fi
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
    # Remove any stale ${OUTPUT}.json from a prior run BEFORE the cp. If cp
    # then fails (full disk, permission, transient I/O), the launcher must not
    # silently fall through to a state where the prior-run JSON is treated as
    # this run's bytes — that would let jq promote the wrong .result into
    # $OUTPUT and record-vendor log the wrong token totals (FINDING_3 of
    # /review round 1). run-external-agent.sh's pre-launch stale cleanup at
    # line ~144 does NOT include .json (the launcher owns that sidecar), so
    # the launcher must clear it itself.
    rm -f "${OUTPUT}.json"
    if ! cp "$OUTPUT" "${OUTPUT}.json" 2>/dev/null; then
        # cp failed — leave $OUTPUT as the wrapper-provided bytes (raw JSON or
        # prose) and skip the post-processing block. Collectors will still see
        # bounded content, just without launcher-extracted .result and without
        # token-ledger updates for this run. Better than silently reading a
        # stale prior-run .json.
        :
    elif command -v jq >/dev/null 2>&1 && [[ -s "${OUTPUT}.json" ]]; then
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

if [[ -f "${OUTPUT}.inner.done" ]]; then
    mv -f "${OUTPUT}.inner.done" "${OUTPUT}.done"
fi
exit "$EXIT_CODE"
