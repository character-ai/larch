## Decision 1: Rebase-site reconciliation
- **Question**: How should the new post-fix (rebase-before-push) re-check relate to the existing `ci-decide.sh` `ACTION=rebase` / `rebase_then_evaluate` routing?
- **Resolution**: Guard only. Insert a behind-count recheck + conditional `run_rebase_rebump` + force-with-lease in the post-fix path. Leave `ci-decide.sh` / `run_ci_phase` routing untouched; the next-poll `ACTION=rebase` becomes a no-op once the branch is up to date. No double-rebase regression because the branch is already up to date after the post-fix rebase.
- **Source**: user

## Decision 2: "Different fixer" rotation semantics
- **Question**: When the fixer exits 0 but local verify shows the failure is NOT fixed, what does "different fixer" mean on the `_max_fix` retry?
- **Resolution**: Rotate the waterfall's starting tier each attempt (attempt 1 cursor-first, attempt 2 codex-first, attempt 3 claude-first) while keeping every tier eligible. A tier may retry itself across attempts. Preserve `_max_fix` / exit-3 `ci-local-unfixable` / `first-fixer-non-health` semantics.
- **Source**: user

## Decision 3: Push-path coverage
- **Question**: Which CI-fix push paths get the rebase-before-push guard?
- **Resolution**: Both. Apply the guard in the shared `_stage_and_push_ci_fixes` (or a single shared wrapper) so both the vendor-fix path (`run_ci_fix_vendor`) and the per-job local-fix path (`run_evaluate_failure`, line ~2289) rebase-before-push. One helper; satisfies the no-duplication hard constraint.
- **Source**: user

## Decision 4: In-scope / out-of-scope
- **Question**: What is in scope vs out of scope?
- **Resolution**: In scope — re-sequence the CI-fix path in `scripts/ship-pr.sh`: recheck behind-count, conditional rebase via `run_rebase_rebump`, re-verify failed jobs + lint on the rebased tree, force-with-lease when a rebase occurred (plain push otherwise), and vendor start-tier rotation per Decision 2; plus regression-harness and docs updates. Out of scope — the #3132 ship-pr.sh Python rewrite (merge-conflict-risk neighbor only; proceed against current bash), and any broader CI decision-matrix refactor (see Decision 1).
- **Source**: codebase + issue

## Decision 5: Hard constraints (must not break)
- **Question**: What existing behavior must be preserved?
- **Resolution**: No code duplication — reuse `run_rebase_rebump` (and `rebase-push.sh`, `git-force-push.sh`, `drop-bump-commit.sh`, `commit-changelog.sh`), the `BEHIND_COUNT` source (`ci-status.sh:177` `git rev-list HEAD..$BASE_TARGET --count`), `run_checks_with_lint_fix_loop` / `lint-fix-loop.sh`, the `run_ci_fix_vendor` waterfall + `_max_fix`, `git-push.sh` (plain) / `git-force-push.sh` (post-rebase), and the same vendor conflict-resolution handling as `run_rebase_rebump`. Preserve the single-runner invariant, force-push safety (force-with-lease), `_max_fix` / exit-3 `ci-local-unfixable` / `first-fixer-non-health` semantics, and the fork path (rebase onto `upstream/main`). No double-rebase regression with the `ci-decide.sh` `ACTION=rebase` next-iteration path.
- **Source**: codebase + issue
