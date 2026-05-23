# Review Round 1

- Mode: `diff`
- Accepted findings: 7
- Rejected findings: 0
- Exonerated findings: 1
- Neutral findings: 0

## Accepted Findings

### FINDING_1: Admission harness and fork paths vs `[DESIGNED]` title gate (exit 5 / tests)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: `has_designed_prefix` (or equivalent) now rejects plain issue titles while several **pass** fixtures in `scripts/test-implement-admission.sh` still use non-`[DESIGNED]` titles and expect exit 0, so the harness fails (exit 5 `missing-designed-prefix` vs expected 0). Fork / generic pass paths may also hard-fail Preflight against upstream issues that lack the prefix unless carve-out, fixture titles, or exit-5 test branching is aligned with the new rule.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_2: `skills/implement/SKILL.md` Preflight exit 5 omits `missing-designed-prefix` / `ADMISSION_RESULT` parsing
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Preflight admission prose maps exit 5 only to `managed-prefix`, but `missing-designed-prefix` shares the same exit code; operators following the skill may apply the wrong recovery unless both `ADMISSION_RESULT` values, the `[DESIGNED]` title precondition, and parsing `ADMISSION_RESULT=` from stdout are documented (with resume carve-out as needed), consistent with `scripts/implement-admission.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_4: `scripts/implement-admission.md` resume omits `[DESIGNED]` / `missing-designed-prefix` bypass
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Resume semantics paragraph documents skipping the managed-title / managed-prefix path on resume but does not clearly state that the `[DESIGNED]` / `missing-designed-prefix` gate is also skipped under resume, which can mislead readers relative to `SECURITY.md` and implementation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_6: Clarify-only success path vs `[DESIGNING]` then `[DESIGNED]` story
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: Clarify-loop success path may apply a designed rename without a prior designing rename, so an issue could reach `[DESIGNED]` without ever having `[DESIGNING]` on that path—either add the designing step in the clarify branch or narrow the documented requirement / plan table so behavior and docs match.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_7: Stale “in-progress” wording in implement round-trip docs
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Round-trip / argv prose still refers to “in-progress” instead of current implementing / `[IMPLEMENTING]` vocabulary, causing mild operator-facing doc drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_8: No hermetic test for combine-issues jq prefix filter
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: `.claude/skills/combine-issues/scripts/fetch-combinable-issues.sh` jq prefix filter lacks a fixture test; a regex typo could silently widen or narrow exclusions and hide or expose the wrong issues.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_9: `[DESIGNED]` title as trust boundary vs plan body
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: `[DESIGNED]` in the title is collaborator-mutable and is not cryptographic proof that design completed or that `larch:plan` body is present/stale-safe; document the trust boundary or strengthen admission with body/plan coupling if required.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


