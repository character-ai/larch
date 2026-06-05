### FINDING_10: Blocked rebase continuation can be preempted by REPO validation
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `RESUME_PHASE=ship-pr-rrr-phase14` with a repo mismatch can route to `STALLED` instead of the unsupported-continuation / user-input handback expected for blocked rebase continuation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_11: Terminal monitor handbacks may not persist consumed fix/rebase counters
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-cap-loop-output.txt
- **Severity**: important
- **Concern**: Terminal non-OK monitor exits can omit increments for consumed fixing/rebase work, allowing later invocations to under-count session-wide budgets.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-cap-loop-output.txt: Address the concern above.


### FINDING_19: Merge retry outcomes consume iteration budget unlike bash
- **Reviewer(s)**: dyn-cap-loop-output.txt
- **Severity**: important
- **Concern**: `ci_not_ready` and `main_advanced` merge results increment the Python loop iteration and can hit the cap, while bash retries those paths without consuming `ITERATION`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cap-loop-output.txt: Address the concern above.


### FINDING_2: Merge loop pre-stalls at iteration cap before observing CI/GitHub state
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-resume-state-output.txt, dyn-github-authority-output.txt, dyn-cap-loop-output.txt
- **Severity**: important
- **Concern**: The merge loop checks `iteration >= cap` before calling `ci_monitor.monitor()`, so an open-PR resume at the cap can stall without observing pass/already-merged outcomes that should still succeed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-resume-state-output.txt, dyn-github-authority-output.txt, dyn-cap-loop-output.txt: Address the concern above.


### FINDING_21: Manifest status can trust state `RUN_ID` during resume routing
- **Reviewer(s)**: dyn-statefile-hardening-output.txt
- **Severity**: important
- **Concern**: Resume routing can treat manifest status as authoritative through `effective_run_id()`, which prefers untrusted state `RUN_ID`; a tampered state file could point at another manifest and skip postmerge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-statefile-hardening-output.txt: Address the concern above.


### FINDING_23: Resumed string fields are re-persisted without value-level validation
- **Reviewer(s)**: dyn-statefile-hardening-output.txt
- **Severity**: important
- **Concern**: `BRANCH_NAME`, `PR_URL`, and `MERGE_RESULT` can be hydrated and rewritten from state with only newline rejection, increasing risk when bash later consumes the same state keys.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-statefile-hardening-output.txt: Address the concern above.


### FINDING_3: Fresh resume paths preserve stale counters while CI locals reset to zero
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-resume-state-output.txt, dyn-github-authority-output.txt, dyn-state-persistence-output.txt
- **Severity**: important
- **Concern**: Fresh fallback paths can carry persisted nonzero counters into state writes even though the CI loop seeds local counters to zero, causing inconsistent state and inflated budgets on later resumes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-resume-state-output.txt, dyn-github-authority-output.txt, dyn-state-persistence-output.txt: Address the concern above.


### FINDING_6: Open-PR resume OOS handling is inconsistent and may either rerun or skip gates incorrectly
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Reviewers disagree on the intended open-PR OOS policy, but the shared risk is that resume behavior is ambiguous: `OOS_PENDING=true` can re-enter OOS helpers despite skip-OOS expectations, while `OOS_PENDING=false` can skip remaining OOS/security artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_7: `_resume_plan` raises on invalid REPO instead of returning a structured safe route
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, dyn-resume-state-output.txt
- **Severity**: latent
- **Concern**: Invalid or mismatched persisted `REPO` can raise `ShipError` and surface as `STALLED`, unlike other corrupt-state paths that degrade through structured resume outcomes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, dyn-resume-state-output.txt: Address the concern above.


### FINDING_9: Normal-repo done resume is gated on manifest status despite GitHub MERGED + PHASE=done
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-resume-state-output.txt, dyn-github-authority-output.txt
- **Severity**: important
- **Concern**: For normal repos, `MERGED` with matching head and `PHASE=done` can rerun postmerge unless the manifest also says done, violating idempotent done-routing expectations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-resume-state-output.txt, dyn-github-authority-output.txt: Address the concern above.


