#!/usr/bin/env bash
# Generated /design wrapper. Keep in sync with skills/design/SKILL.md.
# shellcheck disable=SC1090,SC1091,SC2016,SC2034,SC2086,SC2154,SC2164,SC2312,SC2317,SC2329,SC2206,SC2207
set -euo pipefail

SESSION_ENV_PATH=""
CLAUDE_PID=""
CLAUDE_PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-}"
SITE=""
ARG_ROUND_NUM=""
FORCE_DEDUP=false
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
ROUND_NUM="${ROUND_NUM:-}"
run_id="${run_id:-}"
STEP3_REVIEW_LOOP_STATUS="${STEP3_REVIEW_LOOP_STATUS:-}"
LOOP_STATUS="${LOOP_STATUS:-}"
FINAL_ROUND_NUM="${FINAL_ROUND_NUM:-}"
STEP3_REVIEW_ROUND_NUM="${STEP3_REVIEW_ROUND_NUM:-}"
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
    --site) SITE="$2"; shift 2 ;;
    --round-num) ARG_ROUND_NUM="$2"; shift 2 ;;
    --force-dedup) FORCE_DEDUP=true; shift ;;
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

design_settle_atomic_write() {
  local path="$1" value="$2" base tmp
  base="$(basename "$path")"
  tmp="$(mktemp "$DESIGN_TMPDIR/.${base}.XXXXXX")"
  printf '%s\n' "$value" >"$tmp"
  mv -f "$tmp" "$path"
}

design_settle_resolve_gate_b_round() {
  local candidate
  for candidate in "${ARG_ROUND_NUM:-}" "${FINAL_ROUND_NUM:-}" "${STEP3_REVIEW_ROUND_NUM:-}" "${ROUND_NUM:-}"; do
    case "$candidate" in
      ''|*[!0-9]*) ;;
      *) printf '%s\n' "$candidate"; return 0 ;;
    esac
  done
  return 1
}

design_settle_parse_postplan_rc() {
  local line value seen=false
  POSTPLAN_MACHINE_RC=""
  POSTPLAN_MACHINE_RC_COUNT=0
  while IFS= read -r line || [ -n "$line" ]; do
    case "$line" in
      POSTPLAN_RC=*)
        value="${line#POSTPLAN_RC=}"
        if [ "$seen" = false ]; then
          POSTPLAN_MACHINE_RC="$value"
          seen=true
        fi
        POSTPLAN_MACHINE_RC_COUNT=$((POSTPLAN_MACHINE_RC_COUNT + 1))
        ;;
    esac
  done
}

design_settle_next_action_for_rc() {
  local rc="$1"
  case "$rc:$SITE" in
    0:gate-b) printf '%s\n' 'gate-b-continue' ;;
    0:gate-a|0:discussion-round2) printf '%s\n' 'gate-a-return' ;;
    10:gate-b) printf '%s\n' 'gate-b-validator-fail' ;;
    10:gate-a|10:discussion-round2) printf '%s\n' 'gate-a-validator-fail' ;;
    12:gate-b) printf '%s\n' 'gate-b-hard-size' ;;
    12:gate-a|12:discussion-round2) printf '%s\n' 'gate-a-hard-size' ;;
    13:gate-b) printf '%s\n' 'gate-b-split' ;;
    13:gate-a|13:discussion-round2) printf '%s\n' 'gate-a-split' ;;
    *) return 1 ;;
  esac
}

design_settle_emit_next_action() {
  printf 'SETTLE_NEXT_ACTION=%s\n' "$1"
}

design_source_env_optional
design_require_plugin_root
if [ -z "${DESIGN_TMPDIR:-}" ]; then
  printf '%s\n' "/design Step 3.5 settle: DESIGN_TMPDIR required" >&2
  exit 2
fi
python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" session validate-design-tmpdir "$DESIGN_TMPDIR" || exit 2
DESIGN_TMPDIR="$(cd "$DESIGN_TMPDIR" && pwd -P)"

if [ -f "$DESIGN_TMPDIR/.pause-requested" ]; then
  set +e
  pause_out=$(python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design pause-save --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE_NUMBER" ${REPO:+--repo "$REPO"})
  pause_rc=$?
  set -e
  if [ -n "${pause_out:-}" ]; then
    printf '%s\n' "$pause_out"
  fi
  pause_signal=false
  while IFS= read -r pause_line || [ -n "$pause_line" ]; do
    case "$pause_line" in
      PAUSE_OK=true) pause_signal=true ;;
    esac
  done <<<"$pause_out"
  if [ "$pause_signal" = true ] || [ -f "$DESIGN_TMPDIR/.pause-save-complete" ]; then
    design_settle_emit_next_action pause
    exit 11
  fi
  exit "$pause_rc"
fi

case "${SITE:-}" in
  gate-b) POSTPLAN_SITE=gate-b ;;
  gate-a|discussion-round2) POSTPLAN_SITE=discussion-round2 ;;
  *) printf '%s\n' "design-step35-settle.sh: --site must be gate-b, gate-a, or discussion-round2" >&2; exit 2 ;;
esac

# Retired launcher fence: design-step2b-postplan.sh now maps to the Python CLI.
if [ -n "${DESIGN_STEP35_POSTPLAN_SH:-}" ]; then
  POSTPLAN_CMD=("$DESIGN_STEP35_POSTPLAN_SH")
else
  POSTPLAN_CMD=(python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design step2b-postplan)
fi
GATE_B_ROUND=""

