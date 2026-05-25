### FINDING_14: [OUT_OF_SCOPE] Branch bundles brainstorm with unrelated harness, logs, and plan-surface churn
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The same change-set mixes the brainstorm feature with unrelated dedup/harness edits, high-volume log assets, and paths beyond a tight #2754 trace, increasing review noise, bisect/revert cost, and conflict risk unless the plan explicitly lists every co-delivered path or work is split.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Track as separate PR or commit for reviewers.
  - From cursor-specialist-plan-fidelity-output.txt: Split unrelated commits/PRs or update the authoritative plan to list every co-delivered path explicitly

---

There are 14 merged `### FINDING_N:` blocks, so **`LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` must not appear** anywhere in this output.

Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_5: [OUT_OF_SCOPE] Final summary jq uses `.classification` while run-params stores `design_classification`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Summary mode jq reads `.classification` but run-params uses `design_classification`, so classification display may always fall back to N/A; reviewers treat this as pre-existing on main, not introduced by the brainstorm work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Switch jq to .design_classification (or add a JSON alias) in a dedicated cleanup.
  - From cursor-specialist-edge-cases-output.txt: Align jq field name in a separate fix.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_6: [OUT_OF_SCOPE] `test-implement-structure.sh` ship-pr key extraction coupled to fragile `ship-pr.sh` formatting
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The drift-guard awk range is anchored to patterns (e.g. a literal `} > "$tmp" && mv` tail inside `write_initial_state`) that can break or narrow incorrectly on non-semantic refactors or whitespace changes to `ship-pr.sh`, producing false-positive key drift or harness failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Anchor on explicit markers inside write_initial_state
  - From cursor-specialist-testing-output.txt: Anchor extraction on a dedicated comment marker inside write_initial_state instead of the redirect line
  - From cursor-specialist-edge-cases-output.txt: Anchor on stable markers or exported key-list helper


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

