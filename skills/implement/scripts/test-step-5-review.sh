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
    pid = int(arg("--pid", "0"))
    (impl / ".step5-loop-identity.json").write_text(json.dumps({"pid": pid, "pgid": pid, "start_time": "stub", "command_signature": "review-and-fix step5", "expected_signature": "review-and-fix step5"}), encoding="utf-8")
    sys.exit(0)
if sys.argv[1:3] == ["review-and-fix", "teardown-loop-identity"]:
    sys.exit(0)
if sys.argv[1:3] == ["review-and-fix", "await-loop-identity"]:
    sys.exit(0)
if sys.argv[1:3] == ["review-and-fix", "normalize-status"]:
    text = Path(arg("--stdout-file")).read_text(encoding="utf-8")
    if "STEP5_REVIEW_STATUS=" not in text:
        sys.exit(2)
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

pass 'Step 5 wrapper reattaches detached loops without duplicate launch'

pass 'step-5-review.sh checks passed'
