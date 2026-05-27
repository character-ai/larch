### FINDING_1: `.done` barrier runs after voter status is already frozen
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Codex-Edge, Codex-Innovation, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Codex-dyn-contract-drift
- **Severity**: important
- **Concern**: The planned wait-for-reviewers barrier is placed after `dispatch-code-voters.sh` has already classified voter outputs with `[[ -s "$VOTER_*_PATH" ]]`. If an output becomes visible only during or after the `.done` wait, the voter remains marked failed and parse-rate/tally logic still runs with stale status.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Move the wait (or add a second pass) before status assignment, or re-evaluate `VOTER_*_STATUS` from `-s` after sentinels are present.
  - From Codex-Arch: Move the wait immediately after VOTER_*_PATH and VOTER_*_TOOL are assigned and before any -s status checks, or recompute statuses after the wait; add a test where output appears after the initial status point
  - From Codex-Edge: Move the wait barrier before any status assignment that reads voter output size, or re-run the VOTER_*_STATUS -s checks after the barrier before parse-rate starts
  - From Codex-Innovation: Move the wait_sentinels barrier before the -s based status assignments, or recompute all voter statuses after the wait before parse-rate checks
  - From Codex-Pragmatic: Move the wait barrier before the `[[ -s "$VOTER_*_PATH" ]] || VOTER_*_STATUS="failed"` checks, or recompute all size-based statuses after the wait
  - From Cursor-Requirements: Move the wait block to immediately after waterfall output is parsed (~line 196) and before any STATUS=-s assignments; or re-run the STATUS=-s and effective_judges logic after a successful wait
  - From Codex-Requirements: Move the wait immediately after `VOTER_*_PATH`/`VOTER_*_TOOL` binding and before any `-s` status checks, or recompute all status values after the wait.
  - From Codex-dyn-contract-drift: Move the wait immediately after paths are known and before any -s status/read checks, or recalculate VOTER_*_STATUS after the wait completes

### FINDING_2: wait-for-reviewers timeout records are discarded
- **Reviewer(s)**: Codex-Arch, Cursor-Edge, Codex-Edge, Cursor-Innovation, Codex-Innovation, Cursor-dyn-contract-drift, Codex-dyn-contract-drift, Codex-dyn-test-probe-validity
- **Severity**: important
- **Concern**: The proposed caller checks only `wait-for-reviewers.sh` exit status while redirecting stdout/stderr away, but normal sentinel timeouts are reported as `TIMEOUT` rows on stdout and still exit 0. Timeout warnings therefore never fire, and missing sentinels become silent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Capture wait-for-reviewers stdout/stderr using the collect-agent-results.sh pattern, parse TIMEOUT rows, and log the timed-out sentinel names while still proceeding
  - From Cursor-Edge: Capture stdout (e.g. `_wait_out=$("$PLUGIN_ROOT/scripts/wait-for-reviewers.sh" ...)`), grep for `^TIMEOUT ` and emit `larch_err` per missing sentinel; drop the `_wait_rc != 0` timeout comment or restrict it to usage errors (exit 1).
  - From Codex-Edge: Capture wait-for-reviewers.sh stdout, parse TIMEOUT records like collect-agent-results.sh does, and log those records before proceeding
  - From Cursor-Innovation: Capture stdout to a temp file (or pipe through grep) and treat any TIMEOUT line as the warning path; align dispatch-code-voters.md with wait-for-reviewers.md contract instead of documenting exit-code failure
  - From Codex-Innovation: Capture wait-for-reviewers stdout, grep for TIMEOUT records, and larch_err those records before continuing
  - From Cursor-dyn-contract-drift: Align prose: timeouts are exit 0; detect via missing .done after wait or by capturing stdout and grepping TIMEOUT (collect-agent-results pattern). Drop or repurpose (( _wait_rc != 0 )) to usage-error-only messaging; document timeout warning in dispatch-code-voters.md accordingly
  - From Codex-dyn-contract-drift: Capture wait-for-reviewers stdout, scan for ^TIMEOUT, and log that; handle rc=1 separately as a usage/config error, and update prose to stop saying timeout returns nonzero
  - From Codex-dyn-test-probe-validity: Have dispatch capture wait-for-reviewers stdout, detect TIMEOUT records, and log them while preserving non-fatal behavior; add a timeout-path test so the barrier cannot pass trivially

### FINDING_3: stdin redirect coverage misses run-external-agent branches and may use a weak probe
- **Reviewer(s)**: Codex-Arch, Codex-Pragmatic, Codex-Requirements, Codex-dyn-test-probe-validity
- **Severity**: important
- **Concern**: The plan requires Codex stdin redirection across all run-external-agent spawn modes, but the proposed or listed tests mostly exercise the default voter path and may not detect inherited stdin reliably. `--capture-stdout`, `--capture-stdout-only`, and file-list coverage can remain untested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add direct scripts/test-run-external-agent.sh cases for TOOL_NAME=codex across default, --capture-stdout, and --capture-stdout-only, plus a cursor control proving non-Codex stdin behavior is unchanged
  - From Codex-Pragmatic: Add `scripts/test-run-external-agent.sh` to the modified files and include direct stdin-probe cases for default, `--capture-stdout`, and `--capture-stdout-only` with `--tool codex`, plus a non-Codex control preserving current behavior
  - From Codex-Requirements: Add `test-run-external-agent.sh` cases that probe fd 0 for Codex in default, `--capture-stdout`, and `--capture-stdout-only` modes; include a non-Codex control proving cursor/other tools still inherit stdin.
  - From Codex-dyn-test-probe-validity: Force the wrapper stdin to a temp file or FIFO in the test, have the child command record fd 0 without relying on ambient stdin, and assert it becomes /dev/null only after the production redirect; cover default, --capture-stdout, and --capture-stdout-only
  - From Codex-dyn-test-probe-validity: Add scripts/test-run-external-agent.sh and its sibling md to the Files to modify/create list, then add direct stdin redirect regression cases for every changed spawn branch

