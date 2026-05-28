### FINDING_10: Single-quoted awk body closer misses pipeline suffixes
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `awk '...' | cmd` can leave `in_single_body` set, causing later shell lines to be mis-scanned as awk body content.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_13: Missing test for lint-fix-loop-only HEAD advance
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The ship-pr harness lacks a case where the vendor exits 0 without edits while lint-fix-loop commits, so a faulty HEAD comparison could misclassify that path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_14: Rule 1 continuation joining lacks coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Rule 1 backslash continuation and split `-v VAR =val` parsing are not covered by harness fixtures, leaving regressions without CI signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_15: Rule 2 callsite token coverage is incomplete
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Rule 2 tests cover only `match(` and `~`, leaving `gsub`, `sub`, `split`, and `!~` callsite-token regressions uncovered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_22: Rule 1 does not skip shell comments
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Rule 1 can lint commented shell examples such as `# awk -v re='...'`, producing false positives for code that never executes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_4: Heredoc awk body detection lacks harness coverage
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Heredoc awk body Rule 2 support is implemented and documented but lacks a test fixture, so delimiter or body-span regressions could ship silently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_8: HEAD advance check can be masked by non-vendor commits
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The HEAD equality check runs after broader stage/push work, so refresh-run-logs or lint-fix-loop commits can advance HEAD even when the vendor made no CI fix, masking the no-commit escalation path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_9: Regression test omits refresh-run-logs commit masking
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: The #3134 regression test does not model `refresh-run-logs` committing tracked logs, so production behavior could still mask no-commit detection while the harness passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


