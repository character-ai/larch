# `scripts/test-ship-pr-rebase-phase14.sh`

Thin wrapper around `scripts/test-ship-pr.sh --section phase14`. Covers:

- `run_rebase_rebump` non-bump-only `rebase-push.sh --no-push --keep-on-conflict` exit 1 → `ship-pr.sh` **stalls (exit 4)** after the recovery waterfall exhausts, with `RESUME_PHASE=ship-pr-rrr-phase14`, `CALLER_KIND=ship_pr_pre_push`, resume flag, and the `aggregator-dispatch=conflict-resolution.md` stdout breadcrumb (no premature `rebase-push.sh --keep-on-conflict` execution-issues line). Includes a second stub scenario with a nested-path `CONFLICT_FILES` CSV (not only top-level `Makefile`) so deep-list parsing stays covered.
- `--resume-phase ship-pr-rrr-phase14` resumes `run_rebase_rebump` after simulated orchestrator success (flag consumed, full ship-pr completes).

Canonical assertions remain in `test-ship-pr.sh` so stub helpers (`make_repo`, `write_state`, `run_subject`) stay single-sourced.