### FINDING_4: delayed `.done` regression test targets the wrong launcher layer
- **Reviewer(s)**: Codex-Edge, Codex-Innovation, Codex-Pragmatic, Codex-Requirements, Codex-dyn-contract-drift, Cursor-dyn-test-probe-validity, Codex-dyn-test-probe-validity
- **Severity**: important
- **Concern**: The proposed Claude delayed-`.done` test cannot create the intended dispatcher race because launcher scripts own final output publication and `.done` creation/backfill. A raw `claude` stub may delay both output and sentinel, or be masked by launcher behavior, so the test can pass without proving the barrier works.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Stub the launcher or wait-for-reviewers boundary for this regression, or add a run-external-agent-focused fixture whose wrapper-owned sentinel publication is actually delayed; assert the dispatcher waits before status/read consumption
  - From Codex-Innovation: Use an existing launcher test hook or a focused wait-for-reviewers/dispatch-code-voters fixture that directly creates output and delayed sentinel files, and set WAIT_FOR_REVIEWERS_POLL_INTERVAL low for the harness
  - From Codex-Pragmatic: Test the barrier by shim-driving the dispatcher boundary instead, for example set `CLAUDE_PLUGIN_ROOT` to a fixture whose `scripts/dispatch-with-waterfall.sh` returns an output path before a background writer creates `<path>.done`, then assert `dispatch-code-voters.sh` waits before classification and parse-rate
  - From Codex-Requirements: Add a deterministic test hook or injectable launcher shim that delays between final output publication and `.done`, then assert the new dispatcher barrier fails on main and passes after the fix.
  - From Codex-dyn-contract-drift: Implement the race test at the launcher layer or use a supported post-inner-done hook on an external path; ensure the test fails on main before the production fix
  - From Cursor-dyn-test-probe-validity: Simulate the race on voter 2 or 3 (codex/cursor): use LARCH_ALLOW_TEST_HOOKS=1 plus LARCH_TEST_TRAP_AFTER_INNER_DONE_FILE (scripts/launch-review.sh:985-989) to delay public .done after output is visible, or stub launch-claude-review.sh like scripts/test-dispatch-plan-voters.sh:58-86. Assert wait-for-reviewers blocks until .done exists.
  - From Codex-dyn-test-probe-validity: Specify a test seam that returns control to dispatch with a non-empty voter output and no .done file, then creates .done after a known delay; assert dispatch exits after the sentinel write using explicit start/end timestamps and mtime comparisons

### FINDING_5: arithmetic `&&` check can trip `set -e`
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The proposed `(( _wait_rc != 0 )) && larch_err` pattern can return status 1 on the normal zero-exit path. Under `set -e`, that may abort `dispatch-code-voters.sh` before parse-rate or tally.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Replace with if (( _wait_rc != 0 )); then larch_err "..."; fi (or append || true to the arithmetic test)

### FINDING_6: run-external-agent stdin implementation method is internally contradictory
- **Reviewer(s)**: Cursor-dyn-impl-method-conflict, Codex-dyn-impl-method-conflict
- **Severity**: important
- **Concern**: The plan gives incompatible prescriptions for Codex stdin redirection: helper-level policy or string-variable redirection versus direct per-branch shell redirection. The capture-stdout-only branch is especially ambiguous because it has inner spawn arms that must preserve existing capture behavior while applying `< /dev/null`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-impl-method-conflict: Treat **Implementation Approach (plan.txt:17)** as authoritative. Reconcile Changes bullets 1–2 to match: at `scripts/run-external-agent.sh:206-212`, use three parallel `case "$TOOL_NAME" in codex)` blocks; for the elif branch call `_launch_capture_stdout_only "$@" < /dev/null` (or add `< /dev/null` on **both** spawn lines inside the helper at :199 and :201 if the helper is the single spawn site—pick one, document it, delete “modify helper to accept policy”).
  - From Codex-dyn-impl-method-conflict: Make the direct shell redirection pattern authoritative. Delete the _codex_stdin_redirect_args variable language and specify case "$TOOL_NAME" in codex) ... < /dev/null ... ;; *) ... ;; esac at the actual spawn sites.
  - From Codex-dyn-impl-method-conflict: State the authoritative structure explicitly: either update _launch_capture_stdout_only so both its stdbuf and non-stdbuf spawn arms apply '< /dev/null' for TOOL_NAME=codex, then call it unchanged from the outer CAPTURE_STDOUT_ONLY branch, or factor a shared spawn helper that preserves the existing capture redirections. Add run-external-agent tests for default, --capture-stdout, and --capture-stdout-only, including the stdbuf-enabled capture-only arm.
