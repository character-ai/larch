### [Plan Review] FINDING_1

### FINDING_1: Apply waiver before pre-PR flush
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: Waived unavailable assessment sidecars may be committed before `operator_waived` is applied, leaving run logs without the required waiver audit trail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Load the validated waiver inside the pre-PR gate path, stamp operator_waived on waived unavailable sidecars before _flush_guideline_outcome_before_pr, and add a test that asserts the flushed run-log batch contains operator_waived.
  - From Cursor-Pragmatic: Load the validated waiver before composing gates; write `operator_waived: true` into waived unavailable sidecars before any `_flush_guideline_outcome_before_pr` call, or defer the pre-PR flush until after waiver application when the gate will proceed
  - From Cursor-Requirements: Load and apply a valid waiver before gate flush on the resume path: mark waived unavailable sidecars (or write waiver-aware outcomes) before `_flush_guideline_outcome_before_pr`, or re-flush immediately after marking. Pin ordering in `test_ship.py`.


### [Plan Review] FINDING_3

### FINDING_3: Add a named committed recovery replay
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements
- **Severity**: major
- **Concern**: The testing strategy lacks a committed regression covering the operator-bail, waiver, postmerge, and reconciliation failure chain.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add a named test in test_ship.py or test_ship_recovery.py that stubs ship through postmerge after waiver and asserts merged terminal state, manifest done with pr_number, and summary-final.md outcome merged with a PR line.
  - From Cursor-Requirements: Add a named `python/tests/implement/test_ship_recovery.py` case (or `scripts/test-implement-operator-bail-recovery.sh`) replaying unavailable assessment bail, waiver proceed, stubbed ship through postmerge, and reconcile-before-16-18 gating; or add a one-line no-repro justification in Testing strategy.


### [Plan Review] FINDING_4

### FINDING_4: Pin exact operator-bail choices
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Concern**: The operator-bail contract does not pin the required literal choices and recommended marker.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add the exact option strings and recommended marker to the SKILL and exit-matrix operator-bail bullets; pin them in `scripts/test-implement-anti-halt.sh` or structure harness needles.


