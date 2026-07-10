### [rejected] FINDING_4

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_4: Closure baseline does not have a verified live-scan parity check
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: The committed closure baseline can disagree with the live `scan_skill` classification, producing misleading eager/conditional closure reports. The baseline should be regenerated from the live scan and checked for file-set parity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Regenerate baseline from live scan and add test asserting baseline file sets match scan_skill for split references.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_5: Preview contract is not pinned by the structure harness
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-load-closure
- **Severity**: minor
- **Concern**: The structure harness verifies runtime-before-entry ordering but does not pin the preview-contract strings moved into `plan-review-runtime.md`. The Plan Candidate header, `--variant step3`, summary-mode behavior, and show-full-plan operator path could drift without CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Add contains probes on PLAN_REVIEW_RUNTIME_MD for preview authority strings named in the plan.
  - From cursor-specialist-edge-cases: Add contains probes on PLAN_REVIEW_RUNTIME_MD for Plan Candidate header, --variant step3, summary-mode note, and show-full-plan operator path.
  - From dyn-dyn-load-closure: Add `contains` probes on `PLAN_REVIEW_RUNTIME_MD` for those literals (matching the plan’s acceptance pins) alongside the existing Step 3 load-order check.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0
