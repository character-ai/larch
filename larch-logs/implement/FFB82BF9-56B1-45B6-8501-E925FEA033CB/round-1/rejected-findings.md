### [rejected] FINDING_2

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_2: Structural checks do not enforce marker-mode mutual exclusion
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: major
- **Concern**: The structural harness does not assert that filing mode skips the pre-filing marker block or that default-mode marker fences are guarded by `FILE_MODE=false`. A future edit could reintroduce marker-before-filing behavior while the harness still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_3: Dry-run output validation is incomplete
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: Dry-run validation does not require the `/issue` `ITEMS_TOTAL` and `ITEM_<i>_TITLE` key-value contract, so incorrect counts or titles could be accepted and automatically filed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_5: Partial filing success lacks an idempotent retry path
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: major
- **Concern**: If issue creation succeeds but scan-marker commit fails, rerunning can create duplicate issues because there is no durable resume path that records create outcomes and advances the marker without re-filing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** dismissed (0 YES)

### FINDING_6: Pending filing state lacks stale-input validation
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: major
- **Concern**: Pending state does not identify or validate the report, batch, repository, mined issue set, and search inputs. A retry can consume obsolete proposals after those inputs change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** dismissed (0 YES)

### FINDING_7: Filing mode does not adequately defend against hostile mined content
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: major
- **Concern**: Prompt-only untrusted-content mitigations are insufficient before batch `/issue` creation. Hostile mined issue text may influence filed bodies or downstream agents when independent verification is skipped. Filing mode needs security triage, redaction, and fail-closed handling for unverified claims.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** dismissed (0 YES)

### FINDING_8: Filing artifacts lack secret and path redaction
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: major
- **Concern**: Reports, batch files, pending state, and issue bodies can preserve or publish credentials, session paths, or other sensitive temporary-directory data. Scrubbing must occur before commit or issue egress, with post-scrub verification.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** dismissed (0 YES)

### FINDING_9: Durable filing writes are not hardened against path attacks
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: major
- **Concern**: Repository-relative durable filing paths lack canonicalization, containment, symlink, and regular-file checks. A symlink or non-regular path could redirect prompt-side writes outside the approved run-log root.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_10

**Rejected subtype:** dismissed (0 YES)

### FINDING_10: Durable filing artifacts have no lifecycle or cleanup contract
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Failed or partial runs can leave detailed batch bodies in tracked `larch-logs/` beside the scan marker, with no post-success cleanup or commit guard. Pending storage and promotion need a defined lifecycle.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** dismissed (0 YES)

### FINDING_11: Regression-test requirements are insufficiently pinned in the structural harness
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: major
- **Concern**: The structural harness does not pin the required targeted reads and greps, the “would have caught the bug” gate, or the justification for why nearby existing tests do not cover the root-cause path. Core Step 3 behavior can therefore regress without CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** dismissed (0 YES)

### FINDING_12: Filing-mode and follow-up control-flow anchors are not pinned
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The harness does not assert the filing-mode branch header, dedup-valid and nothing-to-file stop behavior, or the Step 5 “Add regression tests” follow-up. These plan-required behaviors can regress without a structural signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** dismissed (0 YES)

### FINDING_13: Filing orchestration lacks executable behavior-level tests
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: major
- **Concern**: Filing durability and marker ordering are described but are not implemented with concrete commands or covered by behavior-level tests. The workflow needs tests for success, no residuals, dry-run failure, partial failure, full deduplication, and marker-commit failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** dismissed (0 YES)

### FINDING_14: Security and repository-routing checks are prompt-only
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: minor
- **Concern**: Structural checks only search for prompt text and do not exercise hostile mined content or alternate-repository propagation. Regressions could allow copied directives or incorrect issue targeting without CI detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0
