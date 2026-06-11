#!/usr/bin/env bash
# Generated /design wrapper. Keep in sync with skills/design/SKILL.md.
# shellcheck disable=SC1090,SC1091,SC2016,SC2034,SC2086,SC2154,SC2164,SC2312,SC2317,SC2329,SC2206,SC2207
set -euo pipefail

SESSION_ENV_PATH=""
CLAUDE_PID=""
CLAUDE_PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-}"
MODE=""
SITE=""
SUMMARY_OUTCOME="${SUMMARY_OUTCOME:-}"
SKIP_VALIDATE=""
PUBLIC_ARGV_WORDS=()

# Prompt-side values may be supplied only as environment variables by Claude Code.
# Default them before sourced session env overrides to preserve the old inline-fence no-set-u behavior.
DESIGN_TMPDIR="${DESIGN_TMPDIR:-}"
SESSION_TMPDIR="${SESSION_TMPDIR:-}"
SESSION_ID="${SESSION_ID:-}"
ISSUE_NUMBER="${ISSUE_NUMBER:-}"
ISSUE_TITLE="${ISSUE_TITLE:-}"
HAS_CLARIFY_LABEL="${HAS_CLARIFY_LABEL:-false}"
REPO="${REPO:-}"
CODEX_PRESENT="${CODEX_PRESENT:-false}"
CURSOR_PRESENT="${CURSOR_PRESENT:-false}"
CODEX_AVAILABLE="${CODEX_AVAILABLE:-$CODEX_PRESENT}"
CURSOR_AVAILABLE="${CURSOR_AVAILABLE:-$CURSOR_PRESENT}"
CODEX_BINARY_FOUND="${CODEX_BINARY_FOUND:-false}"
CURSOR_BINARY_FOUND="${CURSOR_BINARY_FOUND:-false}"
IMPLEMENT_TMPDIR="${IMPLEMENT_TMPDIR:-}"
POSITIONAL_KIND="${POSITIONAL_KIND:-}"
POSITIONAL_VALUE="${POSITIONAL_VALUE:-}"
hard_requested="${hard_requested:-false}"
partition_requested="${partition_requested:-false}"
brainstorm_requested="${brainstorm_requested:-false}"
approve_requested="${approve_requested:-false}"
skip_approve_requested="${skip_approve_requested:-false}"
no_dedup_requested="${no_dedup_requested:-false}"
run_id="${run_id:-}"
design_classification="${design_classification:-}"
STEP3_REVIEW_LOOP_STATUS="${STEP3_REVIEW_LOOP_STATUS:-}"
LOOP_STATUS="${LOOP_STATUS:-}"
VALIDATE_STATUS="${VALIDATE_STATUS:-}"
VALIDATE_DEFECT_COUNT="${VALIDATE_DEFECT_COUNT:-}"
VALIDATE_UNSAFE_TOKEN_COUNT="${VALIDATE_UNSAFE_TOKEN_COUNT:-}"
VALIDATE_SKIPPED_COUNT="${VALIDATE_SKIPPED_COUNT:-}"
VALIDATE_LOG_FILE="${VALIDATE_LOG_FILE:-}"
_validator_target_file="${_validator_target_file:-}"
PUBLISH_OK="${PUBLISH_OK:-}"
PLAN_WRITE_OK="${PLAN_WRITE_OK:-}"
STANDALONE_HEAVY_FAILED="${STANDALONE_HEAVY_FAILED:-}"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --session-env-path) SESSION_ENV_PATH="$2"; shift 2 ;;
    --claude-pid) CLAUDE_PID="$2"; shift 2 ;;
    --plugin-root) CLAUDE_PLUGIN_ROOT="$2"; shift 2 ;;
    --mode) MODE="$2"; shift 2 ;;
    --site) SITE="$2"; shift 2 ;;
    --snapshot-original) SNAPSHOT_ORIGINAL=true; shift ;;
    --outcome) SUMMARY_OUTCOME="$2"; shift 2 ;;
    --skip-validate) SKIP_VALIDATE=1; shift ;;
    --step3-review-loop-status) STEP3_REVIEW_LOOP_STATUS="$2"; shift 2 ;;
    --loop-status) LOOP_STATUS="$2"; shift 2 ;;
    --) shift; PUBLIC_ARGV_WORDS=("$@"); break ;;
    *) printf '%s\n' "$0: unknown argument: $1" >&2; exit 2 ;;
  esac
