#!/usr/bin/env bash
# test-design-step3-review.sh — Step 3 bgjob reporting contract checks.
unset IMPLEMENT_TMPDIR DESIGN_TMPDIR REVIEW_TMPDIR RESEARCH_TMPDIR SESSION_TMPDIR
unset PYTHONPATH
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
RUST_OWNER="$ROOT/crates/larch-cli/src/plan_review_commands.rs"
export LARCH_BINARY="${LARCH_BINARY:-$ROOT/target/debug/larch}"
WRAPPER="$ROOT/skills/design/scripts/design-step3-review.sh"
SKILL_MD="$ROOT/skills/design/SKILL.md"
fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$*"; }

command grep -Fq 'bgjob write-merge-result-env' "$WRAPPER" || fail 'wrapper must publish through the Rust merge-result writer'
if grep -Fq 'PYTHONPATH=' "$WRAPPER" || grep -Fq 'python3 -' "$WRAPPER"; then
  fail 'wrapper must not retain an inline Python runtime path'
fi

make_fake_step3_plugin() {
  local dir="$1"
  mkdir -p "$dir/python" "$dir/scripts"
  ln -s "$ROOT/python/larch" "$dir/python/larch"
  cat >"$dir/python/cli.py" <<'CLIPY'
#!/usr/bin/env python3
from __future__ import annotations

import os
import shlex
import subprocess
import sys

REAL_ROOT = os.environ["LARCH_TEST_REAL_REPO_ROOT"]
REAL_CLI = os.path.join(REAL_ROOT, "python", "cli.py")

def delegate() -> int:
    return subprocess.call([sys.executable, REAL_CLI, *sys.argv[1:]])

if len(sys.argv) >= 4 and sys.argv[1:4] == ["bgjob", "adapt", "--resolve-session-env"]:
    source = sys.argv[sys.argv.index("--session-env-path") + 1]
    for raw in open(source, encoding="utf-8"):
        line = raw.strip()
        if line.startswith("export "):
            line = line[len("export ") :]
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key in {"DESIGN_TMPDIR", "SESSION_TMPDIR", "SESSION_ID", "REPO", "REPO_ROOT", "ISSUE_NUMBER", "LARCH_RUN_ID"}:
            print(f"export {key}={shlex.quote(value)}")
    raise SystemExit(0)
if len(sys.argv) >= 3 and sys.argv[1] == "bgjob" and sys.argv[2] == "adapt":
    step = sys.argv[sys.argv.index("--step") + 1]
    tmpdir = sys.argv[sys.argv.index("--tmpdir") + 1]
    merge_env = os.path.join(tmpdir, "bgjob", f"{step}.merge.env")
    command = sys.argv[sys.argv.index("--") + 1 :]
    result_dir = os.path.join(tmpdir, "bgjob")
    os.makedirs(result_dir, exist_ok=True)
    result_env = os.path.join(result_dir, f"{step}.result.env")
    if os.path.isfile(result_env) and "--replace-completed-result" not in sys.argv:
        print("BGJOB_STATUS=DONE")
        with open(result_env, encoding="utf-8") as handle:
            print(handle.read(), end="")
        raise SystemExit(0)
    if "--replace-completed-result" in sys.argv:
        try:
            os.unlink(result_env)
        except FileNotFoundError:
            pass
    if "--clear-on-fresh" in sys.argv:
        clear_path = sys.argv[sys.argv.index("--clear-on-fresh") + 1]
        try:
            os.unlink(clear_path)
        except FileNotFoundError:
            pass
    Path = __import__("pathlib").Path
    if os.environ.get("FAKE_STEP3_MERGE_DIRECTORY") == "1":
        Path(merge_env).mkdir()
    else:
        Path(merge_env).write_text("", encoding="utf-8")
    rc = subprocess.call([*command, "--bgjob-child", "--merge-result-env", merge_env], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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
if len(sys.argv) >= 3 and sys.argv[1] == "design" and sys.argv[2] == "pause-save":
    Path = __import__("pathlib").Path
    Path(os.environ["DESIGN_TMPDIR"], ".pause-published").write_text("ok\\n", encoding="utf-8")
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
cat >"$dir/scripts/larch.sh" <<'LARCH'
#!/usr/bin/env bash
case "${1:-} ${2:-}" in
  "session require-plugin-root"|"session validate-design-tmpdir") exit 0 ;;
  "bgjob write-merge-result-env") exec "${LARCH_BINARY:?}" "$@" ;;
  "scope-anchor validate") exec "${LARCH_BINARY:?}" "$@" ;;
  "plan-review run") exec python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" "$@" ;;
  "plan-review normalize-status"|"plan-review prelaunch-failure") exec "${LARCH_BINARY:?}" "$@" ;;
