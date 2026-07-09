#!/usr/bin/env bash
# test-bgjob.sh — real-process regression harness for bgjob start/wait/reap coverage.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
PYTHONPATH="$REPO_ROOT/python${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONPATH

cd "$REPO_ROOT"

if ! python3 - <<'PY'
import os
import sys

from larch.core import process_identity

if process_identity.read_process_identity(pid=os.getpid()) is None:
    sys.exit(1)
PY
then
    echo "SKIP: ps process identity probe unavailable in this sandbox"
    exit 0
fi

TEST_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/larch-bgjob-test.XXXXXX")"
REGISTRY_ROOT="$TEST_ROOT/registry"
PIDS_FILE="$TEST_ROOT/pids.txt"
PGIDS_FILE="$TEST_ROOT/pgids.txt"
export LARCH_BGJOB_REGISTRY_ROOT="$REGISTRY_ROOT"
export LARCH_TEST_BGJOB_OWNER_GRACE_S="0.2"
export LARCH_TEST_BGJOB_DAEMON_POLL_INTERVAL_S="0.1"

touch "$PIDS_FILE" "$PGIDS_FILE"

fail() {
    echo "FAIL: $*" >&2
    exit 1
}

track_pid() {
    printf '%s\n' "$1" >> "$PIDS_FILE"
}

track_pgid() {
    printf '%s\n' "$1" >> "$PGIDS_FILE"
}

cleanup() {
    set +e
    if [ -f "$PGIDS_FILE" ]; then
        while IFS= read -r pgid; do
            [ -n "$pgid" ] || continue
            kill -TERM "-$pgid" 2>/dev/null
        done < "$PGIDS_FILE"
        sleep 0.2
        while IFS= read -r pgid; do
            [ -n "$pgid" ] || continue
            kill -KILL "-$pgid" 2>/dev/null
        done < "$PGIDS_FILE"
    fi
    if [ -f "$PIDS_FILE" ]; then
        while IFS= read -r pid; do
            [ -n "$pid" ] || continue
            kill -TERM "$pid" 2>/dev/null
        done < "$PIDS_FILE"
        sleep 0.2
        while IFS= read -r pid; do
            [ -n "$pid" ] || continue
            kill -KILL "$pid" 2>/dev/null
            wait "$pid" 2>/dev/null
        done < "$PIDS_FILE"
    fi
    rm -rf "$TEST_ROOT"
}
trap cleanup EXIT

start_bgjob() {
    local step="$1"
    local tmpdir="$2"
    local budget_s="$3"
    local owner_pid="$4"
    shift 4
    mkdir -p "$tmpdir"
    python3 python/cli.py bgjob start \
        --step "$step" \
        --tmpdir "$tmpdir" \
        --budget-s "$budget_s" \
        --owner-pid "$owner_pid" \
        -- "$@"
}

assert_started_line() {
    local output="$1"
    local step="$2"
    local line_count
    line_count="$(printf '%s' "$output" | awk 'END {print NR}')"
    [ "$line_count" = "1" ] || fail "start for $step printed $line_count lines: $output"
    if [[ ! "$output" =~ ^BGJOB_STATUS=STARTED\ STEP=${step}\ PGID=[0-9]+$ ]]; then
        fail "start for $step printed unexpected output: $output"
    fi
}

started_pgid() {
    printf '%s\n' "$1" | awk '{
        for (i = 1; i <= NF; i += 1) {
            if ($i ~ /^PGID=/) {
                sub(/^PGID=/, "", $i)
                print $i
                exit
            }
        }
    }'
}

wait_done_rc() {
    local step="$1"
    local tmpdir="$2"
    local expected_rc="$3"
    local max_wait_s="$4"
    local output
    output="$(python3 python/cli.py bgjob wait --step "$step" --tmpdir "$tmpdir" --max-wait-s "$max_wait_s" --poll-interval-s 0.1)"
    case "$output" in
        *"BGJOB_STATUS=DONE"* ) ;;
        * ) fail "wait for $step did not finish: $output" ;;
    esac
    case "$output" in
        *"BGJOB_RC=$expected_rc"* ) ;;
        * ) fail "wait for $step did not report BGJOB_RC=$expected_rc: $output" ;;
    esac
}

wait_dead() {
    local step="$1"
    local tmpdir="$2"
    local output
    output="$(python3 python/cli.py bgjob wait --step "$step" --tmpdir "$tmpdir" --max-wait-s 2 --poll-interval-s 0.1)"
    case "$output" in
        *"BGJOB_STATUS=DEAD"* ) ;;
        * ) fail "wait for $step did not report DEAD: $output" ;;
    esac
}

