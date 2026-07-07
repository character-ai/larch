#!/usr/bin/env bash
# test-bgjob.sh — real-process harness for bgjob start/wait/reap behavior.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd -P)"
CLI="$REPO_ROOT/python/cli.py"
PYTHON_BIN="${PYTHON:-python3}"

PASS=0
FAIL=0
pass() { PASS=$((PASS + 1)); printf 'PASS: %s\n' "$1"; }
fail() { FAIL=$((FAIL + 1)); printf 'FAIL: %s\n' "$1" >&2; }

TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-bgjob.XXXXXX")"
RUN_TMP="$TMP/session"
REGISTRY="$TMP/registry"
mkdir -p "$RUN_TMP" "$REGISTRY"

cleanup() {
  if [ -d "$REGISTRY" ]; then
    for reg in "$REGISTRY"/*.env; do
      [ -f "$reg" ] || continue
      pgid=$(awk -F= '$1 == "CHILD_PGID" { print $2; found=1; exit } END { exit found ? 0 : 1 }' "$reg" 2>/dev/null || true)
      case "$pgid" in ''|*[!0-9]*) ;; *) kill -TERM "-$pgid" 2>/dev/null || true; kill -KILL "-$pgid" 2>/dev/null || true ;; esac
    done
  fi
  rm -rf "$TMP"
}
trap cleanup EXIT

skip_identity_probe() {
  printf 'SKIP: ps identity probes unavailable in this sandbox: %s\n' "$1"
  exit 0
}

ps -p $$ -o lstart= -o command= >/dev/null 2>&1 || skip_identity_probe 'ps cannot read current process'
command -v pgrep >/dev/null 2>&1 || skip_identity_probe 'pgrep is unavailable'

run_cli() {
  LARCH_BGJOB_REGISTRY_ROOT="$REGISTRY" LARCH_CLAUDE_PID="$$" "$PYTHON_BIN" "$CLI" "$@"
}

kv_from_text() {
  local key="$1" text="$2"
  printf '%s\n' "$text" | awk -F= -v k="$key" '$1 == k { sub(/^[^=]*=/, ""); print; found=1; exit } END { exit found ? 0 : 1 }'
}

kv_from_file() {
  local key="$1" path="$2"
  awk -F= -v k="$key" '$1 == k { sub(/^[^=]*=/, ""); print; found=1; exit } END { exit found ? 0 : 1 }' "$path"
}

text_has_line() {
  local text="$1" want="$2"
  printf '%s\n' "$text" | awk -v want="$want" '$0 == want { found=1; exit } END { exit found ? 0 : 1 }'
}

wait_for_registry() {
  local step="$1" deadline=$((SECONDS + 5))
  while [ "$SECONDS" -le "$deadline" ]; do
    for reg in "$REGISTRY"/*-"$step".env; do
      [ -f "$reg" ] || continue
      printf '%s' "$reg"
      return 0
    done
    sleep 0.1
  done
  return 1
}

wait_for_done_rc() {
  local step="$1" expected_rc="$2" timeout_s="$3" out rc
  local deadline=$((SECONDS + timeout_s))
  while [ "$SECONDS" -le "$deadline" ]; do
    out=$(run_cli bgjob wait --step "$step" --tmpdir "$RUN_TMP" --max-wait-s 1 --poll-interval-s 0.1)
    if text_has_line "$out" 'BGJOB_STATUS=DONE'; then
      rc=$(kv_from_text BGJOB_RC "$out" 2>/dev/null || true)
      if [ "$rc" = "$expected_rc" ]; then
        pass "$step completed with BGJOB_RC=$expected_rc"
      else
        fail "$step expected BGJOB_RC=$expected_rc, got '$rc' from: $out"
      fi
      return 0
    fi
    if text_has_line "$out" 'BGJOB_STATUS=DEAD'; then
      fail "$step became DEAD before DONE: $out"
      return 1
    fi
  done
  fail "$step did not reach DONE within ${timeout_s}s"
  return 1
}

pgid_for_pid() {
  "$PYTHON_BIN" - "$1" <<'PY'
import os
import sys

print(os.getpgid(int(sys.argv[1])))
PY
}

wait_for_own_pgid() {
  local pid="$1" deadline=$((SECONDS + 5)) pgid
  while [ "$SECONDS" -le "$deadline" ]; do
    pgid=$(pgid_for_pid "$pid" 2>/dev/null || true)
    if [ "$pgid" = "$pid" ]; then
      return 0
    fi
    sleep 0.1
  done
  return 1
}

identity_rows() {
  local prefix="$1" pid="$2" pgid raw start command
  pgid=$(pgid_for_pid "$pid")
  raw=$(ps -p "$pid" -o lstart= -o command= | awk 'NR == 1 { print; exit }')
  [ -n "$raw" ] || return 1
  start=$(printf '%s\n' "$raw" | awk '{ print $1 " " $2 " " $3 " " $4 " " $5 }')
  command=$(printf '%s\n' "$raw" | awk '{ $1=""; $2=""; $3=""; $4=""; $5=""; sub(/^[[:space:]]+/, ""); print }')
  printf '%s_PID=%s\n' "$prefix" "$pid"
  printf '%s_PGID=%s\n' "$prefix" "$pgid"
  printf '%s_START_TIME=%s\n' "$prefix" "$start"
  printf '%s_COMMAND=%s\n' "$prefix" "$command"
  printf '%s_EXPECTED=\n' "$prefix"
}

assert_one_line_start_stdout() {
  local step='start-contract' out line_count
  out=$(run_cli bgjob start --step "$step" --tmpdir "$RUN_TMP" --budget-s 10 -- "$PYTHON_BIN" -c 'import time; time.sleep(0.2)')
  line_count=$(printf '%s\n' "$out" | awk 'END { print NR }')
  case "$out" in
    "BGJOB_STATUS=STARTED STEP=$step PGID="*)
      if [ "$line_count" -eq 1 ]; then
        pass 'start stdout is one BGJOB_STATUS=STARTED line'
      else
        fail "start stdout should be one line, got $line_count: $out"
      fi
      ;;
    *) fail "unexpected start stdout: $out" ;;
  esac
  wait_for_done_rc "$step" 0 8 || true
}

assert_owner_death_orphaned() {
  local out
  out=$(PYTHONPATH="$REPO_ROOT/python" LARCH_BGJOB_REGISTRY_ROOT="$REGISTRY" "$PYTHON_BIN" - "$RUN_TMP" <<'PY' || true
import subprocess
import sys
import time
from pathlib import Path

from larch import io as larch_io
from larch.bgjob import daemon, model
from larch.core import config

tmpdir = Path(sys.argv[1])
step = "owner-orphaned"
config.BGJOB_OWNER_GRACE_S = 0.0
owner = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(0.5)"])
try:
    spec = model.JobSpec(
        step=step,
        tmpdir=tmpdir,
        log_dir=tmpdir / "bgjob",
        budget_s=20,
        command=(sys.executable, "-c", "import time; time.sleep(20)"),
        run_id=model.default_run_id(tmpdir=tmpdir, clone_path=Path.cwd().resolve()),
        owner=daemon.owner_identity_from_env(str(owner.pid)),
    )
    start_rc = daemon.start_daemon(spec)
    print(f"START_RC={start_rc}")
    owner.wait(timeout=5)
    result = model.result_env_path(tmpdir=tmpdir, step=step)
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if result.is_file() and not result.is_symlink():
            rows = larch_io.read_kvs(result, reject_symlink=True, on_error_default=True, reject_cr=True)
            print(f"BGJOB_RC={rows.get(config.BGJOB_RC_KEY, '')}")
            raise SystemExit(0 if rows.get(config.BGJOB_RC_KEY) == config.BGJOB_RC_ORPHANED else 1)
        time.sleep(0.2)
    print("BGJOB_RC=missing")
    raise SystemExit(1)
finally:
    if owner.poll() is None:
        owner.terminate()
PY
  )
  if text_has_line "$out" 'START_RC=0' && text_has_line "$out" 'BGJOB_RC=orphaned'; then
    pass 'owner death writes BGJOB_RC=orphaned'
  else
    fail "owner death did not write BGJOB_RC=orphaned: $out"
  fi
}

assert_budget_timeout() {
  local step='budget-timeout' out
  out=$(run_cli bgjob start --step "$step" --tmpdir "$RUN_TMP" --budget-s 1 -- "$PYTHON_BIN" -c 'import time; time.sleep(20)')
  case "$out" in "BGJOB_STATUS=STARTED STEP=$step PGID="*) pass 'timeout job started' ;; *) fail "timeout start failed: $out" ;; esac
  wait_for_done_rc "$step" timeout 10 || true
}

assert_external_daemon_kill_dead() {
  local step='daemon-dead' out reg daemon_pid child_pgid deadline=$((SECONDS + 8))
  out=$(run_cli bgjob start --step "$step" --tmpdir "$RUN_TMP" --budget-s 30 -- "$PYTHON_BIN" -c 'import time; time.sleep(20)')
  case "$out" in "BGJOB_STATUS=STARTED STEP=$step PGID="*) pass 'daemon-dead job started' ;; *) fail "daemon-dead start failed: $out"; return ;; esac
  reg=$(wait_for_registry "$step" || true)
  if [ -z "$reg" ]; then
    fail 'daemon-dead registry did not appear'
    return
  fi
  daemon_pid=$(kv_from_file DAEMON_PID "$reg")
  child_pgid=$(kv_from_file CHILD_PGID "$reg")
  kill -TERM "$daemon_pid" 2>/dev/null || true
  while [ "$SECONDS" -le "$deadline" ]; do
    out=$(run_cli bgjob wait --step "$step" --tmpdir "$RUN_TMP" --max-wait-s 1 --poll-interval-s 0.1)
    if text_has_line "$out" 'BGJOB_STATUS=DEAD'; then
      pass 'external daemon kill yields BGJOB_STATUS=DEAD'
      break
    fi
  done
  if ! text_has_line "$out" 'BGJOB_STATUS=DEAD'; then
    fail "daemon-dead wait did not report DEAD: $out"
  fi
  kill -TERM "-$child_pgid" 2>/dev/null || true
  kill -KILL "-$child_pgid" 2>/dev/null || true
  rm -f "$reg"
}

assert_reap_identity_check_spares_recycled_pid() {
  local step='reap-safety' run_id='reaprun' child_pid child_pgid reg out
  "$PYTHON_BIN" -c 'import os, time; os.setsid(); time.sleep(60)' &
  child_pid=$!
  if ! wait_for_own_pgid "$child_pid"; then
    kill "$child_pid" 2>/dev/null || true
    fail 'reap-safety child did not enter its own process group'
    return
  fi
  child_pgid=$(pgid_for_pid "$child_pid")
  reg="$REGISTRY/$run_id-$step.env"
  mkdir -p "$RUN_TMP/bgjob"
  {
    printf 'STEP=%s\n' "$step"
    printf 'RUN_ID=%s\n' "$run_id"
    printf 'TMPDIR=%s\n' "$RUN_TMP"
    printf 'LOG_DIR=%s\n' "$RUN_TMP/bgjob"
    printf 'CLONE_PATH=%s\n' "$REPO_ROOT"
    printf 'START_EPOCH=1\n'
    printf 'BUDGET_S=1\n'
    printf 'STDOUT_LOG=%s\n' "$RUN_TMP/bgjob/$step.stdout.log"
    printf 'STDERR_LOG=%s\n' "$RUN_TMP/bgjob/$step.stderr.log"
    printf 'RESULT_ENV=%s\n' "$RUN_TMP/bgjob/$step.result.env"
    identity_rows DAEMON $$
    printf 'CHILD_PID=%s\n' "$child_pid"
    printf 'CHILD_PGID=%s\n' "$child_pgid"
    printf 'CHILD_START_TIME=Thu Jan 1 00:00:00 1970\n'
    printf 'CHILD_COMMAND=not-the-current-command\n'
    printf 'CHILD_EXPECTED=\n'
  } >"$reg"
  out=$(run_cli bgjob reap)
  if kill -0 "$child_pid" 2>/dev/null; then
    pass 'identity-checked reap leaves mismatched live PID owner untouched'
  else
    fail "identity-checked reap signaled mismatched PID; reap output: $out"
  fi
  kill -TERM "-$child_pgid" 2>/dev/null || true
  kill -KILL "-$child_pgid" 2>/dev/null || true
  wait "$child_pid" 2>/dev/null || true
}

assert_bad_step_rejected() {
  local out
  out=$(run_cli bgjob start --step '../bad' --tmpdir "$RUN_TMP" --budget-s 1 -- "$PYTHON_BIN" -c 'print("hello")' || true)
  case "$out" in
    *BGJOB_ERROR*) pass 'bad step names are rejected by bgjob start' ;;
    *) fail "bad step start should reject, got: $out" ;;
  esac
}

assert_one_line_start_stdout
assert_owner_death_orphaned
assert_budget_timeout
assert_external_daemon_kill_dead
assert_reap_identity_check_spares_recycled_pid
assert_bad_step_rejected

if [ "$FAIL" -ne 0 ]; then
  printf 'FAIL: %s bgjob harness checks failed (%s passed)\n' "$FAIL" "$PASS" >&2
  exit 1
fi
printf 'PASS: bgjob harness complete (%s checks)\n' "$PASS"
