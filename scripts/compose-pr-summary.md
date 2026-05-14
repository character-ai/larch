# compose-pr-summary.sh contract

`scripts/compose-pr-summary.sh` emits 1-3 Markdown bullet lines for the
`## Summary` section of the PR body, replacing the static placeholder on
SIMPLE-path `/implement` runs.

Inputs:

- `--plan-goals-file PATH` is required. The file must exist and be
  non-empty; the `## Goal` section must contain at least one non-blank
  line.

Output (stdout):

- **Bullet 1**: The first non-blank body line of the `## Goal` section
  from the plan-goals file.
- **Bullet 2**: Test-file change count (files matching `test-*.sh`)
  derived from `git diff --name-only` against merge-base with
  `origin/main`. Omitted when count is zero.
- **Bullet 3**: Cross-cutting change note listing the top-level
  directories involved, when changed files span more than two such
  directories. Omitted otherwise.

The script exits non-zero (and emits nothing to stdout) when the
plan-goals file is missing, empty, or lacks a Goal line, and when the
first bullet cannot be composed. This allows `ship-pr.sh` to fail-open
and fall back to `"- Implemented the requested changes."`.

Primary caller: `scripts/ship-pr.sh` `run_pr_prep_phase`.

Harness: `scripts/test-compose-pr-summary.sh`.
