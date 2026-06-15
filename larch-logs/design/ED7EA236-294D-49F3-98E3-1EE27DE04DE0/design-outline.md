## Proposed Design Outline

### Goals
- Delete `scripts/ship-pr.sh` and all its bash-only dependencies; remove `LARCH_SHIP_PR_IMPL=bash` selector from all docs/SKILL.md/AGENTS.md.
- Complete the relevant-checks Python cutover: port `run_relevant_checks` dispatcher in `checks.py` to call pre-commit/agent-lint/make-targets natively; port `check-contains-pins.sh` to Python; delete the entire relevant-checks/lint-fix-loop bash suite.
- Remove the dead `--codex-add-dir` flag from `python/agents.py` (its bash sibling `launch-review.sh` was already deleted in #4167).

### Non-goals
- No behavior change to ship-pr Python path (`python/ship.py`) or any shipped workflow.
- No port of `python/cli.py agent launch-review`'s core Codex/Cursor dispatch logic.
- No porting of CI-side helpers (`gh-pr-checks.sh`, `merge-pr.sh`, `create-pr.sh`, etc.) — those are not ship-pr.sh-only orphans.

### Approach sketch
- Delete ship-pr.sh + orphan libs (`lib-finalize-state-keys.sh`), test harnesses (`test-ship-pr-rebase.sh`, `test-ship-pr-oos-pr-prep.sh`), and `.md` siblings; update Makefile shards.
- In `checks.py` `run_relevant_checks`: replace the `check_script` subprocess with direct calls to `pre-commit run`, `agent-lint`, make direct-targets, and `check_contains_pins_main`.
- Add `check_contains_pins_main` to `python/checks.py` (port of `scripts/check-contains-pins.sh` AWK/bash logic).
- Repoint `review_and_fix.py`'s `_run_relevant_checks_captured` → `checks.run_relevant_checks` and `_run_lint_fix_loop` → `checks.run_lint_fix`.
- Remove `--codex-add-dir` from `python/agents.py` and its tests; strip LARCH_SHIP_PR_IMPL references from SKILL.md/docs/AGENTS.md; simplify conflict-resolution.md.
- Delete bash suite + harnesses; append to `python/migrated-scripts.tsv`; extend `python/test_checks.py` / `test_checks_bash_parity.py`.

### Surfaces in scope
- `scripts/ship-pr.sh` + `.md`, `scripts/ship-pr.md` (sibling doc), `scripts/lib-finalize-state-keys.sh` + `.md`
- `scripts/test-ship-pr-rebase.sh` + `.md`, `scripts/test-ship-pr-oos-pr-prep.sh`
- `scripts/relevant-checks.sh`, `scripts/run-relevant-checks-captured.sh`, `scripts/lint-fix-loop.sh`, `scripts/surface-lint-fix-stderr-tail.sh`, `scripts/check-contains-pins.sh` — each with `.md` and test harnesses
- `python/checks.py` (new `run_relevant_checks` dispatcher + `check_contains_pins_main`)
- `python/review_and_fix.py` (repoint 2 internal helpers)
- `python/agents.py` + `python/test_launch_review.py` (`--codex-add-dir` removal)
- `skills/implement/SKILL.md`, `docs/configuration-and-permissions.md`, `python/README.md`, `AGENTS.md` (LARCH_SHIP_PR_IMPL removal)
- `skills/implement/references/conflict-resolution.md` (single-driver simplification)
- `python/migrated-scripts.tsv`, `Makefile` (shard updates)
- `python/test_checks.py`, `python/test_checks_bash_parity.py` (extend/update)

### Open questions
- None.
