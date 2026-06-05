### FINDING_11: [OUT_OF_SCOPE] Conflict handoff is surfaced as a generic stalled outcome
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `PrePushConflictHandoff` subclasses `Stalled`, so orchestrators must infer conflict-handoff intent from persisted state rather than a distinct outcome.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_12: [OUT_OF_SCOPE] Gh-skipped local_merged treats manifest DONE as a standalone merged signal
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-resume-fsm-output.txt, dyn-state-persistence-output.txt, dyn-postmerge-idempotence-output.txt
- **Severity**: important
- **Concern**: In gh-skipped resumes, `local_merged` can classify a run as merged based on manifest `DONE` plus a PR number without requiring agreeing state such as `PR_CLOSED`, `PHASE=postmerge/done`, or post-merge `MERGE_RESULT`, allowing premature postmerge/done routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-resume-fsm-output.txt, dyn-state-persistence-output.txt, dyn-postmerge-idempotence-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_16: [OUT_OF_SCOPE] Missing no-state-file plus argv PR-number fresh-routing coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-resume-fsm-output.txt
- **Severity**: latent
- **Concern**: Tests do not cover the plan-required case where no state file exists but `ctx.pr_number` is set; the expected route is fresh checks rather than open-pr resume.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-resume-fsm-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_19: [OUT_OF_SCOPE] test_manifest_status encodes the old ctx.run_id precedence
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-resume-fsm-output.txt
- **Severity**: latent
- **Concern**: `test_manifest_status` currently expects `ctx.run_id`-only lookup behavior, so fixing `manifest_status()` to use `effective_run_id(ctx)` requires rewriting this test contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-resume-fsm-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_26: [OUT_OF_SCOPE] Normal gh.pr_view failures can reset counters through fresh fallback
- **Reviewer(s)**: dyn-state-persistence-output.txt
- **Severity**: latent
- **Concern**: A transient `gh.pr_view` failure after handback can route to fresh and reset CI counters even when branch/PR identity in state is otherwise valid.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-persistence-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_28: [OUT_OF_SCOPE] Terminal fixer handbacks may increment FIX_ATTEMPTS differently from bash
- **Reviewer(s)**: dyn-ci-cap-loop-output.txt
- **Severity**: latent
- **Concern**: `_monitor_persisted_counters()` increments `fix_attempts` for terminal handbacks such as `first-fixer-non-health`, while bash exits without bumping that counter.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-cap-loop-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_29: [OUT_OF_SCOPE] monitor.action == wait branch appears dead on the real poll_ci path
- **Reviewer(s)**: dyn-ci-cap-loop-output.txt
- **Severity**: nit
- **Concern**: The iteration-increment guard includes `monitor.action == "wait"`, but real `poll_ci()` spins until a non-wait decision, making that branch misleading outside stubs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-cap-loop-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_31: [OUT_OF_SCOPE] Some write-path state fields lack format validation
- **Reviewer(s)**: dyn-state-injection-output.txt
- **Severity**: latent
- **Concern**: Existing write validation only constrains selected fields, while fields such as `REPO`, `PR_TITLE`, `IMPLEMENT_TMPDIR`, and `MANIFEST_PATH` are written without equivalent format checks; current bash usage mitigates execution risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-injection-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_32: [OUT_OF_SCOPE] Open-pr OOS gate skip is an intentional workflow trade-off
- **Reviewer(s)**: dyn-state-injection-output.txt
- **Severity**: nit
- **Concern**: Open-pr resume deliberately bypasses OOS/security sidecar gates per plan; the reviewer framed this as a workflow-integrity trade-off rather than a new shell-injection issue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-injection-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_33: [OUT_OF_SCOPE] Positive hardening observations
- **Reviewer(s)**: dyn-state-injection-output.txt
- **Severity**: nit
- **Concern**: The reviewer noted existing hardening in this branch, including tmpdir state confinement, repo agreement checks, state value validation, conflict-file traversal checks, blocked-rebase PR_URL sanitization, and newline rejection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-injection-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_35: [OUT_OF_SCOPE] finalize.postmerge can return OK despite main verification or cleanup problems
- **Reviewer(s)**: dyn-postmerge-idempotence-output.txt
- **Severity**: latent
- **Concern**: Pre-existing `finalize.postmerge` behavior reports OK even when main verification is unexpected or cleanup is partial, which can still let callers persist `PHASE=done`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-postmerge-idempotence-output.txt: Address the concern above.

Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_6: [OUT_OF_SCOPE] _fresh_resume_plan exposes an unused counters parameter
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-resume-fsm-output.txt
- **Severity**: nit
- **Concern**: `_fresh_resume_plan()` accepts `counters` but always discards it, creating misleading API surface about whether stale counters can affect fresh routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, dyn-resume-fsm-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_9: [OUT_OF_SCOPE] Resume state lookups repeatedly reread the state file
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Resume classification performs many per-key `read_state_kv()` calls, each reparsing the full state file; this is inefficient on the hot resume path and overlaps with a broader pre-existing `read_state_kv()` design issue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

