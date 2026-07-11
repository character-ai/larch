### [rejected] FINDING_6

**Rejected subtype:** dismissed (0 YES)

### FINDING_6: Present-state reference omits the re-author-required terminal contract
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: major
- **Concern**: The guideline present-state reference does not document the validated `re-author-required` terminal envelope, no-retry behavior, reassessment routing, and no-ship constraint. Callers following the reference may reject a valid terminal result as tool failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Document the validated re-author-required reassessment branch and its no-retry and no-ship constraints.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_7: Step 8 harness lacks re-author behavioral regression coverage
- **[OUT_OF_SCOPE]**
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing, dyn-dyn-gate-authority
- **Severity**: major
- **Concern**: The Step 8 harness lacks fresh and rejoin `re-author-required` cases asserting terminal emission, preserved result and reason data, no attempt-2 retry, reassessment routing, and no ship handoff. Regressions in terminal dispatch can therefore pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Add fresh and rejoin harness cases asserting terminal `re-author-required`, no attempt-2 retry, and no ship handoff.
  - From cursor-specialist-edge-cases: Add emit-reauthor arm to the fresh loop and harness coverage for first-start terminal emit
  - From cursor-specialist-testing: Add dynamic harness cases and wire make test-step-8-assessment.
  - From codex-specialist-testing: Add fresh and rejoin fixtures asserting BGJOB_RC=0 preserved result and reason reassessment routing no retry and no ship handoff.
  - From dyn-dyn-gate-authority: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_8: Coordinator regression tests for re-author and repair paths are missing
- **[OUT_OF_SCOPE]**
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing, dyn-dyn-gate-authority
- **Severity**: major
- **Concern**: Coordinator tests do not cover re-author-required versus unavailable classification, cleanup, reason propagation, legacy metadata repair, and the requirement not to persist unavailable coverage for re-author cases.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Add the plan’s coordinator regression table to test_architectural_assessment.py
  - From cursor-specialist-testing: Add tests for re-author persistence cleanup unavailable distinction and repair metadata handling.
  - From codex-specialist-testing: Add coordinator tests for missing invalid cross-vocabulary and prose-mismatched outcomes, cleanup, reasons, and no unavailable persistence.
  - From dyn-dyn-gate-authority: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** dismissed (0 YES)

### FINDING_9: Ship routing lacks legacy metadata regression tests
- **[OUT_OF_SCOPE]**
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-gate-authority
- **Severity**: minor
- **Concern**: Ship tests do not cover legacy prose-only notes or missing, invalid, and cross-vocabulary `ASSESSMENT_KIND` metadata. Such notes could regress to handled or clean routing instead of `needs_assessment`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Add `_read_current_*` table tests for missing `ASSESSMENT_KIND`, explicit violations/deviations, and unavailable preservation boundaries.
  - From cursor-specialist-edge-cases: Add ship tests asserting needs_assessment for legacy notes missing valid outcome metadata
  - From cursor-specialist-testing: Add load_or_prepare and _read_current routing tests for missing invalid and cross-vocabulary metadata.
  - From dyn-dyn-gate-authority: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** dismissed (0 YES)

### FINDING_11: Exit code collision can misroute re-author results
- **[OUT_OF_SCOPE]**
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-gate-authority
- **Severity**: minor
- **Concern**: `EXIT_REAUTHOR_REQUIRED` shares numeric exit code 7 with `RUN_LOG_INCOMPLETE_RC`. Callers that branch only on the numeric return code may misclassify compose re-author results as run-log incompleteness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Allocate a unique exit code or require status KVs instead of numeric exit branching.
  - From cursor-specialist-edge-cases: Use a distinct exit code or require status KV parsing
  - From cursor-specialist-testing: Document distinct status tokens or assign a unique exit code if rc branching is required.
  - From dyn-dyn-gate-authority: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_12: Dead re-author exception handling remains in environment reads
- **[OUT_OF_SCOPE]**
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: `_read_env` catches `AssessmentReauthorRequired` even though the read path cannot raise it, leaving misleading dead exception handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Remove the dead except clause


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_14: Classifier alias tests are not clearly separated from ship-routing tests
- **[OUT_OF_SCOPE]**
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: Existing classifier alias tests could be mistaken for persisted-metadata ship-routing coverage, encouraging maintainers to re-wire prose classifiers into routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Relabel tests as classifier-only or add explicit routing tests that do not use classifier helpers.
Vote tally: YES=1 NO=2 JUDGE_ERROR=0
