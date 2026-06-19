# Review Round 1

- Mode: `diff`
- 3 accepted, 3 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Stale `test-rebase-checkpoint-probe` docs in `docs/linting.md`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-migration-surface-output.txt
- **Severity**: important
- **Concern**: The Makefile target `test-rebase-checkpoint-probe` and `scripts/test-rebase-checkpoint-probe.sh` were removed, but `docs/linting.md` still documents `make test-rebase-checkpoint-probe` as runnable and as a `make lint` prerequisite via `test-harnesses-8`. Operators following the doc hit a dead target and may believe checkpoint-probe shell parity is still lint-gated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Remove or rewrite the row to point at python3 -m pytest python/test_push.py -k checkpoint and drop the false shard claim.
  - From codex-specialist-correctness-output.txt: Replace the row with the live pytest command for checkpoint coverage and remove the stale make lint prerequisite claim.
  - From cursor-specialist-edge-cases-output.txt: Remove the row or point it at python3 -m pytest python/test_push.py -k checkpoint and drop the incorrect shard-8 claim.
  - From cursor-specialist-testing-output.txt: Remove the row or replace it with python3 -m pytest python/test_push.py -k checkpoint (and note make test-implement-rebase-macro if desired); delete the test-harnesses-8 prerequisite claim.
  - From codex-specialist-testing-output.txt: Remove the stale row or point it at the retained Python checkpoint test command and correct shard text.
  - From dyn-migration-surface-output.txt: Delete the stale row or replace it with the live verification surface, e.g. `python3 -m pytest python/test_push.py -k checkpoint`, and point readers to `python/test_push.py` / `docs/python-migration.md` instead of a deleted Makefile target.


### FINDING_2: Checkpoint-probe pytest parity gaps after bash harness deletion
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-checkpoint-parity-output.txt
- **Severity**: important
- **Concern**: Deleting `scripts/test-rebase-checkpoint-probe.sh` left `python/test_push.py` relying heavily on mocks. Several retired harness scenarios are not clearly ported: mixed-conflict index behavior (cases 17–19), partial trivial-resolution conflict re-derivation (case 22), empty-continue / skip recovery (case 24), and related validation/phantom edge cases. Regressions in `checkpoint_probe_main`, `_resolve_trivial_conflict_file`, conflict-loop logic, or git stderr/index handling can pass CI while breaking `/implement` 1.r/4.r/7.r/7a.r routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Port missing harness scenarios into python/test_push.py or adjacent phantom tests before treating harness deletion as complete.
  - From cursor-specialist-edge-cases-output.txt: Add one disposable-git integration test for the skip recovery path.
  - From cursor-specialist-testing-output.txt: Add a tmp-repo integration test that exercises push checkpoint-probe through the empty rebase --continue and rebase --skip path.
  - From codex-specialist-testing-output.txt: Add a tmp-repo integration test that exercises push checkpoint-probe through the empty rebase --continue and rebase --skip path.
  - From dyn-checkpoint-parity-output.txt: Add an integration-style pytest (temp git repo, same shape as retired harness case 24) that runs `checkpoint_probe_main()` end-to-end and asserts rc=0, `ROUTE=continue`, empty `git diff --name-only --diff-filter=U`, and no `rebase-merge`/`rebase-apply` directory.
  - From dyn-checkpoint-parity-output.txt: Mirror bash case 22 with two trivial paths, succeed on the first checkout/add, fail on the second, and assert stdout contains only the remaining path and not the original comma-separated list.
  - From dyn-checkpoint-parity-output.txt: Add at least one real-git test for mixed conflict (case 19 shape) that asserts post-probe unmerged paths match emitted `CONFLICT_FILES` and that `--continue` was not invoked.


### FINDING_4: `_handle_empty_continue_rc3` continues after completed skip
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `_handle_empty_continue_rc3` calls `git rebase --continue` after every successful `git rebase --skip`, even when the skip already finished the rebase. For larch-log conflicts that resolve to an empty final commit, skip exits 0 with no rebase in progress; the subsequent `--continue` returns rc 3 and the checkpoint incorrectly bails.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: After git.rebase_skip(proc) succeeds, check git.rebase_in_progress(proc); if false, return RebasePushResult(exit_code=0).