if [ "$SITE" = gate-b ]; then
  if ! GATE_B_ROUND="$(design_settle_resolve_gate_b_round)"; then
    printf '%s\n' 'design-step35-settle.sh: Gate B requires --round-num or FINAL_ROUND_NUM, STEP3_REVIEW_ROUND_NUM, or ROUND_NUM' >&2
    exit 2
  fi
  gate_b_ready_marker="$DESIGN_TMPDIR/.gate-b-postapply-ready-$GATE_B_ROUND"
  gate_b_phase_file="$DESIGN_TMPDIR/.step3-round-$GATE_B_ROUND.phase"
fi

gate_b_skip_dedup=false
if [ "$SITE" = gate-b ] && [ -f "$gate_b_ready_marker" ] && [ "$FORCE_DEDUP" != true ]; then
  if [ ! -f "$gate_b_phase_file" ] || [ "$(cat "$gate_b_phase_file")" != awaiting-postplan-operator ]; then
    gate_b_skip_dedup=true
  fi
fi

if [ "$SITE" != gate-b ] || [ "$gate_b_skip_dedup" != true ]; then
  set +e
  if [ -n "${DESIGN_STEP35_DEDUP_PLAN_SH:-}" ]; then
    dedup_out=$("$DESIGN_STEP35_DEDUP_PLAN_SH" --design-tmpdir "$DESIGN_TMPDIR" --dedup)
  else
    dedup_out=$(python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" plan-review gate-b-dedup --design-tmpdir "$DESIGN_TMPDIR" --dedup)
  fi
  dedup_rc=$?
  set -e
  if [ -n "${dedup_out:-}" ]; then
    printf '%s\n' "$dedup_out"
  fi
  case "$dedup_rc" in
    0) ;;
    1)
      design_settle_emit_next_action dedup-revise
      printf '%s\n' "design-step35-settle.sh: post-rewrite dedup requires plan revision; retry settle after cleanup" >&2
      exit 1
      ;;
    *)
      printf '%s\n' "design-step35-settle.sh: post-rewrite dedup failed with rc $dedup_rc" >&2
      exit "$dedup_rc"
      ;;
  esac
  if [ "$SITE" = gate-b ]; then
    design_settle_atomic_write "$gate_b_ready_marker" ready
  fi
fi

if [ "$SITE" = gate-b ]; then
  design_settle_atomic_write "$gate_b_phase_file" awaiting-post-apply
fi

rm -f "$DESIGN_TMPDIR/.pause-save-complete"
set +e
postplan_out=$("${POSTPLAN_CMD[@]}" \
  --session-env-path "$SESSION_ENV_PATH" \
  --claude-pid "$CLAUDE_PID" \
  --plugin-root "$CLAUDE_PLUGIN_ROOT" \
  --site "$POSTPLAN_SITE" \
  ${PUBLIC_ARGV_WORDS[@]+"${PUBLIC_ARGV_WORDS[@]}"})
postplan_child_rc=$?
set -e
printf '%s\n' "${postplan_out:-}"

pause_signal=false
while IFS= read -r postplan_line || [ -n "$postplan_line" ]; do
  case "$postplan_line" in
    PAUSE_OK=true|POSTPLAN_EMIT_STATUS=paused|POSTPLAN_RC=11|POSTPLAN_STATUS=pause-save) pause_signal=true ;;
  esac
done <<< "$postplan_out"
if [ "$pause_signal" = true ] || [ -f "$DESIGN_TMPDIR/.pause-save-complete" ]; then
  design_settle_emit_next_action pause
  exit 11
fi

POSTPLAN_MACHINE_RC=""
POSTPLAN_MACHINE_RC_COUNT=0
design_settle_parse_postplan_rc <<< "$postplan_out"

if [ "$POSTPLAN_MACHINE_RC_COUNT" -eq 0 ]; then
  printf '%s\n' "design-step35-settle.sh: postplan output missing anchored POSTPLAN_RC row" >&2
  exit 3
fi
if [ "$POSTPLAN_MACHINE_RC_COUNT" -gt 1 ]; then
  printf '%s\n' "design-step35-settle.sh: postplan output contained multiple POSTPLAN_RC rows" >&2
  exit 3
fi

case "$POSTPLAN_MACHINE_RC" in
  0)
    if [ "$postplan_child_rc" -ne 0 ]; then
      printf '%s\n' "design-step35-settle.sh: POSTPLAN_RC=0 with child rc $postplan_child_rc" >&2
      exit 3
    fi
    if [ "$SITE" = gate-b ]; then
      design_settle_atomic_write "$gate_b_phase_file" awaiting-continuation
    fi
    design_settle_emit_next_action "$(design_settle_next_action_for_rc 0)"
    exit 0
    ;;
  10|13)
    if [ "$SITE" = gate-b ]; then
      design_settle_atomic_write "$gate_b_phase_file" awaiting-postplan-operator
    fi
    design_settle_emit_next_action "$(design_settle_next_action_for_rc "$POSTPLAN_MACHINE_RC")"
    exit "$POSTPLAN_MACHINE_RC"
    ;;
  11)
    design_settle_emit_next_action pause
    exit 11
    ;;
  12)
    design_settle_emit_next_action "$(design_settle_next_action_for_rc 12)"
    exit 12
    ;;
  *)
    printf '%s\n' "design-step35-settle.sh: unexpected POSTPLAN_RC=$POSTPLAN_MACHINE_RC" >&2
    exit 3
    ;;
esac
