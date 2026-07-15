## Proposed Design Outline

### Goals
- Reconcile all cross-cutting files after Pieces 2-4 retire the pytest-twin bash harnesses.
- Ensure `scripts/residual-bash-paths.txt` lists only permitted runtime Bash plus the four delegation smokes.
- Confirm every remaining Bash harness belongs to exactly one shard and passes `make test-harness-shards-coverage`.

### Non-goals
- Introduce new test behavior or test cases (owned by Pieces 2-4).
- Delete harness scripts (Pieces 2-4 own deletions).
- Create or move harness shards beyond what timing data justifies.

### Approach sketch
- Survey residual-bash-paths.txt against the file tree after Pieces 2-4; remove stale entries.
- Run `make test-harness-shards-coverage --self-test` to validate shard coverage; fix any gaps.
- Sweep agent-lint.toml comment blocks and ARCHITECTURAL_INVARIANTS.md for retired-harness references.
- Query CI shard timings via `python/harness_ci_timing.py`; rebalance Makefile shards and `.github/workflows/ci.yaml` matrix only when imbalanced.
- Update `docs/linting.md` to reflect the measured final inventory.

### Surfaces in scope
- scripts/residual-bash-paths.txt
- scripts/test-harness-shards-coverage.sh (CARVE_OUTS, self-test fixtures)
- Makefile (shard assignment lines, conditional rebalance)
- agent-lint.toml (comment-block cleanup for retired harnesses)
- ARCHITECTURAL_INVARIANTS.md (test-step-7a.sh reference update)
- docs/linting.md (harness inventory section)
- .github/workflows/ci.yaml (conditional on timing evidence)

### Open questions
- None.
