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

design_pause_check() {
  if [ -f "$DESIGN_TMPDIR/.pause-requested" ]; then
    exec python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design pause-save --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE_NUMBER" ${REPO:+--repo "$REPO"}
  fi
}

design_brainstorm_requested() {
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
  printf '%s\n' "$_brainstorm_requested"
}

design_append_brainstorm_failure() {
  _bf_tool="$1"
  _bf_output_file="$2"
  _bf_exit_code="$3"
  [ -s "$_bf_output_file" ] || return 0
  python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" run-log append-failure \
    --log "$DESIGN_TMPDIR/execution-issues.md" \
    --site "design Step 1d.5" \
    --tool "$_bf_tool" \
    --exit-code "$_bf_exit_code" \
    --category "External Reviewer Issues" \
    --output-file "$_bf_output_file" \
    --redact >/dev/null 2>&1
}

design_collect_launch_failure_once() {
  _bc_log="$1"
  _bc_tool="$2"
  [ -s "$_bc_log" ] || return 0
  _bc_sentinel="$DESIGN_TMPDIR/.brainstorm-$(basename "$_bc_log").runlog-appended"
  [ -e "$_bc_sentinel" ] && return 0
  _bc_exit_code=$(awk -F= '$1=="LAUNCHER_EXIT" && $2 ~ /^[0-9]+$/ { print $2; found=1; exit } END { if (!found) print "1" }' "$_bc_log" 2>/dev/null)
  if design_append_brainstorm_failure "$_bc_tool" "$_bc_log" "${_bc_exit_code:-1}"; then
    : > "$_bc_sentinel"
  fi
}

design_brainstorm_stderr_sink_for_output() {
  _bc_out="$1"
  _bc_meta="${_bc_out}.meta"
  if [ -r "$_bc_meta" ]; then
    _bc_sink=$(awk -F= '$1=="STDERR_SINK" { print $2; exit }' "$_bc_meta" 2>/dev/null)
    if [ -n "${_bc_sink:-}" ]; then
      printf '%s\n' "$_bc_sink"
      return 0
    fi
  fi
  case "$(basename "$_bc_out")" in
    cursor-brainstorm-output.txt) printf '%s\n' "$DESIGN_TMPDIR/cursor-brainstorm-launch.failure.log" ;;
    codex-brainstorm-output.txt) printf '%s\n' "$DESIGN_TMPDIR/codex-brainstorm-launch.failure.log" ;;
  esac
}

design_brainstorm_launch_tool_for_sink() {
  _bc_sink="$1"
  case "$(basename "$_bc_sink")" in
    *.failure.log) printf '%s\n' "$(basename "$_bc_sink" .failure.log)" ;;
    *) printf '%s\n' "$(basename "$_bc_sink")" ;;
  esac
}

design_collect_launch_failures() {
  for _bc_path in "$@"; do
    _bc_sink=$(design_brainstorm_stderr_sink_for_output "$_bc_path")
    [ -n "${_bc_sink:-}" ] || continue
    _bc_tool=$(design_brainstorm_launch_tool_for_sink "$_bc_sink")
    design_collect_launch_failure_once "$_bc_sink" "$_bc_tool"
  done
}

