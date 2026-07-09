#!/usr/bin/env bash
# test-step-5-review.sh — Step 5 bgjob wrapper contract.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
WRAPPER="$ROOT/skills/implement/scripts/step-5-review.sh"
fail() { printf 'FAIL: %s
' "$*" >&2; exit 1; }
pass() { printf 'PASS: %s
' "$*"; }

make_fake_plugin() {
  local dir="$1"
  mkdir -p "$dir/python/larch/bgjob"
  : >"$dir/python/larch/__init__.py"
  : >"$dir/python/larch/bgjob/__init__.py"
  cat >"$dir/python/larch/bgjob/registry.py" <<'PY'
from pathlib import Path
import os

class Entry:
    pass

class Verdict:
    def __init__(self, live):
        self.live = live

def read_for(*, tmpdir, step):
    mode = os.environ.get("STEP5_REGISTRY_MODE", "")
    path = Path(tmpdir) / "registry.env"
    if mode == "error":
        raise OSError("registry-check-failed")
    if mode in {"live", "dead"}:
        return path, Entry()
    return path, None

def child_liveness(entry):
    return Verdict(os.environ.get("STEP5_REGISTRY_MODE") == "live")

def daemon_liveness(entry):
    return Verdict(os.environ.get("STEP5_REGISTRY_MODE") == "live")

def unlink_entry(path):
    Path(os.environ["IMPLEMENT_TMPDIR"]).joinpath("registry-unlinked").touch()
PY
  cat >"$dir/python/cli.py" <<'PY'
#!/usr/bin/env python3
import os
import sys
from pathlib import Path

impl = Path(os.environ.get("IMPLEMENT_TMPDIR", "/tmp"))
call_log = impl / "calls.log"
call_log.parent.mkdir(parents=True, exist_ok=True)
with call_log.open("a", encoding="utf-8") as handle:
    handle.write(" ".join(sys.argv[1:]) + "\n")

def arg(name, default=""):
    try:
        return sys.argv[sys.argv.index(name) + 1]
    except (ValueError, IndexError):
        return default

if sys.argv[1:3] == ["timing", "telemetry-mark"]:
    sys.exit(0)
if sys.argv[1:3] == ["session", "read-key"]:
    print(arg("--default"))
    sys.exit(0)
if sys.argv[1:3] == ["bgjob", "start"]:
    merge = Path(arg("--merge-result-env"))
    if merge.read_text(encoding="utf-8"):
        print("BGJOB_ERROR=stale-merge-env")
        sys.exit(2)
    (impl / "bgjob-start-argv.txt").write_text("\n".join(sys.argv[1:]) + "\n", encoding="utf-8")
    print(f"BGJOB_STATUS=STARTED STEP={arg('--step')} PGID=12345")
    sys.exit(0)
if sys.argv[1:3] == ["bgjob", "wait"]:
    mode = os.environ.get("STEP5_WAIT_MODE", "wait")
    if mode == "dead":
        print("BGJOB_STATUS=DEAD")
        print("BGJOB_DIAG=mock-dead")
        sys.exit(0)
    if mode == "done-ok":
        rows = [
            "BGJOB_STATUS=DONE",
            "BGJOB_RC=0",
            "STEP5_REVIEW_STATUS=complete",
            "STALL_TRACKING=false",
            "STALL_REASON=",
            "ROUNDS_COMPLETED=1",
            "FINAL_ROUND_NUM=1",
            "FINAL_REVIEW_AND_FIX_STATUS=complete",
            "CODER_STATUS=",
            "FILES_CHANGED_HINT=",
            "EFFECTIVE_ROUND_CAP=2",
        ]
        print("\n".join(rows))
        sys.exit(0)
    if mode == "done-timeout":
        rows = [
            "BGJOB_STATUS=DONE",
            "BGJOB_RC=timeout",
            "STEP5_REVIEW_STATUS=stall",
            "STALL_TRACKING=true",
            "STALL_REASON=timeout",
            "ROUNDS_COMPLETED=1",
            "FINAL_ROUND_NUM=1",
            "FINAL_REVIEW_AND_FIX_STATUS=stall",
            "CODER_STATUS=",
            "FILES_CHANGED_HINT=",
            "EFFECTIVE_ROUND_CAP=2",
        ]
        print("\n".join(rows))
        sys.exit(0)
    if mode == "done-orphaned":
        rows = [
            "BGJOB_STATUS=DONE",
            "BGJOB_RC=orphaned",
            "STEP5_REVIEW_STATUS=stall",
            "STALL_TRACKING=true",
            "STALL_REASON=orphan-timeout",
            "ROUNDS_COMPLETED=1",
            "FINAL_ROUND_NUM=1",
            "FINAL_REVIEW_AND_FIX_STATUS=stall",
            "CODER_STATUS=",
            "FILES_CHANGED_HINT=",
            "EFFECTIVE_ROUND_CAP=2",
        ]
        print("\n".join(rows))
        sys.exit(0)
    if mode == "done-stall":
        rows = [
            "BGJOB_STATUS=DONE",
            "BGJOB_RC=2",
            "STEP5_REVIEW_STATUS=stall",
            "STALL_TRACKING=true",
            "STALL_REASON=intentional-stall",
            "ROUNDS_COMPLETED=1",
            "FINAL_ROUND_NUM=1",
            "FINAL_REVIEW_AND_FIX_STATUS=stall",
            "CODER_STATUS=",
            "FILES_CHANGED_HINT=",
            "EFFECTIVE_ROUND_CAP=2",
        ]
        print("\n".join(rows))
        sys.exit(0)
    print("BGJOB_STATUS=WAIT")
    print("ELAPSED_S=0")
    sys.exit(0)
if sys.argv[1:3] == ["review-and-fix", "step5"]:
    (impl / "review-argv.txt").write_text("\n".join(sys.argv[1:]) + "\n", encoding="utf-8")
    rows = [
        "STEP5_REVIEW_STATUS=complete",
        "STALL_TRACKING=false",
        "STALL_REASON=",
        "ROUNDS_COMPLETED=1",
        "FINAL_ROUND_NUM=1",
        "FINAL_REVIEW_AND_FIX_STATUS=complete",
        "CODER_STATUS=",
        "FILES_CHANGED_HINT=",
        "EFFECTIVE_ROUND_CAP=2",
    ]
    (impl / ".step5-review-result.env").write_text("\n".join(rows) + "\n", encoding="utf-8")
    print("\n".join(rows))
    sys.exit(0)
sys.exit(0)
PY
  chmod +x "$dir/python/cli.py"
}

make_impl() {
  local dir="$1" plugin="$2"
  mkdir -p "$dir"
  printf 'RUN_ID=run-1\nLARCH_CLAUDE_PLUGIN_ROOT=%s\n' "$plugin" >"$dir/session-env.sh"
  printf 'plan\n' >"$dir/plan.txt"
  printf 'feature\n' >"$dir/feature-description.txt"
}

seed_result_env() {
  local dir="$1" path="$1/bgjob/implement-step5-review.result.env"
  mkdir -p "$dir/bgjob"
  cat >"$path" <<'EOF'
BGJOB_RC=0
STEP5_REVIEW_STATUS=complete
STALL_TRACKING=false
STALL_REASON=
ROUNDS_COMPLETED=1
FINAL_ROUND_NUM=1
FINAL_REVIEW_AND_FIX_STATUS=complete
CODER_STATUS=
FILES_CHANGED_HINT=
EFFECTIVE_ROUND_CAP=2
EOF
}

seed_stall_result_env() {
  local dir="$1" path="$1/bgjob/implement-step5-review.result.env"
  mkdir -p "$dir/bgjob"
  cat >"$path" <<'EOF'
BGJOB_RC=2
STEP5_REVIEW_STATUS=stall
STALL_TRACKING=true
STALL_REASON=intentional-stall
ROUNDS_COMPLETED=1
FINAL_ROUND_NUM=1
FINAL_REVIEW_AND_FIX_STATUS=stall
CODER_STATUS=
FILES_CHANGED_HINT=
EFFECTIVE_ROUND_CAP=2
EOF
}

D=$(mktemp -d "${TMPDIR:-/tmp}/test-step5-review.XXXXXX")
trap 'rm -rf "$D"' EXIT
FAKE="$D/plugin"
make_fake_plugin "$FAKE"

IMPL="$D/normal"
make_impl "$IMPL" "$FAKE"
printf 'STALE=true\n' >"$IMPL/.step5-review-result.env"
CLAUDE_PLUGIN_ROOT="$FAKE" IMPLEMENT_TMPDIR="$IMPL" "$WRAPPER" >"$IMPL/stdout.log" 2>"$IMPL/stderr.log" || fail "normal wrapper failed: $(cat "$IMPL/stderr.log")"
[ "$(cat "$IMPL/stdout.log")" = 'BGJOB_STATUS=STARTED STEP=implement-step5-review PGID=12345' ] || fail "fresh launch stdout must be exact bgjob start line: $(cat "$IMPL/stdout.log")"
[ ! -s "$IMPL/.step5-review-result.env" ] || fail 'fresh launch must truncate stale Step 5 merge env'
[ ! -f "$IMPL/.step5-wrapper-detached" ] || fail 'fresh launch must not create detach sidecar'
[ ! -f "$IMPL/.step5-reattach-active" ] || fail 'fresh launch must not create reattach sidecar'
grep -Fq -- '--step' "$IMPL/bgjob-start-argv.txt" || fail 'wrapper must pass --step to bgjob'
grep -Fq -- 'implement-step5-review' "$IMPL/bgjob-start-argv.txt" || fail 'wrapper must start implement-step5-review bgjob'
grep -Fq -- '--merge-result-env' "$IMPL/bgjob-start-argv.txt" || fail 'wrapper must pass merge-result-env to bgjob'
grep -Fq -- '--sentinel' "$IMPL/bgjob-start-argv.txt" || fail 'wrapper must preserve step-5-terminal sentinel through bgjob'
pass 'Step 5 wrapper fresh launch uses bgjob and clears stale merge env without detach sidecars'

IMPL="$D/canonical-result"
make_impl "$IMPL" "$FAKE"
seed_result_env "$IMPL"
STEP5_REGISTRY_MODE=missing STEP5_WAIT_MODE=done-ok CLAUDE_PLUGIN_ROOT="$FAKE" IMPLEMENT_TMPDIR="$IMPL" "$WRAPPER" >"$IMPL/stdout.log" 2>"$IMPL/stderr.log" || fail "canonical result rejoin wrapper failed: $(cat "$IMPL/stderr.log")"
grep -Fq 'BGJOB_STATUS=DONE' "$IMPL/stdout.log" || fail 'canonical result env must rejoin through bgjob wait'
[ ! -f "$IMPL/bgjob-start-argv.txt" ] || fail 'canonical result env must not relaunch bgjob'
pass 'Step 5 wrapper reuses canonical completed result envs without relaunching'

IMPL="$D/canonical-stall-result"
make_impl "$IMPL" "$FAKE"
seed_stall_result_env "$IMPL"
STEP5_REGISTRY_MODE=missing STEP5_WAIT_MODE=done-stall CLAUDE_PLUGIN_ROOT="$FAKE" IMPLEMENT_TMPDIR="$IMPL" "$WRAPPER" >"$IMPL/stdout.log" 2>"$IMPL/stderr.log" || fail "canonical stall result recovery wrapper failed: $(cat "$IMPL/stderr.log")"
[ "$(cat "$IMPL/stdout.log")" = 'BGJOB_STATUS=STARTED STEP=implement-step5-review PGID=12345' ] || fail 'cached canonical stall result env must start a fresh bgjob'
[ -f "$IMPL/bgjob-start-argv.txt" ] || fail 'cached canonical stall result env must relaunch bgjob'
[ ! -f "$IMPL/bgjob/implement-step5-review.result.env" ] || fail 'cached canonical stall result env must be cleared before fresh start'
pass 'Step 5 wrapper clears cached canonical stall result envs before relaunching'

IMPL="$D/stale-result"
make_impl "$IMPL" "$FAKE"
mkdir -p "$IMPL/bgjob"
cat >"$IMPL/bgjob/implement-step5-review.result.env" <<'EOF'
BGJOB_RC=1
STEP5_REVIEW_STATUS=stall
EOF
STEP5_REGISTRY_MODE=missing STEP5_WAIT_MODE=done-ok CLAUDE_PLUGIN_ROOT="$FAKE" IMPLEMENT_TMPDIR="$IMPL" "$WRAPPER" >"$IMPL/stdout.log" 2>"$IMPL/stderr.log" || fail "stale canonical result wrapper failed: $(cat "$IMPL/stderr.log")"
[ "$(cat "$IMPL/stdout.log")" = 'BGJOB_STATUS=STARTED STEP=implement-step5-review PGID=12345' ] || fail 'stale canonical result env must not be trusted before fresh start'
[ ! -f "$IMPL/bgjob/implement-step5-review.result.env" ] || fail 'stale canonical result env must be cleared before fresh start'
pass 'Step 5 wrapper clears stale canonical result envs before fresh launch'

IMPL="$D/live-registry"
make_impl "$IMPL" "$FAKE"
STEP5_REGISTRY_MODE=live CLAUDE_PLUGIN_ROOT="$FAKE" IMPLEMENT_TMPDIR="$IMPL" "$WRAPPER" >"$IMPL/stdout.log" 2>"$IMPL/stderr.log" || fail "live rejoin wrapper failed: $(cat "$IMPL/stderr.log")"
grep -Fq 'BGJOB_STATUS=WAIT' "$IMPL/stdout.log" || fail 'live registry re-entry must emit bgjob wait output'
[ ! -f "$IMPL/bgjob-start-argv.txt" ] || fail 'live registry re-entry must not launch a second bgjob'
[ ! -f "$IMPL/registry-unlinked" ] || fail 'live registry row must not be cleared'
pass 'Step 5 wrapper rejoins live registry rows without duplicate launch'

IMPL="$D/live-registry-stall-cache"
make_impl "$IMPL" "$FAKE"
seed_stall_result_env "$IMPL"
STEP5_REGISTRY_MODE=live CLAUDE_PLUGIN_ROOT="$FAKE" IMPLEMENT_TMPDIR="$IMPL" "$WRAPPER" >"$IMPL/stdout.log" 2>"$IMPL/stderr.log" || fail "live rejoin with cached stall failed: $(cat "$IMPL/stderr.log")"
grep -Fq 'BGJOB_STATUS=WAIT' "$IMPL/stdout.log" || fail 'live registry with cached stall must still rejoin bgjob wait'
[ ! -f "$IMPL/bgjob-start-argv.txt" ] || fail 'live registry with cached stall must not launch a second bgjob'
[ ! -f "$IMPL/bgjob/implement-step5-review.result.env" ] || fail 'live registry with cached stall must clear non-complete canonical result env before wait'
pass 'Step 5 wrapper clears cached stall envs before live registry rejoin'

for mode in dead done-timeout done-orphaned; do
  IMPL="$D/$mode-live"
  make_impl "$IMPL" "$FAKE"
  STEP5_REGISTRY_MODE=live STEP5_WAIT_MODE="$mode" CLAUDE_PLUGIN_ROOT="$FAKE" IMPLEMENT_TMPDIR="$IMPL" "$WRAPPER" >"$IMPL/stdout.log" 2>"$IMPL/stderr.log" || fail "live registry wait mode $mode failed: $(cat "$IMPL/stderr.log")"
  case "$mode" in
    dead)
      grep -Fq 'BGJOB_STATUS=DEAD' "$IMPL/stdout.log" || fail 'live registry DEAD wait must propagate the DEAD envelope'
      ;;
    done-timeout)
      grep -Fq 'BGJOB_RC=timeout' "$IMPL/stdout.log" || fail 'live registry timeout wait must preserve timeout rc'
      ;;
    done-orphaned)
      grep -Fq 'BGJOB_RC=orphaned' "$IMPL/stdout.log" || fail 'live registry orphaned wait must preserve orphaned rc'
      ;;
  esac
  [ ! -f "$IMPL/bgjob-start-argv.txt" ] || fail "live registry wait mode $mode must not launch a second bgjob"
