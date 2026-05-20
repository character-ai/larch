### [rejected] FINDING_13

### FINDING_13: code-quality: scripts/test-dispatch-code-voters.sh:7-31 and scripts/test-dispatch-code-voters.sh:23-31
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Section names are documented in the header and duplicated again in the validation case list. A future rename can update comments but forget the case arm (or vice versa), reintroducing unknown-section false passes or confusing errors. Single-source section identifiers (one list driving both docs text and validation).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_16

### FINDING_16: risk-integration: Makefile:4 Makefile:519
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] New dispatch-code-voters retry targets are .PHONY on the secondary block but omitted from the mega .PHONY line the plan referenced. Ad-hoc tooling that only parses the first .PHONY line could treat the new targets differently from other harness recipes. Append test-dispatch-code-voters-retry-* to the line-4 mega .PHONY list.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 NEUTRAL=0

### [rejected] FINDING_17

### FINDING_17: risk-integration: Makefile:56
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Shard 12 gained test-rebase-push-force-lease and test-ballot-parse while already hosting many harnesses; timing goal may regress. CI shard 12 could exceed the intended ~40s ceiling even though functional tests pass, weakening the rebalance objective. Re-check LARCH_HARNESS_TIMING after CI; adjust shard assignment or split further if shard 12 spikes.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_18

### FINDING_18: risk-integration: Makefile:56
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Shard 12 grows with rebase-push-force-lease and ballot-parse moved from shard 9. Shard 12 may exceed the intended ~40s CI ceiling while staying green. Re-check LARCH_HARNESS_TIMING; rebalance if shard 12 regresses.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 NEUTRAL=0

### [rejected] FINDING_19

### FINDING_19: risk-integration: Makefile:test-harnesses-12 line (~52)
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Shard 12 gained test-rebase-push-force-lease and test-ballot-parse on an already heavy shard row. CI shard wall time could exceed the ≤40s target while remaining structurally valid; slow merges erode the rebalance goal. Re-check LARCH_HARNESS_TIMING for test-harnesses-12 after CI runs; repack if the shard becomes a new straggler.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 NEUTRAL=0

### [rejected] FINDING_8

### FINDING_8: architecture: scripts/test-dispatch-code-voters.sh:23-30 + Makefile:216-226 + scripts/test-dispatch-code-voters.md
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Section names are triplicated across harness, Makefile, and doc. A typo in one site can desync CI invocation from the harness allowlist or confuse operators. Optional: centralize names or add a structural grep guard in an existing coverage script.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_9

### FINDING_9: architecture: scripts/test-dispatch-code-voters.sh:23-31
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Unknown --section validation added; not enumerated in implementation plan File 1. Typo or experimental section value now exits 1 instead of running ambiguously; no impact on Makefile/CI wiring. Optional: document in plan or scripts/test-dispatch-code-voters.md; no code change required.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 NEUTRAL=0