esac
exec python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" "$@"
LARCH
  chmod +x "$dir/scripts/larch.sh"
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

grep -Fq 'SUMMARY_OUTCOME=failed-postplan' "$RUST_OWNER" || fail 'failed-postplan outcome not staged'
grep -Fq 'record-escalation' "$RUST_OWNER" || fail 'record-escalation call missing'
grep -Fq -- 'step3-review' "$RUST_OWNER" || fail 'record-escalation site missing'
grep -Fq 'main-agent-vote-required' "$RUST_OWNER" || fail 'escalation/degradation status set missing'
grep -Fq 'STEP3_NORMALIZE_ALLOW_KEYS' "$RUST_OWNER" || fail 'normalizer must use the shared result key allowlist'
grep -Fq 'design-step3-review.result.env' "$RUST_OWNER" || fail 'normalizer must prefer bgjob Step 3 result env'
grep -Fq 'bgjob/design-step3-review.result.env' "$SKILL_MD" || fail 'SKILL must name bgjob Step 3 result env'
grep -Fq 'BGJOB_RC=0' "$SKILL_MD" || fail 'SKILL must gate Step 3 success on BGJOB_RC=0'
grep -Fq 'bgjob wait --step design-step3-review' "$SKILL_MD" || fail 'SKILL must use chunked bgjob wait for Step 3'
grep -Fq 'scripts/larch.sh" bgjob adapt' "$WRAPPER" || fail 'wrapper must launch through bgjob adapt'
# shellcheck disable=SC2016
grep -Fq -- '--clear-on-fresh' "$WRAPPER" || fail 'wrapper must request fresh-only clearing'
grep -Fq "\"\$DESIGN_TMPDIR/.completed/step-3\"" "$WRAPPER" || fail 'wrapper must name the Step 3 marker for fresh-only clearing'
grep -Fq -- '--bgjob-child|--merge-result-env' "$WRAPPER" || fail 'wrapper must parse the standard adapter child suffix'
if grep -Fq 'step3_review_bgjob_registry_state' "$WRAPPER" || grep -Fq 'bgjob start' "$WRAPPER"; then
  fail 'wrapper must not retain local registry policy or direct bgjob start'
fi
if grep -Fq 'plan-review write-loop-identity' "$WRAPPER" || grep -Fq 'plan-review teardown-loop-identity' "$WRAPPER"; then
  fail 'Step 3 wrapper must not retain legacy loop identity ownership after bgjob migration'
fi
pass 'Step 3 static bgjob contracts are pinned'

D_BGJOB=$(mktemp -d "${TMPDIR:-/tmp}/test-step3-bgjob.XXXXXX")
FAKE_PLUGIN="$D_BGJOB/fake-plugin"
make_fake_step3_plugin "$FAKE_PLUGIN"
printf 'anchor\n' >"$D_BGJOB/plan-review-scope-anchor.txt"
mkdir -p "$D_BGJOB/.completed"
printf 'stale\n' >"$D_BGJOB/.completed/step-3"
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
test ! -s "$D_BGJOB/.completed/step-3" || fail 'fresh Step 3 start must clear stale completion-marker content'
rm -rf "$D_BGJOB"
pass 'Step 3 wrapper starts bgjob and merges fresh result KVs'

