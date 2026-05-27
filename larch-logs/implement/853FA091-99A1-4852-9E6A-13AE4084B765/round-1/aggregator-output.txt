### FINDING_1: Step 3 review cap is not enforced
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Step 3’s cap guard, round-number handling, and “MUST ALWAYS” prose conflict. The guard sets non-persisted state, the later `plan-review-loop.sh` launch still runs, and `$count` may be unset across Bash fences. After reaching the SIMPLE/HARD review cap, the orchestrator can still launch external review panels or call the driver with an empty/wrong `--round-num`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

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

### FINDING_7: [OUT_OF_SCOPE] Classification warnings are hidden in final summary
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: stderr from `read-design-classification.sh` is suppressed, so warnings on v1 run-params may not surface in the final summary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] Stale topology wording for implement review panel
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `skills/shared/topology.tsv` still has stale `workflow_path` wording for the implement review panel, which can confuse readers about the post-2956 tier model.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_9: Plan review loop cap ownership docs are misleading
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `skills/design/scripts/plan-review-loop.md` says Gate C owns cap enforcement, which may lead implementers to put counter logic in `plan-review-loop.sh` instead of keeping Step 3 responsible for skipping and Gate C responsible for omitting Re-run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

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

### FINDING_12: Plan validator unconditional behavior lacks harness coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: There is no harness directly invoking `invoke-plan-validator.sh` for SIMPLE and HARD fixtures, so quick-mode skip behavior could reappear in the helper without test coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_13: TRIVIAL_DOC_ONLY rejection test does not assert exit code
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-write-run-params.sh` checks the stderr message for rejected `TRIVIAL_DOC_ONLY` but does not assert the required exit status `2`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_14: Plan review prompt allows control-character path injection
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `render-plan-review-prompt.sh` embeds the plan file path in external reviewer prompts without rejecting newline or control-character paths, allowing a malicious path to split the prompt and inject instruction-like lines.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_15: Classification grep fallback can misclassify malformed run params
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `read-design-classification.sh` falls back to matching `SIMPLE` or `HARD` substrings in raw file bytes. Malformed run-params containing decoy strings could select the wrong tier and alter caps or reviewer emphasis.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_16: Empty review-round counter is treated as zero
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: An empty `review-round-count.txt` is treated as `0` without warning, allowing extra review rounds without audit visibility if the counter file is truncated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_17: Gate C prompt still offers Re-run at cap
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The Gate C prompt template still always includes three options, so at cap the user may still see Re-run and re-enter Step 3 until some later cap notice intervenes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
