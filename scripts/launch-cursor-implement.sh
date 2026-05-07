#!/usr/bin/env bash
# launch-cursor-implement.sh — Launch the Cursor implementer subprocess for /implement Step 2.
#
# Modeled after launch-cursor-review.sh but with a tighter stdout contract:
# this wrapper redirects run-external-agent.sh's progress chatter (⏳, ✓, ❌)
# to a sidecar log file so the dispatcher (skills/implement/scripts/step2-implement.sh)
# only sees deterministic KEY=VALUE lines on stdout. The dispatcher's parser
# would otherwise be brittle against the wrapper's human-readable progress
# messages.
#
# The Cursor subprocess writes manifest.json and (optionally) qa-pending.json
# atomically inside $IMPLEMENT_TMPDIR — those paths are passed in as flags
# so this launcher does not need to know how the dispatcher organizes its
# tmpdir.
#
# Usage:
#   launch-cursor-implement.sh \
#     --transcript-path  PATH    # where Cursor transcript lands
#     --sidecar-log      PATH    # where run-external-agent.sh chatter is captured
#     --manifest-path    PATH    # where Cursor must write manifest.json
#     --qa-pending-path  PATH    # where Cursor must write qa-pending.json on needs_qa
#     --plan-file        PATH    # input: plan to implement
#     --feature-file     PATH    # input: original feature description
#     --agent-prompt     PATH    # input: agents/cursor-implementer.md path
#     --timeout          SECS    # wall-clock cap for Cursor subprocess
#     [--answers-file    PATH]   # optional: prior-cycle operator answers (resume)
#
# Stdout (KEY=VALUE only — no human progress text):
#   LAUNCHER_EXIT=<int>            # exit code reported by run-external-agent.sh
#   MANIFEST_WRITTEN=<true|false>  # whether manifest.json exists post-run
#   QA_PENDING_WRITTEN=<true|false># whether qa-pending.json exists post-run
#   TRANSCRIPT=<path>              # path to Cursor transcript on disk (sidecar)
#   SIDECAR_LOG=<path>             # path to run-external-agent.sh chatter log
#
# Exit codes:
#   0 — wrapper completed cleanly, regardless of Cursor's own exit code
#       (the dispatcher inspects MANIFEST_WRITTEN + LAUNCHER_EXIT to decide
#       what happened).
#   2 — wrapper-side error (missing flag, missing input file, etc.); exit
#       before launching Cursor.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd -P)}"

TRANSCRIPT_PATH=""
SIDECAR_LOG=""
MANIFEST_PATH=""
QA_PENDING_PATH=""
PLAN_FILE=""
FEATURE_FILE=""
AGENT_PROMPT=""
TIMEOUT=""
ANSWERS_FILE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --transcript-path)  TRANSCRIPT_PATH="${2:?--transcript-path requires a value}"; shift 2 ;;
        --sidecar-log)      SIDECAR_LOG="${2:?--sidecar-log requires a value}"; shift 2 ;;
        --manifest-path)    MANIFEST_PATH="${2:?--manifest-path requires a value}"; shift 2 ;;
        --qa-pending-path)  QA_PENDING_PATH="${2:?--qa-pending-path requires a value}"; shift 2 ;;
        --plan-file)        PLAN_FILE="${2:?--plan-file requires a value}"; shift 2 ;;
        --feature-file)     FEATURE_FILE="${2:?--feature-file requires a value}"; shift 2 ;;
        --agent-prompt)     AGENT_PROMPT="${2:?--agent-prompt requires a value}"; shift 2 ;;
        --timeout)          TIMEOUT="${2:?--timeout requires a value}"; shift 2 ;;
        --answers-file)     ANSWERS_FILE="${2:?--answers-file requires a value}"; shift 2 ;;
        *) echo "launch-cursor-implement.sh: unknown flag: $1" >&2; exit 2 ;;
    esac
done

