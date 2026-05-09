#!/usr/bin/env bash
# launch-codex-review.sh — Launch a Codex agent review with automatic model args.
#
# Absorbs the command-substitution chain (agent-model-args.sh + optionally
# render-specialist-prompt.sh) so SKILL.md Bash blocks are simple script
# invocations that don't trigger Claude Code permission prompts.
#
# Two modes:
#   Generic:    --prompt "review text..."
#   Specialist: --agent-file agents/reviewer-X.md --mode diff|description
#               [--description-text TEXT] [--scope-files PATH] [--competition-notice]
#
# Usage:
#   launch-codex-review.sh --output FILE --timeout SECS --prompt "PROMPT"
#   launch-codex-review.sh --output FILE --timeout SECS \
#       --agent-file FILE --mode diff|description [--description-text T] [--scope-files F] [--competition-notice]
#
# Output: same stdout as run-external-agent.sh (no additional output).
#
# Exit codes: passed through from run-external-agent.sh.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd -P)}"
# shellcheck source=scripts/lib-codex-launcher-common.sh
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib-codex-launcher-common.sh"
# shellcheck source=scripts/lib-dirty-tree-sidecar.sh
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib-dirty-tree-sidecar.sh"

# shellcheck disable=SC2317,SC2329 # invoked indirectly by the EXIT trap.
_emit_timing_record() {
    local rc=${1:-$?}
    local end_s status
    end_s=$(date +%s)
    (( rc == 0 )) && status=complete || status=signal
    [[ -n "${TIMING_START_S:-}" && -n "${OUTPUT:-}" ]] || return 0
    "$PLUGIN_ROOT/scripts/timing-ledger.sh" record-vendor-task \
        --vendor codex \
        --task-kind "${TIMING_TASK_KIND:-codex-review}" \
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
        --timing-task-kind) [[ -n "${2:-}" && "${2}" != --* ]] || { echo "launch-codex-review.sh: --timing-task-kind requires a non-empty, non-flag-like value" >&2; exit 2; }; TIMING_TASK_KIND="$2"; shift 2 ;;
        --token-budget-cap) case "${2:-}" in ''|*[!0-9]*) echo "launch-codex-review.sh: --token-budget-cap requires a positive integer" >&2; exit 2 ;; esac; (( 10#${2:-0} >= 1 )) || { echo "launch-codex-review.sh: --token-budget-cap requires a positive integer" >&2; exit 2; }; TOKEN_BUDGET_CAP="$2"; shift 2 ;;
        *) echo "launch-codex-review.sh: unknown flag: $1" >&2; exit 2 ;;
    esac
done

if [[ -z "$OUTPUT" ]]; then
    echo "launch-codex-review.sh: --output is required" >&2; exit 2
fi
if [[ -z "$TIMEOUT" ]]; then
    echo "launch-codex-review.sh: --timeout is required" >&2; exit 2
fi

# Validate --output BEFORE installing traps/sidecars so the same byte-exact
# .meta-sidecar contract enforced for the Cursor review launcher applies on
# the Codex path too. Mirrors scripts/launch-cursor-review.sh:60-62.
# shellcheck source=scripts/lib-validate-meta-path.sh
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib-validate-meta-path.sh"
validate_meta_scalar_path --output "$OUTPUT" || exit 1

case "$TIMEOUT" in
    ''|*[!0-9]*|0) echo "launch-codex-review.sh: --timeout must be a positive integer (seconds), got '$TIMEOUT'" >&2; exit 2 ;;
