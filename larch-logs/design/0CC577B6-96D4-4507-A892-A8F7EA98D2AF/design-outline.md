## Proposed Design Outline

### Goals
- In the `/implement` CI-fix path, push an already-rebased, re-bumped, lint-clean commit in one shot so the local "tests pass" verdict reflects the real merge base.
- Cut redundant CI runs and force-push churn caused by deferring rebase to the next `ci-wait` poll.
- Prefer a different fixer vendor when a fix did not actually resolve the failure.

### Non-goals
- No `ci-decide.sh` / `run_ci_phase` routing rework (Decision 1: guard-only; next-poll `ACTION=rebase` stays as the fallback).
- No #3132 ship-pr.sh Python rewrite; implement against the current bash `ship-pr.sh`.
- No new rebase / rebump / behind-count / lint-fix / push logic — reuse existing helpers only.

### Approach sketch
- After the fixer verifies locally and before the fix push, recheck behind-count via a helper extracted from the existing `ci-status.sh:177` source; if behind, call `run_rebase_rebump`, then re-verify failed jobs + lint on the rebased tree.
- Put the guard in the shared `_stage_and_push_ci_fixes` (Decision 3) so both the vendor-fix and per-job local-fix pushes are covered; push force-with-lease when a rebase occurred, plain push otherwise.
- Rotate the `run_ci_fix_vendor` waterfall start tier across `_max_fix` attempts (Decision 2), keeping all tiers eligible.
- Reuse `run_rebase_rebump`, `run_checks_with_lint_fix_loop`, `git-push.sh` / `git-force-push.sh`, and the existing vendor conflict-resolution handling — factor shared steps into one helper called from both sites.

### Surfaces in scope
- `scripts/ship-pr.sh` — `_stage_and_push_ci_fixes`, `run_ci_fix_vendor`, `run_evaluate_failure`, the `run_rebase_rebump` family.
- `scripts/ci-status.sh` — extract the behind-count computation into a shared, lightweight helper.
- `scripts/test-ship-pr.sh` and the rebase/rebump fix-loop regression harnesses; affected `.md` script siblings.
- `docs/workflow-lifecycle.md` and the run-logs contract docs, as needed.

### Open questions
- How the post-fix path resolves `BASE_TARGET` (non-fork `origin/main` vs fork `upstream/main`) when reusing the behind-count source.
- Whether to extract a named wrapper (e.g. rebase-then-push) or parametrize `_stage_and_push_ci_fixes` with a force-with-lease flag — settle in the plan / review.
