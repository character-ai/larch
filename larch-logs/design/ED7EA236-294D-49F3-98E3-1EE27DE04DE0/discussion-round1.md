## Decision 1: run_relevant_checks port approach
- **Question**: What should the Python `run_relevant_checks` do when `relevant-checks.sh` is deleted?
- **Resolution**: Port `run_direct_relevant_targets` routing table and pre-commit/agent-lint invocations to Python in `checks.py`. Run `pre-commit run`, `agent-lint`, direct make targets, and `check_contains_pins` natively via subprocess. Preserve the same log markers ("=== Running pre-commit ...", "=== Running agent-lint ===") so `_scan_checks_log_markers` continues working.
- **Source**: codebase

## Decision 2: orphan sweep scope (ship-pr.sh-only consumers)
- **Question**: Which scripts are ship-pr.sh-only orphans eligible for deletion?
- **Resolution**: `scripts/ship-pr.sh + .md`, `scripts/test-ship-pr-rebase.sh + .md`, `scripts/test-ship-pr-oos-pr-prep.sh` (no .md sibling), `scripts/lib-finalize-state-keys.sh + .md`. `lib-finalize-state-keys.sh` is deferred per #3780 in python-migration.md but ship-pr.sh is its only consumer — retiring it here unblocks #3780.
- **Source**: codebase

## Decision 3: --codex-add-dir removal target
- **Question**: Where does --codex-add-dir live now that launch-review.sh was already deleted (#4167)?
- **Resolution**: Remove `--codex-add-dir` from `python/agents.py` (parser, `_review_validate_codex_add_dir` helper, all call sites) and from `python/test_launch_review.py` (~5 tests). The 8-reference count from the issue was for the already-deleted bash harness.
- **Source**: codebase — `scripts/launch-review.sh` does not exist (deleted in 748647f10 / #4167)

## Decision 4: review_and_fix.py consumer repointing
- **Question**: Does review_and_fix.py need updating when run-relevant-checks-captured.sh and lint-fix-loop.sh are deleted?
- **Resolution**: Yes. `_run_relevant_checks_captured` (calls `run-relevant-checks-captured.sh`) → `checks.run_relevant_checks`; `_run_lint_fix_loop` (calls `lint-fix-loop.sh`) → `checks.run_lint_fix`. Also update `skills/review-and-fix/SKILL.md` which still references `run-relevant-checks-captured.sh`.
- **Source**: codebase

## Decision 5: Makefile targets to remove
- **Question**: Which Makefile targets/shards need updating for ship-pr test deletion?
- **Resolution**: Remove `test-ship-pr-rebase` from shard 15 and `test-ship-pr-oos-pr-prep` from shard 18. Remove both from `.PHONY` and their target bodies.
- **Source**: Makefile analysis