for var in TRANSCRIPT_PATH SIDECAR_LOG MANIFEST_PATH QA_PENDING_PATH PLAN_FILE FEATURE_FILE AGENT_PROMPT TIMEOUT; do
    if [[ -z "${!var}" ]]; then
        flag_lc=$(printf '%s' "$var" | tr '[:upper:]' '[:lower:]' | tr '_' '-')
        echo "launch-cursor-implement.sh: --$flag_lc is required" >&2
        exit 2
    fi
done
# shellcheck disable=SC2154
[[ -f "$PLAN_FILE" ]]    || { echo "launch-cursor-implement.sh: plan file not found: $PLAN_FILE" >&2; exit 2; }
[[ -f "$FEATURE_FILE" ]] || { echo "launch-cursor-implement.sh: feature file not found: $FEATURE_FILE" >&2; exit 2; }
[[ -f "$AGENT_PROMPT" ]] || { echo "launch-cursor-implement.sh: agent prompt not found: $AGENT_PROMPT" >&2; exit 2; }
if [[ -n "$ANSWERS_FILE" && ! -f "$ANSWERS_FILE" ]]; then
    echo "launch-cursor-implement.sh: --answers-file given but path does not exist: $ANSWERS_FILE" >&2
    exit 2
fi

case "$TIMEOUT" in
    ''|*[!0-9]*|0) echo "launch-cursor-implement.sh: --timeout must be a positive integer (seconds), got '$TIMEOUT'" >&2; exit 2 ;;
