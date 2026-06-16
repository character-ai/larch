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
CODEX_BINARY_FOUND="${CODEX_BINARY_FOUND:-}"
CURSOR_BINARY_FOUND="${CURSOR_BINARY_FOUND:-}"
IMPLEMENT_TMPDIR="${IMPLEMENT_TMPDIR:-}"
POSITIONAL_KIND="${POSITIONAL_KIND:-}"
POSITIONAL_VALUE="${POSITIONAL_VALUE:-}"
partition_requested="${partition_requested:-false}"
brainstorm_requested="${brainstorm_requested:-false}"
approve_requested="${approve_requested:-false}"
skip_approve_requested="${skip_approve_requested:-false}"
no_dedup_requested="${no_dedup_requested:-false}"
run_id="${run_id:-}"
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
_brainstorm_requested=false
if [ -f "$DESIGN_TMPDIR/run-params.json" ]; then
  if command -v jq >/dev/null 2>&1; then
    case "$(jq -r '.brainstorm_requested // false' "$DESIGN_TMPDIR/run-params.json" 2>/dev/null)" in
      true) _brainstorm_requested=true ;;
    esac
  elif ( command grep -Eq '"brainstorm_requested"[[:space:]]*:[[:space:]]*true([,}[:space:]]|$)' "$DESIGN_TMPDIR/run-params.json" 2>/dev/null ); then
    _brainstorm_requested=true
  fi
fi
# Repair or write sentinel artifacts; do not overwrite non-sentinel data
_exact_line_file() {
  _elf_file="$1"
  _elf_expected="$2"
  awk -v expected="$_elf_expected" '
    NR == 1 { ok = ($0 == expected) }
    NR > 1 { ok = 0 }
    END { exit (NR == 1 && ok) ? 0 : 1 }
  ' "$_elf_file" 2>/dev/null
}

_artifacts_ok=true
_NO_SKETCHES="NO_SKETCHES"
_NO_CONTESTED="NO_CONTESTED_DECISIONS"
_LEGACY_NO_SKETCHES=false
if _exact_line_file "$DESIGN_TMPDIR/approach-synthesis.txt" "$_NO_SKETCHES"; then
  :
elif [ "$(cat "$DESIGN_TMPDIR/approach-synthesis.txt" 2>/dev/null || true)" = "NO_SKETCHES_CLASSIFIED_SI""MPLE" ] \
  || [ "$(cat "$DESIGN_TMPDIR/approach-synthesis.txt" 2>/dev/null || true)" = "NO_SKETCHES_DEGRADED_HA""RD" ]; then
  _LEGACY_NO_SKETCHES=true
  _artifacts_ok=false
else
  _artifacts_ok=false
fi
if _exact_line_file "$DESIGN_TMPDIR/contested-decisions.md" "$_NO_CONTESTED"; then :; else _artifacts_ok=false; fi
if [ -f "$DESIGN_TMPDIR/dialectic-resolutions.md" ]; then :; else _artifacts_ok=false; fi
_artifact_conflict=false
if [ -s "$DESIGN_TMPDIR/approach-synthesis.txt" ] \
  && ! _exact_line_file "$DESIGN_TMPDIR/approach-synthesis.txt" "$_NO_SKETCHES" \
  && [ "$_LEGACY_NO_SKETCHES" != true ]; then _artifact_conflict=true; fi
if [ -s "$DESIGN_TMPDIR/contested-decisions.md" ] && ! _exact_line_file "$DESIGN_TMPDIR/contested-decisions.md" "$_NO_CONTESTED"; then _artifact_conflict=true; fi
if [ -s "$DESIGN_TMPDIR/dialectic-resolutions.md" ]; then _artifact_conflict=true; fi
if [ "$_artifact_conflict" = true ]; then
  printf '%s\n' '**⚠ Step 2a: sentinel repair refused: non-sentinel artifacts already exist. Inspect before continuing.**' >&2
  exit 1
fi
mkdir -p "$DESIGN_TMPDIR/.completed"
: > "$DESIGN_TMPDIR/.completed/step-1c"
: > "$DESIGN_TMPDIR/.completed/step-1d"
if [ "$_brainstorm_requested" != true ]; then
  : > "$DESIGN_TMPDIR/.completed/step-1d.5"
fi
: > "$DESIGN_TMPDIR/.completed/step-1d.7"
: > "$DESIGN_TMPDIR/.completed/step-1e"
if [ "$_artifacts_ok" != true ]; then
  printf '%s\n' "$_NO_SKETCHES" > "$DESIGN_TMPDIR/approach-synthesis.txt"
  printf '%s\n' "$_NO_CONTESTED" > "$DESIGN_TMPDIR/contested-decisions.md"
  : > "$DESIGN_TMPDIR/dialectic-resolutions.md"
fi
: > "$DESIGN_TMPDIR/.completed/step-2a"
[ -f "$DESIGN_TMPDIR/.pause-requested" ] && exec python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design pause-save --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE_NUMBER" ${REPO:+--repo "$REPO"}
LARCH_TIMING_SKILL=design python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" timing mark "design Step 2a — sentinel prep" || true
