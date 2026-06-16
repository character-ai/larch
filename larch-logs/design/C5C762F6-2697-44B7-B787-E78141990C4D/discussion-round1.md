## Decision 1: Default --kind
- **Question**: What should the default --kind be when /rebalance-tests runs with no kind flag?
- **Resolution**: `all`. A bare invocation rebalances harness shards and Python shards together in one branch, one commit, one PR, one verification run set. Matches the renamed general skill.
- **Source**: user

## Decision 2: Rename mode
- **Question**: How should the rename from /rebalance-test-harnesses to /rebalance-tests handle the old name?
- **Resolution**: Hard rename. Move files to `.claude/skills/rebalance-tests/`, delete the old directory, update the path-pinning test. No back-compat alias. The old `/rebalance-test-harnesses` name stops working.
- **Source**: user

## Decision 3: Verification exit semantics
- **Question**: What exit semantics should each verification leg use?
- **Resolution**: Asymmetric. The Python leg fails closed (non-zero exit on zero parsed rows, missing shard coverage, or spread over threshold). The harness leg stays warning-only (exit 0), its current contract unchanged.
- **Source**: user

## Decision 4: --n-python-shards mismatch handling
- **Question**: What happens when --n-python-shards differs from the shard count CI actually runs?
- **Resolution**: Abort before any write or PR, with a clear error naming the observed CI shard count. Follows from the fail-closed Python preference: never ship an assignment map for a shard count CI does not run.
- **Source**: user (inferred from Decision 3) + codebase

## Decision 5: README.md scope
- **Question**: Does README.md reference /rebalance-test-harnesses and need updating?
- **Resolution**: No change. A repo grep (excluding larch-logs, .git, pytest_cache) found no live README reference to the old skill name.
- **Source**: codebase

## Decision 6: Full rename surface
- **Question**: Which live files reference the old skill name and must change?
- **Resolution**: Exactly five surfaces: the three skill files (`.claude/skills/rebalance-test-harnesses/SKILL.md`, `scripts/rebalance.py`, `scripts/rebalance.md`), the path pin in `python/test_rebalance_script.py`, and `docs/linting.md`. `_REPO_ROOT = Path(__file__).resolve().parents[4]` stays correct after the move (same directory depth).
- **Source**: codebase

## Hard constraints (binding scope)
- **Must not silently reduce CI test coverage.** `python/conftest.py` selecting tests by the assignment map must fail closed on malformed JSON and fall back to global collection-index round-robin when the map's max shard ID does not equal the active shard count. A stale or bad map must never drop tests from every shard.
- **Harness path stays behavior-equivalent for `--kind harness`.** Keep the existing harness steps, packer, Makefile read/write, partition validation, and warning-only verification (exit 0). Do not broad-refactor `main()`.
- **Checked-in `python/shard-assignments.json` starts as `{}`** (round-robin only) so adding the file does not change current CI behavior until the rebalancer populates it.
- **Out of scope**: changing the harness verification contract; uncommenting auto-merge; touching README.md; running pytest collection locally in the script (use CI timing nodeids as the assignment set).

Decisions resolved: 6 (plus binding constraints).
