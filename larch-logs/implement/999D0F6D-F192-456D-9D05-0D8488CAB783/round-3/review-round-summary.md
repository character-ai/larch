# Review Round 3

- Mode: `diff`
- 9 accepted, 5 rejected (5 exonerated)

## Accepted Findings

### FINDING_1: Rule 2 fixtures suppress the violations they are meant to test
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Cases 16-17 in `scripts/test-lint-awk-multibyte-regex.sh` place `lint-awk-multibyte-regex ok` pragmas inside fixture awk-body lines that are expected to violate Rule 2, so the lint can exit 0 or fail to exercise the intended pipeline-close / callsite coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_11: Missing ship-pr test for lint-fix-loop-only HEAD advance
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `scripts/test-ship-pr.sh` lacks coverage for vendor no-op plus committing lint-fix-loop behavior, where production should return success rather than misclassify as `first-fixer-non-health`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_12: Missing ship-pr test for stage-and-push failure classification
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: There is no test ensuring a `git-push` / stage-and-push failure after a no-commit vendor does not set `first-fixer-non-health`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_13: Multi-callsite Rule 2 test only asserts the first violation line
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Case 17 checks only the first reported violation, so regressions in later `gsub` / `sub` / `split` callsite detection could be missed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_19: Rule 2 is not applied to trailing continuation at EOF
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The END block applies only Rule 1 to a pending trailing continuation, so a non-ASCII regex token split across a final backslash continuation at EOF can evade Rule 2.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_2: Rule 2 `sub(` detection false-positives on `substr(`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `regex_callsite` matches bare `sub(`, which also matches `substr(`, so non-ASCII comments plus `awk substr()` can be incorrectly reported as `awk-body-nonascii-regex`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_20: Tier-order tests diverge from the plan’s sentinel filename
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The tier-order happy-path tests touch `README.md` instead of the plan’s literal `sentinel-fix.txt`, reducing traceability even if behavior is equivalent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_4: Test harness uses bare `grep` despite doc claiming `command grep`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-lint-awk-multibyte-regex.md` says the harness uses `command grep`, but the shell harness uses bare `grep`, which can terminate Claude Code Bash blocks on non-zero exit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_6: `ship-pr.sh` HEAD comparison can be defeated by run-log commits
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: The HEAD-non-advance check runs after run-log refresh may commit `larch-logs`, so a vendor no-op plus log-only commit can advance HEAD and avoid `first-fixer-non-health`, causing retries instead of autonomous CI-fix routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