done

design_require_plugin_root() {
  _cpr_literal='$''{CLAUDE_PLUGIN_ROOT}'
  if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ]; then
    printf '%s\n' "/design wrapper: CLAUDE_PLUGIN_ROOT is empty; abort" >&2
    exit 1
  fi
  if [ "${CLAUDE_PLUGIN_ROOT:-}" = "$_cpr_literal" ]; then
    printf '%s\n' "/design wrapper: CLAUDE_PLUGIN_ROOT is the unexpanded template literal ${_cpr_literal}; abort" >&2
    exit 1
  fi
  export CLAUDE_PLUGIN_ROOT
}

design_source_env_optional() {
  if [ -n "${SESSION_ENV_PATH:-}" ] && [ -f "$SESSION_ENV_PATH" ]; then
    # shellcheck source=/dev/null
    . "$SESSION_ENV_PATH"
  fi
}

design_source_env_optional
[ -f "$DESIGN_TMPDIR/.pause-requested" ] && exec "$CLAUDE_PLUGIN_ROOT/scripts/design-pause-save.sh" --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE_NUMBER" ${REPO:+--repo "$REPO"}
_drafter_postplan_fallback_used=false
if [ -f "$DESIGN_TMPDIR/.step2b-postplan-inline-retry-done" ]; then
  _drafter_postplan_fallback_used=true
fi
printf '%s\n' "${_drafter_postplan_fallback_used}" > "$DESIGN_TMPDIR/.step2b-postplan-fallback-used"
# Vendor selection: LARCH_DESIGN_DRAFTER=codex|claude; when unset, prefer codex if CODEX_PRESENT=true.
_step2b_drafter_vendor="${LARCH_DESIGN_DRAFTER:-}"
if [[ -z "$_step2b_drafter_vendor" ]]; then
  if [[ "${CODEX_PRESENT:-false}" == "true" ]]; then
    _step2b_drafter_vendor="codex"
  else
    _step2b_drafter_vendor="claude"
  fi
fi
_step2b_drafter_model=""
if [[ "$_step2b_drafter_vendor" == "claude" ]]; then
  _step2b_drafter_model="${LARCH_DESIGN_PLAN_MODEL:-claude-fable-5}"
fi
_step2b_drafter_skip_reason=""
case "$_step2b_drafter_vendor" in
  codex|claude) ;;
  ''|*[[:space:]]*|*[$'\n\r\t']*) _step2b_drafter_skip_reason="invalid-vendor" ;;
  *) _step2b_drafter_skip_reason="unknown-vendor" ;;
esac
if [[ "$_step2b_drafter_vendor" == "claude" && -z "$_step2b_drafter_skip_reason" ]]; then
  case "$_step2b_drafter_model" in
    ''|*[[:space:]]*|*[$'\n\r\t']*) _step2b_drafter_skip_reason="invalid-model" ;;
  esac
fi
rm -f "$DESIGN_TMPDIR/plan.txt" \
      "$DESIGN_TMPDIR/plan-summary.md" \
      "$DESIGN_TMPDIR/step2b-drafter-status.txt" \
      "$DESIGN_TMPDIR/step2b-drafter-status.txt.done" \
      "$DESIGN_TMPDIR/step2b-drafter-status.txt.dirty-tree" \
      "$DESIGN_TMPDIR/step2b-drafter-status.txt.meta" \
      "$DESIGN_TMPDIR/step2b-drafter-status.txt.stderr" \
      "$DESIGN_TMPDIR/step2b-drafter-status.txt.stderr-tail" \
      "$DESIGN_TMPDIR/step2b-drafter-status.txt.failure-diag" \
      "$DESIGN_TMPDIR/step2b-drafter-status.txt.json" \
      "$DESIGN_TMPDIR/step2b-drafter-baseline.porcelain"
