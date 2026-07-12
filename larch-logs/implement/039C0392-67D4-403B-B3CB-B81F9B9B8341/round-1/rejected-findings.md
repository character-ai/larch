### [rejected] FINDING_7

**Rejected subtype:** dismissed (0 YES)

### FINDING_7: Report, ledger, and snapshot persistence are not failure-safe
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-ledger-history
- **Severity**: major
- **Concern**: `render_report` can write `report.md` and/or append hydrated ledger rows before the final snapshot write succeeds. A later persistence failure leaves report, ledger, and “Since last run” state inconsistent, breaking rerender continuity and potentially exposing guidance that was not durably recorded.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From dyn-dyn-ledger-history: Persist ledger hydration and `run-state.json` first (or in one atomic transaction), validate the assembled report, then write `report.md` last; on any persistence failure, leave `report.md` absent or clearly mark the run incomplete.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** dismissed (0 YES)

### FINDING_18: Historical marker backfill prioritization can omit relevant issues
- **Reviewer(s)**: dyn-dyn-ledger-history
- **Severity**: major
- **Concern**: Backfill candidates are selected by ascending issue number rather than analytics relevance. When more than 50 historical issues need backfill, issues that complete active chain edges or contribute to chronic-zone routing can be skipped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-ledger-history: Prioritize backfill candidates by graph distance to active manifest issues, chronic-zone membership, or recency inside the 14-day window before applying the fixed cap.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0
