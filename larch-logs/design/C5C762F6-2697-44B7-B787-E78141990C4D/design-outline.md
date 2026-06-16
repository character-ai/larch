## Proposed Design Outline

### Goals
- Rename the dev-only skill `/rebalance-test-harnesses` to `/rebalance-tests` (hard rename, no alias).
- Add Python pytest matrix shard rebalancing from CI `--durations=0` timing.
- Unify both legs under `--kind {harness,python,all}`, default `all`.

### Non-goals
- Changing the harness verification contract (stays warning-only, exit 0).
- Uncommenting auto-merge, touching README.md, or running pytest collection locally in the script.
- Broad-refactoring `rebalance.py` `main()`.

### Approach sketch
- Move the skill directory; update the path pin in `python/test_rebalance_script.py` and `docs/linting.md`.
- Add `python/pytest_ci_timing.py`, a stdlib parser mirroring `python/harness_ci_timing.py`.
- Teach `python/pytest_sharding.py` and `python/conftest.py` to honor a checked-in `python/shard-assignments.json`, with global collection-index round-robin fallback and fail-closed on bad maps.
- Add `--kind` and `--n-python-shards` to `rebalance.py` with minimal `main()` change, kind-aware staging/commit, and `--kind all` write ordering (Makefile + partition validation before assignments JSON).
- Asymmetric verification: the Python leg fails closed; the harness leg stays warning-only.

### Surfaces in scope
- `.claude/skills/rebalance-tests/`: `SKILL.md`, `scripts/rebalance.py`, `scripts/rebalance.md` (moved from old path).
- `python/pytest_ci_timing.py` (new), `python/pytest_sharding.py`, `python/conftest.py`, `python/shard-assignments.json` (new `{}`).
- Tests: `python/test_pytest_ci_timing.py` (new), `python/test_pytest_sharding.py`, `python/test_rebalance_script.py`.
- `docs/linting.md`.

### Open questions
- None. Round 1 resolved default kind (`all`), rename mode (hard), and verification semantics (asymmetric).