D_DONE=$(mktemp -d "${TMPDIR:-/tmp}/test-step3-bgjob-done.XXXXXX")
FAKE_DONE="$D_DONE/fake-plugin"
make_fake_step3_plugin "$FAKE_DONE"
printf 'anchor\n' >"$D_DONE/plan-review-scope-anchor.txt"
mkdir -p "$D_DONE/bgjob"
mkdir -p "$D_DONE/.completed"
: >"$D_DONE/.completed/step-3"
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
test -f "$D_DONE/.completed/step-3" || fail 'completed Step 3 reattachment must preserve its completion marker'
rm -rf "$D_DONE"
pass 'Step 3 wrapper reuses an existing completed result env instead of relaunching'

D_SESSION=$(mktemp -d "${TMPDIR:-/tmp}/test-step3-bgjob-session.XXXXXX")
FAKE_SESSION="$D_SESSION/fake-plugin"
make_fake_step3_plugin "$FAKE_SESSION"
printf 'anchor\n' >"$D_SESSION/plan-review-scope-anchor.txt"
printf 'export DESIGN_TMPDIR=%s\n' "$D_SESSION" >"$D_SESSION/session-env.sh"
start_out=$(env -u DESIGN_TMPDIR -u LARCH_QUIET_LOG_FILE LARCH_QUIET_DISABLE=1 \
  LARCH_BGJOB_REGISTRY_ROOT="$D_SESSION/registry" \
  LARCH_TEST_REAL_REPO_ROOT="$ROOT" \
  CLAUDE_PLUGIN_ROOT="$FAKE_SESSION" ISSUE_NUMBER=9 \
  "$WRAPPER" --claude-pid "$$" --session-env-path "$D_SESSION/session-env.sh" 2>"$D_SESSION/start.stderr")
case "$start_out" in
  BGJOB_STATUS=STARTED\ STEP=design-step3-review\ PGID=*) ;;
  *) fail "session-env launch must start Step 3, got: $start_out stderr=$(cat "$D_SESSION/start.stderr")" ;;
esac
test -f "$D_SESSION/bgjob/design-step3-review.result.env" || fail 'session-env launch must publish a result env'
rm -rf "$D_SESSION"
pass 'Step 3 wrapper resolves session-env launches'

D_RESUME=$(mktemp -d "${TMPDIR:-/tmp}/test-step3-bgjob-resume.XXXXXX")
FAKE_RESUME="$D_RESUME/fake-plugin"
make_fake_step3_plugin "$FAKE_RESUME"
printf 'anchor\n' >"$D_RESUME/plan-review-scope-anchor.txt"
mkdir -p "$D_RESUME/bgjob"
printf '%s\n' 'BGJOB_RC=0' 'BGJOB_ELAPSED_S=0' 'STEP=design-step3-review' 'NEXT_ACTION=old-result' 'STEP3_REVIEW_LOOP_STATUS=complete' >"$D_RESUME/bgjob/design-step3-review.result.env"
printf '1\n' >"$D_RESUME/review-round-count.txt"
start_out=$(env -u LARCH_QUIET_LOG_FILE LARCH_QUIET_DISABLE=1 \
  LARCH_BGJOB_REGISTRY_ROOT="$D_RESUME/registry" \
  LARCH_TEST_REAL_REPO_ROOT="$ROOT" \
  CLAUDE_PLUGIN_ROOT="$FAKE_RESUME" DESIGN_TMPDIR="$D_RESUME" ISSUE_NUMBER=9 \
  "$WRAPPER" --claude-pid "$$" --starting-round 1 --phase awaiting-apply 2>"$D_RESUME/start.stderr")
