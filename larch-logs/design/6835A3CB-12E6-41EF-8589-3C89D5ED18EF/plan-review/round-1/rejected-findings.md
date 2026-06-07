### [Plan Review] FINDING_8

### FINDING_8: SIMPLE /design final round is pruned instead of receiving a full re-probe
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: SIMPLE /design has a tier review cap of 3, but the plan only bypasses pruning at round 5. Its terminal Gate C pass can therefore run as a reduced panel and never receive the intended final full-panel re-probe.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: SIMPLE /design exits with a reduced panel on its final Gate C pass and never gets a full re-probe Extend filter bypass to treat N >= tier_review_cap (SIMPLE 3 HARD 5) as full panel, not only N >= 5; document tier mapping in reviewer-prune.md and acceptance criteria


