### [rejected] FINDING_6

**Rejected subtype:** dismissed (0 YES)

### FINDING_6: Harness does not assert merge-env truncation or merge-result-env wiring
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: minor
- **Concern**: The structure harness only checks the path literals today; it does not prove the `: >` truncation and `--merge-result-env` wiring that keep stale merge envs from satisfying wait gates.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Harness does not assert merge-env truncation before start. Prose drops : > truncate lines; Check 10 still passes on path literals only. Pin truncate-before-start commands in structure harness.
  - From cursor-specialist-edge-cases: Add contains checks for : > merge-env truncation and --merge-result-env on each lane start
  - From cursor-specialist-testing: Add contains pins for : > merge-env truncation and --merge-result-env in both reference files.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** dismissed (0 YES)

### FINDING_7: Collision regression coverage still misses runtime slug wiring
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: major
- **Concern**: The collision regression only proves a few hard-coded strings are unique; it never exercises slug/path wiring at runtime, so two concurrent lanes could still clobber each other while CI stays green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Collision regression only checks six hard-coded strings for self-uniqueness; it never inspects reference prose or slug-to-path mapping. Two concurrent lanes could reuse one --step slug and clobber result envs while CI stays green. Assert slug/path wiring in research-phase.md and validation-phase.md, or add an offline bgjob harness that proves distinct result env files.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** dismissed (0 YES)

### FINDING_8: The harness does not pin the post-round-1 COLLECT_ARGS contract
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: major
- **Concern**: Nothing in the harness forbids reintroducing the old availability-based `COLLECT_ARGS` pre-fill, so a future edit could send failed lanes back to collect-results without a test failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add negative grep for codex_binary_available/cursor_binary_available COLLECT_ARGS pre-fill and positive pins for failed-lane exclusion prose.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** dismissed (0 YES)

### FINDING_9: Check 10 still greps an obsolete phrase
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: major
- **Concern**: The new harness assertion is looking for wording the docs no longer use, so the check fails against the current tree and blocks CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Change the assertion to the actual prose or assert the concrete BGJOB_RC=0 and STEP=... gate.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

