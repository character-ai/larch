### OOS_1: [OUT_OF_SCOPE] The new `lint_bg_wait_coverage` plus pre-commit and CI wiring is extra surface for a feature that already ships with the marker and hook updates. `/review` has no current background fence to police, so this is future-proofing rather than required correctness.
- **Description**: [OUT_OF_SCOPE] The new `lint_bg_wait_coverage` plus pre-commit and CI wiring is extra surface for a feature that already ships with the marker and hook updates. `/review` has no current background fence to police, so this is future-proofing rather than required correctness.. Scenario: Future markdown edits under `skills/design`, `skills/implement`, `skills/review`, or `skills/review-and-fix` will inherit a repo-wide scan and workflow churn even though the present bug is already addressed by the hook and marker changes.
- **Reviewer**: Codex-Pragmatic
- **Severity**: latent
- **Focus area**: architecture
- **Location**: <TMPDIR>/plan.txt:117-171
- **Phase**: design