case "$start_out" in
  BGJOB_STATUS=STARTED\ STEP=design-step3-review\ PGID=*) ;;
  *) fail "resume replacement must start a fresh Step 3 child, got: $start_out stderr=$(cat "$D_RESUME/start.stderr")" ;;
esac
grep -Fxq 'NEXT_ACTION=step3b' "$D_RESUME/bgjob/design-step3-review.result.env" || fail 'resume replacement must replace the completed Step 3 result'
grep -Fxq 'awaiting-apply' "$D_RESUME/.step3-round-1.phase" || fail 'resume replacement must persist its phase before launch'
rm -rf "$D_RESUME"
pass 'Step 3 wrapper replaces completed results on resume'

D_PAUSE=$(mktemp -d "${TMPDIR:-/tmp}/test-step3-bgjob-pause.XXXXXX")
D_PAUSE="$(cd "$D_PAUSE" && pwd -P)"
FAKE_PAUSE="$D_PAUSE/fake-plugin"
make_fake_step3_plugin "$FAKE_PAUSE"
printf 'anchor\n' >"$D_PAUSE/plan-review-scope-anchor.txt"
: >"$D_PAUSE/.pause-requested"
mkdir -p "$D_PAUSE/bgjob"
: >"$D_PAUSE/bgjob/design-step3-review.merge.env"
env -u LARCH_QUIET_LOG_FILE LARCH_QUIET_DISABLE=1 \
  LARCH_TEST_REAL_REPO_ROOT="$ROOT" \
  CLAUDE_PLUGIN_ROOT="$FAKE_PAUSE" DESIGN_TMPDIR="$D_PAUSE" ISSUE_NUMBER=9 \
  "$WRAPPER" --claude-pid "$$" --bgjob-child --merge-result-env "$D_PAUSE/bgjob/design-step3-review.merge.env" >"$D_PAUSE/child.out" 2>"$D_PAUSE/child.stderr" || fail "pause child route failed: $(cat "$D_PAUSE/child.stderr")"
test -f "$D_PAUSE/.pause-published" || fail 'pause child route must publish the pause state'
grep -Fxq 'NEXT_ACTION=pause-save' "$D_PAUSE/bgjob/design-step3-review.merge.env" || fail 'pause child route must publish its terminal merge envelope'
grep -Fxq 'PAUSE_OK=true' "$D_PAUSE/bgjob/design-step3-review.merge.env" || fail 'pause child route must mark its merge envelope successful'
rm -rf "$D_PAUSE"
pass 'Step 3 wrapper publishes pause terminal routing'

D_MERGE=$(mktemp -d "${TMPDIR:-/tmp}/test-step3-bgjob-merge.XXXXXX")
FAKE_MERGE="$D_MERGE/fake-plugin"
make_fake_step3_plugin "$FAKE_MERGE"
printf 'anchor\n' >"$D_MERGE/plan-review-scope-anchor.txt"
mkdir -p "$D_MERGE/registry"
env -u LARCH_QUIET_LOG_FILE LARCH_QUIET_DISABLE=1 FAKE_STEP3_MERGE_DIRECTORY=1 \
  LARCH_BGJOB_REGISTRY_ROOT="$D_MERGE/registry" \
  LARCH_TEST_REAL_REPO_ROOT="$ROOT" \
  CLAUDE_PLUGIN_ROOT="$FAKE_MERGE" DESIGN_TMPDIR="$D_MERGE" ISSUE_NUMBER=9 \
  "$WRAPPER" --claude-pid "$$" >"$D_MERGE/start.out" 2>"$D_MERGE/start.stderr"
grep -Fxq 'BGJOB_RC=1' "$D_MERGE/bgjob/design-step3-review.result.env" || fail 'merge-publication failure must make the Step 3 child fail'
rm -rf "$D_MERGE"
pass 'Step 3 wrapper propagates merge-publication failures'

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
