### [rejected] FINDING_4

**Rejected subtype:** dismissed (0 YES)

### FINDING_4: Structured nit rows are not pruned
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: important
- **Concern**: Structured TSV nit rows are rendered as `[nit]` concern text, but the nit filter only matches a `Severity` field, so `prune_nit_findings` misses them and nits can reach aggregation and voting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

