### FINDING_10: [OUT_OF_SCOPE] No focused unit harness for awk trailer parser modes
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `lib-plan-optional-trailers.awk` behavior is only covered via integration tests. Subtle last-match-wins or `has_key` bugs may require debugging through full `plan-review-loop` or waterfall fixtures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_13: [OUT_OF_SCOPE] Gate B trailer preservation not surfaced in SKILL.md Step 2b/2b.5
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Gate B optional-trailer preservation lives in `approval-gates.md` but is not duplicated in `SKILL.md` as the plan file list requested. Operators reading only Step 2b/2b.5 may miss rewrite snapshot/validate rules unless they follow the Gate B mandatory read.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

---

**Merge notes (for voters, not machine output):** Input findings 1/6/15 → FINDING_1; 2/9 → FINDING_2; 8/14 → FINDING_7. FINDING_12 (test case 25) is kept separate from FINDING_1 because it targets a different artifact (harness expectations) even though it tracks the same root parser behavior. All source slots used generic “Address the concern above” revisions; no additional verbatim fix text was available to quote.

Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_5: [OUT_OF_SCOPE] Keys-only trailer preservation lacks deliberate-documentation
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `validate_optional_trailer_preservation` checks keys only, not trailer values—intentional for the recompute path but easy to misread when extending validation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

