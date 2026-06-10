# Review Round 3

- Mode: `diff`
- 5 accepted, 2 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Step 0 dirty-tree resume drops issue-number/bootstrap argv
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Dirty-tree resume invokes Step 0 bootstrap in resume mode without the issue-number/initial argv context needed by `implement-bootstrap.sh --resume-plan-tail`, so resumes can fail with `issue-number-required-for-resume` after tracking adoption.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Pass the same argv bundle as the initial Step 0 fence on dirty-tree resume, or have step-0-bootstrap.sh derive --issue-number from parent-issue.md when omitted.
  - From cursor-specialist-correctness-output.txt: Update SKILL prose to list required resume argv, or implement tmpdir/session auto-assembly in step-0-bootstrap.sh.
  - From cursor-specialist-edge-cases-output.txt: Hydrate ISSUE_NUMBER/TARGET_ISSUE_NUMBER from parent-issue.md (and session artifacts) inside step-0-bootstrap.sh before calling implement-bootstrap-invoke.sh.


### FINDING_11: Step 0/18 session lifecycle uses wrapper PPID instead of Claude PID
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Wrapperized Step 0 and Step 18 use transient wrapper process PPIDs for current implement session pointers, leaving stale pointers and breaking PID-keyed session lifecycle semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Preserve caller PPID at the SKILL fence boundary via LARCH_CLAUDE_PID="$PPID", do not overwrite it in step-0-bootstrap.sh, and use the same persisted/forwarded value in step-18-finalize.sh.


### FINDING_13: Step 8 Python 3.11/STALLED JSON/exit-4 contract lacks wrapper pins
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Tests no longer directly pin `step-8-ship.sh` for the Python 3.11 guard, `STALLED` JSON stdout, and exit 4 behavior, so wrapper drift could misroute stale-Python stalls.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add structure or offline harness pins (or stubbed-python invocation) asserting sys.version_info guard, STALLED JSON stdout, and exit 4 on skills/implement/scripts/step-8-ship.sh.


### FINDING_18: Step 18a stall-tracking memory flag is not exported into wrapper call
- **Reviewer(s)**: dyn-kv-relay-output.txt
- **Severity**: important
- **Concern**: The Step 18a fence passes `${STALL_TRACKING:-false}` without exporting orchestrator memory into the subprocess, so `step-18a-gate.sh` can emit `STALL_TRACKING_MEMORY=false` and skip recovery when only the memory layer is set.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-kv-relay-output.txt: Add `export STALL_TRACKING="${STALL_TRACKING:-false}"` (or pass an orchestrator-substituted literal `true`/`false`) in the fence before invoking the wrapper, and pin the behavior in `scripts/test-implement-structure.sh`.


### FINDING_6: Step 8 bash ship wrapper expands empty array under Bash 3.2 nounset
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-testing-output.txt, dyn-bash32-compat-output.txt
- **Severity**: important
- **Concern**: On the legacy `LARCH_SHIP_PR_IMPL=bash` path, `step-8-ship.sh` expands an empty `_resume_args` array under `set -u`, which aborts on macOS Bash 3.2 before `ship-pr.sh` runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Use guarded expansion "${_resume_args[@]+"${_resume_args[@]}"}" or branch the command so --resume-phase is only appended when present.
  - From codex-specialist-testing-output.txt: Use the Bash-3.2-safe ${_resume_args[@]+"${_resume_args[@]}"} expansion or branch on array emptiness, and add a regression test for empty RESUME_PHASE in bash mode.
  - From dyn-bash32-compat-output.txt: Use the repo’s established guard idiom at the call site, e.g. `"${_resume_args[@]+"${_resume_args[@]}"}"`, matching `skills/implement/scripts/step-7a.sh:430` and `skills/implement/scripts/oos-disposition-checkpoint.sh:196`; optionally add a static grep pin (like `scripts/test-collect-agent-bash32.sh` Case 1) so the safe form cannot regress.


