## Goal
Implement issue #4178: [IMPLEMENTING] [BUG] (URGENT) design-step3-review.sh exits without killing run-step3-review.sh: orphan loop modifies plan.txt post-completion.

## Implementation Plan
## Plan

Use the approved narrow fix with the accepted reviewer hardening.

- Keep the Step 3 review wrapper as the owner of `run-step3-review.sh --mode loop`.
- Launch that loop in the background from `design-step3-review.sh`.
- Enable job control before launch so the loop gets its own process group.
- Verify monitor mode is active before launching.
- Fail closed before launch if monitor mode cannot be enabled and verified.
- Treat pre-launch monitor-mode failure as a terminal panel failure, not a wrapper hard failure.
- Exit 0 after writing and printing the pre-launch `panel-failed` envelope.
- Reserve non-zero wrapper exits for existing hard-failure paths, including postplan failure and `run-step3-review.sh` rc 2 handling.
- Before any pre-launch abort, overwrite the Step 3 result envelope so a stale `.step3-review-result.env` cannot be replayed.
- Capture `_loop_pid=$!`.
- Install an `EXIT` trap that kills the loop process group if the wrapper exits before cleanup completes.
- `wait "$_loop_pid"` and capture `_plan_review_rc`.
- After `wait` returns, run a final best-effort process-group kill before clearing `_loop_pid`.
- Clear the trap and restore monitor mode only after the final teardown.
- Leave `run-step3-review.sh` unchanged.

## Files to modify/create

### UPDATED: skills/design/scripts/design-step3-review.sh

Replace the current synchronous `run-step3-review.sh` block with a guarded background launch.

Implement near the existing `set +e` region:

- Add `_loop_pid=""`.
- Record whether monitor mode was already enabled with `case $- in *m*) ...`.
- Add `_step3_review_monitor_enabled_by_wrapper=0`.
- Add a helper that writes a fresh pre-launch failure result envelope:
  - overwrite the same result-env file later consumed by `read-result-env`, normally `$DESIGN_TMPDIR/.step3-review-result.env`
  - include `STEP3_REVIEW_LOOP_STATUS=panel-failed`
  - include `LOOP_STATUS=panel-failed`
  - include a concrete reason, preferably `REASON=monitor-mode-unavailable` if compatible with the existing envelope grammar
  - print the same required KVs to stdout before exiting
  - do not leave any stale result envelope from an earlier partial or orphan loop in place
  - exit 0 after writing and printing the envelope
- If monitor mode was not already enabled:
  - run `set -m 2>/dev/null`
  - capture the rc
  - verify active monitor mode with `case $- in *m*)`
  - set `_step3_review_monitor_enabled_by_wrapper=1` only when the flag is active
- If monitor mode is still not active:
  - emit a visible error or warning that process-group isolation is unavailable
  - call the pre-launch failure envelope helper
  - terminate the wrapper with exit 0 after the helper writes and prints the panel-failed KVs
  - do not launch `run-step3-review.sh`
  - do not continue in a degraded mode that can orphan reviewer descendants
- Define a small teardown helper before launch:
  - accept the loop pid
  - if non-empty, send `kill -- -"$_pid" 2>/dev/null || true`
  - suppress missing-process failures
- Define a small cleanup function before launch:
  - capture `$?`
  - disable its own `EXIT` trap
  - if `_loop_pid` is non-empty, call the teardown helper for `$_loop_pid`
  - `wait "$_loop_pid" 2>/dev/null || true` to reap when possible
  - restore `set +m` only if the wrapper enabled monitor mode
  - exit with the original rc
- Install `trap _step3_review_cleanup EXIT`.
- Start `run-step3-review.sh` with the existing argv and stdout redirection, but append `&`.
- Set `_loop_pid=$!`.
- Keep the existing `set +e` / `set -e` behavior around the wait.
- `wait "$_loop_pid"` and assign `_plan_review_rc=$?`.
- Immediately call the teardown helper for `$_loop_pid`.
- Only after that:
  - set `_loop_pid=""`
  - clear the trap
  - restore monitor mode if the wrapper enabled it

Keep existing behavior intact:

- Preserve `--starting-round "$STARTING_ROUND"` forwarding.
- Preserve `$_plan_review_stdout_file` capture.
- Preserve rc 2 handling after the loop has actually launched.
- Preserve existing post-loop `panel-failed` and `degraded-empty-collector` behavior.
- Preserve result env parsing and emitted KVs.
- Preserve the gate-b-bypass path through Step 3b and Step 4 for terminal loop failures.
- Preserve existing stdout and stderr contracts.

