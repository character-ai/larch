### FINDING_1: Manifest parity checks can miss lint/test filter drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: B6 row-count parity only proves both consumers see 11 rows, not that lint and harness use identical TSV filtering/path enumeration. Comment or blank-line handling could drift while the count remains unchanged.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_2: Fixture step IDs drift from TSV step_markers
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `write_skill_md_with_steps` hardcodes step IDs instead of deriving them from TSV `step_markers`, so renamed markers can leave placement fixtures testing stale IDs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: Step placement scans SKILL.md once per marker
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `check_step_placement` performs a full awk pass per step marker, adding avoidable repeated work on every lint run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: Style-line constants are duplicated between lint and tests
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Production lint and harness fixtures duplicate style-line strings, so fixture expectations can become stale when lint text changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: Relevant-check routing assertions are weaker for sections 3h/3i
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Sections 3h/3i only grep for a substring, so direct-target routing regressions may pass if the make banner format changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] BASH_COMPAT smoke is not real Bash 3.2 coverage
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: The Bash compatibility harness uses host Bash compat mode rather than a real Bash 3.2 interpreter, and some checks only compare exit status. Runtime-only or parser-output regressions could pass this smoke while still failing stronger Bash 3.2 coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] Design edits route through multiple costly direct targets
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Design edits trigger three direct make targets, adding local latency through foreground, structure, and pin harness checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] test-design-structure.sh edits do not route to its harness
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Edits to `scripts/test-design-structure.sh` do not trigger `make test-design-structure`, so structural regressions in that harness can slip past relevant-checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] Step marker lines with same-line directives are ignored
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Step-placement awk skips immediately after matching a step marker, so a readability directive on the same physical line as the marker is not counted toward that step.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_10: Pin harness does not run scanner against production line shape
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The harness never runs `check-contains-pins` against the real repo or `test-design-structure.sh`, so CI can pass even if the scanner breaks on the production double-quoted pin shape that motivated the drift fix.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_11: TSV paths are not contained to repo root before reads
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Manifest paths are joined as `ROOT/path` without rejecting traversal, absolute paths, or symlink escapes, so lint could read outside the intended tree during CI or fixture runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_12: Double-quoted pin unescaping does not match Bash for non-special escapes
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `unescape_double_body` keeps unrecognized escapes as two characters, while Bash removes the backslash before non-special characters in double quotes. Pins containing escapes like `\n` or `\t` can be checked against the wrong literal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_13: Sketch count uses substring semantics despite exact-line documentation
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Sketch enforcement uses `grep -Fc` substring matching while other modes use exact-line matching, allowing embedded prompt lines to satisfy the count contrary to the documented exact-line contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_14: TSV step IDs are interpolated into awk regexes without validation
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Regex metacharacters in TSV `step_markers` IDs can break or skew placement matching because the IDs are interpolated directly into awk regexes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_15: Duplicate step markers can hide missing directives
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Duplicate `<!-- step:id -->` markers reset placement counting, so an empty first segment and populated later segment can pass even if the earlier step body lacks the required directive.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_16: expected_count accepts leading-zero values
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `validate_expected_count` accepts leading-zero digit strings, so values like `04` can produce confusing mismatches instead of clear schema errors or normalized comparisons.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] TSV-only edits do not route to readability preamble harness
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: TSV-only edits may skip `test-lint-readability-preamble` when pre-commit is bypassed, leaving manifest-related regressions to later checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] Single-quoted pin scanning misses escaped single quotes
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Single-quoted literals still use a naive index scan, so escaped single quotes in pins are not verified correctly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_19: Harness does not validate expected_count despite shared TSV contract
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: The shared TSV contract says lint and harness reject invalid `expected_count`, but only the lint script validates it; the harness can ingest malformed rows while building fixtures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
