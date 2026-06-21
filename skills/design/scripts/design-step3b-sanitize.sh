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

write_bounded_failure() {
  _reason="$1"
  _exit_code="$2"
  _raw_capture="${3:-}"
  python3 - "$CLAUDE_PLUGIN_ROOT" "$DESIGN_TMPDIR" "$_reason" "$_exit_code" "$_raw_capture" <<'PY'
from pathlib import Path
import sys
sys.path.insert(0, str(Path(sys.argv[1]) / "python"))
import design_diagram_log
raw = sys.argv[5] or None
path = design_diagram_log.write_bounded_diagram_failure_log(
    sys.argv[2],
    site="design Step 5b.5",
    reason=sys.argv[3],
    exit_code=sys.argv[4],
    raw_capture_path=raw,
)
print(path)
PY
}

append_sanitizer_failure() {
  _reason="$1"
  _exit_code="$2"
  _raw_capture="${3:-}"
  _bounded_file="$(write_bounded_failure "$_reason" "$_exit_code" "$_raw_capture")"
  python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" run-log append-failure \
    --log "$DESIGN_TMPDIR/execution-issues.md" \
    --site "design Step 5b.5" \
    --tool "python/cli.py mermaid sanitize architecture" \
    --exit-code "$_exit_code" \
    --category Warnings \
    --output-file "$_bounded_file" \
    --redact >/dev/null 2>&1 || true
}

design_source_env_optional
design_require_plugin_root
design_pause_check
mkdir -p "$DESIGN_TMPDIR/.completed"

_candidate="$DESIGN_TMPDIR/architecture-diagram.candidate.md"
_failure_log="$DESIGN_TMPDIR/architecture-diagram-sanitizer.failure.log"

if [ ! -r "$_candidate" ]; then
  rm -f "$DESIGN_TMPDIR/architecture-diagram.md" "$_candidate"
  : > "$DESIGN_TMPDIR/architecture-diagram.skipped"
  printf '%s\n' 'architecture diagram candidate is missing or unreadable' >"$_failure_log"
  printf '%s\n' '**⚠ 5b.5: architecture diagram — candidate missing; proceeding without diagram.**'
  append_sanitizer_failure "candidate-missing" 2 "$_failure_log"
  : > "$DESIGN_TMPDIR/.completed/step-5b.5"
  exit 0
fi

_sanitizer_output_file=$(mktemp "${TMPDIR:-/tmp}/design-step3b-sanitize.XXXXXX")
set +e
python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" mermaid sanitize \
  --input "$_candidate" \
  --from-md \
  --warnings-step "5b.5" \
  >"$_sanitizer_output_file" 2>&1
_sanitizer_rc=$?
set -e
_sanitizer_output=$(cat "$_sanitizer_output_file")

if [ "$_sanitizer_rc" -eq 0 ] && ! printf '%s\n' "$_sanitizer_output" | grep -qE '^STATUS=rejected$'; then
  rm -f "$_failure_log" "$DESIGN_TMPDIR/architecture-diagram.skipped" "$DESIGN_TMPDIR/architecture-diagram-generation.failure.log"
  mv "$_candidate" "$DESIGN_TMPDIR/architecture-diagram.md"
  : > "$DESIGN_TMPDIR/.completed/step-5b.5"
  rm -f "$_sanitizer_output_file"
  exit 0
fi

_reason_token=$(printf '%s\n' "$_sanitizer_output" | sed -n 's/.*REASON_TOKEN=\([^[:space:]);,]*\).*/\1/p' | head -1)
if [ -z "${_reason_token:-}" ]; then
  _reason_token="unknown"
fi
rm -f "$DESIGN_TMPDIR/architecture-diagram.md" "$_candidate"
: > "$DESIGN_TMPDIR/architecture-diagram.skipped"
printf 'reason=sanitizer-rejected:%s\nexit-code=%s\nsite=design Step 5b.5\n' "$_reason_token" "$_sanitizer_rc" >"$_failure_log"
printf '%s\n' "**⚠ 5b.5: architecture diagram — rejected by mermaid sanitizer (REASON_TOKEN=${_reason_token}); proceeding without diagram.**"
append_sanitizer_failure "sanitizer-rejected:${_reason_token}" "$_sanitizer_rc" "$_sanitizer_output_file"
: > "$DESIGN_TMPDIR/.completed/step-5b.5"
rm -f "$_sanitizer_output_file"
