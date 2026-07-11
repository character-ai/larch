#!/usr/bin/env bash
# Step 8 CI fixer: start or finalize one identity-bound waterfall tier.
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
CLAUDE_PLUGIN_ROOT=${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}
IMPLEMENT_TMPDIR=${IMPLEMENT_TMPDIR:?IMPLEMENT_TMPDIR required}
export CLAUDE_PLUGIN_ROOT IMPLEMENT_TMPDIR

fail() { printf 'RESULT=operator-bail\nREASON=%s\n' "$1"; exit 0; }
read_key() {
  python3 - "$1" "$2" <<'PY'
from pathlib import Path
import re, sys
path=Path(sys.argv[2])
if not path.is_file() or path.is_symlink(): raise SystemExit(0)
seen={}
for raw in path.read_text(encoding="utf-8", errors="strict").splitlines():
    if not raw or "=" not in raw: raise SystemExit(2)
    key,value=raw.split("=",1)
    if key in seen or not re.fullmatch(r"[A-Z][A-Z0-9_]*",key) or any(ord(c)<32 or ord(c)==127 for c in value): raise SystemExit(2)
    seen[key]=value
print(seen.get(sys.argv[1],""))
PY
}
safe_root() {
  python3 - "$1" <<'PY'
from pathlib import Path
import sys
path=Path(sys.argv[1])
if not path.is_absolute() or path.is_symlink() or not path.is_dir(): raise SystemExit(1)
PY
}

MODE_ARG=${1:-}
STEP_ARG=
if [ "$MODE_ARG" = "--finalize" ]; then
  [ "${2:-}" = "--step" ] && [ -n "${3:-}" ] && [ "$#" -eq 3 ] || fail invalid-finalize-arguments
  STEP_ARG=$3
elif [ "$MODE_ARG" = "--start" ] && [ "$#" -eq 1 ]; then
  :
else
  fail invalid-mode
fi
safe_root "$IMPLEMENT_TMPDIR" || fail unsafe-tmpdir
HANDOFF_DIR="$IMPLEMENT_TMPDIR/ci-fixer"
BGJOB_DIR="$IMPLEMENT_TMPDIR/bgjob"
mkdir -p "$HANDOFF_DIR" "$BGJOB_DIR"
SESSION="$IMPLEMENT_TMPDIR/session-env.sh"
STATE="$IMPLEMENT_TMPDIR/ship-pr-state.sh"
ROUTE="$IMPLEMENT_TMPDIR/.ship-route-exit-handoff.env"
REPO_ROOT=${REPO_ROOT:-$(read_key REPO_ROOT "$SESSION")} || fail invalid-session-env
REPO=${REPO:-$(read_key REPO "$STATE")} || fail invalid-ship-state
PR_NUMBER=${PR_NUMBER:-$(read_key PR_NUMBER "$STATE")} || fail invalid-ship-state
[ -n "$REPO_ROOT" ] && [ -d "$REPO_ROOT/.git" ] && [ ! -L "$REPO_ROOT" ] || fail missing-repo-root
[ -n "$REPO" ] || fail missing-repo

