#!/usr/bin/env bash
# test-design-step3-review.sh — Step 3 bgjob reporting contract checks.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
MODULE="$ROOT/python/larch/review/plan_review.py"
NORMALIZE_MODULE="$ROOT/python/larch/review/plan_review_normalize.py"
WRAPPER="$ROOT/skills/design/scripts/design-step3-review.sh"
SKILL_MD="$ROOT/skills/design/SKILL.md"
fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$*"; }

make_fake_step3_plugin() {
  local dir="$1"
  mkdir -p "$dir/python"
  ln -s "$ROOT/python/larch" "$dir/python/larch"
  cat >"$dir/python/cli.py" <<'CLIPY'
#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import sys

REAL_ROOT = os.environ["LARCH_TEST_REAL_REPO_ROOT"]
REAL_CLI = os.path.join(REAL_ROOT, "python", "cli.py")

def delegate() -> int:
    return subprocess.call([sys.executable, REAL_CLI, *sys.argv[1:]])

if len(sys.argv) >= 3 and sys.argv[1] == "bgjob" and sys.argv[2] == "start":
    step = sys.argv[sys.argv.index("--step") + 1]
    tmpdir = sys.argv[sys.argv.index("--tmpdir") + 1]
    merge_env = sys.argv[sys.argv.index("--merge-result-env") + 1]
    sentinel = sys.argv[sys.argv.index("--sentinel") + 1]
    command = sys.argv[sys.argv.index("--") + 1 :]
    result_dir = os.path.join(tmpdir, "bgjob")
    os.makedirs(result_dir, exist_ok=True)
    result_env = os.path.join(result_dir, f"{step}.result.env")
    try:
        os.unlink(result_env)
    except FileNotFoundError:
        pass
    rc = subprocess.call(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if os.environ.get("FAKE_STEP3_EMPTY") == "1" and rc == 0:
        # Emulate the daemon's invalid-result path so the stale-merge regression
        # can assert the non-success routing branch.
        rc = 1
    rows = [("BGJOB_RC", str(rc)), ("BGJOB_ELAPSED_S", "0"), ("STEP", step)]
    if os.path.isfile(merge_env) and not os.path.islink(merge_env):
        with open(merge_env, encoding="utf-8") as handle:
            for raw in handle:
                line = raw.rstrip("\n")
                if not line or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                if key not in {"BGJOB_RC", "BGJOB_ELAPSED_S", "STEP"}:
                    rows.append((key, value))
    with open(result_env, "w", encoding="utf-8") as handle:
        for key, value in rows:
            handle.write(f"{key}={value}\n")
    os.makedirs(os.path.dirname(sentinel), exist_ok=True)
    open(sentinel, "w", encoding="utf-8").close()
    print(f"BGJOB_STATUS=STARTED STEP={step} PGID=12345")
    raise SystemExit(0)
if len(sys.argv) >= 3 and sys.argv[1] == "bgjob" and sys.argv[2] == "wait":
    step = sys.argv[sys.argv.index("--step") + 1]
    tmpdir = sys.argv[sys.argv.index("--tmpdir") + 1]
    result_env = os.path.join(tmpdir, "bgjob", f"{step}.result.env")
    if not os.path.isfile(result_env) or os.path.islink(result_env):
        print("BGJOB_STATUS=DEAD")
        print("BGJOB_DIAG=missing-registry")
        raise SystemExit(0)
    print("BGJOB_STATUS=DONE")
    with open(result_env, encoding="utf-8") as handle:
        print(handle.read(), end="")
    raise SystemExit(0)
if len(sys.argv) >= 2 and sys.argv[1] == "bgjob":
    raise SystemExit(delegate())
if len(sys.argv) >= 3 and sys.argv[1] == "session" and sys.argv[2] == "validate-design-tmpdir":
    raise SystemExit(0)
if len(sys.argv) >= 3 and sys.argv[1] == "scope-anchor" and sys.argv[2] == "validate":
    raise SystemExit(0)
if len(sys.argv) >= 3 and sys.argv[1] == "plan-review" and sys.argv[2] == "normalize-status":
    raise SystemExit(delegate())
if len(sys.argv) >= 3 and sys.argv[1] == "plan-review" and sys.argv[2] == "prelaunch-failure":
    raise SystemExit(delegate())
if len(sys.argv) >= 3 and sys.argv[1] == "plan-review" and sys.argv[2] == "run":
    design_tmpdir = sys.argv[sys.argv.index("--design-tmpdir") + 1]
    if os.environ.get("FAKE_STEP3_EMPTY") == "1":
        raise SystemExit(0)
    with open(os.path.join(design_tmpdir, ".step3-review-result.env"), "w", encoding="utf-8") as handle:
        handle.write("NEXT_ACTION=step3b\n")
        handle.write("STEP3_REVIEW_LOOP_STATUS=complete\n")
        handle.write("LOOP_STATUS=complete\n")
        handle.write("ROUNDS_COMPLETED=1\n")
        handle.write("FINAL_ROUND_NUM=1\n")
        handle.write("ACCEPTED_COUNT=0\n")
    print("STEP3_REVIEW_LOOP_STATUS=complete")
    raise SystemExit(0)
raise SystemExit(delegate())
CLIPY
  chmod +x "$dir/python/cli.py"
}

wait_for_done() {
  local tmpdir="$1" out_file="$2" plugin_root="$3" waited=0
  while [ "$waited" -lt 50 ]; do
    CLAUDE_PLUGIN_ROOT="$plugin_root" LARCH_TEST_REAL_REPO_ROOT="$ROOT" python3 "$plugin_root/python/cli.py" bgjob wait --step design-step3-review --tmpdir "$tmpdir" --max-wait-s 0 >"$out_file"
    if grep -Fq 'BGJOB_STATUS=DONE' "$out_file" || grep -Fq 'BGJOB_STATUS=DEAD' "$out_file"; then
      return 0
    fi
    sleep 0.1
    waited=$((waited + 1))
  done
  return 1
}

grep -Fq 'step3_stage_postplan_failed' "$NORMALIZE_MODULE" || fail 'postplan-failed staging helper missing'
grep -Fq 'failed-postplan' "$NORMALIZE_MODULE" || fail 'failed-postplan outcome not staged'
grep -Fq 'record-escalation' "$NORMALIZE_MODULE" || fail 'record-escalation call missing'
grep -Fq -- 'step3-review' "$MODULE" || fail 'record-escalation site missing'
grep -Fq 'main-agent-vote-required' "$MODULE" || fail 'escalation/degradation status set missing'
grep -Fq 'BGJOB_RC_KEY' "$NORMALIZE_MODULE" || fail 'normalizer must include BGJOB_RC in allowed/read keys'
grep -Fq 'design-step3-review.result.env' "$NORMALIZE_MODULE" || fail 'normalizer must prefer bgjob Step 3 result env'
grep -Fq 'bgjob/design-step3-review.result.env' "$SKILL_MD" || fail 'SKILL must name bgjob Step 3 result env'
grep -Fq 'BGJOB_RC=0' "$SKILL_MD" || fail 'SKILL must gate Step 3 success on BGJOB_RC=0'
grep -Fq 'bgjob wait --step design-step3-review' "$SKILL_MD" || fail 'SKILL must use chunked bgjob wait for Step 3'
grep -Fq 'python/cli.py" bgjob start' "$WRAPPER" || fail 'wrapper must launch through bgjob start'
# shellcheck disable=SC2016
grep -Fq -- '--merge-result-env "$DESIGN_TMPDIR/.step3-review-result.env"' "$WRAPPER" || fail 'wrapper must pass Step 3 merge-result env'
# shellcheck disable=SC2016
grep -Fq -- '--sentinel "$DESIGN_TMPDIR/.completed/step-3-terminal"' "$WRAPPER" || fail 'wrapper must preserve Step 3 terminal sentinel'
grep -Fq 'step3_review_recreate_merge_env' "$WRAPPER" || fail 'wrapper must recreate stale merge env safely before start'
grep -Fq 'step3_review_bgjob_registry_state' "$WRAPPER" || fail 'wrapper must check live bgjob registry before start'
if grep -Fq '.bg-wait-active' "$WRAPPER"; then
  fail 'Step 3 wrapper must not write legacy .bg-wait-active marker after bgjob migration'
fi
if grep -Fq 'plan-review write-loop-identity' "$WRAPPER" || grep -Fq 'plan-review teardown-loop-identity' "$WRAPPER"; then
  fail 'Step 3 wrapper must not retain legacy loop identity ownership after bgjob migration'
fi
pass 'Step 3 static bgjob contracts are pinned'

D_BGJOB=$(mktemp -d "${TMPDIR:-/tmp}/test-step3-bgjob.XXXXXX")
FAKE_PLUGIN="$D_BGJOB/fake-plugin"
make_fake_step3_plugin "$FAKE_PLUGIN"
printf 'anchor\n' >"$D_BGJOB/plan-review-scope-anchor.txt"
mkdir -p "$D_BGJOB/registry"
start_out=$(env -u LARCH_QUIET_LOG_FILE LARCH_QUIET_DISABLE=1 \
  LARCH_BGJOB_REGISTRY_ROOT="$D_BGJOB/registry" \
  LARCH_TEST_REAL_REPO_ROOT="$ROOT" \
  CLAUDE_PLUGIN_ROOT="$FAKE_PLUGIN" DESIGN_TMPDIR="$D_BGJOB" ISSUE_NUMBER=9 \
  "$WRAPPER" --claude-pid "$$" 2>"$D_BGJOB/start.stderr")
case "$start_out" in
  BGJOB_STATUS=STARTED\ STEP=design-step3-review\ PGID=*) ;;
  *) fail "wrapper stdout must be exactly bgjob STARTED line, got: $start_out stderr=$(cat "$D_BGJOB/start.stderr")" ;;
