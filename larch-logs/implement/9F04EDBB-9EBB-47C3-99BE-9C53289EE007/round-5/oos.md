### FINDING_18: [OUT_OF_SCOPE] Branch bundles unrelated changes and large run logs
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: `CHANGELOG.md`, unrelated landed fixes, and large `larch-logs/implement/*` content widen bisect/review surface; sources mark this as not a logic defect in the cutover itself.
- **Suggested revision**: None required for cutover correctness per sources; accept bisect noise or split history in a follow-up if desired.


Vote tally: YES=0 NO=1 EXON=1 JUDGE_ERROR=0 Result=exonerated

### FINDING_19: [OUT_OF_SCOPE] hook-stop-fail-close JSON hardening for exotic paths
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: `jq --arg` with `REASON` containing `basename`; exotic path edge case noted as pre-existing alongside Stop-hook logic, not specific to manifest removal.
- **Suggested revision**: Optional hardening only; none required for this PR per sources.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_20: [OUT_OF_SCOPE] Committed session transcripts volume
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Committed transcripts include long tool transcripts; aligns with intentional run-log policy per `AGENTS.md`.
- **Suggested revision**: No change per sources.


Vote tally: YES=0 NO=1 EXON=1 JUDGE_ERROR=0 Result=exonerated

### FINDING_21: [OUT_OF_SCOPE] NON_PR /fix-issue path not plan-gated at lock time
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Only PR-shaped `/fix-issue` runs pass `--require-plan-block`; NON_PR work is not plan-gated at lock—product scope, not introduced solely by this cutover.
- **Suggested revision**: Accept as scope or extend plan probe to additional `INTENT` values in a separate decision.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_22: [OUT_OF_SCOPE] review skill docs still mention PANEL_SHAPE / review-core --panel
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: `skills/review/SKILL.md` retains `PANEL_SHAPE=simple|hard` and `--panel` on `review-core`; orthogonal if the operator sweep goal was only implement/design surfaces.
- **Suggested revision**: Clarify sweep scope or adjust review SKILL wording in a follow-up if global token removal was intended.
```

Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

