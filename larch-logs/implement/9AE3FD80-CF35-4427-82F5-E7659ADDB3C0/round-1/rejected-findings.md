### [rejected] FINDING_1

**Rejected subtype:** dismissed (0 YES)

### FINDING_1: sidecar materialization failure drops findings
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: important
- **Concern**: A structured sidecar materialization failure on an OK reviewer is being treated as zero findings even when the prose is substantive; that should only collapse to zero for exact no-findings or no-issues sentinels.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Treat sidecar failure as zero rows only for exact no-findings prose or no-issues sentinels; otherwise mark the record non-substantive or fail collection.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** dismissed (0 YES)

### FINDING_2: stale structured sidecars reused after reviewer changes
- **Reviewer(s)**: cursor-specialist-edge-cases, codex-specialist-edge-cases, cursor-specialist-testing
- **Severity**: important
- **Concern**: Existing structured sidecars are still preferred when reviewer prose is newer, so stale `.tsv`/`.jsonl` rows can republish old findings or drop new ones.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Regenerate or delete sidecars when reviewer output is newer, or always lazy-materialize for OK records without STRUCTURED_SIDECAR.
  - From codex-specialist-edge-cases: Regenerate fallback sidecars when STRUCTURED_SIDECAR is absent and the fallback is missing or older than reviewer_file; write to temp and replace only on successful validation.
  - From cursor-specialist-testing: Regenerate or invalidate sidecars when reviewer file is newer (or clear on Step 3 --reentry); add a stale-sidecar regression in test_plan_review_round.py


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

