### [rejected] FINDING_10

**Rejected subtype:** dismissed (0 YES)

### FINDING_10: correctness: python/migrated-scripts.tsv
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] C4c retired scripts not listed; bash counterparts still on disk Migration lint and stale-reference sweep incomplete per plan Add migrated-scripts.tsv rows delete retired bash after parity tests
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_29

**Rejected subtype:** dismissed (0 YES)

### FINDING_29: risk-integration: python/migrated-scripts.tsv
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] C4c retired bash helpers still on disk and absent from migrated-scripts.tsv while callers use Python. Dual authority and lint-retired-scripts gaps hide stale references and confuse which implementation is authoritative. Complete cutover, list retired paths in migrated-scripts.tsv, delete bash surfaces per plan.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