esac
wait_for_done "$D_BGJOB" "$D_BGJOB/wait.out" "$FAKE_PLUGIN" || fail "bgjob did not finish; last wait=$(cat "$D_BGJOB/wait.out")"
grep -Fxq 'BGJOB_STATUS=DONE' "$D_BGJOB/wait.out" || fail "bgjob wait must finish DONE: $(cat "$D_BGJOB/wait.out")"
grep -Fxq 'BGJOB_RC=0' "$D_BGJOB/wait.out" || fail 'bgjob result must include BGJOB_RC=0'
grep -Fxq 'NEXT_ACTION=step3b' "$D_BGJOB/bgjob/design-step3-review.result.env" || fail 'bgjob result env must include fresh Step 3 KVs'
grep -Fxq 'STEP3_REVIEW_LOOP_STATUS=complete' "$D_BGJOB/bgjob/design-step3-review.result.env" || fail 'bgjob result env must include loop status'
rm -rf "$D_BGJOB"
pass 'Step 3 wrapper starts bgjob and merges fresh result KVs'

D_DONE=$(mktemp -d "${TMPDIR:-/tmp}/test-step3-bgjob-done.XXXXXX")
FAKE_DONE="$D_DONE/fake-plugin"
make_fake_step3_plugin "$FAKE_DONE"
printf 'anchor\n' >"$D_DONE/plan-review-scope-anchor.txt"
mkdir -p "$D_DONE/bgjob"
printf '%s\n' 'BGJOB_RC=0' 'BGJOB_ELAPSED_S=0' 'STEP=design-step3-review' 'NEXT_ACTION=step3b' 'STEP3_REVIEW_LOOP_STATUS=complete' 'LOOP_STATUS=complete' 'ROUNDS_COMPLETED=1' >"$D_DONE/bgjob/design-step3-review.result.env"
start_out=$(env -u LARCH_QUIET_LOG_FILE LARCH_QUIET_DISABLE=1 \
  LARCH_BGJOB_REGISTRY_ROOT="$D_DONE/registry" \
  LARCH_TEST_REAL_REPO_ROOT="$ROOT" \
  CLAUDE_PLUGIN_ROOT="$FAKE_DONE" DESIGN_TMPDIR="$D_DONE" ISSUE_NUMBER=9 \
  "$WRAPPER" --claude-pid "$$" 2>"$D_DONE/start.stderr")
