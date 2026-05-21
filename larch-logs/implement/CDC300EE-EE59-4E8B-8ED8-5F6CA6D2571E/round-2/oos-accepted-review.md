### FINDING_1: [OUT_OF_SCOPE] ship-pr.md Exit 5 CALLER_KIND documentation gap
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Operators relying on [scripts/ship-pr.md](scripts/ship-pr.md) may see Exit 5 documentation that mentions `step8b_rebase` but not `step8_apply_bump_same_version`, so they may miss the second Exit 5 `CALLER_KIND` token after runtime alignment.
- **Suggested revision**: Add a concise bullet beside the existing Exit 5 description that documents both Exit 5 caller-kind values (`step8b_rebase` vs `step8_apply_bump_same_version`).


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0 Result=exonerated


### FINDING_3: [OUT_OF_SCOPE] Garbled pasted plan bullet
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: A pasted implementation-plan bullet does not describe an actual token change; it is noise for diff judgment.
- **Suggested revision**: Ignore for code review; rely on `feature_description` and the code.


Vote tally: YES=0 NO=1 EXON=1 JUDGE_ERROR=0 Result=exonerated


### FINDING_4: [OUT_OF_SCOPE] Run log plan narrative uses legacy token name
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: A committed run-log plan file still uses the legacy token in narrative; it is not runtime behavior.
- **Suggested revision**: None required; optional editorial cleanup only if desired.


Vote tally: YES=0 NO=1 EXON=1 JUDGE_ERROR=0 Result=exonerated


### FINDING_5: [OUT_OF_SCOPE] Feature / issue narrative may under-describe branch surface
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Narrow `feature_description` text may not mention ship-pr, harness, or run-log edits present on the branch, so PR/issue narrative keyed only to a short feature tag may under-describe delivered surface.
- **Suggested revision**: Reconcile issue/PR description with the full diff when publishing; not a functional code defect.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated


