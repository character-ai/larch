#!/usr/bin/env bash
# Dormant Step 8 CI fixer: one bgjob-backed waterfall tier per invocation.
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
CLAUDE_PLUGIN_ROOT=${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}
IMPLEMENT_TMPDIR=${IMPLEMENT_TMPDIR:?IMPLEMENT_TMPDIR required}
export CLAUDE_PLUGIN_ROOT IMPLEMENT_TMPDIR

read_key() {
  local key=$1 file=$2 line
  [ -f "$file" ] || return 0
  line=$(command grep "^${key}=" "$file" 2>/dev/null | tail -n 1 || true)
  [ -n "$line" ] && printf '%s\n' "${line#*=}"
}

fail() { printf 'RESULT=operator-bail\nREASON=%s\n' "$1"; exit 0; }

case "$IMPLEMENT_TMPDIR" in /*) ;; *) fail unsafe-tmpdir ;; esac
[ ! -L "$IMPLEMENT_TMPDIR" ] && [ -d "$IMPLEMENT_TMPDIR" ] || fail unsafe-tmpdir
HANDOFF_DIR="$IMPLEMENT_TMPDIR/ci-fixer"
BGJOB_DIR="$IMPLEMENT_TMPDIR/bgjob"
[ ! -L "$HANDOFF_DIR" ] || fail unsafe-handoff
[ ! -L "$BGJOB_DIR" ] || fail unsafe-bgjob-dir
mkdir -p "$HANDOFF_DIR" "$BGJOB_DIR"

STATE="$IMPLEMENT_TMPDIR/ship-pr-state.sh"
SESSION="$IMPLEMENT_TMPDIR/session-env.sh"
REPO_ROOT=${REPO_ROOT:-$(read_key REPO_ROOT "$SESSION")}
REPO=${REPO:-$(read_key REPO "$STATE")}
PR_NUMBER=${PR_NUMBER:-$(read_key PR_NUMBER "$STATE")}
RUN_ID=${CI_RUN_ID:-$(read_key FAILED_RUN_ID "$STATE")}
[ -n "$REPO_ROOT" ] && [ -d "$REPO_ROOT/.git" ] && [ ! -L "$REPO_ROOT" ] || fail missing-repo-root
[ -n "$REPO" ] || fail missing-repo

STARTING_HEAD=$(git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null || true)
case "$STARTING_HEAD" in ''|*[!0-9a-f]*) fail invalid-head ;; esac
INPUT_FINGERPRINT=$(git -C "$REPO_ROOT" diff --binary HEAD | shasum -a 256 | awk '{print $1}')
ROUNDS="$HANDOFF_DIR/fixer-rounds.tsv"
STATUS="$HANDOFF_DIR/fixer-status.env"
[ ! -L "$ROUNDS" ] && [ ! -L "$STATUS" ] || fail unsafe-sidecar
ATTEMPTED=""
if [ -f "$ROUNDS" ]; then
  ATTEMPTED=$(python3 - "$ROUNDS" "$RUN_ID" "$STARTING_HEAD" "$INPUT_FINGERPRINT" <<'PY'
from pathlib import Path
import sys
path, run_id, head, fingerprint = Path(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4]
seen=[]
for raw in path.read_text(encoding="utf-8").splitlines():
    parts=raw.split("\t")
    if len(parts) != 7 or not parts[0].isdigit() or parts[1] not in {"codex","cursor","claude"}:
        raise SystemExit(2)
    if parts[2] != run_id or parts[3] != head or parts[4] != fingerprint:
        raise SystemExit(2)
    seen.append(parts[1])
print(",".join(seen))
PY
  ) || fail invalid-rounds
fi

SELECT=$(python3 - "$CLAUDE_PLUGIN_ROOT" "$ATTEMPTED" <<'PY'
from pathlib import Path
import shutil, sys
sys.path.insert(0, str(Path(sys.argv[1]) / "python"))
from larch.core import external_defaults
attempted=tuple(filter(None, sys.argv[2].split(",")))
result=external_defaults.next_untried_tier(
    "implement.ci_recovery_fixer", attempted,
    codex_present=shutil.which("codex") is not None,
    cursor_present=shutil.which("cursor") is not None,
    claude_present=shutil.which("claude") is not None,
)
print(f"{result.action}\t{result.tier}\t{result.reason}")
PY
) || fail tier-selection-failed
ACTION=$(printf '%s' "$SELECT" | cut -f1)
TIER=$(printf '%s' "$SELECT" | cut -f2)
REASON=$(printf '%s' "$SELECT" | cut -f3)
[ "$ACTION" = selected ] || fail "${REASON:-waterfall-exhausted}"
ATTEMPT=$(( $(printf '%s' "$ATTEMPTED" | awk -F, '{ if ($0 == "") print 0; else print NF }') + 1 ))
IDENTITY_RUN=${RUN_ID:-pr-$PR_NUMBER}
SUFFIX=$(printf '%s\0%s\0%s\0%s\0%s' "$IDENTITY_RUN" "$ATTEMPT" "$TIER" "$STARTING_HEAD" "$INPUT_FINGERPRINT" | shasum -a 256 | awk '{print substr($1,1,16)}')
STEP="implement-step8-ci-fixer-${ATTEMPT}-${TIER}-${SUFFIX}"
MERGE_ENV="$BGJOB_DIR/$STEP.merge.env"
RESULT_ENV="$BGJOB_DIR/$STEP.result.env"
[ ! -L "$MERGE_ENV" ] && [ ! -L "$RESULT_ENV" ] || fail unsafe-result

set +e
WAIT_OUT=$(python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" bgjob wait --step "$STEP" --tmpdir "$IMPLEMENT_TMPDIR" --max-wait-s 0 2>/dev/null)
WAIT_RC=$?
set -e
if [ "$WAIT_RC" -eq 0 ] && printf '%s\n' "$WAIT_OUT" | command grep -q '^BGJOB_STATUS='; then
  printf '%s\n' "$WAIT_OUT"
  case "$WAIT_OUT" in *BGJOB_STATUS=WAIT*) exit 0 ;; esac
else
  rm -f "$MERGE_ENV" "$RESULT_ENV"
  CHILD=(python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" ci fixer-lane
    --repo-root "$REPO_ROOT" --implement-tmpdir "$IMPLEMENT_TMPDIR"
    --handoff-dir "$HANDOFF_DIR" --repo "$REPO" --tier "$TIER"
    --attempt "$ATTEMPT" --starting-head "$STARTING_HEAD"
    --input-fingerprint "$INPUT_FINGERPRINT" --bgjob-result-env "$MERGE_ENV")
  if [ -n "$RUN_ID" ]; then CHILD+=(--run-id "$RUN_ID"); else CHILD+=(--pr "$PR_NUMBER"); fi
  if [ -f "$IMPLEMENT_TMPDIR/architectural-invariants.md" ]; then
    CHILD+=(--invariant-evidence "$IMPLEMENT_TMPDIR/architectural-invariants.md")
  fi
  python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" bgjob start \
    --step "$STEP" --tmpdir "$IMPLEMENT_TMPDIR" --budget-s 5400 \
    --owner-pid "${LARCH_CLAUDE_PID:-$PPID}" --merge-result-env "$MERGE_ENV" -- "${CHILD[@]}"
  exit $?
fi

case "$WAIT_OUT" in *BGJOB_STATUS=DONE*BGJOB_RC=0*) ;; *) fail bgjob-not-successful ;; esac
[ -f "$MERGE_ENV" ] && [ ! -L "$MERGE_ENV" ] && [ -f "$STATUS" ] || fail missing-result
python3 - "$MERGE_ENV" "$STATUS" "$STEP" "$IDENTITY_RUN" "$ATTEMPT" "$TIER" "$STARTING_HEAD" "$INPUT_FINGERPRINT" <<'PY'
from pathlib import Path
import sys
merge, status = Path(sys.argv[1]), Path(sys.argv[2])
def rows(path):
    out={}
    for raw in path.read_text(encoding="utf-8").splitlines():
        if "=" not in raw: continue
        key,value=raw.split("=",1)
        if key in out: raise SystemExit(2)
        out[key]=value
    return out
left,right=rows(merge),rows(status)
keys=("STEP","RESULT","RUN_ID","ATTEMPT","TIER","STARTING_HEAD","INPUT_FINGERPRINT","FINAL_HEAD")
if any(left.get(k) != right.get(k) for k in keys): raise SystemExit(2)
expected=dict(zip(("STEP","RUN_ID","ATTEMPT","TIER","STARTING_HEAD","INPUT_FINGERPRINT"),sys.argv[3:9]))
if any(left.get(k) != v for k,v in expected.items()): raise SystemExit(2)
if left.get("RESULT") not in {"reship","retry-next-tool","operator-bail"}: raise SystemExit(2)
for key in ("RESULT","REASON","RUN_ID","ATTEMPT","TIER","STARTING_HEAD","INPUT_FINGERPRINT","FINAL_HEAD"):
    print(f"{key}={left.get(key,'')}")
PY
