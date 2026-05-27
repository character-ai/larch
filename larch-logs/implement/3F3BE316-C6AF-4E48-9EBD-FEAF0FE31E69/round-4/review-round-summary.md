# Review Round 4

- Mode: `diff`
- 10 accepted, 13 rejected (10 exonerated)

## Accepted Findings

### FINDING_13: Stall tracking clear path lacks negative durability tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Tests cover successful `STALL_TRACKING` clearing but not read-back or `mv` failure paths, so a failed durable clear could still leave Step 18b believing recovery completed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_17: bug-comment attempts file lacks tmpdir containment
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `bug-comment --attempts-file` can read attempt metadata from outside the current session tmpdir, potentially merging another session's attempt data into a public terminal comment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### FINDING_21: Step 18a omits canonical BAIL_FAILURE_DETAIL_LOG handoff
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The Step 18a classify procedure does not require reading `BAIL_FAILURE_DETAIL_LOG` from `ship-pr-state.sh` and passing it through `--failure-detail-log`, so recovery may classify from lower-quality state/session evidence instead of the canonical detail log.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_22: Terminal-failure stall persistence is prose-only
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Terminal-failure seeding into `ship-pr-state.sh` has no script or harness coverage, so early bail paths without state files can leave finalize-state non-stalled even while in-memory `STALL_TRACKING=true`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_23: Retry caps are not mechanically enforced before dispatch
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `retry-policy` reports caps but does not gate dispatch, so the orchestrator can exceed documented retry limits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_26: classify attempts-file lacks tmpdir containment
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `classify --attempts-file` can read a path outside `$IMPLEMENT_TMPDIR` for signature comparison if mispointed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_27: Manual synthetic-stall acceptance test is missing
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Acceptance criterion #10 requires a demonstrated manual synthetic-stall integration run covering Step 18a dry-run consumer behavior and dev-clone issue filing, but the branch only shows script-level and offline harness coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_3: Retry policy table lacks full doc/code parity
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The markdown retry-cap table can drift from `retry_cap_for` / `retry_delay_for`; current harness coverage only samples some classes, so documented retry limits may disagree with runtime behavior while CI still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_5: Classification file is not confined to IMPLEMENT_TMPDIR
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `bug-body` / `bug-comment --classification-file` can read a file outside `$IMPLEMENT_TMPDIR` or through a symlink, weakening the public-output allowlist boundary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt: Address the concern above.


### FINDING_8: Same-cause override can bypass contract-failure zero-retry handling
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: For `STALL_STEP` 3 or 6, a contract failure can be reclassified as `same-cause-repeat` after a matching prior signature, allowing an alternate restart despite the zero-retry contract-failure rule.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