if [ "$MODE_ARG" = "--finalize" ]; then
  LAUNCH="$HANDOFF_DIR/launch-$STEP_ARG.env"
  [ -f "$LAUNCH" ] && [ ! -L "$LAUNCH" ] || fail missing-launch-envelope
  MODE=$(read_key MODE "$LAUNCH") || fail invalid-launch-envelope
  RUN_ID=$(read_key RUN_ID "$LAUNCH") || fail invalid-launch-envelope
  STARTING_HEAD=$(read_key STARTING_HEAD "$LAUNCH") || fail invalid-launch-envelope
  INPUT_FINGERPRINT=$(read_key INPUT_FINGERPRINT "$LAUNCH") || fail invalid-launch-envelope
  TIER=$(read_key TIER "$LAUNCH") || fail invalid-launch-envelope
  ATTEMPT=$(read_key ATTEMPT "$LAUNCH") || fail invalid-launch-envelope
  STEP=$(read_key STEP "$LAUNCH") || fail invalid-launch-envelope
  LINEAGE=$(read_key LINEAGE "$LAUNCH") || fail invalid-launch-envelope
  [ "$STEP" = "$STEP_ARG" ] || fail launch-step-mismatch
  MERGE_ENV="$BGJOB_DIR/$STEP.merge.env"
  STATUS="$HANDOFF_DIR/fixer-status.env"
  [ -f "$MERGE_ENV" ] && [ ! -L "$MERGE_ENV" ] && [ -f "$STATUS" ] && [ ! -L "$STATUS" ] || fail missing-result
  OUT=$(python3 - "$MERGE_ENV" "$STATUS" "$MODE" "$STEP" "$RUN_ID" "$ATTEMPT" "$TIER" "$STARTING_HEAD" "$INPUT_FINGERPRINT" <<'PY'
from pathlib import Path
import re, sys
def rows(path):
    out={}
    for raw in Path(path).read_text(encoding="utf-8",errors="strict").splitlines():
        if not raw or "=" not in raw: raise SystemExit(2)
        key,value=raw.split("=",1)
        if key in out or not re.fullmatch(r"[A-Z][A-Z0-9_]*",key): raise SystemExit(2)
        out[key]=value
    return out
left,right=rows(sys.argv[1]),rows(sys.argv[2])
if left != right: raise SystemExit(2)
keys=("MODE","STEP","RUN_ID","ATTEMPT","TIER","STARTING_HEAD","INPUT_FINGERPRINT")
expected=dict(zip(keys,sys.argv[3:10]))
if any(left.get(key)!=value for key,value in expected.items()): raise SystemExit(2)
if left.get("RESULT") not in {"reship","retry-next-tool","operator-bail"}: raise SystemExit(2)
for key in ("RESULT","REASON","MODE","RUN_ID","ATTEMPT","TIER","STARTING_HEAD","INPUT_FINGERPRINT","FINAL_HEAD"):
    print(f"{key}={left.get(key,'')}")
PY
  ) || fail merge-status-disagreement
  printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$ATTEMPT" "$TIER" "$STARTING_HEAD" "$INPUT_FINGERPRINT" "$(printf '%s\n' "$OUT" | sed -n 's/^RESULT=//p')" "$(printf '%s\n' "$OUT" | sed -n 's/^FINAL_HEAD=//p')" >>"$LINEAGE"
  printf '%s\n' "$OUT"
  exit 0
fi

STARTING_HEAD=$(git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null) || fail invalid-head
case "$STARTING_HEAD" in ''|*[!0-9a-f]*) fail invalid-head ;; esac
INPUT_FINGERPRINT=$(git -C "$REPO_ROOT" diff --binary HEAD | shasum -a 256 | awk '{print $1}')
NEEDS_USER_REASON=$(read_key NEEDS_USER_REASON "$ROUTE") || fail invalid-route-handoff
if [ "$NEEDS_USER_REASON" = "architectural-invariants-violation" ]; then
  MODE=invariant-primary
  RUN_ID=$(read_key LARCH_RUN_ID "$SESSION") || fail invalid-session-env
  case "$RUN_ID" in ''|*[!A-Za-z0-9._-]*) fail invalid-invariant-run-id ;; esac
else
  MODE=ci
  SCOPE=$(read_key CI_FAILURE_SCOPE "$ROUTE") || fail invalid-route-handoff
  FAILED_RUN_ID=$(read_key FAILED_RUN_ID "$ROUTE") || fail invalid-route-handoff
  MAIN_FAILED_RUN_ID=$(read_key MAIN_FAILED_RUN_ID "$IMPLEMENT_TMPDIR/main-health.env") || fail invalid-main-health
  case "$SCOPE" in
    pr) RUN_ID=$FAILED_RUN_ID ;;
    main) RUN_ID=$MAIN_FAILED_RUN_ID ;;
    *) fail unknown-ci-failure-scope ;;
  esac
  case "$RUN_ID" in ''|*[!0-9]*) fail invalid-selected-run-id ;; esac
  case "$FAILED_RUN_ID" in ''|*[!0-9]*) [ -z "$FAILED_RUN_ID" ] || fail malformed-pr-run-id ;; esac
  case "$MAIN_FAILED_RUN_ID" in ''|*[!0-9]*) [ -z "$MAIN_FAILED_RUN_ID" ] || fail malformed-main-run-id ;; esac
  if [ -n "$FAILED_RUN_ID" ] && [ -n "$MAIN_FAILED_RUN_ID" ] && [ "$FAILED_RUN_ID" != "$MAIN_FAILED_RUN_ID" ]; then fail conflicting-run-ids; fi
