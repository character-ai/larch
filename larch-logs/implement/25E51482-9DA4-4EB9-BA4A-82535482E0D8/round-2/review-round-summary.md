# Review Round 2

- Mode: `diff`
- 6 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Malformed assessment rows block fallback lanes
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: major
- **Concern**: Malformed row fields are classified as re-author-required instead of lane-unavailable, causing valid fallback lanes to be skipped and Step 8 to block.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.


### FINDING_2: Step 8 budget documentation is stale
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-testing
- **Severity**: minor
- **Concern**: The documentation still states a 5700-second budget and outdated single-lane overhead, while runtime derives 11040 seconds for two full three-lane waterfalls. Document the derived formula, 11040-second default, and adapter attempt-2 as a full child retry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.


### FINDING_3: Assessment output symlinks can redirect launcher writes
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: major
- **Concern**: A same-UID process can replace an assessment output with a symlink after cleanup and redirect Cursor output or sidecar writes outside `IMPLEMENT_TMPDIR`. Reject symlinks before existence checks and use no-follow creation for final output and sidecar files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Address the concern above.


### FINDING_4: Missing timeout waterfall coverage
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: Tests do not verify that `EXIT_TIMEOUT` advances through lanes and produces the expected final unavailable diagnostic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


### FINDING_5: Missing invariants-violation stop coverage
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: Tests cover stopping on deviation but not a valid invariants violation. A regression could launch later lanes or overwrite the first valid result.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


### FINDING_8: Codex assessment sandbox is broader than the evidence directory
- **Reviewer(s)**: dyn-dyn-launch-contract
- **Severity**: major
- **Concern**: Codex receives `output.parent` as an `--add-dir`, granting access to the entire session tmpdir rather than only the validated evidence directory and repository workdir.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-launch-contract: Address the concern above.
