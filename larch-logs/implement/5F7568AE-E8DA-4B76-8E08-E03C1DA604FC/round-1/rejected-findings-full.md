### [rejected] FINDING_13

### FINDING_13: correctness: skills/review/scripts/emit-tally.sh:101-102
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Digit-only validation allows leading zeros for slot counts. Dispatch emits `09`; jq `--argjson` may fail and abort emit-tally. Strip leading zeros or validate strict decimal JSON integers before jq.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=1 NEUTRAL=1

### [rejected] FINDING_20

### FINDING_20: risk-integration: skills/review/scripts/emit-tally.sh:134-168
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] review-summary.json bumps schema_version from 1 to 2 and adds panel. External scripts or dashboards that require schema_version==1 may mis-handle or ignore new summaries, breaking automated consumers without parallel updates. Update consumer contracts and docs, or retain backward-compatible versioning policy if strict equality checks exist in the wild.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=1 NEUTRAL=1

