### FINDING_1: Cap short-circuit still routes through Gate B
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Step 3 cap-reached prose says to skip Gate B, but nearby mandatory Gate B instructions and blockquote ordering can still cause the orchestrator to run Gate B or surface stale accepted-plan-findings after the cap has already been reached.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_11: timing-ledger fallback acceptance is unresolved
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The plan/acceptance text mentions timing-ledger behavior for run-params fallback, but `scripts/timing-ledger.sh` was not changed, leaving acceptance ambiguous even if timing-report works.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_15: Step 0b reads run-params before creating it
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Step 0b requires merging brainstorm state into `run-params.json` before the later sub-step creates the file, so already-planned brainstorm flows can incorrectly see `brainstorm_requested` as false or absent and skip brainstorm handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_2: Review-round counter no longer increments on every Step 3 entry
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The review-round counter is persisted only after a successful panel, not on each Step 3 entry as the plan and acceptance text require. Panel dispatch failures can therefore be retried indefinitely without advancing toward the SIMPLE/HARD cap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_3: Review-round counter persists after tally errors
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The counter write excludes only `panel-failed`, so `tally-error`, empty status, or other non-success states can still consume a capped review round even though Gate B artifacts may be incomplete or degraded.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_5: Cap breadcrumb text drifts across docs
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The cap-reached breadcrumb/message differs between `SKILL.md` and `approval-gates.md`, so operators and harnesses may not reliably identify the same cap guard behavior across Step 3 and Gate C documentation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_6: plan-review-loop doc assigns cap ownership to the wrong place
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `plan-review-loop.md` says Gate C owns cap enforcement, which contradicts the intended model where Step 3 owns counter writes, Gate C reads for UI, and the loop script remains stateless.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_8: Step 3 cap behavior lacks executable harness coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The Step 3 review-round cap contract is enforced mostly through prose/Bash orchestration, so regressions such as double increments, failed-panel consumption, or skipped Gate B behavior may not fail lint.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_9: invoke-plan-validator wrapper lost direct test coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: After deleting the prior invoke harness, `skills/design/scripts/invoke-plan-validator.sh` can break while other SKILL pins and driver tests still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