esac
if (( 10#$TIMEOUT < 1 )); then
    echo "launch-cursor-implement.sh: --timeout must be a positive integer (seconds), got '$TIMEOUT'" >&2
    exit 2
fi

# Compose the Cursor prompt by concatenating the agent system prompt with
# inline references to the plan, feature, manifest path, qa-pending path,
# and (optionally) the answers file. Keeping this composition in shell (not
# in agent-side prose) lets the launcher's contract document exactly what
# Cursor sees on every invocation without depending on Cursor's tool use to
# read referenced files.
RESUME_BLOCK=""
if [[ -n "$ANSWERS_FILE" ]]; then
    RESUME_BLOCK="$(cat <<EOF

## Resume invocation

This is a RESUME of a prior /implement Step 2 attempt that ended in needs_qa.
Operator answers to your prior questions are in: $ANSWERS_FILE

Per agents/cursor-implementer.md "Resume protocol":
1. Inspect git log main..HEAD and git status FIRST.
2. Read the answers file.
3. If the answers are consistent with prior partial work, continue from there.
4. If not, set status=bailed bail_reason=resume-incompatible — DO NOT git reset.

EOF
)"
fi

PROMPT="$(cat "$AGENT_PROMPT")

## This invocation's parameters

- Plan to implement: $PLAN_FILE
- Original feature description: $FEATURE_FILE
- Write manifest.json (atomically) at: $MANIFEST_PATH
- Write qa-pending.json (atomically, only if status=needs_qa) at: $QA_PENDING_PATH
- Working directory: $PWD (this is the repo root for git operations)
$RESUME_BLOCK

Begin by inspecting the current branch state, then proceed per the system prompt above."

MODEL_ARGS=$("$SCRIPT_DIR/agent-model-args.sh" --tool cursor --with-effort)
WRAPPED_PROMPT=$("$SCRIPT_DIR/cursor-wrap-prompt.sh" "$PROMPT")

# Source the Cursor auth helper. On preflight failure (Darwin + empty
# CURSOR_API_KEY + missing `cursor-user` keychain entry), emit the standard
# KV envelope before exiting so step2-implement.sh's parser surfaces a
# specific failure (LAUNCHER_EXIT=2 + actionable SIDECAR_LOG content)
# instead of a generic timeout/missing-manifest message.
# shellcheck source=scripts/lib-cursor-auth.sh
. "$SCRIPT_DIR/lib-cursor-auth.sh"
PREFLIGHT_RC=0
cursor_auth_preflight 2> >(tee -a "$SIDECAR_LOG" >&2) || PREFLIGHT_RC=$?
if [[ "$PREFLIGHT_RC" != "0" ]]; then
    printf 'LAUNCHER_EXIT=%s\n'           "$PREFLIGHT_RC"
    printf 'MANIFEST_WRITTEN=false\n'
    printf 'QA_PENDING_WRITTEN=false\n'
    printf 'TRANSCRIPT=%s\n'              "$TRANSCRIPT_PATH"
    printf 'SIDECAR_LOG=%s\n'             "$SIDECAR_LOG"
    # Exit 0 keeps the launcher contract (LAUNCHER_EXIT is the failure
    # signal, not the wrapper's process exit). The dispatcher reads
    # LAUNCHER_EXIT=2 and surfaces the SIDECAR_LOG content.
    exit 0
fi

# Build the conditional --api-key argv segment. CURSOR_AUTH_ARGS is empty
# when CURSOR_API_KEY is unset/whitespace-only (preserves today's
# `cursor login` keychain fallback for users who chose not to set the env
# var); otherwise CURSOR_AUTH_ARGS=(--api-key "$KEY"). Inserted between
# `$MODEL_ARGS` and `--workspace` so the prompt remains the final positional
# argument.
CURSOR_AUTH_ARGS=()
cursor_auth_argv

# Run the wrapper, redirecting its stdout AND stderr to the sidecar log so
# Claude (the dispatcher's caller) never sees the wrapper's progress lines.
# The wrapper's own exit code is captured into LAUNCHER_EXIT.
LAUNCHER_EXIT=0
# shellcheck disable=SC2086
"$SCRIPT_DIR/run-external-agent.sh" \
    --tool cursor \
    --output "$TRANSCRIPT_PATH" \
    --timeout "$TIMEOUT" \
    --capture-stdout-only \
    -- \
    cursor agent -p --force --trust \
    --output-format json \
    $MODEL_ARGS \
    ${CURSOR_AUTH_ARGS[@]+"${CURSOR_AUTH_ARGS[@]}"} \
    --workspace "$PWD" \
    "$WRAPPED_PROMPT" \
    >"$SIDECAR_LOG" 2>&1 || LAUNCHER_EXIT=$?

if command -v jq >/dev/null 2>&1; then
    read -r INP OUT CR CW < <(jq -r '.usage // {} | "\(.inputTokens // 0) \(.outputTokens // 0) \(.cacheReadTokens // 0) \(.cacheWriteTokens // 0)"' "$TRANSCRIPT_PATH" 2>/dev/null || echo "0 0 0 0")
    if [[ "$INP" =~ ^[0-9]+$ && "$OUT" =~ ^[0-9]+$ && "$CR" =~ ^[0-9]+$ && "$CW" =~ ^[0-9]+$ ]]; then
        TOT=$((INP + OUT + CR + CW))
        "$PLUGIN_ROOT/scripts/token-ledger.sh" record-vendor cursor input="$INP" output="$OUT" cache_read="$CR" cache_create="$CW" total="$TOT" raw="cursor_implement" >/dev/null 2>&1 || true
    fi
fi

MANIFEST_WRITTEN=false
QA_PENDING_WRITTEN=false
[[ -s "$MANIFEST_PATH" ]]   && MANIFEST_WRITTEN=true
[[ -s "$QA_PENDING_PATH" ]] && QA_PENDING_WRITTEN=true

printf 'LAUNCHER_EXIT=%s\n'           "$LAUNCHER_EXIT"
printf 'MANIFEST_WRITTEN=%s\n'        "$MANIFEST_WRITTEN"
printf 'QA_PENDING_WRITTEN=%s\n'      "$QA_PENDING_WRITTEN"
printf 'TRANSCRIPT=%s\n'              "$TRANSCRIPT_PATH"
printf 'SIDECAR_LOG=%s\n'             "$SIDECAR_LOG"
exit 0
