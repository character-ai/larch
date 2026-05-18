### [rejected] FINDING_11

### FINDING_11: code-quality: docs/linting.md:253
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] test-harness-shards-coverage row genericizes placement of the partition guard. Text no longer reflects the Makefile’s deliberate first-slot placement on test-harnesses-12, hiding the sentinel-shard contract the Makefile comment documents. Name test-harnesses-12 (or state first prerequisite of that shard) on this row only.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 NEUTRAL=1

### [rejected] FINDING_12

### FINDING_12: risk-integration: docs/linting.md:94-130
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Shard expansion adds three new matrix-derived status check names that must be required on main. If branch protection is not updated before merge, merges can succeed while test-harnesses (14)/(15)/(16) are non-required or failing, weakening CI gating on those shards. Update GitHub branch protection required checks to include test-harnesses (14), (15), and (16) before merging (per Branch protection migration in the same doc).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 NEUTRAL=1

### [rejected] FINDING_6

### FINDING_6: architecture: docs/linting.md (Makefile targets table; multiple rows in the rebalance diff)
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Concrete via test-harnesses-N shard hints replaced by generic partition wording. Harder to jump from a failing harness name to the correct matrix cell without Makefile grep. Optionally restore selective shard numbers or add a short pointer to Makefile grep / test-harness-shards-coverage for lookup.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 NEUTRAL=1

### [rejected] FINDING_9

### FINDING_9: code-quality: docs/linting.md:167-252
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Broad replacement of explicit per-shard doc hints with generic test-harnesses-N wording exceeds the plan’s enumerated doc edits. Operators lose one-hop mapping from a failing harness name to the CI matrix shard without Makefile ripgrep, slowing reruns and ownership triage. Restore explicit test-harnesses-<k> suffixes in the table or add a single authoritative pointer to Makefile plus coverage guard.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 NEUTRAL=1

