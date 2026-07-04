### OOS_1: [OUT_OF_SCOPE] brittle awk extraction in parity harness
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: latent
- **Concern**: `scripts/test-hook-clone-ownership-parity.sh` uses an awk-based `extract_function` that stops at the first standalone `}` line inside a function body. Future helper refactors with nested brace constructs could truncate extraction and yield misleading pass/fail results.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] missing behavioral parity for completion-sentinel helper renames
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: latent
- **Concern**: The parity coverage does not exercise the renamed completion helpers `marker_step_completed` and `is_step_completed`, so one-sided edits could change step-completion detection without failing the clone-ownership parity check.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Add a behavioral-equivalence fixture for completion-sentinel logic in a follow-up; out of this plan’s non-goals.
  - From cursor-specialist-testing: Add a behavioral-equivalence fixture only if scope is expanded beyond this issue's explicit non-goals.

### OOS_3: [OUT_OF_SCOPE] missing behavioral parity for liveness helper renames
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: latent
- **Concern**: The parity coverage does not exercise the renamed liveness helpers `marker_is_live` and `is_marker_live`, so one-sided edits could change marker-liveness blocking behavior without failing the clone-ownership parity check.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Add a behavioral-parity fixture for liveness logic in a follow-up issue.
  - From cursor-specialist-testing: Add a behavioral-equivalence fixture only if scope is expanded beyond this issue's explicit non-goals.
