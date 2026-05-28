### FINDING_1: Step 0b sync pins do not cover recovery control flow
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The harness and edit-in-sync doc pin the jq filter text, but not the surrounding guard branches, jq-unavailable path, or jq failure handling. SKILL.md Step 0b recovery behavior can drift while current substring/filter checks still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_2: Harness markdown is missing from agent-lint exclusions
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-step0b-router-flag-recovery.sh` is excluded as a Makefile-only harness, but the sibling `.md` is not listed like peer harness pairs, creating inconsistent lint policy.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: Harness documentation has stale line references
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-step0b-router-flag-recovery.md` points maintainers to old `scripts/test-design-structure.sh` line numbers for per-arm jq pins, so future edits may inspect unrelated checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] Sibling router flags keep asymmetric invalid-argv parsing
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `--partition-requested` and `--brainstorm-requested` still use `${2:?...}` behavior while `--manual-gate-b` now explicitly rejects missing or empty values with exit 2, leaving future callers with inconsistent invalid-argv handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] Gate B stale-prose lint is intentionally narrow
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-absent-phrase-scope-output.txt
- **Severity**: latent
- **Concern**: The stale Gate B prose checks cover only `approval-gates.md` and `skills/design/SKILL.md`; other canonical docs and case variants can drift without CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-absent-phrase-scope-output.txt: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] Write-failure recovery remains unproven and possibly unreachable
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Current cases exercise successful writer runs plus recovery, but not the original writer-failure plus manual recovery scenario. SKILL.md also appears to require exit 1 on writer failure before the recovery block, creating ambiguity about whether the recovery path can run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_7: Missing run-params degraded path differs between harness and SKILL
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The harness hard-fails when `run-params.json` is missing, while SKILL.md says to warn and continue. That degraded missing-file path is untested and the harness contract can mislead future maintainers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_8: Jq merge failure path is not asserted for non-mutation
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: A jq merge failure aborts the harness, while production is expected to log and preserve `run-params.json`; corrupt JSON or failed merge behavior can regress without a checksum/non-mutation assertion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_9: Whitespace-only manual Gate B values get a different rejection path
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `--manual-gate-b " "` bypasses the empty-value check and fails later as an invalid enum, so callers matching the new “requires a value” stderr may mishandle whitespace-only argv.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_10: Broad `no auto-apply` absent needle can false-positive on accurate prose
- **Reviewer(s)**: dyn-absent-phrase-scope-output.txt
- **Severity**: latent
- **Concern**: The bare fixed-string `no auto-apply` absent check can fail CI on accurate non-stale documentation that happens to use that phrase outside the legacy Gate B contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-absent-phrase-scope-output.txt: Replace the short needle with a longer stale-only literal (e.g. a full legacy contract sentence from #3009-era docs) or add a second, context-aware check that only fails when `no auto-apply` appears in Gate B normative sections, not in loop-internals prose.
