# Review Round 2

- Mode: `diff`
- 2 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Bare slot-1 duplicate stdout is dropped
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, codex-specialist-testing, dyn-dyn-oos-rollup
- **Severity**: important
- **Concern**: `design_oos.py` only accepts indexed `ISSUE_<n>_URL` / `ISSUE_<n>_DUPLICATE_OF_URL` keys, so a cap-1 deduped stdout that reports bare `ISSUE_DUPLICATE_OF_URL` or `ISSUE_URL` leaves `successful_slots` empty, skips rollup mapping, omits `Filed URL` / `OOS_FILE_MAP` rows, and can let `prepare` refire the same bundle.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From codex-specialist-testing: Address the concern above.
  - From dyn-dyn-oos-rollup: Address the concern above.


### FINDING_2: Cap-1 rollup stamping is over-gated on failure
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, codex-specialist-testing, dyn-dyn-oos-rollup
- **Severity**: important
- **Concern**: `_cap1_rollup_url` still returns `""` whenever `has_failures` is true, so a cap-1 batch with one surviving slot-1 URL and nonzero `ISSUES_FAILED` does not stamp the rollup URL onto later originals; only the first original gets a `Filed URL` / `OOS_FILE_MAP` row, and `prepare` can file the bundle again.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From codex-specialist-testing: Address the concern above.
  - From dyn-dyn-oos-rollup: Address the concern above.


