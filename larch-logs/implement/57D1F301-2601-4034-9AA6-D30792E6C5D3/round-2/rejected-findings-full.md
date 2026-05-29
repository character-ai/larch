### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: Honor-system optional trailers can bypass hard size gate
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Optional plan-size trailers are self-asserted without independent verification. A designer or compromised agent can set `mechanical_churn: true` and low `diff_added` to bypass diff hard Split/Cancel while the plan remains large and complex; `mechanical_churn: true` is trusted without verifying mechanicality.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: No cross-check between optional trailers and `diff_lines`
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: No consistency check between `diff_added` / `diff_deleted` and final `diff_lines` while emit still publishes `diff_lines`. Gates may pass on low `diff_added` while `diff-lines.txt` / `DIFF_LINES` show a very large total, or high `diff_deleted` with low totals can bypass hard triggers while misrepresenting churn.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_17: Gate A/B direct `plan.txt` rewrites lack script trailer guard
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Gate A/B direct `plan.txt` rewrites enforce optional trailers via prompt only, with no script guard. A Gate B dedup rewrite that drops `mechanical_churn: true` can revert to legacy `diff_lines` hard gating and force Split/Cancel on a deletion-heavy plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: Magic `substr` offsets for trailer values in awk
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `diff_added` and `diff_deleted` extraction in `lib-plan-optional-trailers.awk` uses fixed `substr` offsets tied to token spelling; renaming trailers or changing single-space grammar can break extraction without a clear regex failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_6: Legacy `diff_lines` hard trigger when `diff_added` is absent
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Deletion-heavy relief depends on designers emitting `diff_added`, but the script still hard-triggers on legacy `diff_lines` when `diff_added` is absent. A plan with large `diff_lines` and no optional trailers still gets `HARD_TRIGGER_FIRED=true` and Split/Cancel only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: Structural tests omit `SKILL.md` Gate A/B trailer guardrails
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Structural pins omit `SKILL.md` requirements for snapshot / `diff_deleted` / validate-before-`EMIT_PLAN` that plan acceptance expects. Gate B and discussion direct-rewrite preservation prose may live only in references; an operator following `SKILL.md` for manual rewrites could omit trailer preservation while `test-design-structure.sh` still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

