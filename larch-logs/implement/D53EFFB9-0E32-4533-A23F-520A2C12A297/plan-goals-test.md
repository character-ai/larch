## Goal
Implement issue #4309: [IMPLEMENTING] /design leaves orphan background processes after skill completes.

## Implementation Plan
## Plan

### Approach

- Treat `approach-synthesis.txt` as `NO_SKETCHES`.
- Treat the approved outline as binding scope.
- Keep the fix small:
  - Do not change reviewer timeouts.
  - Do not add retry behavior.
  - Do not change `/implement` cleanup.
- Fix Step 3 orphaning with layered cleanup:
  1. Keep `run-step3-review.sh --mode loop` descendants in the wrapper-owned process group.
  2. Add an `EXIT` trap in `dispatch-with-waterfall.sh` for tracked launcher PIDs.
  3. Add a `session kill-background-processes --design-tmpdir` CLI command that reuses `finalize.kill_session_background_processes`.
  4. Call that command from `design-step3-review.sh` after the existing process-group kill.
- Incorporate accepted reviewer corrections:
  - Add a real `RUN_STEP3_REVIEW_LOOP_SH` source seam so tests can observe monitor mode at the `review-design-step3-loop.sh` source site.
  - Test `set +m` under `bash -m` so the regression fails if the line is removed.
  - Validate cleanup CLI tmpdirs with `session_env.validate_design_tmpdir` plus design-session-specific guards, not the weaker generic allowlist.

## Files to modify/create

### UPDATED: `skills/design/scripts/run-step3-review.sh`

- In the `STEP3_MODE == loop` branch, run `set +m 2>/dev/null || true` before sourcing the loop driver.
- Add `_review_loop_sh="${RUN_STEP3_REVIEW_LOOP_SH:-$PLUGIN_ROOT/skills/design/scripts/review-design-step3-loop.sh}"`.
- Source `$_review_loop_sh` instead of hard-coding the path.
- Validate that `$_review_loop_sh` is readable before sourcing.
- Keep `RUN_STEP3_PLAN_REVIEW_LOOP_SH` unchanged. It controls the nested `plan-review-loop.sh` command, not the sourced loop driver.
- Add a short comment:
  - `design-step3-review.sh` enables monitor mode so the loop process gets its own process group.
  - The loop driver disables monitor mode inside that process so background descendants remain in the loop process group.
  - The wrapper's existing `kill -- -$_loop_pid` can then reach descendants.
- Leave preview mode and single-round mode behavior unchanged.

### UPDATED: `skills/design/scripts/run-step3-review.md`

- Document that loop mode disables monitor mode before sourcing `review-design-step3-loop.sh`.
- Document `RUN_STEP3_REVIEW_LOOP_SH` as a test seam for the sourced loop driver.
- State that this preserves wrapper-owned process-group cleanup for plan-review descendants.
- Keep the existing `RUN_STEP3_PLAN_REVIEW_LOOP_SH` documentation scoped to the nested plan-review subprocess.

### UPDATED: `skills/design/scripts/design-step3-review.sh`

- Add `_step3_review_kill_tmpdir_processes`.
  - Return quietly if `CLAUDE_PLUGIN_ROOT`, `DESIGN_TMPDIR`, `python3`, or `python/cli.py` is unavailable.
  - Run `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" session kill-background-processes --design-tmpdir "$DESIGN_TMPDIR"`.
  - Ignore failures. Redirect helper stdout and stderr away from the Step 3 result parser.
- Call the helper:
  - In `_step3_review_cleanup` after `_step3_review_teardown_loop_group "$_loop_pid"`.
  - On the normal path after `_step3_review_teardown_loop_group "$_loop_pid"` and before clearing `_loop_pid`.
- Keep existing monitor-mode setup and result-env parsing unchanged.

### UPDATED: `skills/design/scripts/design-step3-review.md`

- Add an invariant: the wrapper performs two cleanup passes.
  - First: kill the loop process group.
  - Second: best-effort kill any remaining process whose argv references `$DESIGN_TMPDIR`.