if [[ -z "$_step2b_drafter_skip_reason" ]]; then
  _baseline_arg=()
  if git -C "$PWD" status --porcelain > "$DESIGN_TMPDIR/step2b-drafter-baseline.porcelain" 2>/dev/null; then
    _baseline_arg=(--baseline-porcelain "$DESIGN_TMPDIR/step2b-drafter-baseline.porcelain")
  else
    rm -f "$DESIGN_TMPDIR/step2b-drafter-baseline.porcelain"
  fi
  _resolved_design_classification="$(python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" session read-classification "$DESIGN_TMPDIR/run-params.json" || printf '%s\n' HARD)"
  # shellcheck source=scripts/lib-untrusted-block.sh
  source "$CLAUDE_PLUGIN_ROOT/scripts/lib-untrusted-block.sh"
  {
    printf '%s\n\n' 'You are an expert engineer researching this repository and producing an implementation plan for /design Step 2b.'
    printf 'Trusted resolved design_classification: %s\n\n' "$_resolved_design_classification"
    printf '%s\n' 'You may use only side-effect-free repository discovery. Do not write repository files, design tmpdir files, or any other files. Return only the sentinel-delimited response requested below.'
    printf '\n%s\n' 'Drafting requirements to follow:'
    printf '%s\n' '- Apply SIMPLE tier by minimizing scope; apply HARD tier by surfacing edge cases, failure modes, invariants, and downstream consumers.'
    printf '%s\n' '- Read approach-synthesis.txt: if it is exactly NO_SKETCHES_CLASSIFIED_SIMPLE, draft from direct codebase/doc inspection without fabricating sketch agreement; if exactly NO_SKETCHES_DEGRADED_HARD, preserve HARD thoroughness without fabricating sketch agreement.'
    printf '%s\n' '- Read discussion-round1.md when present for scope boundaries and hard constraints.'
    printf '%s\n' '- Read design-outline.md only when non-empty and .outline-approved exists; treat Goals, Non-goals, and Surfaces as binding scope.'
    printf '%s\n' '- Read brainstorm.md when present as additive ideation only when it does not conflict with binding dialectic resolutions or explicit user refusals.'
    printf '%s\n' '- Read dialectic-resolutions.md when present and branch on Disposition: voted — follow Resolution and address antithesis; fallback-to-synthesis / bucket-skipped / over-cap — synthesis stands, note Why reason, do not fabricate antithesis-engagement prose.'
    printf '%s\n' '- Use a Files to modify/create section with per-file headings exactly one path each: ### NEW:, ### UPDATED:, or ### REWRITTEN: (at least one ASCII space after ### before the keyword).'
    printf '%s\n' '- Include Approach, Edge cases, Failure modes when non-trivial, Testing strategy, optional diff_added/diff_deleted/mechanical_churn trailers, and final diff_lines: <N>.'
    printf '%s\n' '- The final plan body must end with a whole-line diff_lines: <N> trailer.'
    printf '\n%s\n' 'Readability style (trusted):'
    cat "$CLAUDE_PLUGIN_ROOT/skills/design/references/readability-style.md"
    printf '\n%s\n' 'Required output format:'
    printf '%s\n' 'LARCH_SUMMARY_BEGIN'
    printf '%s\n' 'A concise summary for large-plan preview. Omit this whole summary block only when no useful summary is needed.'
    printf '%s\n' 'LARCH_SUMMARY_END'
    printf '%s\n' 'LARCH_PLAN_BEGIN'
    printf '%s\n' 'Full implementation plan body ending with diff_lines: <N>.'
    printf '%s\n' 'LARCH_PLAN_END'
    printf '\n%s\n' 'Optional advisory status may be included between LARCH_STATUS_BEGIN and LARCH_STATUS_END, but the plan and summary sentinels above are the only parsed contract.'
    if [ -s "$DESIGN_TMPDIR/feature-description.txt" ]; then
      printf '\n%s\n' 'Untrusted feature description:'
      larch_emit_untrusted_file_block feature_description "$DESIGN_TMPDIR/feature-description.txt"
    fi
    if [ -s "$DESIGN_TMPDIR/approach-synthesis.txt" ]; then
      printf '\n%s\n' 'Untrusted approach synthesis:'
      larch_emit_untrusted_file_block approach_synthesis "$DESIGN_TMPDIR/approach-synthesis.txt"
    fi
    if [ -s "$DESIGN_TMPDIR/discussion-round1.md" ]; then
      printf '\n%s\n' 'Untrusted discussion round 1:'
      larch_emit_untrusted_file_block discussion_round1 "$DESIGN_TMPDIR/discussion-round1.md"
    fi
    if [ -s "$DESIGN_TMPDIR/design-outline.md" ] && [ -f "$DESIGN_TMPDIR/.outline-approved" ]; then
      printf '\n%s\n' 'Untrusted approved design outline:'
      larch_emit_untrusted_file_block design_outline "$DESIGN_TMPDIR/design-outline.md"
    fi
    if [ -s "$DESIGN_TMPDIR/brainstorm.md" ]; then
      printf '\n%s\n' 'Untrusted brainstorm:'
      larch_emit_untrusted_file_block brainstorm "$DESIGN_TMPDIR/brainstorm.md"
    fi
    if [ -s "$DESIGN_TMPDIR/dialectic-resolutions.md" ]; then
      printf '\n%s\n' 'Untrusted dialectic resolutions:'
      larch_emit_untrusted_file_block dialectic_resolutions "$DESIGN_TMPDIR/dialectic-resolutions.md"
    fi
  } > "$DESIGN_TMPDIR/step2b-drafter-prompt.txt"
  _repo_root="$(git -C "$PWD" rev-parse --show-toplevel)"
  set +e
  if [[ "$_step2b_drafter_vendor" == "codex" ]]; then
    "$CLAUDE_PLUGIN_ROOT/scripts/launch-codex-drafter.sh" \
      --prompt-file "$DESIGN_TMPDIR/step2b-drafter-prompt.txt" \
      --output-file "$DESIGN_TMPDIR/step2b-drafter-status.txt" \
      "${_baseline_arg[@]}" \
      --timeout 1800 \
      --timing-task-kind codex-plan-draft \
      --design-tmpdir "$DESIGN_TMPDIR" \
      --repo-root "$_repo_root"
  else
    "$CLAUDE_PLUGIN_ROOT/scripts/launch-claude-drafter.sh" \
      --model "$_step2b_drafter_model" \
      --prompt-file "$DESIGN_TMPDIR/step2b-drafter-prompt.txt" \
      --output-file "$DESIGN_TMPDIR/step2b-drafter-status.txt" \
      "${_baseline_arg[@]}" \
      --timeout 1800 \
      --timing-task-kind claude-plan-draft \
      --design-tmpdir "$DESIGN_TMPDIR" \
      --repo-root "$_repo_root"
  fi
  _drafter_rc=$?
  set -e
