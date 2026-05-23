### FINDING_13: [OUT_OF_SCOPE] `GH_HOST` embedded in grep EREs is only dot-escaped
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Exotic hostnames with other regex metacharacters could be interpreted differently than intended; caller marked as out-of-scope shared escape strategy with pre-existing helpers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_18: [OUT_OF_SCOPE] Global filed count vs per-block SKILL prose (disjunctive gate semantics)
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Pre-existing tension between global “filed > 0” pass semantics and per-block prose expectations; noted as documented disjunctive gate not solely changed by strict counter work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### FINDING_20: [OUT_OF_SCOPE] Planned broad file list has no current denylist invocations under linter rules
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Several planned file entries have no fenced denylist invocations under current lint semantics; acceptable if fence-only acceptance remains authoritative—no marker obligation from lint alone.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

---

**Notes on merging (for voters, not findings):**  
- Source slots `cursor-specialist-structure-output.txt`, `cursor-specialist-correctness-output.txt`, and `cursor-specialist-edge-cases-output.txt` largely duplicate the same AGENTS §4 and BASH §4 gaps; they are folded into **FINDING_1** and **FINDING_2**.  
- EOF / `in_fence` risks from structure, correctness, and edge cases are folded into **FINDING_5**.  
- Harness “missing fixtures / scenarios” and “parse-only non-exec invariant” are kept as **FINDING_9** vs **FINDING_12** because they imply different fixes (broad matrix vs explicit execution-negative contract).  
- **FINDING_4** (CHANGELOG omission) is not merged with **FINDING_7** / **FINDING_20** out-of-scope “bundling” notes: one is an in-scope consumer-doc gap; the others are process/scope observations.

Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_7: [OUT_OF_SCOPE] Multi-feature branch / PR scope and attribution noise
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: The branch stacks unrelated work (OOS, foreground markers, logs/chores), increasing bisect/revert cost, review noise, and ambiguity when attributing changes to a single acceptance surface—not a line-level defect in the foreground linter itself.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

