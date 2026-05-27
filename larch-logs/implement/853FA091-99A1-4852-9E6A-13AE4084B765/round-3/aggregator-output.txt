### FINDING_1: Cap short-circuit still routes through Gate B
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Step 3 cap-reached prose says to skip Gate B, but nearby mandatory Gate B instructions and blockquote ordering can still cause the orchestrator to run Gate B or surface stale accepted-plan-findings after the cap has already been reached.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

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

### FINDING_4: timing-report duplicates classification parsing
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `scripts/timing-report.sh` has its own fallback parsing for workflow/tier resolution, including precedence that can drift from `read-design-classification.sh` and mislabel runs on hosts without JSON tooling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.

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

### FINDING_7: [OUT_OF_SCOPE] Legacy Quick heuristic mislabels report-token workflows
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The legacy Quick mode tally heuristic in `skills/report-tokens/scripts/run-analysis.sh` can force historical or malformed runs to `SIMPLE`, producing misleading token reports after Quick mode removal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

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

### FINDING_10: v1 absent-classification fallback lacks fixture coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The fallback behavior for schema version 1 or absent `design_classification` is not covered, so regressions in the expected HARD default and warning could ship unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_11: timing-ledger fallback acceptance is unresolved
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The plan/acceptance text mentions timing-ledger behavior for run-params fallback, but `scripts/timing-ledger.sh` was not changed, leaving acceptance ambiguous even if timing-report works.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] report-tokens v2 workflow_path path lacks direct test coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `run-analysis.sh` lacks a direct fixture for v2 design runs using `workflow_path`, so token report output may regress independently of timing-report behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_13: SIMPLE reviewer prompt can suppress security findings
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: SIMPLE tier emphasis biases reviewers toward EXONERATE without a security carve-out, so auth, secrets, or other security-sensitive design gaps may be dismissed as forward-looking scope creep.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_14: read-design-classification grep fallback can read decoy tier strings
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: On hosts without `python3` or `jq`, the grep fallback in `read-design-classification.sh` can match embedded or malformed JSON substrings instead of the true tier, potentially lowering review strictness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_15: Step 0b reads run-params before creating it
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Step 0b requires merging brainstorm state into `run-params.json` before the later sub-step creates the file, so already-planned brainstorm flows can incorrectly see `brainstorm_requested` as false or absent and skip brainstorm handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_16: Failed panel retries reuse round artifact paths
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Because `panel-failed` attempts do not advance the cap counter, repeated retries use the same `--round-num` and `round-N` artifact paths, allowing output overwrite and unclear retry history.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] v1 run-params tier labels can differ across readers
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: For v1 run-params, timing can label workflow via `workflow_path` while the classification reader defaults to HARD, causing inconsistent labels between timing reports and final summaries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
