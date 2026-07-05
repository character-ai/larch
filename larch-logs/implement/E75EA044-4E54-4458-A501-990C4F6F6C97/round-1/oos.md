### FINDING_3: [OUT_OF_SCOPE] `_PhaseRound.oos_proposed` field name no longer matches stored semantics
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: The live-report model field name implies vote-accepted proposals, but the value now carries proposed+rejected total OOS; that naming drift predates this branch and is worsened by the split.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: `Address the concern above.`


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_4: [OUT_OF_SCOPE] shared voting protocol doc still uses stale OOS filing wording
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: minor
- **Concern**: The shared voting protocol still says accepted non-security OOS are filed directly and retains old blocker-or-major wording, so it disagrees with the updated filing rule and can mislead readers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: `Address the concern above.`


Vote tally: YES=0 NO=2 JUDGE_ERROR=1 Result=rejected Fileable=false

### FINDING_5: [OUT_OF_SCOPE] final-report docs still describe the old OOS column name
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: `write-final-report.md` still documents the review table as OOS proposed/accepted after the renderer renamed the column to OOS fileable, so the doc no longer matches the current wording.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: `Address the concern above.`
Vote tally: YES=0 NO=2 JUDGE_ERROR=1 Result=rejected Fileable=false

