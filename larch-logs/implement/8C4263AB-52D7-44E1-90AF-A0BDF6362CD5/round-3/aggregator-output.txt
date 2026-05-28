### FINDING_1: Indented canonical contains lines are silently skipped
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `parse_contains` uses a fixed `substr(text,9)` offset even though the matcher permits leading whitespace, so indented canonical `contains "$VAR" ...` assertions can be ignored without failing or warning.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_2: Double-quoted backtick pins are skipped
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The pin verifier skips static double-quoted literals containing backticks, including several `test-design-structure.sh` pins, so local `relevant-checks` can pass while CI later catches drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_3: Full-repo test-script scan adds unnecessary local-check cost
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The pin phase scans all `test-*.sh` harness files during `relevant-checks`, which can add unnecessary O(all harness files) cost for small edits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] PR mixes unrelated #3064 and #2828 surfaces
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: The branch appears to combine pin-verification work with readability-preamble changes, making review, plan-fidelity assessment, and bisecting harder.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] Bash 3.2 portability coverage is only static
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: The portability test relies on static source checks instead of actually running the subject under Bash 3.2 or the planned POSIX-like invocation, so runtime-only portability regressions could pass the harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_6: Deletion-only paths bypass pin verification
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Deletion-only or no-regular-file changed-path flows can exit before running pin verification, allowing stale harness pins for deleted targets to pass local checks while failing later.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_7: Missing fixture for single-quoted Markdown-backtick pins
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The verifier harness lacks a fixture matching the exact single-quoted Markdown-backtick pin shape, so regressions on that real pattern may not fail `make test-check-contains-pins`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_8: Relevant-checks pin-phase test stubs the verifier
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `test-relevant-checks` pin phase 3f uses a stub verifier, so argument-wiring bugs against the production `check-contains-pins.sh` can evade that test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_9: Pin verifier runs too late for design-doc edits
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: For design-doc edits, `relevant-checks` runs the heavier `test-design-structure` path before the faster pin verifier, so the pin phase does not shorten the common failure path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_10: Direct-target order assertion is brittle
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: A `test-relevant-checks` assertion hard-codes target ordering, so harmless future reordering could fail the harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_11: Pin targets can escape repository root
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Resolved pin targets are not confined under `REPO_ROOT`, so changed test scripts can add out-of-tree probes and make CI reveal whether host-readable files contain chosen substrings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_12: Scoped non-canonical or unresolved assertions warn but still pass
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Non-canonical, mixed-quote, or unresolved-variable `contains` assertions only warn and do not fail when in changed-files scope, allowing the pin backstop to be bypassed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_13: Changed-files scoping is broader than plan-described target filtering
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `--changed-files` mode re-verifies pins when the test script changed, not only when the resolved target path changed, diverging from the stated target-path-only plan unless documented as intentional.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_14: Static double-quoted skip documentation omits dollar behavior
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `check-contains-pins.md` does not clearly document that any `$` byte, including escaped-dollar forms, causes static double-quoted literals to be skipped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_15: Agent-lint excludes lack explanatory comment
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: New `check-contains-pins` exclude rows in `agent-lint.toml` lack the explanatory block comment style used by adjacent validation-helper exclusions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
