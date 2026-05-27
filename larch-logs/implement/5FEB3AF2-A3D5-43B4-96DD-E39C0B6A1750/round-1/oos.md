### FINDING_14: [OUT_OF_SCOPE] Collector and validator sentinel-body semantics differ
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Collector sentinel classification uses only the first line, while validator literal matching uses the full trimmed body; this is safe but creates inconsistent telemetry for sentinel-first outputs with trailing prose.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=1 JUDGE_ERROR=2 Result=exonerated

### FINDING_15: [OUT_OF_SCOPE] Branch bundles unrelated design re-entry commit
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The branch also includes unrelated #2935 work, including plugin version bumps, `larch-logs/implement/`, and design-guard changes outside the #2995 plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=1 JUDGE_ERROR=2 Result=exonerated

### FINDING_16: [OUT_OF_SCOPE] Cursor probe doc still references omitted plan mode
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `scripts/check-reviewers.md` still documents the Cursor probe as intentionally omitting `--mode plan`; the source reviewer marked this as outside the #2995 plan rather than a plan violation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

Vote tally: YES=1 NO=0 EXON=0 JUDGE_ERROR=2 Result=rejected