else
  # Use exit 2 to match launcher argv/config validation failures.
  _drafter_rc=2
fi
_plan_lines=0
if [ -s "$DESIGN_TMPDIR/plan.txt" ]; then
  _plan_lines=$(wc -l < "$DESIGN_TMPDIR/plan.txt" | tr -d ' ')
fi
_drafter_structural_ok=false
if [[ "$_drafter_rc" -eq 0 ]] \
  && [[ -s "$DESIGN_TMPDIR/plan.txt" ]] \
  && tail -n 1 "$DESIGN_TMPDIR/plan.txt" | command grep -Eq '^diff_lines: [0-9][0-9]*$' \
  && command grep -Fq 'PLAN_WRITTEN=true' "$DESIGN_TMPDIR/step2b-drafter-status.txt"; then
  _drafter_structural_ok=true
fi
_drafter_dirty_block=false
_drafter_dirty_reason="unknown"
if [[ -f "$DESIGN_TMPDIR/step2b-drafter-status.txt.dirty-tree" ]]; then
  _dirty_status=""
  _dirty_mode=""
  while IFS= read -r _dirty_line || [[ -n "$_dirty_line" ]]; do
    case "$_dirty_line" in
      STATUS=*) _dirty_status="${_dirty_line#STATUS=}" ;;
      MODE=*) _dirty_mode="${_dirty_line#MODE=}" ;;
    esac
  done < "$DESIGN_TMPDIR/step2b-drafter-status.txt.dirty-tree"
  if [[ "$_dirty_status" == "dirty" && "$_dirty_mode" == "baseline-delta" ]]; then
    _drafter_dirty_block=true
    _drafter_dirty_reason="confirmed-baseline-delta"
  fi
