#!/usr/bin/env bash
# step-8-ship.sh — /implement Step 8 bgjob launcher and Python ship-driver child.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
IMPLEMENT_TMPDIR="${IMPLEMENT_TMPDIR:?IMPLEMENT_TMPDIR required}"
export IMPLEMENT_TMPDIR
BGJOB_CHILD=false
MERGE_RESULT_ENV=""
while [ $# -gt 0 ]; do
  case "$1" in
    --bgjob-child) BGJOB_CHILD=true; shift ;;
    --merge-result-env) [ $# -ge 2 ] || exit 2; MERGE_RESULT_ENV=$2; shift 2 ;;
    --help) printf '%s\n' 'Usage: step-8-ship.sh'; exit 0 ;;
    *) printf '%s\n' "step-8-ship.sh: unknown argument: $1" >&2; exit 2 ;;
  esac
done

rehydrate_plugin_root() {
  if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/plugin-root.env" ]; then
    # shellcheck source=/dev/null
    . "$IMPLEMENT_TMPDIR/plugin-root.env"
  fi
  if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ]; then
    CLAUDE_PLUGIN_ROOT=$PLUGIN_ROOT
  fi
  export CLAUDE_PLUGIN_ROOT
}

read_state_key() {
  local key=$1 default_value=$2 line state_file
  state_file="$IMPLEMENT_TMPDIR/ship-pr-state.sh"
  if [ -f "$state_file" ]; then
    line=$(grep "^${key}=" "$state_file" 2>/dev/null | tail -n 1 || true)
if [ -n "$line" ]; then
      printf '%s\n' "${line#*=}"
      return 0
    fi
  fi
  printf '%s\n' "$default_value"
}

require_value() {
  local name=$1 value=$2
  if [ -z "$value" ]; then
    printf 'step-8-ship.sh: missing %s (not exported and absent from ship-pr-state.sh)\n' "$name" >&2
    exit 2
  fi
}

