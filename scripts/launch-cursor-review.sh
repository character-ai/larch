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
# shellcheck source=scripts/lib-cursor-launcher-common.sh
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib-cursor-launcher-common.sh"
# shellcheck source=scripts/lib-dirty-tree-sidecar.sh
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib-dirty-tree-sidecar.sh"

# shellcheck disable=SC2329 # invoked indirectly by the EXIT trap.
_emit_timing_record() {
    local rc=${1:-$?}
    local end_s status
    end_s=$(date +%s)
    (( rc == 0 )) && status=complete || status=signal
    [[ -n "${TIMING_START_S:-}" && -n "${OUTPUT:-}" ]] || return 0
    "$PLUGIN_ROOT/scripts/timing-ledger.sh" record-vendor-task \
        --vendor cursor \
        --task-kind "${TIMING_TASK_KIND:-cursor-review}" \
        --start-s "$TIMING_START_S" \
        --end-s "$end_s" \
        --output "$OUTPUT" \
        --exit-code "$rc" \
        --status "$status" \
        >/dev/null 2>&1 || true
}

OUTPUT=""
TIMEOUT=""
PROMPT=""
PROMPT_FILE=""
AGENT_FILE=""
MODE=""
DESCRIPTION_TEXT=""
SCOPE_FILES=""
COMPETITION_NOTICE=false
TIMING_TASK_KIND="${LARCH_TIMING_TASK_KIND:-}"
TOKEN_BUDGET_CAP=""

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
        --timing-task-kind) [[ -n "${2:-}" && "${2}" != --* ]] || { echo "launch-cursor-review.sh: --timing-task-kind requires a non-empty, non-flag-like value" >&2; exit 2; }; TIMING_TASK_KIND="$2"; shift 2 ;;
        --token-budget-cap) case "${2:-}" in ''|*[!0-9]*) echo "launch-cursor-review.sh: --token-budget-cap requires a positive integer" >&2; exit 2 ;; esac; (( 10#${2:-0} >= 1 )) || { echo "launch-cursor-review.sh: --token-budget-cap requires a positive integer" >&2; exit 2; }; TOKEN_BUDGET_CAP="$2"; shift 2 ;;
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
# shellcheck disable=SC1091
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

if [[ -n "${IMPLEMENT_TMPDIR:-}" && -s "${IMPLEMENT_TMPDIR}/session-id" ]]; then
    file_id=$(tr -d '\r\n' < "${IMPLEMENT_TMPDIR}/session-id" 2>/dev/null || true)
    if [[ -n "$file_id" ]]; then export LARCH_TOKEN_SESSION_ID="$file_id"; fi
fi
if [[ -n "${IMPLEMENT_TMPDIR:-}" && -s "${IMPLEMENT_TMPDIR}/claude-source.env" ]]; then
    export LARCH_CLAUDE_SOURCE_FILE="${IMPLEMENT_TMPDIR}/claude-source.env"
fi

# Per-step token budget cap: short-circuit before spawning Cursor when the
# combined vendor spend since the last ledger mark already exceeds the cap.
if [[ -n "$TOKEN_BUDGET_CAP" ]]; then
    _budget_out=$("$SCRIPT_DIR/check-step-token-budget.sh" --cap "$TOKEN_BUDGET_CAP" --step "${TIMING_TASK_KIND:-cursor-review}" 2>/dev/null || true)
    _budget_status=$(printf '%s' "$_budget_out" | awk '{for(i=1;i<=NF;i++){if($i~/^STATUS=/){print substr($i,8);exit}}}')
    if [[ "$_budget_status" == "cap_hit" ]]; then
        printf '⚠ launch-cursor-review.sh: step token budget cap of %s tokens exceeded (%s combined vendor tokens); external reviewer fan-out skipped\n' \
            "$TOKEN_BUDGET_CAP" "$(printf '%s' "$_budget_out" | awk '{for(i=1;i<=NF;i++){if($i~/^TOTAL=/){print substr($i,7);exit}}}')" >&2
        printf 'STATUS=cap_hit\n' > "$OUTPUT"
        printf 'STATUS=cap_hit\n%s\n' "$_budget_out" > "${OUTPUT}.cap-hit"
        if [[ -n "${IMPLEMENT_TMPDIR:-}" ]]; then
            printf 'STATUS=cap_hit\n%s\n' "$_budget_out" > "${IMPLEMENT_TMPDIR}/step-budget-cap-hit.env"
        fi
        printf '%s\n' "0" > "${OUTPUT}.done" 2>/dev/null || true
        exit 0
    fi
    unset _budget_out _budget_status
fi

# Defensive: env-derived LARCH_TIMING_TASK_KIND may be empty or flag-shaped
# (e.g. "--prompt") if a caller mis-parses argv. The CLI form was
# already validated above (#1480); apply the same predicate to the env path
# and fall back silently. Whitespace-only and other invalid-but-non-flag
# shapes rely on timing-ledger.sh's regex backstop (do not extend here).
if [[ -z "$TIMING_TASK_KIND" || "$TIMING_TASK_KIND" == --* ]]; then
    TIMING_TASK_KIND="cursor-review"
fi
: "${TIMING_TASK_KIND:=cursor-review}"
TIMING_START_S=$(date +%s)

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

if cursor_launcher_load_model_args; then
    :
else
    rc=$?
    exit "$rc"
fi

WRAPPER_PID=""
DIRTY_TREE_WRITTEN=false
UNTRACKED_BASELINE="${OUTPUT}.untracked-baseline"
DIRTY_TREE_SIDECAR="${OUTPUT}.dirty-tree"

# _write_dirty_tree_sidecar is provided by lib-dirty-tree-sidecar.sh
# (sourced above) and reads/writes the OUTPUT, DIRTY_TREE_WRITTEN,
# UNTRACKED_BASELINE, DIRTY_TREE_SIDECAR, SCRIPT_DIR globals declared
# above. _write_unknown_dirty_tree_sidecar below is cursor-only and
# stays inline.

_write_unknown_dirty_tree_sidecar() {
    # Used by the auth-preflight short-circuit when no agent ran. We have
    # NOT probed the working tree (no `check-mid-run-dirty-tree.sh` call),
    # so emit STATUS=unknown rather than STATUS=clean. Pre-launch tracked
    # or staged edits would otherwise be silently masked when consumers
    # treat a present sidecar with STATUS=clean as "launcher proved the
    # tree clean." STATUS=unknown routes consumers through the same
    # recovery-safe path as a real detector failure.
    local reason="$1"
    local tmp="${DIRTY_TREE_SIDECAR}.tmp.$$"
    {
        printf 'STATUS=unknown\n'
        printf 'MODE=baseline\n'
        if [[ -r "$UNTRACKED_BASELINE" ]]; then
            printf 'UNTRACKED_BASELINE=present\n'
        else
            printf 'UNTRACKED_BASELINE=missing\n'
        fi
        printf 'REASON=%s\n' "$reason"
    } > "$tmp" 2>/dev/null && mv -f "$tmp" "$DIRTY_TREE_SIDECAR" 2>/dev/null || rm -f "$tmp" 2>/dev/null || true
    DIRTY_TREE_WRITTEN=true
}

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
    _write_dirty_tree_sidecar
    if [[ -f "${OUTPUT}.inner.done" ]]; then
        mv -f "${OUTPUT}.inner.done" "${OUTPUT}.done" 2>/dev/null || true
    else
        echo "99" > "${OUTPUT}.done" 2>/dev/null || true
    fi
    return 0
}
# shellcheck disable=SC2154 # _rc is assigned inside the trap string at runtime.
trap '_rc=$?; _emit_timing_record "$_rc"; _publish_done_on_exit; exit "$_rc"' EXIT

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

# Issue #1529: prepend a HARD-CONSTRAINTS read-only preamble to every Cursor
# review prompt (specialist or generic, --prompt or --prompt-file or
# --agent-file). Mirrors the GEMINI_REVIEW_HARDENING_PREAMBLE in
# scripts/launch-gemini-review.sh. The cursor argv below passes `--mode plan`
# so the CLI itself disables the agent's write tools; the preamble is the
# prompt-level reinforcement so the model also reasons about its read-only
# role. The launcher's existing dirty-tree-sidecar machinery
# (snapshot-untracked.sh untracked-files baseline + _write_dirty_tree_sidecar
# EXIT trap) remains the after-the-fact detector.
#
# Retry-replay safety: ${OUTPUT}.prompt is consumed by collect-agent-results.sh
# empty-output retries via `--prompt-file`. To keep that replay idempotent
# (one preamble, not N), the sidecar is written from $ORIGINAL_PROMPT
# (the user/specialist-rendered body BEFORE prepending the preamble) so that
# on retry the launcher reads the body, prepends the preamble exactly once,
# and produces an identical outgoing PROMPT — no preamble stacking.
CURSOR_SANDBOX_ENFORCEMENT_LINE="The launcher passes --mode plan to the cursor CLI. Read-only enforcement relies on these prompt constraints plus the launcher's untracked-files baseline + dirty-tree sidecar; any post-run mutation will be detected after the fact, not blocked at the call."
CURSOR_REVIEW_HARDENING_PREAMBLE=$(cat <<EOF
HARD CONSTRAINTS — your role is read-only review. You MUST NOT modify the working tree by any means:
- Do not redirect, tee, append, or pipe into any file (no \`>\`, \`>>\`, \`tee\`, \`tee -a\`).
- Do not run \`rm\`, \`mv\`, \`cp\` (when target is in the repo), \`mkdir\`, \`touch\`, \`sed -i\`, \`awk -i inplace\`, \`perl -i\`, or any command with an in-place / write effect.
- Do not run \`git add\`, \`git commit\`, \`git checkout <path>\`, \`git reset <path>\`, \`git restore\`, \`git stash\`, \`git rebase\`, \`git merge\`, \`git push\`, or any command that mutates branch state, the index, or refs.
- Do not invoke any tool that writes files (write_file, replace, edit, edit_file, delete_file, or any future-renamed equivalent).
${CURSOR_SANDBOX_ENFORCEMENT_LINE}
EOF
)
ORIGINAL_PROMPT="$PROMPT"
PROMPT="${CURSOR_REVIEW_HARDENING_PREAMBLE}"$'\n\n'"${PROMPT}"

WRAPPED_PROMPT=$({ "$SCRIPT_DIR/cursor-wrap-prompt.sh" "$PROMPT"; _wrap_status=$?; printf X; exit "$_wrap_status"; })
WRAPPED_PROMPT=${WRAPPED_PROMPT%X}
RUN_EXTERNAL="$SCRIPT_DIR/run-external-agent.sh"
SIDECAR="${OUTPUT}.sidecar"
PROMPT_FILE_SIDECAR="${OUTPUT}.prompt"
# Retry-safe: store the user-original (pre-preamble) bytes so
# collect-agent-results.sh `--prompt-file` replay re-prepends the preamble
# exactly once. See ORIGINAL_PROMPT comment above.
printf '%s' "$ORIGINAL_PROMPT" > "$PROMPT_FILE_SIDECAR"
rm -f "$DIRTY_TREE_SIDECAR" "$UNTRACKED_BASELINE" "${DIRTY_TREE_SIDECAR}.tracked-paths" "${DIRTY_TREE_SIDECAR}.new-untracked-paths"
"$SCRIPT_DIR/snapshot-untracked.sh" --output "$UNTRACKED_BASELINE" --nul

# Run Cursor auth preflight. On preflight failure (Darwin + empty
# CURSOR_API_KEY + missing `cursor-user` keychain entry), synthesize the
# sentinel/diag artifacts that `run-external-agent.sh` would have written so
# backgrounded callers see STATUS=FAILED with the actionable reason within
# seconds rather than SENTINEL_TIMEOUT after the full collector timeout.
PREFLIGHT_RC=0
cursor_launcher_setup_auth_argv || PREFLIGHT_RC=$?
if [[ "$PREFLIGHT_RC" != "0" ]]; then
    : > "$OUTPUT" 2>/dev/null || true
    {
        printf 'STATUS=FAILED\n'
        printf 'FAILURE_REASON=cursor-auth-preflight: CURSOR_API_KEY unset/empty and cursor-user keychain entry missing on Darwin; see docs/installation-and-setup.md (Cursor section)\n'
    } > "${OUTPUT}.diag" 2>/dev/null || true
    # Stub .meta so collect-agent-results.sh's parser does not regress on a
    # missing file (TOOL/TIMEOUT keys keep its retry classifier sane; CMD_JSON
    # is intentionally an empty array because no child was launched, so the
    # collector's retry path will see CMD_JSON=[] and skip retry).
    {
        printf 'TOOL=cursor\n'
        printf 'TIMEOUT=%s\n' "$TIMEOUT"
        printf 'CAPTURE_STDOUT=false\n'
        printf 'CAPTURE_STDOUT_ONLY=true\n'
        printf 'OUTPUT_FILE=%s\n' "$OUTPUT"
        printf 'CMD_JSON=[]\n'
    } > "${OUTPUT}.meta" 2>/dev/null || true
    _write_unknown_dirty_tree_sidecar "preflight-short-circuit-no-agent-ran"
    # `.done` is the last artifact written so polling collectors see all
    # other sidecars in place once they observe `.done`. The wrapper's trap
    # writes the EXIT_CODE; we mirror that by writing the preflight RC.
    printf '%s\n' "$PREFLIGHT_RC" > "${OUTPUT}.done" 2>/dev/null || true
    exit "$PREFLIGHT_RC"
fi

# shellcheck disable=SC2086
EXIT_CODE=0
if : > "$SIDECAR" 2>/dev/null; then
    _STDERR_TARGET="$SIDECAR"
else
    SIDECAR=/dev/null
    _STDERR_TARGET=/dev/null
fi

RUN_EXTERNAL_AGENT_INNER_SENTINEL_SUFFIX=.inner.done \
"$RUN_EXTERNAL" \
        --tool cursor \
        --output "$OUTPUT" \
        --timeout "$TIMEOUT" \
        --capture-stdout-only \
        -- \
        cursor agent -p --trust --mode plan \
        --output-format json \
        ${MODEL_ARGS[@]+"${MODEL_ARGS[@]}"} \
        ${CURSOR_AUTH_ARGS[@]+"${CURSOR_AUTH_ARGS[@]}"} \
        --workspace "$PWD" \
        "$WRAPPED_PROMPT" \
        2>>"$_STDERR_TARGET" &
WRAPPER_PID=$!
wait "$WRAPPER_PID" && EXIT_CODE=0 || EXIT_CODE=$?

cursor_launcher_append_outer_meta "${OUTPUT}.meta" "$SCRIPT_DIR/launch-cursor-review.sh" "$PROMPT_FILE_SIDECAR" "$PWD"

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

_write_dirty_tree_sidecar
cursor_launcher_promote_inner_done "$OUTPUT"
exit "$EXIT_CODE"
