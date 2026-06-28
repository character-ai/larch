# Review Round 1

- Mode: `diff`
- 1 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Stale consumable note skips invalidation when drop notice already exists
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: important
- **Concern**: When a consumable note is fingerprint-stale and a persisted `DROPPED_NOTE_ARTIFACT` notice already exists, `final_report.py` returns the old notice at lines 238–241 and never reaches `_persist_drop_notice_and_invalidate()` at lines 246–247. A rerun after a prior drop can therefore leave the stale durable note on disk and keep serving the old marker in the report.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.


