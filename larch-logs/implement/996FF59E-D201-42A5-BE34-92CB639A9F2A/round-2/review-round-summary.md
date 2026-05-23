# Review Round 2

- Mode: `diff`
- 9 accepted, 9 rejected (9 exonerated)

## Accepted Findings

### FINDING_1: Unused `checks-step10` branch in recovery waterfall
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: `run_recovery_waterfall` defines a `verify_kind=checks-step10` path that no caller passes; tests never hit it. Same dead arm noted as maintenance/confusion risk and as plan-fidelity dead code; risks false assumptions about step10 recovery parity with step6-style checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt: Remove the dead case arm or wire a real call site with a contract comment
  - From cursor-specialist-plan-fidelity-output.txt: Remove checks-step10 or add a real call site if step10 coverage is intended.


### FINDING_10: `usage()` omits `--failure-log` in `launch-cursor-ci.sh`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: Operators copying argv from usage-only help miss implemented flags.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Update usage string to mirror implemented argv


### FINDING_13: Missing Acceptance #12 rollback harness tests (only grep pins)
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Plan AC#12 names rollback harness cases not present in `scripts/`; structural grep can pass while rollback behavior (ordering, spaces, globs, staged restore) regresses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add recovery_waterfall_rollback_handles_paths_with_spaces_and_globs and recovery_waterfall_rollback_restores_staged_changes_via_git_restore_staged to test-ship-pr.sh
  - From cursor-specialist-plan-fidelity-output.txt: Add recovery_waterfall_rollback_handles_paths_with_spaces_and_globs and recovery_waterfall_rollback_restores_staged_changes_via_git_restore_staged to scripts/test-ship-pr.sh (or alias existing tests to those names).


### FINDING_16: Redaction pipeline fail-open: raw `head -c` on redactor failure
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Redact pipe falls back to raw `head -c` when `redact-secrets.sh` errors or is missing; up to ~4KB unredacted (or unredacted excerpt) can reach external model prompts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Fail closed: drop excerpt or substitute fixed text and surface error; do not fall back to raw bytes
  - From cursor-specialist-edge-cases-output.txt: Fail close omit excerpt or non-zero exit when redaction fails


### FINDING_20: Sourcing `ship-pr.sh` runs `larch_quiet_init` outside `main`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Sourcing without `LARCH_QUIET_DISABLE` can redirect stdout/stderr and touch disk, conflicting with strict zero side-effect wording.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Defer quiet init to main or document required env


### FINDING_21: Plan vs shipped verifier naming (`run-relevant-checks-captured.sh` vs `pr-prep-oos`)
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Pasted plan lists `run-relevant-checks-captured.sh` as pr-prep verifier; code uses `pr-prep-oos` (OOS gate); future audits may false-flag mismatch though OOS-gate rerun may match stall domain.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Reconcile plan text with shipped ship-pr.md + verify_kind naming (document OOS verifier for pr-prep explicitly).


### FINDING_3: Inconsistent stderr redirection across Cursor vs other tiers
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Cursor tier stderr is sent to `wf_log` with truncate (`2>`) while Codex/Claude append (`2>>`), making combined tier diagnostics harder to read when debugging waterfall failures and dropping earlier stderr context on Cursor failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Normalize stderr redirection across tiers
  - From cursor-specialist-testing-output.txt: Standardize on 2>> for all tiers
  - From cursor-specialist-edge-cases-output.txt: Use 2>> append like other tiers


### FINDING_4: `with_transient_retry` passes unused `fail_file` to predicates
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: `fail_file` is passed into envelope predicates but unused, so readers may assume fail-file-aware behavior that never runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Align signature and comment (drop arg or use it)


### FINDING_8: `commit_post_waterfall_checks_fix_or_stall` may miss untracked-only recovery work
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: Uses `git diff` without untracked detection; if recovery produces only untracked fixes, both diffs can be quiet, function returns 0 without add/commit/push, phase advances with dirty tree and no failure record.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Use git status --porcelain (or existing dirty capture) for early-out; only skip when truly clean


