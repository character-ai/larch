# Review Round 1

- Mode: `diff`
- 1 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Summary gap reappearance handling is inconsistent
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases, dyn-dyn-ledger-gap
- **Severity**: important
- **Concern**: Summary mode does not handle disappear/reappear gaps consistently: reviewers report it can count a reappearance as a raise from 0, inflate `raises` / `largest_raise_delta`, or drop the summary row and under-report selected-range totals after a gap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: Carry a gap-restart marker from `_build_revisions()` or teach `_summarize()` to start a fresh accumulator on reappearance after a gap, and add a regression test for `--summary` on a disappear/reappear history.
  - From dyn-dyn-ledger-gap: Teach `_summarize()` to treat a reappearance the same way as detailed deltas (e.g., when a target is present in the snapshot but its `TargetDelta` has `previous is None` while an accumulator already exists with `current == 0`, reset or drop that accumulator instead of advancing `0 → current`), and add a summary test on the gap fixture that pins non-spurious `delta` / `raises` for `panel-tier`.