### UPDATED: scripts/test-design-structure.sh

Add structure pins in `assert_wrapper_contract_pins`.

Pin the wrapper contract with `contains` checks for:

- `_loop_pid=`
- `set -m 2>/dev/null`
- `case $- in *m*)`
- `trap _step3_review_cleanup EXIT`
- `wait "$_loop_pid"`
- the teardown helper definition or name
- `kill -- -"$_pid"`
- a teardown call that passes `$_loop_pid`
- `STEP3_REVIEW_LOOP_STATUS=panel-failed`
- `LOOP_STATUS=panel-failed`
- `monitor-mode-unavailable`
- an exit-0 path for the pre-launch monitor-mode failure envelope

Do not pin a literal `kill -- -"$_loop_pid"` if the implementation uses a parameterized teardown helper. The structure test should verify the helper kills a supplied pid's process group and that the wrapper passes `_loop_pid` to that helper.

Add labels that explain the orphan-prevention, stale-envelope, and terminal-status invariants, for example:

- `Step 3 review wrapper missing loop pid capture`
- `Step 3 review wrapper missing monitor-mode verification`
- `Step 3 review wrapper missing process-group kill trap`
- `Step 3 review wrapper missing loop wait`
- `Step 3 review wrapper missing final process-group teardown`
- `Step 3 review wrapper missing pre-launch panel-failed envelope`
- `Step 3 review wrapper may replay a stale result envelope`
- `Step 3 review wrapper monitor-mode failure must exit 0`

Do not add a behavioral integration test that launches real Cursor or Codex reviewers.

## Edge cases

- **Monitor mode activation failure:** overwrite the Step 3 result envelope with a fresh `panel-failed` envelope, print matching KVs, then exit 0 before launching the loop.
- **Stale result envelope:** a pre-launch abort must not leave an old `.step3-review-result.env` that can be read as success or degraded completion.
- **Early wrapper exit after launch:** the `EXIT` trap kills the loop process group.
- **Config error rc 2:** the wrapper still waits for the loop, performs final teardown, captures rc 2, then follows the existing abort path.
- **Normal completion:** the wrapper reaps the loop, then still sends a final best-effort kill to the loop process group before parsing results.
- **Existing monitor mode:** restore only if this wrapper enabled it.
- **Launch failure before `_loop_pid` is set:** cleanup sees an empty pid and does not call `kill`.
- **Grandchildren in the loop process group:** `kill -- -"$_pid"` targets the process group, not only the direct child.
- **Process group already gone:** suppress `kill` failures with `|| true`.
- **Children that call `setsid`:** out of scope per the approved non-goal.

## Failure modes

- If `run-step3-review.sh` starts descendants in a different process group or session, this fix may not kill them.
- If monitor mode cannot be enabled in the current Bash environment, Step 3 review now exits 0 with a fresh `panel-failed` envelope before launch instead of risking an orphan.
- If a trap runs after the loop has already exited, `kill` may fail with no such process. Suppress that with `|| true`.
- If the pre-launch failure envelope omits required existing keys, the orchestrator may mishandle the abort. Reuse the existing result-env grammar where possible and include the required `panel-failed` loop status keys.
- If the pre-launch monitor-mode failure exits non-zero, `/design` may treat it as a wrapper hard failure instead of the existing gate-b-bypass terminal loop path.

## Testing strategy

Run targeted checks first:

- `bash -n skills/design/scripts/design-step3-review.sh`
- `bash scripts/test-design-structure.sh`
- `bash skills/design/scripts/test-step3-orchestrator-fence.sh`

Then run the repository-required check:

- `bash scripts/relevant-checks.sh`

If time permits, run:

- `make lint`

## Acceptance

- All acceptance criteria from issue #4178 are met.
- After `design-step3-review.sh` exits for any reason (complete, degraded-empty-collector, cap-reached, panel-failed, monitor-mode-unavailable), no child subprocess of the wrapper survives.
- `plan.txt` and session artifacts are not modified after the `<task-notification>`.
- Structure-test pins in `test-design-structure.sh` confirm the kill/wait pattern.
- `make lint` passes.

diff_added: 80
diff_deleted: 12
diff_lines: 92

## Test plan
(no test plan section in plan-file)
