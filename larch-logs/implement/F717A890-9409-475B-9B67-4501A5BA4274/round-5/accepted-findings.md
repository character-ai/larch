### FINDING_1: manifest_status reads manifests from ctx.run_id instead of effective_run_id
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-resume-fsm-output.txt, dyn-state-persistence-output.txt, dyn-ci-cap-loop-output.txt
- **Severity**: important
- **Concern**: `manifest_status()` resolves and validates the manifest path using `ctx.run_id` instead of `effective_run_id(ctx)`, so resumes where persisted state `RUN_ID` differs from argv `ctx.run_id` can miss or read the wrong manifest and misroute gh-skipped merged/open-pr/done handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-resume-fsm-output.txt, dyn-state-persistence-output.txt, dyn-ci-cap-loop-output.txt: Address the concern above.


### FINDING_13: Missing ITERATION=50 non-pass cap stall coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Tests do not cover the plan-required case where an open-pr resume at `ITERATION=50` receives a wait/non-pass monitor outcome and should stall after monitor handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_14: Missing two-invocation terminal counter round-trip coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Tests do not verify that counters persisted across an exit-3/exit-6 handback survive a second `run_ship()` invocation and are reused on the next monitor entry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_15: Missing open-pr resume coverage with leftover OOS artifacts
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Tests do not cover open-pr resume when OOS/security sidecar artifacts are present, so accidental re-enabling of OOS gates on open-pr resume would not be caught.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_17: Missing two-invocation blocked-rebase marker preservation coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Tests do not verify that blocked-rebase continuation markers such as `RESUME_PHASE`, `CALLER_KIND`, and counters remain intact across a second refusal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_18: Missing transient_rerun_attempted counter persistence coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Tests do not cover terminal handback with `transient_rerun_attempted=True`, leaving `TRANSIENT_RETRIES` persistence unverified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_22: Additional plan-mandated resume acceptance scenarios are missing
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Beyond separately identified gaps, the plan-fidelity review reports missing acceptance coverage for invalid PR identity fresh routing, stale merged flags routing OPEN, and repo-unavailable identity preservation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_25: RUN_ID is not hydrated from persisted state before rewriting state
- **Reviewer(s)**: dyn-state-persistence-output.txt
- **Severity**: important
- **Concern**: `_write_ship_state()` writes `RUN_ID=ctx.run_id`, while resume hydration does not restore `run_id` from state, so a resumed write can overwrite the persisted session `RUN_ID` with stale argv data.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-persistence-output.txt: Address the concern above.


### FINDING_27: CI loop increments ITERATION for fix-only and transient-rerun paths
- **Reviewer(s)**: dyn-ci-cap-loop-output.txt
- **Severity**: important
- **Concern**: Python increments `iteration` for `monitor.did_fixing` and `monitor.transient_rerun_attempted`, while bash only bumps `ITERATION` on rebase-consuming paths, potentially hitting iteration caps earlier than bash parity allows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-cap-loop-output.txt: Address the concern above.


### FINDING_34: Merged-resume path can write PHASE=done after skipped postmerge
- **Reviewer(s)**: dyn-postmerge-idempotence-output.txt
- **Severity**: important
- **Concern**: The merged resume path writes `PHASE=done` whenever `run_postmerge_phase` returns OK, but `finalize.postmerge` can return OK for `merge=false` without substantive postmerge work, allowing incomplete runs to be marked done.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-postmerge-idempotence-output.txt: Address the concern above.


