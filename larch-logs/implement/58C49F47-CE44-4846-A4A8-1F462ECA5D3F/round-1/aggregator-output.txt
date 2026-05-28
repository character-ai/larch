### FINDING_1: emit-design-plan-preview skips allowlist validation before early exits and sentinel writes
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `skills/design/scripts/emit-design-plan-preview.sh` validates too late for `step3`/`gatec` early exits. Missing or empty `plan.txt` can exit successfully before allowlist validation, and `step3` can create `.step3-entry-plan-printed` under a disallowed existing directory. The existing sentinel short-circuit can also skip validation on later runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_2: render-plan-review-prompt rejects not-yet-created allowlisted tmpdirs before shared validation
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `skills/design/scripts/render-plan-review-prompt.sh` gates allowlist validation behind `! -d`, so valid allowlisted session paths that do not exist yet receive a generic directory error instead of the shared allowlist diagnostic used by peer scripts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: design-pause-save reports missing tmpdir before allowlist violation
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `scripts/design-pause-save.sh` checks `-d` before `larch_design_tmpdir_validate`, so a non-existent disallowed path reports `tmpdir-missing` instead of `tmpdir-invalid`, obscuring the configuration error.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_4: Missing contract-level negative harnesses for tmpdir validator wiring
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: CI only covers the shared tmpdir validation library, not contract-preserving negative paths in individual consumers. Future edits could break rc/KV/stdout mappings for allowlist failures without detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_5: SECURITY.md overstates tmpdir validation ordering
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `SECURITY.md` claims all consumers validate before any tmpdir read/write, but `emit-design-plan-preview.sh` can still write the step3 sentinel before validation until the script ordering is fixed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_6: finalize-plan uses the same status for allowlist failure and missing directory
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `skills/design/scripts/finalize-plan.sh` maps allowlist rejection to `FINALIZE_PLAN_STATUS=missing-design-tmpdir`, the same token used for missing directories, making operator telemetry and tests ambiguous.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_7: Harnesses lack allowlist failure coverage for plan review and waterfall paths
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `test-plan-review-loop.sh` and `test-revise-plan-with-waterfall.sh` use `mktemp` under `TMPDIR` only, so new allowlist failure behavior is not exercised in those harnesses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_8: revise-plan-with-waterfall doc overstates validation timing
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `skills/design/scripts/revise-plan-with-waterfall.md` says validation runs immediately after the required argument check, but the script validates only after directory and other precondition checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] Env-based DESIGN_TMPDIR consumers lack allowlist validation
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `skills/design/scripts/render-final-summary.sh` consumes `DESIGN_TMPDIR` from the environment without allowlist validation. This was identified as pre-existing and outside the argv-consumer sweep.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] No repo-wide wiring lint enforces validator calls
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The plan deferred a grep or harness guard for per-caller validator wiring, leaving no CI check if a consumer later drops the source line.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] Missing sibling doc for emit-design-plan-preview
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `skills/design/scripts/emit-design-plan-preview.sh` lacks a sibling `.md` documenting validator and warning contracts. Reviewers marked this as pre-existing or deferred.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] finalize-plan status ambiguity should be tracked as follow-up
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `skills/design/scripts/finalize-plan.sh` reuses `FINALIZE_PLAN_STATUS=missing-design-tmpdir` for allowlist rejection. This matches the plan but leaves ambiguous telemetry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] revise-plan-with-waterfall requires directory existence before validation
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `skills/design/scripts/revise-plan-with-waterfall.sh` requires `-d` before allowlist validation, so a not-yet-created but allowlisted path fails with a directory error before validation. Reviewer marked this as pre-existing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] Validator permits nonexistent allowlisted paths that callers may cd into
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `scripts/lib-design-tmpdir.sh` permits nonexistent allowlisted paths, while some callers immediately `cd`, risking unstructured `set -e` failures. Reviewer marked this as pre-existing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] test-emit-design-plan-preview lacks allowlist negative regression
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `skills/design/scripts/test-emit-design-plan-preview.sh` does not include a disallowed-tmpdir negative case, so drift in step3 ordering would not be caught.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] PR stacks quiet-log bridge changes with tmpdir commit
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Branch `76739286` stacks #3136 quiet-log bridge changes under the tmpdir commit, requiring reviewers to separate tmpdir plan-fidelity concerns from breadcrumb and exit-code changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
