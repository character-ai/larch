# Review Round 1

- Mode: `diff`
- 10 accepted, 5 rejected (5 exonerated)

## Accepted Findings

### FINDING_1: Step 3 review cap is not enforced
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Step 3’s cap guard, round-number handling, and “MUST ALWAYS” prose conflict. The guard sets non-persisted state, the later `plan-review-loop.sh` launch still runs, and `$count` may be unset across Bash fences. After reaching the SIMPLE/HARD review cap, the orchestrator can still launch external review panels or call the driver with an empty/wrong `--round-num`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_10: Missing round-2 artifact test for plan review loop
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `skills/design/scripts/test-plan-review-loop.sh` only validates round-1 paths, so passing a wrong `--round-num` could go undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_11: Classification reader lacks focused fallback tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `scripts/read-design-classification.sh` has no unit harness covering SIMPLE, HARD, missing, and invalid cases, so tier fallback behavior can break silently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_13: TRIVIAL_DOC_ONLY rejection test does not assert exit code
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-write-run-params.sh` checks the stderr message for rejected `TRIVIAL_DOC_ONLY` but does not assert the required exit status `2`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_17: Gate C prompt still offers Re-run at cap
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The Gate C prompt template still always includes three options, so at cap the user may still see Re-run and re-enter Step 3 until some later cap notice intervenes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_2: Structural design harness was reduced instead of extended
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `scripts/test-design-structure.sh` appears to have removed broad existing structural assertions rather than adding new SIMPLE/HARD/cap pins on top, reducing regression coverage for unrelated design-skill contracts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_3: Timing report workflow path fallback and v2 fixtures are missing
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The planned fallback from `workflow_path` to `design_classification` is not implemented or covered by v2 timing fixtures. Design timing reports may still show `workflow_path` as `unknown`, and acceptance coverage does not exercise both run-params shapes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_4: Missing structural pins for Step 3 and Gate C cap prose
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The structural test suite does not pin the cap breadcrumb and Gate C cap contract strings, so cap enforcement prose can drift or be deleted without CI catching it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_5: Duplicate anti-pattern guidance
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `skills/design/SKILL.md` has duplicated “Why” text in anti-pattern #1, which can make maintainer guidance contradictory or noisy.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_6: Classification warnings are hidden in final summary
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `render-final-summary.sh` suppresses `read-design-classification.sh` stderr, so v1 or corrupt run-params fallback warnings may be hidden while summaries silently report HARD/default behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


