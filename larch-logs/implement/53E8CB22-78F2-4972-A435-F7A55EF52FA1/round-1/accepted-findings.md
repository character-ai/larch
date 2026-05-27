### FINDING_1: Missing regression test for outside-input move failure
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The guarded outside-input `mv` failure path is implemented but not covered by regression tests. A future regression could lose the non-fatal `REASON=dispatch-failed` behavior, clobber or alter the input ballot, or exit under `set -e` without CI catching it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_2: CLI docs show unsupported equals-form flag syntax
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: The CLI table documents `--allow-findings-outside-tmpdir=true`, but the parser accepts only split argv form. Operators copying the documented caveat get an unknown option instead of enabling outside input.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_3: Move-failure warning hardcodes findings.md
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: The new move-failure warning hardcodes `findings.md` despite generic `--findings-file` support, so outside-ballot failures with other names report a misleading preserved-file message.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt: Address the concern above.


