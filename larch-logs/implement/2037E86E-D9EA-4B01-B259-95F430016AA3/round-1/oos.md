### FINDING_13: [OUT_OF_SCOPE] Optional realism fixture absent; harness skips by design
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: Optional realism fixture not present; no CI coverage for ±10% realism until a fixture is added—acceptable as a gated plan state rather than a present defect in-tree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_18: [OUT_OF_SCOPE] Branch mixes unrelated merges/commits complicating DE-2622 attribution
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Branch history/diff includes non-DE-2622 items (e.g., Step 5 absorption, other chores, `larch-logs`), increasing reviewer noise when attributing failures to DE-2622 alone; mitigated by scoping review to a specific commit or splitting PRs if separation matters—process/scope note rather than a code defect.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_8: [OUT_OF_SCOPE] Plan references fix-issue parity but no skill directory exists here
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Plan bullets referenced `skills/fix-issue/` updates, but no such directory exists in this tree—no actionable diff relative to current repo layout (not a missing-file defect for this branch).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_9: [OUT_OF_SCOPE] Large committed `larch-logs/**` churn adds review noise
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Massive committed run-log deltas create diff noise; treated as intentional per repo policy with no structure-review change required.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

