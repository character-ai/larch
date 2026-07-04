### OOS_1: [OUT_OF_SCOPE] Missing resume-mode coverage in shell-wrapper regression
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: latent
- **Concern**: The new shell-wrapper regression only covers the normal review-loop branch. The resume short-circuit modes (`--ready-to-commit` / `--record-only`) could regress without this test failing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: `Address the concern above.`

### OOS_2: [OUT_OF_SCOPE] Brittle ordering assertion in dynamic-archetypes validation test
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: The static source-order test for dynamic-archetypes validation is brittle and could fail on harmless shell refactors, such as reordering validation/export/banner lines without changing behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: `Address the concern above.`

