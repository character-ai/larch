## Goal
Add per-role stall detection (180s) to launch-cursor-ci.sh to kill stalled cursor-ci processes early

## Implementation Plan

### Goal
Add per-role output-channel stall detection (180s) to scripts/launch-cursor-ci.sh so cursor-ci processes that produce 0 bytes are killed early rather than waiting the full 1800s wall-clock budget.

### Files to change

**scripts/lib-cursor-launcher-common.sh** — add `cursor_launcher_run_stall_monitor` helper function:
- Args: channel, output_file, stall_threshold, diag_file, target_pid
- Supports 3 channel types: `stdout` (watch $OUTPUT file size), `file:<path>` (watch specific file mtime/size), `tree:<path>` (watch directory tree for any mtime change excluding .git)
- Poll cadence: `${RUN_EXTERNAL_AGENT_POLL_INTERVAL:-10}` seconds (shared with run-external-agent.sh test infrastructure)
- On stall detected: append diagnostic to diag_file (channel, time_since_last_progress, ps -o pid,pcpu,etime,stat of target_pid and cursor-related processes), kill target_pid with SIGTERM + 2s + SIGKILL, return 0
- On target_pid exits normally: return 0
- Bash 3.2 compatible: no declare -A, no mapfile, use date +%s for timestamps, wc -c for sizes, find -newer for tree
- Tree baseline: mktemp file; touch to update when progress detected; cleaned up on return

**scripts/launch-cursor-ci.sh** — add stall detection wiring:
- Add `STALL_THRESHOLD=${LARCH_CURSOR_CI_STALL_THRESHOLD:-180}` (env var override for test harnesses)
- Add `STALL_CHANNEL` variable (no default)
- After arg parsing and validation, add per-role case block:
  ```
  case "$ROLE" in
      fix|bump-classify|changelog-draft) STALL_CHANNEL=stdout ;;
      resolve-conflict) STALL_CHANNEL="tree:${PWD}" ;;
  esac
  ```
- Restructure auth-retry loop to enable parallel stall monitoring:
  - Background run-external-agent.sh: append `&` after the command, capture `_REA_PID=$!`
  - Call `cursor_launcher_run_stall_monitor "$STALL_CHANNEL" "$OUTPUT" "$STALL_THRESHOLD" "${OUTPUT}.diag" "$_REA_PID" || true`
  - `wait "$_REA_PID" && LAUNCHER_EXIT=0 || LAUNCHER_EXIT=$?`
  - Auth-retry logic unchanged (stall kill produces non-auth verdict → no retry)

**scripts/test-launch-cursor-ci.sh** — add 6 stall detection fixtures:
Setup for all stall tests:
- CURSOR_API_KEY=test_key (bypass cursor auth preflight)
- LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 (test mode)
- LARCH_CURSOR_CI_STALL_THRESHOLD=3 (3-second stall threshold)
- RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.5 (0.5s poll interval)
- LARCH_EXTERNAL_AUTH_RETRIES=1 (no auth retry on stall kill)
- Fake cursor stub via PATH injection (replaces real cursor binary)

Fixture 1 — stdout-role 0-byte stall:
- Stub: cursor binary that sleeps 300s with no output
- Run with --role fix --timeout 1800
- Assert: exits in <20s (well before 1800s wall-clock cap)
- Assert: exits non-zero
- Assert: ${OUTPUT}.diag contains "Stall detected"

Fixture 2 — stdout-role progress-then-stall:
- Stub: cursor binary that writes 1 byte, then sleeps 300s
- Run with --role fix --timeout 1800
- Assert: exits in <15s (stall fires ~3s after last byte written)
- Assert: exits non-zero
- Assert: ${OUTPUT}.diag contains "Stall detected"

Fixture 3 — tree-role stall (resolve-conflict):
- Create temp git repo (git init + git commit --allow-empty)
- Stub: cursor binary that sleeps 300s without modifying the working tree
- Run with --role resolve-conflict --timeout 1800 inside the temp git repo
- Assert: exits in <20s
- Assert: exits non-zero
- Assert: ${OUTPUT}.diag contains "Stall detected"

Fixture 4 — progress within stall window (anti-regression):
- Stub: cursor binary that writes 1 byte every 1s for 6 iterations then exits 0
- Run with --role fix --timeout 1800, stall threshold=3
- Assert: exits 0 (no stall kill — cursor exits before any stall)

Fixture 5 — wall-clock cap still fires:
- Stub: cursor binary that writes 1 byte every 0.5s indefinitely
- Run with --role fix --timeout 5 (short wall-clock cap), stall threshold=3
- Assert: exits 124 (run-external-agent.sh timeout exit code)
- Assert: elapsed < 15s (killed by wall-clock cap, not stall)

Fixture 6 — diagnostic record shape:
- Stub: cursor binary that sleeps 300s
- Run with --role fix --timeout 1800, IMPLEMENT_TMPDIR set
- Assert: ${OUTPUT}.diag contains "channel=stdout"
- Assert: ${OUTPUT}.diag contains "time_since_last_progress="
- Assert: execution-issues.md exists and contains "cursor-ci" (append_launch_failure fired)

**scripts/launch-cursor-ci.md** — update:
- Add description of stall detection: per-role STALL_CHANNEL, STALL_THRESHOLD, LARCH_CURSOR_CI_STALL_THRESHOLD env override
- Add note that stall kill appends to ${OUTPUT}.diag and triggers append_launch_failure like normal failures

**scripts/lib-cursor-launcher-common.md** — update:
- Document cursor_launcher_run_stall_monitor function


## Test plan
- `make test-launch-cursor-ci` should pass all existing + new fixtures
- `make relevant-checks` passes
- Stall tests each complete in <30s total
