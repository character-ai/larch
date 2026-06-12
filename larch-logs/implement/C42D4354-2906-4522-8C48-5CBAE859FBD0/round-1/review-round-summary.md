# Review Round 1

- Mode: `diff`
- 5 accepted, 2 rejected (0 neutral)

## Accepted Findings

### FINDING_10: `--filter-manifest` mode lacks direct regression tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Drafter launchers depend on wrapper filtering, but cap, reserved slug, duplicate, invalid row, and invalid JSON fail-open behavior is not pinned.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add direct --filter-manifest harness cases for cap, reserved slugs, duplicates, invalid rows, and invalid JSON fail-open.


### FINDING_5: Drafter parser scout-manifest detection is not JSON-string-aware
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `scripts/parse-drafter-output.py` counts braces without respecting quoted strings and escapes, so standalone scout JSON can evade rejection or be parsed incorrectly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Use JSON-string-aware raw_decode scanning or brace tracking that ignores quoted strings and escapes.
  - From codex-specialist-edge-cases-output.txt: Use JSONDecoder raw_decode or string-aware brace tracking for candidate object extraction outside fenced blocks.


### FINDING_7: Pre-scout normalizers accept non-array `archetypes` containers
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: A malformed pre-scout manifest with `.archetypes` as an object can be normalized into valid dynamic slots instead of failing open to static-only review.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Require .archetypes to be an array before reduce in both normalizers.


### FINDING_8: Drafter/parser launcher scout edge cases lack required harness coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Scout sentinel placement, malformed scout blocks, standalone scout JSON, filter behavior, and `SCOUT_WRITTEN` launcher KVs can regress without Codex and Claude drafter tests failing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add scout sentinel stub modes and assertions to test-launch-codex-drafter.sh and test-launch-claude-drafter.sh per the plan matrix.
  - From codex-specialist-testing-output.txt: Add the planned scripts/test-launch-codex-drafter.sh and scripts/test-launch-claude-drafter.sh cases.


### FINDING_9: Pre-scout dispatch and Step 2/5 routing coverage is incomplete
- **Reviewer(s)**: cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-kv-protocol-output.txt
- **Severity**: important
- **Concern**: The implemented pre-scout chain lacks regression coverage across dispatch, review-core forwarding, Step 2 sidecar materialization, Step 5 marker handling, classifier skips, and legacy scout suppression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add pre-scout test cases from the plan: valid normalized manifest, invalid/missing/empty, classifier skips, dynamic-archetypes 0, and assert scout-dynamic-archetypes.sh is never invoked.
  - From cursor-specialist-testing-output.txt: Extend test-step2-dispatch.sh and test-run-step5-review.sh to cover the full Step 2/5 scout routing matrix from the plan.
  - From codex-specialist-testing-output.txt: Add the planned dispatch-panel, run-step5-review, and step2-dispatch coverage.
  - From dyn-kv-protocol-output.txt: Add the planned harness cases to `test-dispatch-panel.sh` and `test-review-core.sh`, asserting `SCOUT_STATUS`, `DYNAMIC_SLOTS`, and that `scout-dynamic-archetypes.sh` is not invoked when `--pre-scouted-manifest` is supplied.


