### OOS_1: [OUT_OF_SCOPE] `docs/linting.md` stale on bare-basename matching rules
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The `make lint-retired-scripts` row still says "full repo-relative path matching only — never bare basenames," but the matcher now flags scoped `.claude/skills/**/*.md` bare basenames. Operators following that doc may misread legitimate lint failures or miss the `# lint-ignore` escape hatch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Update the table row to describe the scoped dev-skill markdown exception (or point at `python/migration_lint.py`).