fi
LINEAGE_KEY=$(printf '%s\0%s' "$MODE" "$RUN_ID" | shasum -a 256 | awk '{print substr($1,1,20)}')
LINEAGE="$HANDOFF_DIR/lineage-$LINEAGE_KEY.tsv"
ATTEMPTED=$(awk -F '\t' '{print $2}' "$LINEAGE" 2>/dev/null | paste -sd, - || true)
SELECT=$(python3 - "$CLAUDE_PLUGIN_ROOT" "$ATTEMPTED" <<'PY'
from pathlib import Path
import shutil,sys
sys.path.insert(0,str(Path(sys.argv[1])/"python"))
from larch.core import external_defaults
result=external_defaults.next_untried_tier("implement.ci_recovery_fixer",tuple(filter(None,sys.argv[2].split(','))),codex_present=shutil.which("codex") is not None,cursor_present=shutil.which("cursor") is not None,claude_present=shutil.which("claude") is not None)
print(f"{result.action}\t{result.tier}\t{result.reason}")
PY
) || fail tier-selection-failed
ACTION=$(printf '%s' "$SELECT" | cut -f1); TIER=$(printf '%s' "$SELECT" | cut -f2); REASON=$(printf '%s' "$SELECT" | cut -f3)
[ "$ACTION" = selected ] || fail "${REASON:-ci-fix-exhausted}"
ATTEMPT=$(( $(awk 'END{print NR+0}' "$LINEAGE" 2>/dev/null || printf 0) + 1 ))
SUFFIX=$(printf '%s\0%s\0%s\0%s\0%s\0%s' "$MODE" "$RUN_ID" "$ATTEMPT" "$TIER" "$STARTING_HEAD" "$INPUT_FINGERPRINT" | shasum -a 256 | awk '{print substr($1,1,16)}')
STEP="implement-step8-ci-fixer-${ATTEMPT}-${TIER}-${SUFFIX}"
LAUNCH="$HANDOFF_DIR/launch-$STEP.env"
MERGE_ENV="$BGJOB_DIR/$STEP.merge.env"
printf 'MODE=%s\nRUN_ID=%s\nSTARTING_HEAD=%s\nINPUT_FINGERPRINT=%s\nTIER=%s\nATTEMPT=%s\nSTEP=%s\nLINEAGE=%s\n' "$MODE" "$RUN_ID" "$STARTING_HEAD" "$INPUT_FINGERPRINT" "$TIER" "$ATTEMPT" "$STEP" "$LINEAGE" >"$LAUNCH.tmp"
chmod 600 "$LAUNCH.tmp" && mv "$LAUNCH.tmp" "$LAUNCH"
CHILD=(python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" ci fixer-lane --mode "$MODE" --repo-root "$REPO_ROOT" --implement-tmpdir "$IMPLEMENT_TMPDIR" --handoff-dir "$HANDOFF_DIR" --repo "$REPO" --run-id "$RUN_ID" --tier "$TIER" --attempt "$ATTEMPT" --starting-head "$STARTING_HEAD" --input-fingerprint "$INPUT_FINGERPRINT" --bgjob-result-env "$MERGE_ENV")
if [ "$MODE" = invariant-primary ]; then
  python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" ci materialize-invariant-evidence --implement-tmpdir "$IMPLEMENT_TMPDIR" --route-handoff "$ROUTE" --mode "$MODE" --run-id "$RUN_ID" --starting-head "$STARTING_HEAD" --input-fingerprint "$INPUT_FINGERPRINT" --tier "$TIER" --attempt "$ATTEMPT" --step "$STEP" >/dev/null || fail invariant-evidence-failed
  CHILD+=(--invariant-evidence "$IMPLEMENT_TMPDIR/architectural-invariants.md")
fi
python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" bgjob start --step "$STEP" --tmpdir "$IMPLEMENT_TMPDIR" --budget-s 5400 --owner-pid "${LARCH_CLAUDE_PID:-$PPID}" --merge-result-env "$MERGE_ENV" -- "${CHILD[@]}" || fail bgjob-start-failed
printf 'BGJOB_STATUS=STARTED\nSTEP=%s\nMODE=%s\nRUN_ID=%s\nTIER=%s\nATTEMPT=%s\n' "$STEP" "$MODE" "$RUN_ID" "$TIER" "$ATTEMPT"