design_brainstorm_dirty_checkpoint() {
  _bc_recovery_required=false
  _bc_reason_status=""
  for _bc_path in "$@"; do
    _bc_sidecar="${_bc_path}.dirty-tree"
    if [ -r "$_bc_sidecar" ]; then
      _bc_sidecar_status=$(awk -F= '$1=="STATUS" { print $2; exit }' "$_bc_sidecar" 2>/dev/null)
      [ -n "${_bc_sidecar_status:-}" ] || _bc_sidecar_status=unknown
      case "$_bc_sidecar_status" in
        dirty|unknown)
          _bc_recovery_required=true
          _bc_reason_status="$_bc_sidecar_status"
          ;;
      esac
    fi
  done
  _dirty_stdout="$DESIGN_TMPDIR/brainstorm-dirty-tree.checkpoint.out"
  _dirty_stderr="$DESIGN_TMPDIR/brainstorm-dirty-tree.checkpoint.err"
  set +e
  python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" dirty-tree checkpoint >"$_dirty_stdout" 2>"$_dirty_stderr"
  _dirty_rc=$?
  set -e
  _dirty_status=$(awk -F= '$1=="STATUS" { print $2; exit }' "$_dirty_stdout" 2>/dev/null)
  if [ "$_dirty_rc" -ne 0 ] && [ -z "${_dirty_status:-}" ]; then
    _dirty_status=unknown
  fi
  case "${_dirty_status:-}" in
    dirty|unknown)
      _bc_recovery_required=true
      [ -n "${_bc_reason_status:-}" ] || _bc_reason_status="$_dirty_status"
      ;;
  esac
  if [ "$_bc_recovery_required" = true ]; then
    {
      printf 'STAGE=brainstorm-collection\n'
      printf 'RECOVERY_REQUIRED=true\n'
      printf 'DIRTY_TREE_STATUS=%s\n' "${_bc_reason_status:-unknown}"
      if [ -s "$_dirty_stdout" ]; then
        cat "$_dirty_stdout"
      fi
    } >"$DESIGN_TMPDIR/dirty-tree-detected.env"
    printf 'WARN=brainstorm-collection dirty-tree recovery required (status=%s)\n' "${_bc_reason_status:-unknown}"
  else
    {
      printf 'STAGE=brainstorm-collection\n'
      printf 'RECOVERY_REQUIRED=false\n'
    } >"$DESIGN_TMPDIR/dirty-tree-detected.env"
  fi
}

case "${MODE:-}" in
  entry)
    design_source_env_optional
    mkdir -p "$DESIGN_TMPDIR/.completed"
    : > "$DESIGN_TMPDIR/.completed/step-1c"
    : > "$DESIGN_TMPDIR/.completed/step-1d"
    [ -f "$DESIGN_TMPDIR/.pause-requested" ] && exec python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design pause-save --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE_NUMBER" ${REPO:+--repo "$REPO"}
    LARCH_TIMING_SKILL=design python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" timing mark "design Step 1d.5 — brainstorm" || true
    ;;
  collect)
    design_source_env_optional
    design_require_plugin_root
    design_pause_check
    [ "${#PUBLIC_ARGV_WORDS[@]}" -gt 0 ] || { printf '%s\n' "$0: --mode collect requires at least one output path after --" >&2; exit 2; }
    _collect_stdout="$DESIGN_TMPDIR/brainstorm-collect.stdout.log"
    _collect_stderr="$DESIGN_TMPDIR/brainstorm-collect.stderr.log"
    set +e
    python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" agent collect-results --timeout 1260 "${PUBLIC_ARGV_WORDS[@]}" >"$_collect_stdout" 2>"$_collect_stderr"
    _collect_rc=$?
    set -e
    cat "$_collect_stdout"
    if [ "$_collect_rc" -ne 0 ]; then
      {
        cat "$_collect_stdout"
        cat "$_collect_stderr"
      } >"$DESIGN_TMPDIR/brainstorm-collect.failure.log"
      design_append_brainstorm_failure "agent collect-results" "$DESIGN_TMPDIR/brainstorm-collect.failure.log" "$_collect_rc" || true
    fi
    design_collect_launch_failures "${PUBLIC_ARGV_WORDS[@]}"
    design_brainstorm_dirty_checkpoint "${PUBLIC_ARGV_WORDS[@]}"
    ;;
  complete)
    design_source_env_optional
    mkdir -p "$DESIGN_TMPDIR/.completed"
    : > "$DESIGN_TMPDIR/.completed/step-1d.5"
    if [ -f "$DESIGN_TMPDIR/.pause-requested" ]; then
      exec python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design pause-save --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE_NUMBER" ${REPO:+--repo "$REPO"}
    fi
    ;;
  *) printf '%s\n' "$0: --mode required" >&2; exit 2 ;;
esac