elif [[ -s "$DESIGN_TMPDIR/step2b-drafter-baseline.porcelain" ]]; then
  if git -C "$PWD" status --porcelain > "$DESIGN_TMPDIR/step2b-drafter-current.porcelain" 2>/dev/null \
    && ! diff -u "$DESIGN_TMPDIR/step2b-drafter-baseline.porcelain" "$DESIGN_TMPDIR/step2b-drafter-current.porcelain" >/dev/null 2>&1; then
    _drafter_dirty_block=true
    _drafter_dirty_reason="missing-sidecar-positive-baseline-delta"
  fi
fi
if [[ "$_drafter_structural_ok" == "true" && "$_drafter_dirty_block" != "true" ]]; then
  printf '%s\n' drafter > "$DESIGN_TMPDIR/.step2b-plan-source"
  _diff_lines="$(tail -n 1 "$DESIGN_TMPDIR/plan.txt" | sed 's/^diff_lines: //')"
  env LARCH_QUIET_DISABLE=1 "$CLAUDE_PLUGIN_ROOT/skills/design/scripts/emit-design-plan-preview.sh" \
    --design-tmpdir "$DESIGN_TMPDIR" \
    --variant step2b
  printf '✅ 2b: drafter subprocess succeeded (vendor=%s plan_lines=%s diff_lines=%s)\n' "$_step2b_drafter_vendor" "$_plan_lines" "$_diff_lines"
elif [[ "$_drafter_dirty_block" == "true" ]]; then
  printf 'STATUS=%s\nSTAGE=step-2b-drafter\nRECOVERY_REQUIRED=true\nREASON=%s\n' "dirty" "$_drafter_dirty_reason" > "$DESIGN_TMPDIR/dirty-tree-detected.env"
  printf '%s\n' "**⚠ 2b: drafter subprocess may have introduced working-tree mutations; dirty-tree recovery is required before fallback.**"
else
  rm -f "$DESIGN_TMPDIR/plan-summary.md"
  printf '%s\n' inline > "$DESIGN_TMPDIR/.step2b-plan-source"
  printf '%s\n' "**⚠ 2b: drafter subprocess failed — falling back to inline drafting (vendor=$_step2b_drafter_vendor)**"
  if [[ -n "${DESIGN_TMPDIR:-}" ]]; then
    printf '%s\n' "Step 2b drafter fallback: ${_step2b_drafter_skip_reason:-rc-${_drafter_rc}}" > "$DESIGN_TMPDIR/step2b-drafter-fallback.log"
    "$CLAUDE_PLUGIN_ROOT/scripts/append-tool-failure.sh" \
      --log "$DESIGN_TMPDIR/execution-issues.md" \
      --site "design Step 2b drafter" \
      --tool "launch-${_step2b_drafter_vendor}-drafter.sh" \
      --exit-code "$_drafter_rc" \
      --category Warnings \
      --output-file "$DESIGN_TMPDIR/step2b-drafter-fallback.log" \
      --redact >/dev/null 2>&1 || true
  fi
fi
