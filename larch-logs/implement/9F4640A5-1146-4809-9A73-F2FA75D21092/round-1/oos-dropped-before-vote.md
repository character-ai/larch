### OOS_1: [OUT_OF_SCOPE] architecture: centralize review-round parsing helper
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-gate-render
- **Severity**: latent
- **Concern**: Review-round parsing is duplicated instead of sharing the existing helper, which increases drift risk between Gate C and Step 3.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From dyn-dyn-gate-render: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] Re-render after See full plan still advertises a hidden option
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: nit
- **Concern**: After `--without-see-full-plan`, the question text still mentions See full plan even though that option is removed. That creates a prompt/copy mismatch on the rerendered Gate C prompt.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Thread `without_see_full_plan` into `_gate_c_question()` and render no-see-plan variants for below-cap and at-cap prompts.

