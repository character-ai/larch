### FINDING_1: migrated-scripts.tsv omits harness retirement rows
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Codex-Generic
- **Severity**: important
- **Concern**: The plan’s `### UPDATED: python/migrated-scripts.tsv` subsection (and related prose) requires retiring all four Bash surfaces — helper `oos-file-conflict-deps.{sh,md}` plus harness `test-oos-file-conflict-deps.{sh,md}` — but the enumerated manifest rows cover only the helper pair. If the implementer deletes all four files but registers only two rows, `make lint-retired-scripts` will not enforce harness literals still referenced in `Makefile`, `agent-lint.toml`, `docs/linting.md`, and `scripts/residual-bash-paths.txt`, so migration can appear clean while stale harness references remain unguarded.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Under ### UPDATED: python/migrated-scripts.tsv enumerate all four paths: skills/implement/scripts/oos-file-conflict-deps.sh, skills/implement/scripts/oos-file-conflict-deps.md, skills/implement/scripts/test-oos-file-conflict-deps.sh, skills/implement/scripts/test-oos-file-conflict-deps.md
  - From Cursor-Pragmatic: Add explicit bullets for `skills/implement/scripts/test-oos-file-conflict-deps.sh` and `skills/implement/scripts/test-oos-file-conflict-deps.md` in the migrated-scripts.tsv section (same `#4967` rows as the helper siblings)
  - From Codex-Generic: Add the two missing rows: skills/implement/scripts/test-oos-file-conflict-deps.sh and skills/implement/scripts/test-oos-file-conflict-deps.md