- Note that the second pass is allowed to fail silently.

### UPDATED: `scripts/dispatch-with-waterfall.sh`

- Add a Bash 3.2-compatible cleanup trap near the `pids=()` definition.
- Add `_waterfall_kill_active_pids` that copies current `pids`, sends `TERM` to each, and reaps each with `wait "$pid" 2>/dev/null || true`. No noisy output.
- Install `trap _waterfall_kill_active_pids EXIT`.
- Clear `pids=()` after `collect_phase` finishes waiting for the active phase.
- Preserve all existing `DISPATCH_OK`, fallback, and drop behavior.
- Do not alter `--timeout 1860`.

### UPDATED: `scripts/dispatch-with-waterfall.md`

- Document the EXIT trap: kills active phase launcher PIDs on exit.
- Note this is a cleanup guard only; does not change fallback semantics or timeout values.

### UPDATED: `python/cli.py`

- Add the registry entry: `("session", "kill-background-processes"): ("finalize", "kill_background_processes_main")`.

### UPDATED: `python/finalize.py`

- Add `kill_background_processes_main(argv: list[str]) -> int`.
- Parse `--design-tmpdir PATH`.
- Validate in order: present, non-relative, no `..`, `session_env.validate_design_tmpdir` ok, resolved path exists and is a directory, basename starts with `claude-design-`, directory contains regular non-symlink `source-env.sh`.
- On failure: emit `ERROR=<message>` to stderr, return `2`, do not kill.
- Build `RunContext` with `IMPLEMENT_TMPDIR` set to resolved design tmpdir via `RunContext.from_env`.
- Call `kill_session_background_processes(proc, ctx)`.
- Emit `KILLED=true` or `KILLED=false`. Return `0` on success, `2` on validation error.

### UPDATED: `python/test_cli.py`

- Add a dispatcher test that `cli.main(["session", "kill-background-processes", "--design-tmpdir", "<TMPDIR>"])` routes to `finalize.kill_background_processes_main`.

### UPDATED: `python/test_finalize.py`

- Add tests for `kill_background_processes_main`:
  - Rejects missing `--design-tmpdir`.
  - Rejects relative input, newline-bearing input, `..` path segments.
  - Rejects an allowed-root non-design path such as `/tmp/x`.
  - Rejects a design-looking path that lacks the `source-env.sh` marker.
  - Calls `kill_session_background_processes` with a context whose `tmpdir` equals the resolved design tmpdir.
  - Emits `KILLED=true` or `KILLED=false` correctly.
  - Does not call `kill_session_background_processes` on validation failure.
  - For valid-path tests: create a temp directory with `claude-design-` basename and a regular `source-env.sh` marker.

### UPDATED: `skills/design/scripts/test-run-step3-review.sh`

- Add a loop-mode regression using the new `RUN_STEP3_REVIEW_LOOP_SH` seam.
- The stub: records `case $- in *m*)` at top level when sourced; defines `run_design_step3_loop` that emits a valid complete result envelope.
- Preflight: `bash -m -c 'case $- in *m*) exit 0;; *) exit 97;; esac'` confirms monitor mode is observable.
- Run `bash -m "$LAUNCHER" --design-tmpdir "$D" --mode loop` with `RUN_STEP3_REVIEW_LOOP_SH="$stub"`.
- Assert stub saw monitor mode disabled. Assert a valid complete result envelope is returned.
- Keep existing `RUN_STEP3_PLAN_REVIEW_LOOP_SH` tests for nested plan-review behavior.

### UPDATED: `skills/design/scripts/test-design-step3-review.sh`

- Add a regression that verifies `design-step3-review.sh` invokes `session kill-background-processes --design-tmpdir "$DESIGN_TMPDIR"`.
- Use a stubbed `python3` or fake CLI path.
- Assert the helper runs after the loop path. Assert helper failure is best-effort (wrapper still emits expected Step 3 result envelope).

### UPDATED: `scripts/test-dispatch-with-waterfall.sh`

