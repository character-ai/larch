### FINDING_1: [OUT_OF_SCOPE] Required core flags still use Bash expansion errors
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `--classification` and `--output` still use `${2:?...}` while the boolean flags now use `require_value`, leaving inconsistent exit code and stderr behavior for required-flag mistakes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] Nullable flag arity checks remain duplicated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Nullable and budget flags still repeat inline `if [[ $# -lt 2 ]]` checks before `take_value`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] Related script still permits flag-shaped next token until enum validation
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `scripts/eval-research.sh` has a related pre-existing parsing asymmetry where boolean flags can accept a `--*` next token before later enum validation fails.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] Harness sibling doc is stale
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-write-run-params.md` still references schema v2 and does not document the expanded missing/empty boolean rejection coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] Invalid enum tests only assert failure
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Invalid `maybe` cases for the boolean flags still use a weak “must not succeed” assertion instead of checking `exit 2` and the expected stderr shape.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] Whitespace-only boolean values are not rejected by `require_value`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `require_value` rejects unset or empty argv values, but whitespace-only tokens pass to later enum validation and fail with a different message.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
