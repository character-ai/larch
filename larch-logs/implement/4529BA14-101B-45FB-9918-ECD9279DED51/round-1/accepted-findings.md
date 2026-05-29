### FINDING_1: unsafe eval while recovering prior reviewer env
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-eval-safety-output.txt
- **Severity**: important
- **Concern**: `scripts/write-design-current-env.sh` recovers reviewer keys by `eval`ing matching `export KEY=...` lines from the prior output file. A hand-edited or attacker-controlled `source-env.sh` can execute shell during refresh; eval errors may also be swallowed. Parse only strict `export KEY=true|false` lines, or use the repo's safe parser, and validate recovered values.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-eval-safety-output.txt: Address the concern above.


### FINDING_2: recovered reviewer booleans bypass validation
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Recovered `CODEX_PRESENT`, `CURSOR_PRESENT`, `CODEX_AVAILABLE`, and `CURSOR_AVAILABLE` values are re-emitted without `validate_bool`. Corrupt prior values such as `maybe`, empty values, or invalid enums can survive refresh and fail later in downstream reviewer dispatch or Step 3.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