safe_truncate() {
  local path=$1 parent tmp
  parent=${path%/*}
  if [ -L "$parent" ]; then
    printf 'step-8-ship.sh: refusing symlinked parent for %s\n' "$path" >&2
    exit 2
  fi
  if [ -L "$path" ]; then
    printf 'step-8-ship.sh: refusing symlinked file %s\n' "$path" >&2
    exit 2
  fi
  tmp=$(mktemp "${path}.tmp.XXXXXX") || exit 2
  : >"$tmp"
  mv -f "$tmp" "$path" 2>/dev/null || { rm -f "$tmp" 2>/dev/null || true; exit 2; }
}

step8_live_registry_exists() {
  python3 <<'PY'
from pathlib import Path
import os
import sys

plugin_root = Path(os.environ["CLAUDE_PLUGIN_ROOT"])
sys.path.insert(0, str(plugin_root / "python"))
try:
    from larch.bgjob import registry  # noqa: E402

    path, entry = registry.read_for(tmpdir=Path(os.environ["IMPLEMENT_TMPDIR"]), step="implement-step8-ship")
    if entry is None:
        raise SystemExit(1)
    if registry.child_liveness(entry).live or registry.daemon_liveness(entry).live:
        print("live")
        raise SystemExit(0)
    if entry.result_env.exists():
        raise SystemExit(1)
    registry.unlink_entry(path)
except SystemExit:
    raise
except Exception:
    print("BGJOB_ERROR=registry-check-failed", file=sys.stderr)
    raise SystemExit(2)
raise SystemExit(1)
PY
}

step8_result_env_rejoinable() {
  python3 <<'PY'
from pathlib import Path
import os
import sys

impl = Path(os.environ["IMPLEMENT_TMPDIR"])
result_env = impl / "bgjob" / "implement-step8-ship.result.env"
route_handoff = impl / ".ship-route-exit-handoff.env"
rc_file = impl / ".step-8-ship-handoff.rc"
if result_env.is_symlink() or (result_env.exists() and not result_env.is_file()):
    print("BGJOB_ERROR=result-env-invalid", file=sys.stderr)
    raise SystemExit(2)
if route_handoff.exists() or not result_env.exists() or not rc_file.is_file():
    raise SystemExit(1)
rows: dict[str, str] = {}
for line in result_env.read_text(encoding="utf-8", errors="replace").splitlines():
    if "=" not in line:
        continue
    key, value = line.split("=", 1)
    rows.setdefault(key, value)
if rows.get("STEP") != "implement-step8-ship":
    raise SystemExit(1)
recorded_rc = rows.get("STEP8_HANDOFF_RC", "")
if recorded_rc and recorded_rc != rc_file.read_text(encoding="utf-8", errors="replace").strip():
    raise SystemExit(1)
print("rejoin")
raise SystemExit(0)
PY
}

write_merge_result_env() {
  local driver_rc=$1 json_present=$2 tmp
  [ -n "$MERGE_RESULT_ENV" ] || return 0
  if [ -L "$MERGE_RESULT_ENV" ]; then
    printf 'step-8-ship.sh: refusing symlinked merge-result-env\n' >&2
    return 2
  fi
  tmp=$(mktemp "${MERGE_RESULT_ENV}.tmp.XXXXXX") || return 2
  {
    printf 'STEP8_SHIP_STATUS=handoff-ready\n'
    printf 'STEP8_HANDOFF_RC=%s\n' "$driver_rc"
    printf 'STEP8_HANDOFF_JSON_PRESENT=%s\n' "$json_present"
    printf 'STEP8_HANDOFF_RC_FILE=%s\n' "$HANDOFF_RC"
    printf 'STEP8_HANDOFF_JSON_FILE=%s\n' "$HANDOFF_JSON"
  } >"$tmp" || { rm -f "$tmp" 2>/dev/null || true; return 2; }
  mv -f "$tmp" "$MERGE_RESULT_ENV" || { rm -f "$tmp" 2>/dev/null || true; return 2; }
}

run_child() {
  local line last_json rc json_present clone_tag_env
  HANDOFF_CAPTURE="$IMPLEMENT_TMPDIR/.step-8-ship-handoff.stdout-capture"
  HANDOFF_RC="$IMPLEMENT_TMPDIR/.step-8-ship-handoff.rc"
  HANDOFF_JSON="$IMPLEMENT_TMPDIR/.step-8-ship-handoff.json"
  rm -f "$HANDOFF_RC" "$HANDOFF_JSON" 2>/dev/null || true
  : >"$HANDOFF_CAPTURE"
  persist_handoff() {
    rc=$1
    set +e
    printf '%s\n' "$rc" >"$HANDOFF_RC" 2>/dev/null || true
    last_json=""
    if [ -f "$HANDOFF_CAPTURE" ]; then
      while IFS= read -r line || [ -n "$line" ]; do
        case "$line" in
          \{*\})
            if printf '%s' "$line" | grep -Fq '"outcome"'; then
              last_json=$line
            fi
            ;;
        esac
      done <"$HANDOFF_CAPTURE"
    fi
    json_present=false
    if [ -n "$last_json" ]; then
      printf '%s\n' "$last_json" >"$HANDOFF_JSON" 2>/dev/null || true
      json_present=true
    else
      rm -f "$HANDOFF_JSON" 2>/dev/null || true
    fi
    write_merge_result_env "$rc" "$json_present" || return 2
    rm -f "$IMPLEMENT_TMPDIR/.bg-wait-active" 2>/dev/null || true
    return 0
  }
  trap 'persist_handoff "$?"' EXIT

  run_and_capture_stdout() {
    local captured_rc
    set +e
    "$@" | tee -a "$HANDOFF_CAPTURE"
    captured_rc=${PIPESTATUS[0]}
    return "$captured_rc"
  }

  BRANCH_NAME_RESOLVED="${BRANCH_NAME:-$(read_state_key BRANCH_NAME "")}"
  ISSUE_NUMBER_RESOLVED="${ISSUE_NUMBER:-$(read_state_key ISSUE_NUMBER "")}"
  RUN_ID_RESOLVED="${RUN_ID:-$(read_state_key RUN_ID "")}"
  REPO_RESOLVED="${REPO:-$(read_state_key REPO "")}"
  MERGE_RESOLVED="${merge:-$(read_state_key MERGE "")}"
  DRAFT_RESOLVED="${draft:-$(read_state_key DRAFT "")}"
  FORKED_TARGET_RESOLVED="${forked_target:-$(read_state_key FORKED_TARGET "")}"
  REPO_UNAVAILABLE_RESOLVED="${REPO_UNAVAILABLE:-$(read_state_key REPO_UNAVAILABLE "")}"
  MANIFEST_PATH_RESOLVED="${MANIFEST_PATH:-$(read_state_key MANIFEST_PATH "")}"
  TOOL_LABEL_RESOLVED="${coder:-$(read_state_key TOOL_LABEL "")}"
  NO_ADMIN_FALLBACK_RESOLVED="${no_admin_fallback:-$(read_state_key NO_ADMIN_FALLBACK "")}"
  NO_LOGS_COMMIT_RESOLVED="${no_logs_commit:-$(read_state_key NO_LOGS_COMMIT "")}"

  require_value BRANCH_NAME "$BRANCH_NAME_RESOLVED"
  require_value RUN_ID "$RUN_ID_RESOLVED"
  require_value REPO "$REPO_RESOLVED"
  [ -n "$MERGE_RESOLVED" ] || MERGE_RESOLVED=false
  [ -n "$DRAFT_RESOLVED" ] || DRAFT_RESOLVED=false
  [ -n "$FORKED_TARGET_RESOLVED" ] || FORKED_TARGET_RESOLVED=false
  [ -n "$REPO_UNAVAILABLE_RESOLVED" ] || REPO_UNAVAILABLE_RESOLVED=false
  [ -n "$TOOL_LABEL_RESOLVED" ] || TOOL_LABEL_RESOLVED=claude
  [ -n "$NO_ADMIN_FALLBACK_RESOLVED" ] || NO_ADMIN_FALLBACK_RESOLVED=false
  [ -n "$NO_LOGS_COMMIT_RESOLVED" ] || NO_LOGS_COMMIT_RESOLVED=false

  rm -f "$IMPLEMENT_TMPDIR/no-progress-turns.count" "$IMPLEMENT_TMPDIR/no-progress-circuit-breaker-armed" 2>/dev/null || true
  rm -f "$IMPLEMENT_TMPDIR/no-progress-stop-block-emitted" "$IMPLEMENT_TMPDIR/no-progress-task-output-clamped" 2>/dev/null || true
  rm -f "$IMPLEMENT_TMPDIR"/bg-poll-guard-task-output-read.*.count 2>/dev/null || true
  rm -f "$IMPLEMENT_TMPDIR/bg-poll-guard-probe-denials.step-8-ship-handoff.rc.count" 2>/dev/null || true

  set +e
  run_and_capture_stdout bash "$IMPLEMENT_TMPDIR/larch-run.sh" skills/implement/scripts/step-8-python-guard.sh
  rc=$?
  set -e
  if [ "$rc" -ne 0 ]; then
    if ! persist_handoff "$rc"; then
      trap - EXIT
      exit 2
    fi
    trap - EXIT
    exit 0
  fi
  clone_tag_env=$(python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" implement clone-tag) || exit $?
  eval "$clone_tag_env"
  : "${EXPECTED_TMPDIR_BASENAME_PREFIX:?}"
  python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" git phantom-probe --step 8-pre-ship >&2
  set +e
  run_and_capture_stdout python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" ship pr \
    --branch "$BRANCH_NAME_RESOLVED" \
    --issue "$ISSUE_NUMBER_RESOLVED" \
    --repo "$REPO_RESOLVED" \
    --run-id "$RUN_ID_RESOLVED" \
    --tmpdir "$IMPLEMENT_TMPDIR" \
    --manifest-path "$MANIFEST_PATH_RESOLVED" \
    --state-file "$IMPLEMENT_TMPDIR/ship-pr-state.sh" \
    --tool-label "$TOOL_LABEL_RESOLVED" \
    --merge "$MERGE_RESOLVED" \
    --draft "$DRAFT_RESOLVED" \
    --forked "$FORKED_TARGET_RESOLVED" \
    --repo-unavailable "$REPO_UNAVAILABLE_RESOLVED" \
    --no-admin-fallback "$NO_ADMIN_FALLBACK_RESOLVED" \
    --no-logs-commit "$NO_LOGS_COMMIT_RESOLVED" \
    --expected-session-id "$(cat "$IMPLEMENT_TMPDIR/session-id" 2>/dev/null || true)" \
    --expected-tmpdir-basename-prefix "$EXPECTED_TMPDIR_BASENAME_PREFIX"
  rc=$?
  set -e
  if ! persist_handoff "$rc"; then
    trap - EXIT
    exit 2
  fi
  trap - EXIT
  exit 0
}

rehydrate_plugin_root
export PYTHONPATH="$CLAUDE_PLUGIN_ROOT/python${PYTHONPATH:+:$PYTHONPATH}"

if [ "$BGJOB_CHILD" = true ]; then
  [ -n "$MERGE_RESULT_ENV" ] || { printf '%s\n' 'step-8-ship.sh: --merge-result-env is required in child mode' >&2; exit 2; }
  run_child
fi

if [ -L "$IMPLEMENT_TMPDIR/bgjob" ]; then
  printf '%s\n' 'step-8-ship.sh: refusing symlinked bgjob directory' >&2
  exit 2
fi
mkdir -p "$IMPLEMENT_TMPDIR/bgjob"
STEP="implement-step8-ship"
RESULT_ENV="$IMPLEMENT_TMPDIR/bgjob/$STEP.result.env"
MERGE_RESULT_ENV="$IMPLEMENT_TMPDIR/bgjob/$STEP.merge.env"
if [ -L "$RESULT_ENV" ] || { [ -e "$RESULT_ENV" ] && [ ! -f "$RESULT_ENV" ]; }; then
  printf '%s\n' 'step-8-ship.sh: refusing invalid bgjob result env' >&2
  exit 2
fi
set +e
registry_state=$(step8_live_registry_exists)
registry_rc=$?
set -e
if [ "$registry_rc" -eq 2 ]; then
  exit 2
fi
if [ "$registry_state" = live ]; then
  python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" bgjob wait --step "$STEP" --tmpdir "$IMPLEMENT_TMPDIR" --max-wait-s 0
  exit $?
fi
set +e
rejoin_state=$(step8_result_env_rejoinable)
rejoin_rc=$?
set -e
if [ "$rejoin_rc" -eq 2 ]; then
  exit 2
fi
if [ "$rejoin_state" = rejoin ]; then
  python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" bgjob wait --step "$STEP" --tmpdir "$IMPLEMENT_TMPDIR" --max-wait-s 0
  exit $?
fi
safe_truncate "$MERGE_RESULT_ENV"
rm -f "$RESULT_ENV" 2>/dev/null || true
rm -f "$IMPLEMENT_TMPDIR/.step-8-ship-handoff.rc" "$IMPLEMENT_TMPDIR/.step-8-ship-handoff.json" 2>/dev/null || true

python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" bgjob start \
  --step "$STEP" \
  --tmpdir "$IMPLEMENT_TMPDIR" \
  --budget-s 21600 \
  --owner-pid "${LARCH_CLAUDE_PID:-$PPID}" \
  --merge-result-env "$MERGE_RESULT_ENV" \
  -- \
  bash "$SCRIPT_DIR/step-8-ship.sh" --bgjob-child --merge-result-env "$MERGE_RESULT_ENV"
