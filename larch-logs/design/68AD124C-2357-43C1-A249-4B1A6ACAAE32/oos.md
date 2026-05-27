### OOS_2:
- **Description**: New external assessor panel not covered in security policy. Scenario: Operators lack documented read-only/sandbox posture for assessor launches
- **Reviewer**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: security
- **Location**: SECURITY.md:53-59
- **Phase**: design


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_3:
- **Description**: Design topology projection may omit new Step 3.6. Scenario: Consumer topology counts/steps drift from runtime SKILL
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/shared/topology.tsv
- **Phase**: design


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_4:
- **Description**: Canonical run-log docs only describe plan-review/round-<N>/findings-classification.tsv, not new top-level assessor/snapshot basenames. Scenario: Operators auditing larch-logs/design/<RUN_ID>/ will not find assessor-verdict-round-<N>.txt or plan-after-round-<N>.txt documented alongside voter TSV layout
- **Reviewer**: Cursor-dyn-schema-drift
- **Severity**: latent
- **Focus area**: architecture
- **Location**: docs/run-logs.md:126-129
- **Phase**: design


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

