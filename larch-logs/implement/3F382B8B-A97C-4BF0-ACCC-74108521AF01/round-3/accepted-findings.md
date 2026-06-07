### FINDING_13: Continuation helper invocation uses stale approve_requested variable
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `SKILL.md` references `approve_requested` even though only `_approve_requested` is set in the relevant shell scope, so the continuation helper can receive an empty/unbound argument and fail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_14: Gate-B-settled prose still routes directly to Step 3b
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Stale SKILL and approval-gate directions can skip the new continuation check after Gate B applies accepted findings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_16: MainAgent-required rounds can accumulate tentative accepted findings
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Findings later rejected or errored by MainAgent can remain in `accepted-plan-findings-all.md` and be reported as accepted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_17: Final summary can count findings explicitly skipped at Gate B
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `render-final-summary.sh` prefers cumulative accepted findings even after one-by-one Gate B approval skips, so skipped findings can remain in the accepted count.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_18: Continuation predicate branches lack targeted coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Small-clean convergence, non-nit continuation, and structural/HARD continuation branches lack harness coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_19: Cumulative accepted append and restore behavior lacks tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `_accumulate_round_accepted_all` and panel-failed/tally-error restore paths are not covered by behavioral tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_20: Persist-retally cumulative merge tests are not wired into relevant checks
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-bash-portability-output.txt
- **Severity**: important
- **Concern**: New `persist-retally-step3-env` merge behavior has test coverage but edits to the script are not mapped through `relevant-checks.sh` / make shard routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, dyn-bash-portability-output.txt: Address the concern above.


### FINDING_22: Continuation tier resolution uses stale workflow_path precedence
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The continuation helper can prefer `workflow_path` over canonical `design_classification` and fail to default invalid/missing classification to HARD.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_26: Tally-error rollback leaves accepted artifacts inconsistent
- **Reviewer(s)**: dyn-artifact-state-output.txt
- **Severity**: latent
- **Concern**: The `tally-error` path restores cumulative accepted findings but can leave `accepted-plan-findings.md` and `ACCEPTED_COUNT` reflecting partial failed tally output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-artifact-state-output.txt: Address the concern above.


### FINDING_6: Auto-continuation leaves Step 3 sentinel state unsafe for pause/resume
- **Reviewer(s)**: codex-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-state-machine-output.txt
- **Severity**: important
- **Concern**: Follow-up Step 3 rounds can run while `.completed/step-3` remains set and `.completed/step-3.5` absent, causing pause/resume to jump to Gate B and skip an unfinished review panel or reuse stale artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-state-machine-output.txt: Address the concern above.


### FINDING_9: Zero-findings Gate B prose bypasses continuation check
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-state-machine-output.txt
- **Severity**: important
- **Concern**: Documentation still routes zero-findings Gate B directly to Step 3b, which can skip the continuation helper for degraded zero-finding panels.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-state-machine-output.txt: Address the concern above.