case "$start_out" in
  BGJOB_STATUS=DONE*) ;;
  *) fail "wrapper must rejoin an existing completed result env, got: $start_out stderr=$(cat "$D_DONE/start.stderr")" ;;
esac
grep -Fxq 'NEXT_ACTION=step3b' "$D_DONE/bgjob/design-step3-review.result.env" || fail 'existing completion result env must remain authoritative on restart'
rm -rf "$D_DONE"
pass 'Step 3 wrapper reuses an existing completed result env instead of relaunching'

D_STALE=$(mktemp -d "${TMPDIR:-/tmp}/test-step3-bgjob-stale.XXXXXX")
FAKE_STALE="$D_STALE/fake-plugin"
make_fake_step3_plugin "$FAKE_STALE"
printf 'anchor\n' >"$D_STALE/plan-review-scope-anchor.txt"
printf '%s\n' 'NEXT_ACTION=step3b' 'STEP3_REVIEW_LOOP_STATUS=complete' >"$D_STALE/.step3-review-result.env"
mkdir -p "$D_STALE/registry"
env -u LARCH_QUIET_LOG_FILE LARCH_QUIET_DISABLE=1 FAKE_STEP3_EMPTY=1 \
  LARCH_BGJOB_REGISTRY_ROOT="$D_STALE/registry" \
  LARCH_TEST_REAL_REPO_ROOT="$ROOT" \
  CLAUDE_PLUGIN_ROOT="$FAKE_STALE" DESIGN_TMPDIR="$D_STALE" ISSUE_NUMBER=9 \
  "$WRAPPER" --claude-pid "$$" >"$D_STALE/start.out" 2>"$D_STALE/start.stderr"
wait_for_done "$D_STALE" "$D_STALE/wait.out" "$FAKE_STALE" || fail "stale regression bgjob did not finish; last wait=$(cat "$D_STALE/wait.out")"
if grep -Fxq 'STEP3_REVIEW_LOOP_STATUS=complete' "$D_STALE/bgjob/design-step3-review.result.env"; then
  fail 'stale merge input must not satisfy a fresh child that emitted no Step 3 KVs'
fi
grep -Fxq 'BGJOB_RC=1' "$D_STALE/bgjob/design-step3-review.result.env" || fail 'missing fresh KVs must route to a non-success child rc'
rm -rf "$D_STALE"
pass 'Step 3 wrapper truncates stale merge input before fresh bgjob start'

pass 'Step 3 bgjob wrapper checks passed'
