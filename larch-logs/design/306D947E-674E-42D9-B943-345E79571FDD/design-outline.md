## Proposed Design Outline

### Goals
- Enforce per-file directive **count** for `orchestrator-inline` rows, so removing one of N directives in a multi-directive file (notably SKILL.md with 4) fails the lint.
- Mirror the existing `external-prompt:<count>` manifest pattern for consistency.

### Non-goals
- Refactoring unrelated lint scripts or hooks.
- Moving, renaming, or rewriting any existing readability directive in SKILL.md or references.
- Adding markdown section / heading / line-range parsing.

### Approach sketch
- Extend `manifest_rows` rows for the `orchestrator-inline` variant from `path:variant` to `path:variant:expected_count` (SKILL.md→4, six references→1 each).
- In the `orchestrator-inline` branch, replace `grep -Eq` with `grep -Ec` and compare against `expected_count`; emit a count-mismatch error message naming the file, expected, and actual count.
- Update `scripts/test-lint-readability-preamble.sh` to (a) populate SKILL.md fixtures with 4 directives, (b) populate each reference fixture with 1, (c) add a regression case where SKILL.md has only 3 (one per-step directive removed) and assert lint fails with the count-mismatch message.

### Surfaces in scope
- `scripts/lint-readability-preamble.sh`
- `scripts/test-lint-readability-preamble.sh`

### Open questions
- None.