done
pass 'Step 5 wrapper does not false-start on DEAD, timeout, or orphaned wait envelopes'

IMPL="$D/dead-registry"
make_impl "$IMPL" "$FAKE"
STEP5_REGISTRY_MODE=dead CLAUDE_PLUGIN_ROOT="$FAKE" IMPLEMENT_TMPDIR="$IMPL" "$WRAPPER" >"$IMPL/stdout.log" 2>"$IMPL/stderr.log" || fail "dead registry wrapper failed: $(cat "$IMPL/stderr.log")"
grep -Fq 'BGJOB_STATUS=STARTED STEP=implement-step5-review PGID=12345' "$IMPL/stdout.log" || fail 'dead registry re-entry must fresh-start bgjob'
[ -f "$IMPL/registry-unlinked" ] || fail 'dead registry row must be cleared before fresh start'
pass 'Step 5 wrapper clears dead registry rows before fresh launch'

IMPL="$D/probe-error"
make_impl "$IMPL" "$FAKE"
if STEP5_REGISTRY_MODE=error CLAUDE_PLUGIN_ROOT="$FAKE" IMPLEMENT_TMPDIR="$IMPL" "$WRAPPER" >"$IMPL/stdout.log" 2>"$IMPL/stderr.log"; then
  fail 'registry probe errors must fail closed'