- Add a regression for the waterfall `EXIT` trap.
- Use stub launchers that sleep and write their PID to a test file.
- Start `dispatch-with-waterfall.sh` in the background. Wait until the stub PID is recorded (bounded wait).
- Send `TERM` to the dispatcher. Assert the child launcher PID is no longer alive.
- Add a cleanup trap to kill leftover stub PIDs if the assertion fails.

### UPDATED: `BASH_AUTHORING.md`

- Add a note in the Bash quoting section:
  - Avoid `cat > file << EOF` with `${LARGE_VAR}` expansion inside `run_in_background` tool calls.
  - Prefer the Write tool for large generated content or file-backed handoff.
  - Quoted heredocs remain fine for literal scripts, but not for expanding large runtime variables into the heredoc body.

## Edge cases

- If monitor mode cannot be enabled in `design-step3-review.sh`, keep the current prelaunch failure behavior.
- If `set +m` fails inside `run-step3-review.sh`, continue. The command is a cleanup-shaping guard only.
- If `RUN_STEP3_REVIEW_LOOP_SH` is unset, use the production `review-design-step3-loop.sh`.
- If the tmpdir cleanup helper cannot run, continue. The process-group kill remains the primary cleanup.
- If the cleanup CLI receives a relative path, newline-bearing path, `..` segment, non-design basename, missing directory, or missing `source-env.sh` marker, return `2` and perform no kill.
- If `dispatch-with-waterfall.sh` exits before any phase launches, the `pids` array is empty and the trap is a no-op.
- If a phase has already been collected, `pids` is cleared so the trap does not try to kill stale PIDs.

## Failure modes

- The Python cleanup helper may match unrelated commands if another process has the same random design tmpdir in argv. This is acceptable because the design tmpdir is session-unique and validation rejects broad non-design paths.
- The helper skips its own process and live ancestors through the existing `kill_session_background_processes` logic.
- A process that ignores `TERM` may survive the best-effort Python helper. Do not add SIGKILL unless tests show `TERM` is insufficient for this bug.
- If a valid historical design tmpdir lacks `source-env.sh`, the CLI rejects it. This is acceptable because normal `/design` Step 0 writes `source-env.sh` before Step 3.

## Acceptance

- `run-step3-review.sh --mode loop` disables monitor mode before sourcing the loop driver, so `dispatch-with-waterfall.sh`'s `( )&` children remain in PG_R.
- `design-step3-review.sh` calls `python3 python/cli.py session kill-background-processes --design-tmpdir "$DESIGN_TMPDIR"` after the process-group kill on both the EXIT trap path and the normal path.
- `dispatch-with-waterfall.sh` installs `trap _waterfall_kill_active_pids EXIT` and clears `pids=()` after each `collect_phase`.
- `python/cli.py session kill-background-processes --design-tmpdir PATH` exists, validates the path with design-session-specific guards, and returns `KILLED=true` or `KILLED=false` on success, `2` on validation error.
- Existing tests pass; new harness regressions added for each changed surface.
- After a complete `/design` Step 3 review, `ps aux | grep "$(basename "$DESIGN_TMPDIR")" | grep -v grep` returns no leftover orphan processes.

## Testing strategy

- Run focused shell harnesses: `make test-run-step3-review`, `make test-design-step3-review`, `make test-dispatch-with-waterfall`.
- Run Python tests: `python3 -m pytest python/test_cli.py python/test_finalize.py`.
- Run lint and relevant checks: `bash scripts/relevant-checks.sh`, `make lint-bash32`.
- Manual validation: run `/design`, after final summary run `ps aux | grep "$(basename "$DESIGN_TMPDIR")" | grep -v grep`. Expect no leftover `plan-review-loop.sh`, `run-step3-review.sh`, `dispatch-plan-voters.sh`, `dispatch-with-waterfall.sh`, `collect-agent-results.sh`, or `agent wait-reviewers` processes.

diff_lines: 250

## Test plan
(no test plan section in plan-file)
