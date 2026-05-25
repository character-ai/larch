### OOS_1:
- **Description**: Code retry prefix names only FINDING_N while code ballots stay finding-only today. Scenario: Future code ballot grammar adding OOS ids would leave retry text misaligned with renderer
- **Reviewer**: Cursor-Edge
- **Severity**: nit
- **Focus area**: risk-integration
- **Location**: scripts/lib-voter-parse-rate.sh:10-12
- **Phase**: design


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_2:
- **Description**: Zero-finding loop short-circuit skips tally entirely. Scenario: `findings-classification.tsv` never materializes on `skipped-empty-findings` unlike rounds that run `tally-plan-review.sh`.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/scripts/plan-review-loop.sh:485-489
- **Phase**: design


Vote tally: YES=0 NO=0 EXON=0 JUDGE_ERROR=3 Result=rejected

### OOS_3:
- **Description**: Parallel L6 design also proposes a `test-findings-classification` Makefile target for a different script path. Scenario: Two issues landing independently could duplicate the same `.PHONY` target name or shard assignment expectations
- **Reviewer**: Cursor-dyn-schema-wire-consistency
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: larch-logs/design/3CDFC6C9-391D-419F-9FEF-D5C9048B12BA/plan.txt:170-172 vs plan.txt:115-123
- **Phase**: design


Vote tally: YES=0 NO=0 EXON=0 JUDGE_ERROR=3 Result=rejected

