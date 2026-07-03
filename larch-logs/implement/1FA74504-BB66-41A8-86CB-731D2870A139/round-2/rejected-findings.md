### [rejected] FINDING_4

**Rejected subtype:** dismissed (0 YES)

### FINDING_4: Hash-bearing sidecars need last-write-wins dedupe
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases, codex-specialist-testing
- **Severity**: important
- **Concern**: Repeated `finding_hash` sidecar rows are being deduped by a composite key instead of `finding_hash` last-row-wins, so stale and newer annotations for the same hash can both survive and inflate the reported burden.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: When `finding_hash` is present, use it as the dedupe key and overwrite the prior row; only fall back to a composite key for hashless rows.
  - From codex-specialist-testing: Key hashed sidecar rows by `finding_hash` alone, overwrite with the later row, keep duplicate counting, and update the test so only the last verdict contributes.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