registry_file_for_step() {
    local step="$1"
    local candidate
    for candidate in "$REGISTRY_ROOT"/*-"$step".env; do
        if [ -f "$candidate" ]; then
            printf '%s\n' "$candidate"
            return 0
        fi
    done
    return 1
}

registry_value() {
    local key="$1"
    local path="$2"
    awk -F= -v wanted="$key" '
        $1 == wanted {
            print substr($0, length($1) + 2)
            found = 1
            exit
        }
        END {
            if (!found) {
                exit 1
            }
        }
    ' "$path"
}

spawn_sleeper() {
    python3 - <<'PY'
import subprocess
import sys

process = subprocess.Popen(  # noqa: S603 - test harness starts a controlled sleeper
    [sys.executable, "-c", "import time; time.sleep(60)"],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    start_new_session=True,
)
print(process.pid)
PY
}

write_reap_fixture() {
    local tmpdir="$1"
    local step="$2"
    local daemon_pid="$3"
    local child_pid="$4"
    python3 - "$tmpdir" "$step" "$daemon_pid" "$child_pid" <<'PY'
import dataclasses
import sys
import time
from pathlib import Path

from larch.bgjob import model, registry
from larch.core import process_identity


def capture(pid: int) -> process_identity.RecordedProcessIdentity:
    deadline = time.time() + 5.0
    while time.time() < deadline:
        identity = process_identity.read_process_identity(pid=pid)
        if identity is not None:
            return identity
        time.sleep(0.05)
    raise RuntimeError(f"could not capture identity for pid {pid}")


tmpdir = Path(sys.argv[1]).resolve()
step = sys.argv[2]
daemon_pid = int(sys.argv[3])
child_pid = int(sys.argv[4])
log_dir = tmpdir / "bgjob"
log_dir.mkdir(parents=True, exist_ok=True)
stdout_log = log_dir / f"{step}.stdout.log"
stderr_log = log_dir / f"{step}.stderr.log"
result_env = log_dir / f"{step}.result.env"
stdout_log.touch()
stderr_log.touch()
if result_env.exists():
    result_env.unlink()
daemon_identity = capture(daemon_pid)
child_identity = capture(child_pid)
stale_child = dataclasses.replace(child_identity, start_time=f"stale {child_identity.start_time}")
entry = model.RegistryEntry(
    step=step,
    run_id=model.default_run_id(tmpdir=tmpdir, clone_path=Path.cwd().resolve()),
    tmpdir=tmpdir,
    log_dir=log_dir,
    clone_path=Path.cwd().resolve(),
    daemon=daemon_identity,
    child=stale_child,
    owner=None,
    start_epoch=int(time.time()) - 10,
    budget_s=1,
    stdout_log=stdout_log,
    stderr_log=stderr_log,
    result_env=result_env,
)
print(registry.write_entry(entry))
PY
}

test_start_prints_one_line() {
    local step="start-check"
    local tmpdir="$TEST_ROOT/$step"
    local output
    local pgid
    output="$(start_bgjob "$step" "$tmpdir" 10 "$$" python3 -c 'print("start-check")')"
    assert_started_line "$output" "$step"
    pgid="$(started_pgid "$output")"
    [ -n "$pgid" ] || fail "missing PGID for $step"
    track_pgid "$pgid"
    wait_done_rc "$step" "$tmpdir" "0" 5
}

test_owner_death_reports_orphaned() {
    local step="owner-death"
    local tmpdir="$TEST_ROOT/$step"
    local owner_pid
    local output
    local pgid
    python3 -c 'import time; time.sleep(60)' &
    owner_pid="$!"
    track_pid "$owner_pid"
    output="$(start_bgjob "$step" "$tmpdir" 20 "$owner_pid" python3 -c 'import time; time.sleep(60)')"
    assert_started_line "$output" "$step"
    pgid="$(started_pgid "$output")"
    track_pgid "$pgid"
    kill "$owner_pid"
    wait "$owner_pid" 2>/dev/null || true
    wait_done_rc "$step" "$tmpdir" "orphaned" 8
}

test_budget_expiry_kills_child_group() {
    local step="budget-expiry"
    local tmpdir="$TEST_ROOT/$step"
    local output
    local pgid
    local registry_file
    local child_pid
    output="$(start_bgjob "$step" "$tmpdir" 1 "$$" python3 -c 'import time; time.sleep(60)')"
    assert_started_line "$output" "$step"
    pgid="$(started_pgid "$output")"
    track_pgid "$pgid"
    registry_file="$(registry_file_for_step "$step")" || fail "missing registry row for $step"
    child_pid="$(registry_value CHILD_PID "$registry_file")" || fail "missing CHILD_PID for $step"
    wait_done_rc "$step" "$tmpdir" "timeout" 8
    if kill -0 "$child_pid" 2>/dev/null; then
        fail "timeout left child pid $child_pid alive"
    fi
}

test_external_daemon_kill_reports_dead() {
    local step="external-kill"
    local tmpdir="$TEST_ROOT/$step"
    local output
    local pgid
    local registry_file
    local daemon_pid
    output="$(start_bgjob "$step" "$tmpdir" 30 "$$" python3 -c 'import time; time.sleep(60)')"
    assert_started_line "$output" "$step"
    pgid="$(started_pgid "$output")"
    track_pgid "$pgid"
    registry_file="$(registry_file_for_step "$step")" || fail "missing registry row for $step"
    daemon_pid="$(registry_value DAEMON_PID "$registry_file")" || fail "missing DAEMON_PID for $step"
    kill "$daemon_pid"
    wait_dead "$step" "$tmpdir"
    rm -f "$registry_file"
}

test_reap_recycled_pid_does_not_signal_new_owner() {
    local step="reap-recycled"
    local tmpdir="$TEST_ROOT/$step"
    local daemon_pid
    local recycled_pid
    local registry_file
    local output
    mkdir -p "$tmpdir"
    daemon_pid="$(spawn_sleeper)"
    recycled_pid="$(spawn_sleeper)"
    track_pid "$daemon_pid"
    track_pid "$recycled_pid"
    registry_file="$(write_reap_fixture "$tmpdir" "$step" "$daemon_pid" "$recycled_pid")"
    [ -f "$registry_file" ] || fail "reap fixture did not create registry row"
    if ! kill -0 "$daemon_pid" 2>/dev/null; then
        fail "reap fixture daemon pid $daemon_pid died before reap"
    fi
    python3 - "$registry_file" "$daemon_pid" <<'PY'
import sys
from pathlib import Path

from larch.bgjob import registry

path = Path(sys.argv[1])
daemon_pid = int(sys.argv[2])
entry = registry.read_entry(path)
if entry is None:
    raise SystemExit(f"missing registry entry at {path}")
if entry.daemon.pid != daemon_pid:
    raise SystemExit(f"unexpected daemon pid {entry.daemon.pid}")
if not registry.daemon_liveness(entry).live:
    raise SystemExit("daemon liveness precondition failed")
if registry.child_liveness(entry).live:
    raise SystemExit("child liveness precondition failed")
if not registry.entry_expired(entry):
    raise SystemExit("expiry precondition failed")
PY
    output="$(python3 python/cli.py bgjob reap)"
    [ "$output" = "BGJOB_REAPED=1" ] || fail "unexpected reap output: $output"
    [ ! -e "$registry_file" ] || fail "reap did not remove recycled fixture row"
    if ! kill -0 "$recycled_pid" 2>/dev/null; then
        fail "reap signaled recycled pid $recycled_pid"
    fi
}

expect_bad_step() {
    local step="$1"
    local output
    local rc
    set +e
    output="$(python3 python/cli.py bgjob start --step "$step" --tmpdir "$TEST_ROOT/bad-step" --budget-s 1 --owner-pid "$$" -- python3 -c 'print("bad")')"
    rc="$?"
    set -e
    [ "$rc" = "2" ] || fail "bad step $step returned rc $rc: $output"
    case "$output" in
        *"BGJOB_ERROR"* ) ;;
        * ) fail "bad step $step did not print BGJOB_ERROR: $output" ;;
    esac
}

test_bad_step_names_reject() {
    mkdir -p "$TEST_ROOT/bad-step"
    expect_bad_step "../bad"
    expect_bad_step "bad/step"
    expect_bad_step "bad\\step"
}

test_start_prints_one_line
test_owner_death_reports_orphaned
test_budget_expiry_kills_child_group
test_external_daemon_kill_reports_dead
test_reap_recycled_pid_does_not_signal_new_owner
test_bad_step_names_reject

echo "bgjob real-process harness passed"
