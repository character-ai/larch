### OOS_1: [OUT_OF_SCOPE] `chore(larch-logs)` flush is outside review scope
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: The reviewer explicitly marked this `chore(larch-logs)` flush as out of review scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] README still omits `--skip-approve` semantics
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: nit
- **Concern**: `README.md` still leaves the `/release` description row without the `--skip-approve` non-empty-window semantics that `docs/skills.md` already documents.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] Private release skill has no mechanical flag-parser coverage
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: `lint-skill-md-flag-signature` does not scan `.claude/skills/`, so the private release skill's inline Step 1 parser is not mechanically validated and could regress without CI catching it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.