esac
if (( 10#$TIMEOUT < 1 )); then
    echo "launch-codex-review.sh: --timeout must be a positive integer (seconds), got '$TIMEOUT'" >&2
    exit 2
fi

if [[ -n "${IMPLEMENT_TMPDIR:-}" && -s "${IMPLEMENT_TMPDIR}/session-id" ]]; then
    file_id=$(tr -d '\r\n' < "${IMPLEMENT_TMPDIR}/session-id" 2>/dev/null || true)
    if [[ -n "$file_id" ]]; then export LARCH_TOKEN_SESSION_ID="$file_id"; fi
fi
if [[ -n "${IMPLEMENT_TMPDIR:-}" && -s "${IMPLEMENT_TMPDIR}/claude-source.env" ]]; then
    export LARCH_CLAUDE_SOURCE_FILE="${IMPLEMENT_TMPDIR}/claude-source.env"
fi

# Per-step token budget cap: short-circuit before spawning Codex when the
# combined vendor spend since the last ledger mark already exceeds the cap.
if [[ -n "$TOKEN_BUDGET_CAP" ]]; then
    _budget_out=$("$SCRIPT_DIR/check-step-token-budget.sh" --cap "$TOKEN_BUDGET_CAP" --step "${TIMING_TASK_KIND:-codex-review}" 2>/dev/null || true)
    _budget_status=$(printf '%s' "$_budget_out" | awk '{for(i=1;i<=NF;i++){if($i~/^STATUS=/){print substr($i,8);exit}}}')
    if [[ "$_budget_status" == "cap_hit" ]]; then
        printf '⚠ launch-codex-review.sh: step token budget cap of %s tokens exceeded (%s combined vendor tokens); external reviewer fan-out skipped\n' \
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

_src_count=0
[[ -n "$PROMPT" ]] && _src_count=$((_src_count + 1))
[[ -n "$AGENT_FILE" ]] && _src_count=$((_src_count + 1))
[[ -n "$PROMPT_FILE" ]] && _src_count=$((_src_count + 1))
if [[ "$_src_count" -gt 1 ]]; then
    echo "launch-codex-review.sh: --prompt, --agent-file, and --prompt-file are mutually exclusive" >&2
    exit 2
fi
if [[ "$_src_count" -eq 0 ]]; then
    echo "launch-codex-review.sh: one of --prompt, --agent-file, --prompt-file is required" >&2
    exit 2
fi

# Defensive: env-derived LARCH_TIMING_TASK_KIND may be empty or flag-shaped
# (e.g. "--prompt") if a caller mis-parses argv. The CLI form was
# already validated above (#1480); apply the same predicate to the env path
# and fall back silently. Whitespace-only and other invalid-but-non-flag
# shapes rely on timing-ledger.sh's regex backstop (do not extend here).
if [[ -z "$TIMING_TASK_KIND" || "$TIMING_TASK_KIND" == --* ]]; then
    TIMING_TASK_KIND="codex-review"
fi
: "${TIMING_TASK_KIND:=codex-review}"
TIMING_START_S=$(date +%s)

MODEL_ARGS_TMP=""
DIRTY_TREE_WRITTEN=false
UNTRACKED_BASELINE="${OUTPUT}.untracked-baseline"
DIRTY_TREE_SIDECAR="${OUTPUT}.dirty-tree"

# _write_dirty_tree_sidecar is provided by lib-dirty-tree-sidecar.sh
# (sourced above) and reads/writes the OUTPUT, DIRTY_TREE_WRITTEN,
# UNTRACKED_BASELINE, DIRTY_TREE_SIDECAR, SCRIPT_DIR globals declared
# above.

# shellcheck disable=SC2329,SC2317 # body invoked indirectly by the EXIT trap below.
_codex_exit_dispatcher() {
    local rc=${1:-$?}
    _emit_timing_record "$rc"
    [[ -n "$MODEL_ARGS_TMP" ]] && rm -f "$MODEL_ARGS_TMP"
    _write_dirty_tree_sidecar
    codex_launcher_promote_inner_done "$OUTPUT"
    exit "$rc"
}
# shellcheck disable=SC2154 # _rc is assigned inside the trap string at runtime.
trap '_rc=$?; _codex_exit_dispatcher "$_rc"' EXIT

if [[ -n "$PROMPT_FILE" ]]; then
    if ! PROMPT=$({ cat -- "$PROMPT_FILE"; _cat_status=$?; printf X; exit "$_cat_status"; }); then
        echo "launch-codex-review.sh: failed to read --prompt-file $PROMPT_FILE" >&2
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

# Issue #1529: prepend a HARD-CONSTRAINTS read-only preamble to every Codex
# review prompt (specialist or generic, --prompt or --prompt-file or
# --agent-file). Mirrors the GEMINI_REVIEW_HARDENING_PREAMBLE in
# scripts/launch-gemini-review.sh. The codex argv below also passes
# `--sandbox read-only` (replacing the prior `--full-auto`'s workspace-write)
# so the CLI itself rejects model-issued shell writes; the preamble is the
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
CODEX_REVIEW_HARDENING_PREAMBLE=$(cat <<'EOF'
HARD CONSTRAINTS — your role is read-only review. You MUST NOT modify the working tree by any means:
- Do not redirect, tee, append, or pipe into any file (no `>`, `>>`, `tee`, `tee -a`).
- Do not run `rm`, `mv`, `cp` (when target is in the repo), `mkdir`, `touch`, `sed -i`, `awk -i inplace`, `perl -i`, or any command with an in-place / write effect.
- Do not run `git add`, `git commit`, `git checkout <path>`, `git reset <path>`, `git restore`, `git stash`, `git rebase`, `git merge`, `git push`, or any command that mutates branch state, the index, or refs.
- Do not invoke any tool that writes files (write_file, replace, edit, edit_file, delete_file, or any future-renamed equivalent).
The launcher enforces this with a CLI-level read-only sandbox (`--sandbox read-only`); any write the agent attempts will be rejected by the sandbox. The launcher also captures an untracked-files baseline at entry, so any post-run mutation is detected and reported via the dirty-tree sidecar.
EOF
)
ORIGINAL_PROMPT="$PROMPT"
PROMPT="${CODEX_REVIEW_HARDENING_PREAMBLE}"$'\n\n'"${PROMPT}"

OUTPUT_DIR=$(dirname -- "$OUTPUT")
CANON_OUTPUT_DIR=$(cd "$OUTPUT_DIR" && pwd -P)
MODEL_ARGS_TMP=$(mktemp)
PROMPT_FILE_SIDECAR="${OUTPUT}.prompt"
# Retry-safe: store the user-original (pre-preamble) bytes so
# collect-agent-results.sh `--prompt-file` replay re-prepends the preamble
# exactly once. See ORIGINAL_PROMPT comment above.
printf '%s' "$ORIGINAL_PROMPT" > "$PROMPT_FILE_SIDECAR"
rm -f "$DIRTY_TREE_SIDECAR" "$UNTRACKED_BASELINE" "${DIRTY_TREE_SIDECAR}.tracked-paths" "${DIRTY_TREE_SIDECAR}.new-untracked-paths"
"$SCRIPT_DIR/snapshot-untracked.sh" --output "$UNTRACKED_BASELINE" --nul
MODEL_ARGS_ERR=$(mktemp)
if "$SCRIPT_DIR/agent-model-args.sh" --tool codex --with-effort > "$MODEL_ARGS_TMP" 2> "$MODEL_ARGS_ERR"; then
    :
else
    rc=$?
    _emit_timing_record "$rc"
    rm -f "$MODEL_ARGS_TMP"
    _codex_ma_dts_tmp="${OUTPUT}.dirty-tree.tmp.$$"
    printf 'STATUS=unknown\nMODE=baseline\nUNTRACKED_BASELINE=missing\nREASON=model-args-preflight-no-agent-ran\n' \
        > "$_codex_ma_dts_tmp" 2>/dev/null && \
        mv -f "$_codex_ma_dts_tmp" "${OUTPUT}.dirty-tree" 2>/dev/null || \
        rm -f "$_codex_ma_dts_tmp" 2>/dev/null || true
    : > "$OUTPUT" 2>/dev/null || true
    {
        printf 'STATUS=FAILED\n'
        printf 'FAILURE_REASON=agent-model-args.sh failed (exit %s): %s\n' \
            "$rc" "$(head -1 "$MODEL_ARGS_ERR" 2>/dev/null | tr '\n' ' ')"
    } > "${OUTPUT}.diag" 2>/dev/null || true
    rm -f "$MODEL_ARGS_ERR"
    {
        printf 'TOOL=codex\n'
        printf 'TIMEOUT=%s\n' "$TIMEOUT"
        printf 'CAPTURE_STDOUT=false\n'
        printf 'OUTPUT_FILE=%s\n' "$OUTPUT"
        printf 'CMD_JSON=[]\n'
    } > "${OUTPUT}.meta" 2>/dev/null || true
    printf '%s\n' "$rc" > "${OUTPUT}.done" 2>/dev/null || true
    trap - EXIT
    exit "$rc"
fi
rm -f "$MODEL_ARGS_ERR"
MODEL_ARGS=()
while IFS= read -r arg; do
    MODEL_ARGS+=("$arg")
done < "$MODEL_ARGS_TMP"
RUN_EXTERNAL="$SCRIPT_DIR/run-external-agent.sh"
SIDECAR="${OUTPUT}.sidecar"

EXIT_CODE=0
if : > "$SIDECAR" 2>/dev/null; then
    RUN_EXTERNAL_AGENT_INNER_SENTINEL_SUFFIX=.inner.done \
    "$RUN_EXTERNAL" \
        --tool codex \
        --output "$OUTPUT" \
        --timeout "$TIMEOUT" \
        -- \
        codex exec --sandbox read-only -C "$PWD" \
        --add-dir "$CANON_OUTPUT_DIR" \
        ${MODEL_ARGS[@]+"${MODEL_ARGS[@]}"} \
        --output-last-message "$OUTPUT" \
        "$PROMPT" \
        2>>"$SIDECAR" || EXIT_CODE=$?
else
    SIDECAR=/dev/null
    RUN_EXTERNAL_AGENT_INNER_SENTINEL_SUFFIX=.inner.done \
    "$RUN_EXTERNAL" \
        --tool codex \
        --output "$OUTPUT" \
        --timeout "$TIMEOUT" \
        -- \
        codex exec --sandbox read-only -C "$PWD" \
        --add-dir "$CANON_OUTPUT_DIR" \
        ${MODEL_ARGS[@]+"${MODEL_ARGS[@]}"} \
        --output-last-message "$OUTPUT" \
        "$PROMPT" \
        2>/dev/null || EXIT_CODE=$?
fi

codex_launcher_append_outer_meta "${OUTPUT}.meta" "$SCRIPT_DIR/launch-codex-review.sh" "$PROMPT_FILE_SIDECAR" "$PWD"

N=$(awk '/^tokens used$/ { getline n; gsub(",","",n); last=n } END { print last }' "$SIDECAR" 2>/dev/null || true)
if [[ "$N" =~ ^[0-9]+$ ]]; then
    "$PLUGIN_ROOT/scripts/token-ledger.sh" record-vendor codex total="$N" raw="codex_review" >/dev/null 2>&1 || true
fi

exit "$EXIT_CODE"
