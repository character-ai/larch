### FINDING_1: `set -m` failure leaves process-group kill guarantees unverified
- **Reviewer(s)**: Cursor-Arch, Cursor-dyn-process-tree-guard, Cursor-dyn-bash-compatibility
- **Severity**: important
- **Concern**: The plan enables `set -m` so `kill -- -"$_loop_pid"` can reach dispatch-spawned reviewer grandchildren, but does not detect when monitor mode silently fails. In non-interactive Bash (including Claude Code), a failed `set -m` can leave backgrounded `run-step3-review.sh` and its descendants in the parent process group, so group SIGTERM may only hit the direct child while Cursor/Codex reviewers keep running after wrapper exit. The repo already documents this failure mode in `validate-citations.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Mirror the validate-citations pattern: `set -m 2>/dev/null || true`, branch on `$?`, emit a visible WARN when monitor mode failed, and document that orphan-prevention is degraded (or fall back to killing the direct child PID plus `pkill -P` only on that branch).
  - From Cursor-dyn-process-tree-guard, Cursor-dyn-bash-compatibility: After set -m, assert monitor mode is active (case $- in *m*) and warn or fail closed when it is not, matching the validate-citations pattern


### FINDING_3: Normal completion path disarms cleanup before final process-group teardown
- **Reviewer(s)**: Codex-Innovation, Codex-Pragmatic, Codex-dyn-bash-compatibility
- **Severity**: important
- **Concern**: The proposed normal path runs `wait "$_loop_pid"`, captures `_plan_review_rc`, then clears `_loop_pid` and disables the EXIT trap without a final `kill -- -"$_loop_pid"`. `wait` reaps only `run-step3-review.sh`; if an external reviewer grandchild survives in the same process group after the loop reports `complete` or `degraded-empty-collector`, the wrapper can emit task completion while descendants continue modifying `plan.txt` and session artifacts. This preserves the post-completion mutation class the bug fix is meant to close.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add a final best-effort process-group kill after wait returns and before _loop_pid is cleared, or keep the EXIT trap armed until wrapper exit so kill -- -"$_loop_pid" still runs on the normal completion path
  - From Codex-Pragmatic: After capturing _plan_review_rc, kill the process group before setting _loop_pid empty and clearing the trap. Or factor cleanup so the normal path and EXIT path both terminate -"$_loop_pid" before the wrapper can complete.
  - From Codex-dyn-bash-compatibility: Run `kill -- -"$_loop_pid" 2>/dev/null || true` after capturing `_plan_review_rc` and before clearing `_loop_pid` or the trap, then restore monitor mode. Keep the existing cleanup trap for premature exits.


### FINDING_6: `make lint` demoted to optional despite acceptance criteria requiring it
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: Issue acceptance criteria require `make lint` to pass, but the plan's testing strategy lists `make lint` under optional "if time permits" wording. An implementer can follow the plan, skip full lint, and leave the change unverifiable against stated acceptance criteria.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Elevate make lint to a required post-change check alongside bash scripts/relevant-checks.sh not an optional if-time-permits step
  - From Codex-Requirements: Move `make lint` into the required testing section, not the time-permits section; keep or replace `bash scripts/relevant-checks.sh` as needed.




### FINDING_1: Structure pin conflicts with parameterized teardown kill helper
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements
- **Severity**: important
- **Concern**: The structure pin requires a literal `kill -- -"$_loop_pid"` substring, but the plan routes kills through a parameterized teardown helper using `kill -- -"$_pid"`. A correct implementation following the helper abstraction may fail `assert_wrapper_contract_pins`, or implementers may add a redundant inline kill only to satisfy CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Pin kill -- -" or the teardown helper function name; or require both the helper definition and a post-wait call that passes $_loop_pid
  - From Cursor-Requirements: Change the pin to match the helper (e.g. kill -- -"$_pid") or pin a call-site pattern; drop the _loop_pid-only kill needle if kills live only in the helper


### FINDING_3: Monitor-mode pre-launch abort leaves stale Step 3 result envelope
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: When monitor-mode pre-launch aborts because `set -m` cannot be verified, the plan exits before starting `run-step3-review.sh` but leaves the existing `read-result-env` handoff unchanged. Orchestrator Step 3 is file-first on `$DESIGN_TMPDIR/.step3-review-result.env` after the background task returns, so a stale envelope from an earlier partial or orphan loop can be replayed as complete/degraded-empty-collector even though no loop ran.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Before exiting on monitor-mode failure, overwrite .step3-review-result.env with a fresh panel-failed envelope (STEP3_REVIEW_LOOP_STATUS=panel-failed LOOP_STATUS=panel-failed) and print the same KVs to stdout; optionally rm stale round phase files when aborting pre-launch




### FINDING_1: Pre-launch monitor-mode abort must exit 0 with panel-failed envelope
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements
- **Severity**: important
- **Concern**: The plan requires a pre-launch panel-failed envelope when monitor mode is unavailable, but does not pin the wrapper exit status. Terminal panel-failed and degraded-empty-collector loop outcomes today exit 0 after emitting `STEP3_REVIEW_LOOP_STATUS` / `LOOP_STATUS` KVs so SKILL.md can route through gate-b-bypass to Step 3b. If the implementer exits 1 on the monitor-mode pre-launch abort path, the background task looks like a wrapper hard failure instead of the existing terminal short-circuit, and `/design` may skip or mishandle the gate-b-bypass → Step 3b → Step 4 path even though no loop child was started.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Pin pre-launch monitor-mode failure to exit 0 after writing and printing the panel-failed envelope, matching the existing post-loop panel-failed path
  - From Cursor-Requirements: Spell out in the plan that the monitor-mode pre-launch abort path must exit 0 after writing/printing STEP3_REVIEW_LOOP_STATUS=panel-failed and LOOP_STATUS=panel-failed (and REASON=monitor-mode-unavailable), matching other terminal loop failures; reserve exit 1 for postplan-failed and run-step3-review rc=2 only.



