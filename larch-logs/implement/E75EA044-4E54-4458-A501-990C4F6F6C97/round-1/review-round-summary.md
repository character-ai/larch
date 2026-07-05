# Review Round 1

- Mode: `diff`
- 2 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: OOS proposed count is inflated by rejected ballots
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, codex-specialist-testing
- **Severity**: major
- **Concern**: `_phase_round_from_meta` / `render_phase_detail` add rejected OOS ballots into `oos_proposed`, so the rendered OOS proposed column shows total OOS instead of vote-accepted proposals and no longer matches persisted metadata or the planned proposed-vs-fileable split.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: `Address the concern above.`
  - From codex-specialist-correctness: `Address the concern above.`
  - From cursor-specialist-edge-cases: `Address the concern above.`
  - From codex-specialist-edge-cases: `Address the concern above.`
  - From codex-specialist-testing: `Address the concern above.`


### FINDING_2: Missing footnote/test coverage for proposed vs fileable OOS split
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: minor
- **Concern**: The canonical decomposition footnote and its coverage were not extended to reflect the proposed-vs-fileable OOS split, so accepted-minor vs fileable totals are still not reconciled in the footnote path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: `Address the concern above.`
  - From cursor-specialist-testing: `Address the concern above.`