fi
grep -Fq 'BGJOB_ERROR=registry-check-failed' "$IMPL/stderr.log" || fail 'registry probe failure must be reported on stderr'
[ ! -f "$IMPL/bgjob-start-argv.txt" ] || fail 'registry probe failure must not fresh-start bgjob'
pass 'Step 5 wrapper fails closed on registry probe errors'

IMPL="$D/child"
make_impl "$IMPL" "$FAKE"
CLAUDE_PLUGIN_ROOT="$FAKE" IMPLEMENT_TMPDIR="$IMPL" "$WRAPPER" --bgjob-child >"$IMPL/child.stdout" 2>"$IMPL/child.stderr" || fail "child wrapper failed: $(cat "$IMPL/child.stderr")"
grep -Fq 'review-and-fix step5' "$IMPL/calls.log" || fail 'child mode must run review-and-fix step5'
grep -Fq '/implement 5: code review' "$IMPL/child.stderr" || fail 'child mode must emit banner on stderr'
! grep -Fq -- '--new-process-group' "$IMPL/review-argv.txt" || fail 'bgjob-owned child must not use legacy new-process-group wrapper ownership'
! grep -Fq -- '--orphan-timeout-s' "$IMPL/review-argv.txt" || fail 'bgjob-owned child must delegate orphan handling to bgjob'
grep -Fq 'STEP5_REVIEW_STATUS=complete' "$IMPL/.step5-review-result.env" || fail 'child mode must publish Step 5 KVs for bgjob merge'
pass 'Step 5 child mode runs review loop under bgjob ownership assumptions'

pass 'step-5-review.sh checks passed'
