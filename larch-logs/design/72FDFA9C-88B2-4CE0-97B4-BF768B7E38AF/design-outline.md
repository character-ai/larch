## Proposed Design Outline

### Goals
- Eliminate the test-fixture leak into the live `larch-logs/` working tree by removing both `run-analysis.sh` test harnesses entirely.
- Leave `skills/report-tokens/scripts/run-analysis.sh` and the production env-var contract unchanged.

### Non-goals
- No migration of tests to `${TMPDIR}`-based fixtures.
- No new tests added in their place.
- No change to `run-analysis.sh` semantics (it must continue scanning a real git repo's `larch-logs/<skill>/`).

### Approach sketch
- Delete the two harness scripts, the orphaned `.md` sibling contract, and the orphaned `fixtures/recompute-run/` directory under `skills/report-tokens/scripts/`.
- Remove the two `make test-*` recipes, their `.PHONY` entries, and their listings in the `test-harnesses-13` and `test-harnesses-20` shard prerequisites in `Makefile`.
- Drop the now-stale `agent-lint.toml` `exclude=[…]` entry and the `docs/linting.md` row that documents `make test-report-tokens-recompute`.
- Drop the dangling "Rate harness: …" sentence in `skills/report-tokens/SKILL.md`.
- Add a single `### Removed` bullet under `## [Unreleased]` in `CHANGELOG.md` recording the deletion and citing #3121.

### Surfaces in scope
- `skills/report-tokens/scripts/test-report-tokens-recompute.sh`, `test-rate-assertions.sh`, `test-rate-assertions.md`, `fixtures/recompute-run/`
- `Makefile`
- `agent-lint.toml`
- `docs/linting.md`
- `skills/report-tokens/SKILL.md`
- `CHANGELOG.md`

### Open questions
- None.
