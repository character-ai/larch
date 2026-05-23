### OOS_2: `.claude/rules/timing-task-kind-allowlist.md` stale `(28g)` reference
- **Description**: The rule file claims assertion `(28g)` lives in `scripts/test-implement-structure.sh`, but that anchor is absent from the current tree (confirmed by reviewer searches; this is the same stale anchor cited in FINDING_4). Affected file: `.claude/rules/timing-task-kind-allowlist.md` (around the lines describing the assertion).
- **Reviewer**: Cursor-Edge
- **Phase**: design


### OOS_4: `.pre-commit-config.yaml` header comment vs reality
- **Description**: The header comment in `.pre-commit-config.yaml` claims "CI uses: make lint" while `.github/workflows/ci.yaml` actually runs `make lint-only` for the `lint` job (this is the underlying cause of FINDING_1's miscommunication). Affected file: `.pre-commit-config.yaml` (top-of-file comment block).
- **Reviewer**: Cursor-Pragmatic, Cursor-Requirements
- **Phase**: design

