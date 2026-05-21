### FINDING_12: [OUT_OF_SCOPE] conflict-resolution intro overgeneralizes reviewer panel gating
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Intro prose can read like the reviewer panel always applies on exit 1 even when caller families skip Phase 3.
- **Suggested revision**: Tighten intro to reference caller families / Phase 3 gating; treat as minor pre-existing imprecision unless editing that section anyway.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_13: [OUT_OF_SCOPE] SKILL.md token naming diverges from sub-procedure vocabulary
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: skills/implement/SKILL.md uses step8b_same_version style naming that diverges from sub-procedure tokens, risking cross-file orchestrator confusion.
- **Suggested revision**: SKILL-only follow-up alignment; explicitly out of scope for the referenced two-doc threading change.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_14: [OUT_OF_SCOPE] Historical CHANGELOG text may contradict current references
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Older changelog entries can make readers briefly think step8b behavior is unchanged versus the updated reference docs.
- **Suggested revision**: Accept as historical or add a separate changelog note in a later change if cross-time clarity matters.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_15: [OUT_OF_SCOPE] Run artifacts widen scope vs stated “two markdown files only” framing
- **Reviewer(s)**: dyn-caller-kind-contract-output.txt
- **Concern**: Branch history includes added larch-logs/implement/... material beyond a narrow “two files only” scope narrative in planning text.
- **Suggested revision**: Reconcile scope documentation/process expectations separately; not a caller_kind threading defect.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_16: [OUT_OF_SCOPE] Doc-only lifecycle vs executable enforcement gap
- **Reviewer(s)**: dyn-caller-kind-contract-output.txt
- **Concern**: The documented lifecycle assumes orchestrators adopt sub-procedure step 2’s --no-push --keep-on-conflict for step8b_rebase, but this diff’s verification surface is documentation-first relative to SKILL.md/shell helpers.
- **Suggested revision**: Track as follow-up automation/testing alignment (overlaps FINDING_8’s direction) rather than a contradiction inside the markdown handoff alone.
```

Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### FINDING_3: [OUT_OF_SCOPE] Step 6e “already pushed” wording overstates skip-push paths
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Step 6e bump/push-state wording can read as “already pushed” even when a step8 skip-push path applies, overstating remote push guarantees.
- **Suggested revision**: Refactor step 6e wording in a later change; treat as pre-existing scope drift rather than blocking this thread.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_7: [OUT_OF_SCOPE] DROPPED=false warning references Phase 1–3 routing drift
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Pre-existing DROPPED=false warning text still describes Phase 1–3 routing even when the step8b path skips Phase 3, creating minor terminology drift.
- **Suggested revision**: Optional follow-up doc hygiene; no PR-blocking requirement unless that line is being edited for other reasons.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### FINDING_9: [OUT_OF_SCOPE] Macro test (H) header comment is outdated about flags
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: The test header comment still implies the sub-procedure story is --no-push alone, which can mislead maintainers updating rebase flags.
- **Suggested revision**: Update the comment on a future edit to the test file; treat as non-blocking hygiene outside the core doc contract edits.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

