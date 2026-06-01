Normalizing the nine reviewer inputs into merged findings with stable IDs, max severity, and verbatim suggested revisions.


### FINDING_1: Exhaustion routing vs entry-based `ci-fix-exhausted` flag
- **Reviewer(s)**: Codex-Arch, Codex-Pragmatic, Codex-Requirements, Codex-dyn-dual-impl-parity
- **Severity**: important
- **Concern**: The plan requires push/launcher/no-tier failures to stay on the stall path (exit 4 / `STALLED`), but also proposes setting the ready-log exhaustion/dispatch flag when `run_ci_fix_vendor`, `run_ci_fix`, or the per-job local fix loop is entered, and rewrites launcher-failure exhaustion tests to expect `ci-fix-exhausted` (exit 3). Current Bash/Python helpers collapse launcher and push failures into generic waterfall failures, so an entry-based flag would route carve-out failures to exit 3; preserving carve-outs would fail the planned tests. Implementers face a single inconsistent predicate across plan, flag semantics, and tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Pick one predicate and encode it consistently. For minimum change, keep push launcher and no-tier failures as exit 4 by setting ci-fix-exhausted only for the intended real fixer-exhaustion class, returning or detecting distinct push/no-tier/all-launcher failure details, and aligning the Bash/Python tests with that split.
  - From Codex-Pragmatic: Make one contract. For the safer minimum-change path, keep launcher/push/no-tier failures on exit 4, only set the ready-log exhaustion flag after an actual code-fix attempt runs, and leave vendor_loop_ci_fix_exhausted asserting exit 4; otherwise remove the launcher-failure carveout everywhere.
  - From Codex-Requirements: Track the terminal cause/status separately. Set ci-fix-exhausted only for actual fixer-attempt exhaustion after a ready-log dispatch, and explicitly keep no tiers/all tiers failed/launcher failure/push failure on existing exit_stall or Outcome.STALLED paths; add a regression for at least one launcher/push failure exception.
  - From Codex-dyn-dual-impl-parity: Revise the plan to set the exhaustion flag only from an explicit code-fix exhaustion signal and exclude push failed, no launcher tiers, and launcher-health failures; expose a separate dispatched/exhausted bool or status from the fixer if needed.

### FINDING_2: Upfront log reuse not limited to ready captures
- **Reviewer(s)**: Cursor-Edge, Cursor-Innovation
- **Severity**: important
- **Concern**: The plan tells `evaluate_failure` to reuse the upfront `collect_failed_logs` result on the first fix-loop iteration (after skipping a blind rerun for deterministic/unreadable/cap cases) without requiring `logs.state == ready`. Reusing an `in_progress` or `error` capture on iteration 1 can defer or mis-route the first outer attempt, call `run_ci_fix` with empty/non-ready logs, and break parity with Bash re-fetch at `scripts/ship-pr.sh:2532-2534`, `gh-run-logs` rc=3 deferral, and `test_evaluate_failure_in_progress_defers_launch`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Only reuse the upfront capture when logs.state == ready (and only skip the first collect_failed_logs call in that case); otherwise keep per-attempt refresh
  - From Cursor-Innovation: Reuse the upfront capture only when `logs.state == "ready"`; otherwise leave the fix loop unchanged and call `collect_failed_logs` on the first iteration (same as later attempts). Mark Bash log reuse as optional and apply the same ready-only rule if implemented.

### FINDING_3: Re-sourcing legacy `#2632` include runs stale top-level tests
- **Reviewer(s)**: Codex-Innovation, Codex-dyn-test-plan-gaps
- **Severity**: important
- **Concern**: The plan re-sources `scripts/test-ship-pr-fix-loop-2632.inc.sh`, whose top-level body runs every `#2632` case (e.g. t5/t6/t21), not only the new `#3334` regressions. That can force unrelated stale harness failures, add runtime, and conflict with the planned exit-3 `ci-fix-exhausted` contract vs existing rc-4 assertions—breaking minimum-change scope and `make test-ship-pr-fix-loop`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Put the two #3334 rerun-gate regressions directly in scripts/test-ship-pr.sh or move them to a new tiny sourced helper with no top-level legacy invocations
  - From Codex-dyn-test-plan-gaps: Minimum-change fix: add the two #3334 rerun-gate regressions inline in scripts/test-ship-pr.sh instead of sourcing the whole include, or guard the include auto-run block and update any retained ready-log exhaustion cases to the new exit-3 contract

### FINDING_4: Bash/Python parity gap on `ci-failed-jobs` in progress
- **Reviewer(s)**: Codex-dyn-dual-impl-parity
- **Severity**: important
- **Concern**: When `gh-run-logs` returns rc0 but `ci-failed-jobs.sh` returns rc3 (`in_progress`), proposed Bash tracking keyed on `gh_logs_rc==0` can fall through to `run_ci_fix_vendor` while Python backs off on `jobs_state == in_progress` before `run_ci_fix`. Exhaustion can then exit 3 in Bash and `STALLED` in Python.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-dual-impl-parity: Add a Bash ci_failed_rc == 3 branch matching Python jobs_state == in_progress: no fixer dispatch, no ready-log dispatch flag, backoff/continue, plus a parity regression test
