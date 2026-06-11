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

design_require_plugin_root
_cpr_literal='$''{CLAUDE_PLUGIN_ROOT}'
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ]; then
  printf '%s\n' "/design Step 0-pre: CLAUDE_PLUGIN_ROOT is empty after export — skill loader must expand ${_cpr_literal} in the template line before Bash runs; abort" >&2
  exit 1
fi
if [ "${CLAUDE_PLUGIN_ROOT:-}" = "$_cpr_literal" ]; then
  printf '%s\n' "/design Step 0-pre: CLAUDE_PLUGIN_ROOT is the unexpanded template literal ${_cpr_literal} — skill loader must expand it before Bash runs; abort" >&2
  exit 1
fi
if [ ! -x "${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/parse-design-argv.sh" ]; then
  printf '%s\n' "/design Step 0-pre: parse-design-argv.sh not executable at ${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/parse-design-argv.sh; abort" >&2
  exit 1
fi

_argv_env="$(mktemp "${TMPDIR:-/tmp}/larch-argv.XXXXXX")" || {
  printf '%s\n' "**⚠ /design: could not allocate argv parser env capture; aborting before session setup.**" >&2
  exit 1
}
_argv_err_file="$(mktemp "${TMPDIR:-/tmp}/larch-argv-err.XXXXXX")" || {
  rm -f "$_argv_env"
  printf '%s\n' "**⚠ /design: could not allocate argv parser stderr capture; aborting before session setup.**" >&2
  exit 1
}

# Contract pin for CI (scripts/test-design-structure.sh): parse-design-argv.sh
set +e
"${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/parse-design-argv.sh" \
  --output "$_argv_env" \
  2>"$_argv_err_file" \
  "${PUBLIC_ARGV_WORDS[@]}" \
  >/dev/null
_argv_rc=$?
_argv_err="$(cat "$_argv_err_file" 2>/dev/null)"
rm -f "$_argv_err_file"
set -e

case "${_argv_err:-}" in
  *PUBLIC_ARGV_WORDS*)
    rm -f "$_argv_env"
    printf '%s\n' "**⚠ /design: skill loader did not expand public argv words; aborting before session setup.**" >&2
    exit 1
    ;;
esac

VALIDATION_ERROR=""
case "${_argv_rc:-0}" in
  0)
    # shellcheck source=/dev/null
    . "$_argv_env"
    rm -f "$_argv_env"
    if [ -n "${VALIDATION_ERROR:-}" ]; then
      printf '%s\n' "**⚠ /design: parse-design-argv.sh reported VALIDATION_ERROR but exited ${_argv_rc}; aborting before session setup.**" >&2
      exit 1
    fi
    ;;
  3)
    # shellcheck source=/dev/null
    . "$_argv_env"
    rm -f "$_argv_env"
    if [ -n "${VALIDATION_ERROR:-}" ]; then
      printf '%s %s\n' "**⚠ /design: unrecognized or disallowed public flag — aborting before session setup.**" "$VALIDATION_ERROR" >&2
    else
      printf '%s\n' "**⚠ /design: unrecognized or disallowed public flag — aborting before session setup.**" >&2
    fi
    exit 1
    ;;
  *)
    rm -f "$_argv_env"
    printf '%s\n' "**⚠ /design: parse-design-argv.sh failed (exit ${_argv_rc}); aborting before session setup.**" >&2
    exit 1
    ;;
esac
case "$POSITIONAL_KIND" in
  issue | verbal | none) ;;
  *)
    printf '%s\n' "**⚠ /design: parse-design-argv.sh emitted invalid POSITIONAL_KIND; aborting before session setup.**" >&2
    exit 1
    ;;
esac
_step0_parsed_cache_dir="${HOME}/.cache/larch/sessions"
mkdir -p "$_step0_parsed_cache_dir"
_step0_parsed_cache="$_step0_parsed_cache_dir/step0-parsed-${CLAUDE_PID}.env"
cat > "$_step0_parsed_cache" <<EOF_PARSED
hard_requested=${hard_requested}
partition_requested=${partition_requested}
brainstorm_requested=${brainstorm_requested}
approve_requested=${approve_requested}
skip_approve_requested=${skip_approve_requested}
no_dedup_requested=${no_dedup_requested}
run_id=${run_id}
POSITIONAL_KIND=${POSITIONAL_KIND}
POSITIONAL_VALUE=${POSITIONAL_VALUE}
EOF_PARSED
printf 'STEP0_PARSED_ENV_PATH=%s\n' "$_step0_parsed_cache"
printf 'HARD_REQUESTED=%s\nPARTITION_REQUESTED=%s\nBRAINSTORM_REQUESTED=%s\nAPPROVE_REQUESTED=%s\nSKIP_APPROVE_REQUESTED=%s\nNO_DEDUP_REQUESTED=%s\nRUN_ID=%s\nPOSITIONAL_KIND=%s\nPOSITIONAL_VALUE=%s\n' \
  "$hard_requested" \
  "$partition_requested" \
  "$brainstorm_requested" \
  "$approve_requested" \
  "$skip_approve_requested" \
  "$no_dedup_requested" \
  "$run_id" \
  "$POSITIONAL_KIND" \
  "$POSITIONAL_VALUE"
