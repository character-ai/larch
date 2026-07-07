#!/usr/bin/env bash
# test-step-5-review.sh — Step 5 signal-aware wrapper contract.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
WRAPPER="$ROOT/skills/implement/scripts/step-5-review.sh"
fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$*"; }

make_fake_plugin() {
  local dir="$1"
  mkdir -p "$dir/python"
  cat >"$dir/python/cli.py" <<'PY'
#!/usr/bin/env python3
import json
import os
import signal
import sys
import time
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
if sys.argv[1:3] == ["session", "kill-background-processes"]:
    sys.exit(0)
if sys.argv[1:3] == ["review-and-fix", "write-loop-identity"]:
    if os.environ.get("STEP5_STUB_DELAY_IDENTITY") == "1":
        time.sleep(5)
        sys.exit(0)
    pid = int(arg("--pid", "0"))
    (impl / ".step5-loop-identity.json").write_text(json.dumps({"pid": pid, "pgid": pid, "start_time": "stub", "command_signature": "review-and-fix step5", "expected_signature": "review-and-fix step5"}), encoding="utf-8")
    sys.exit(0)
if sys.argv[1:3] == ["review-and-fix", "teardown-loop-identity"]:
    sys.exit(0)
if sys.argv[1:3] == ["review-and-fix", "await-loop-identity"]:
    if os.environ.get("STEP5_STUB_AWAIT_RC"):
        sys.exit(int(os.environ["STEP5_STUB_AWAIT_RC"]))
    sys.exit(0)
if sys.argv[1:3] == ["review-and-fix", "normalize-status"]:
    text = Path(arg("--stdout-file")).read_text(encoding="utf-8")
    if "STEP5_REVIEW_STATUS=" not in text:
        sys.exit(2)
    if os.environ.get("STEP5_STUB_NORMALIZE_RC"):
        sys.exit(int(os.environ["STEP5_STUB_NORMALIZE_RC"]))
    print(text, end="")
    sys.exit(0)
if sys.argv[1:3] == ["review-and-fix", "step5"]:
    if "--new-process-group" in sys.argv[3:]:
        os.setsid()
    (impl / "argv.txt").write_text("\n".join(sys.argv[1:]) + "\n", encoding="utf-8")
    marker = impl / ".bg-wait-active"
    if marker.is_file() and "STEP=implement-step5-review" in marker.read_text(encoding="utf-8", errors="replace"):
        (impl / "bg-marker-observed").touch()
    mode = os.environ.get("STEP5_STUB_MODE", "normal")
    if mode == "sleep":
        signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
        time.sleep(30)
    print("STEP5_REVIEW_STATUS=complete")
    print("STALL_TRACKING=false")
    print("STALL_REASON=")
    print("ROUNDS_COMPLETED=1")
    print("FINAL_ROUND_NUM=1")
    print("FINAL_REVIEW_AND_FIX_STATUS=complete")
    print("CODER_STATUS=")
    print("FILES_CHANGED_HINT=")
    print("EFFECTIVE_ROUND_CAP=2")
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

D=$(mktemp -d "${TMPDIR:-/tmp}/test-step5-review.XXXXXX")
trap 'rm -rf "$D"' EXIT
FAKE="$D/plugin"
make_fake_plugin "$FAKE"

IMPL="$D/normal"
make_impl "$IMPL" "$FAKE"
STEP5_STUB_MODE=normal CLAUDE_PLUGIN_ROOT="$FAKE" IMPLEMENT_TMPDIR="$IMPL" "$WRAPPER" >"$IMPL/stdout.log" 2>"$IMPL/stderr.log" || fail "normal wrapper failed: $(cat "$IMPL/stderr.log")"
[ -f "$IMPL/bg-marker-observed" ] || fail 'wrapper must write .bg-wait-active before review launch'
[ -f "$IMPL/.completed/step-5-terminal" ] || fail 'normal completion must write step-5-terminal'
grep -Fq -- '--new-process-group' "$IMPL/argv.txt" || fail 'wrapper must pass --new-process-group'
grep -Fq -- '--orphan-timeout-s' "$IMPL/argv.txt" || fail 'wrapper must pass --orphan-timeout-s'
grep -Fq 'review-and-fix normalize-status' "$IMPL/calls.log" || fail 'wrapper must normalize captured stdout'
! grep -Fq '/implement 5: code review' "$IMPL/stdout.log" || fail 'wrapper must not emit banner on stdout before review completion'
grep -Fq '/implement 5: code review' "$IMPL/stderr.log" || fail 'wrapper must emit banner on stderr to avoid premature task-notification'
pass 'Step 5 wrapper normal completion writes bg marker, argv, normalization, and terminal sentinel'

IMPL="$D/detach"
make_impl "$IMPL" "$FAKE"
set +e
STEP5_STUB_MODE=sleep CLAUDE_PLUGIN_ROOT="$FAKE" IMPLEMENT_TMPDIR="$IMPL" "$WRAPPER" >"$IMPL/stdout.log" 2>"$IMPL/stderr.log" &
wpid=$!
for _ in 1 2 3 4 5 6 7 8 9 10; do
  [ -f "$IMPL/.step5-loop-identity.json" ] && break
  sleep 0.1
done
kill -TERM "$wpid" 2>/dev/null || true
wait "$wpid"
rc=$?
set -e
[ "$rc" -eq 143 ] || fail "TERM wrapper rc should be 143, got $rc"
[ -f "$IMPL/.step5-wrapper-detached" ] || fail 'signal after identity must write detached marker'
[ ! -f "$IMPL/.completed/step-5-terminal" ] || fail 'signal detach must not write terminal sentinel'
pass 'Step 5 wrapper signal detach withholds false terminal sentinel'

IMPL="$D/reattach"
make_impl "$IMPL" "$FAKE"
cat >"$IMPL/detached.stdout" <<'EOF'
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
cat >"$IMPL/.step5-wrapper-detached" <<EOF
PID=321
SIGNAL=TERM
STDOUT_FILE=$IMPL/detached.stdout
DETACHED_AT_EPOCH=1
EOF
STEP5_STUB_MODE=normal CLAUDE_PLUGIN_ROOT="$FAKE" IMPLEMENT_TMPDIR="$IMPL" "$WRAPPER" >"$IMPL/reattach.stdout" 2>"$IMPL/reattach.stderr" || fail "reattach wrapper failed: $(cat "$IMPL/reattach.stderr")"
[ -f "$IMPL/.completed/step-5-terminal" ] || fail 'reattach path must write terminal sentinel after normalization'
grep -Fq 'review-and-fix normalize-status' "$IMPL/calls.log" || fail 'reattach path must normalize detached stdout'
! grep -Fq 'review-and-fix step5' "$IMPL/calls.log" || fail 'reattach path must not relaunch step5'
pass 'Step 5 wrapper reattaches detached loops without duplicate launch'

IMPL="$D/reattach-fail"
make_impl "$IMPL" "$FAKE"
cat >"$IMPL/detached.stdout" <<'EOF'
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
cat >"$IMPL/.step5-wrapper-detached" <<EOF
PID=654
SIGNAL=TERM
STDOUT_FILE=$IMPL/detached.stdout
DETACHED_AT_EPOCH=123
EOF
set +e
STEP5_STUB_NORMALIZE_RC=2 CLAUDE_PLUGIN_ROOT="$FAKE" IMPLEMENT_TMPDIR="$IMPL" "$WRAPPER" >"$IMPL/reattach-fail.stdout" 2>"$IMPL/reattach-fail.stderr"
rc=$?
set -e
[ "$rc" -eq 2 ] || fail "reattach normalize failure should preserve rc 2, got $rc"
grep -Fq 'DETACHED_AT_EPOCH=123' "$IMPL/.step5-wrapper-detached" || fail 'reattach normalize failure must preserve stored detach epoch'
! grep -Fq 'review-and-fix step5' "$IMPL/calls.log" || fail 'reattach normalize failure must not relaunch step5'
pass 'Step 5 wrapper restores detached markers without bumping the detach epoch'

IMPL="$D/reattach-stall"
make_impl "$IMPL" "$FAKE"
cat >"$IMPL/detached.stdout" <<'EOF'
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
cat >"$IMPL/.step5-wrapper-detached" <<EOF
PID=777
SIGNAL=TERM
STDOUT_FILE=$IMPL/detached.stdout
DETACHED_AT_EPOCH=1
EOF
set +e
STEP5_STUB_AWAIT_RC=2 CLAUDE_PLUGIN_ROOT="$FAKE" IMPLEMENT_TMPDIR="$IMPL" "$WRAPPER" >"$IMPL/reattach-stall.stdout" 2>"$IMPL/reattach-stall.stderr"
rc=$?
set -e
[ "$rc" -eq 2 ] || fail "reattach await failure should preserve rc 2, got $rc"
grep -Fq 'STALL_TRACKING=true' "$IMPL/reattach-stall.stdout" || fail 'reattach await failure must emit a stall envelope with STALL_TRACKING=true'
grep -Fq 'STALL_REASON=reattach-await-failed' "$IMPL/reattach-stall.stdout" || fail 'reattach await failure must name the stall reason'
pass 'Step 5 wrapper stall envelopes keep STALL_TRACKING=true'

IMPL="$D/preidentity"
make_impl "$IMPL" "$FAKE"
set +e
STEP5_STUB_DELAY_IDENTITY=1 CLAUDE_PLUGIN_ROOT="$FAKE" IMPLEMENT_TMPDIR="$IMPL" "$WRAPPER" >"$IMPL/preidentity.stdout" 2>"$IMPL/preidentity.stderr" &
wpid=$!
sleep 0.1
kill -TERM "$wpid" 2>/dev/null || true
wait "$wpid"
rc=$?
set -e
[ "$rc" -eq 143 ] || fail "pre-identity TERM wrapper rc should be 143, got $rc"
[ ! -f "$IMPL/.step5-wrapper-detached" ] || fail 'pre-identity TERM must not write detached marker'
[ ! -f "$IMPL/.completed/step-5-terminal" ] || fail 'pre-identity TERM must not write terminal sentinel'
pass 'Step 5 wrapper pre-identity TERM falls back to direct cleanup'

pass 'step-5-review.sh checks passed'
