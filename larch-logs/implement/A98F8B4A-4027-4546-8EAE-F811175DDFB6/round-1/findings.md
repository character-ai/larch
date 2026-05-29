### FINDING_1: [OUT_OF_SCOPE] write_then_recover can mark degraded missing-file recovery as complete
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `write_then_recover` touches the spy after any successful `recovery_merge_if_needed` return, including the missing-file warn-only path where no merge/file-present recovery occurred. This can overstate recovery completion if the helper is reused after a writer exits 0 without creating output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_2: Case 7 only covers pre-I/O enum validation failure
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Case 7 uses invalid `--classification BOGUS`, which fails before file I/O. It does not cover other non-zero writer failures such as jq or atomic-write errors, so regressions in post-validation failure handling could remain untested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_3: Case 7 and 7b setup formatting is denser than prior cases
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Cases 7 and 7b use compact one-line setup while cases 1-6 use a more scannable per-line pattern, making future edits harder to compare.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: Case 7 warning assertion is less stable than Case 6
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Case 7 checks a warning substring while Case 6 pins full warning equality, so warning text edits could make the cases drift independently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] Markdown purpose omits Case 6
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The sibling markdown purpose list omits Case 6, making the exercised coverage harder to discover without reading the shell harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] Step 0b guard and merge logic is duplicated
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The harness duplicates Step 0b guard/merge behavior rather than testing the live SKILL bash blocks directly, creating drift risk across the duplicated surfaces.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] relevant-checks does not route this harness directly
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `scripts/relevant-checks.sh` lacks a mapping from `scripts/test-step0b-router-flag-recovery.sh` or related `write-run-params.sh` changes to `make test-step0b-router-flag-recovery`, so local relevant checks may skip the new cases.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] SKILL heading suggests recovery on write failure
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The `skills/design/SKILL.md` section title around Step 0b can be read as allowing recovery on write failure even though the preceding prose aborts first, which may invite future prose drift or block reordering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
