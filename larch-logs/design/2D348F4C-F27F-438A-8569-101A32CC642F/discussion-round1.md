## Decision 1: Scope direction — code change vs documentation
- **Question**: Issue #2632 offers two paths: (a) extend run_ci_fix_vendor with a Claude tier, or (b) document the asymmetry as intentional.
- **Resolution**: Option (a) — extend run_ci_fix_vendor with a Claude tier to match the new recovery waterfall depth. Real code change in scripts/ship-pr.sh:1216-1307.
- **Source**: user (Step 1c)

## Decision 2: Baseline — dependency on #2395
- **Question**: #2395 (which introduces launch-claude-ci.sh + run_recovery_waterfall) is [IMPLEMENTING] and not yet merged. Should this design assume #2395 has merged, or design against today's main?
- **Resolution**: Assume #2395 has merged. Express the dependency natively via /larch:block-issue 2632 2395 (executed in Step 1d).
- **Source**: user

## Decision 3: Inner-loop shape and outer retry budget
- **Question**: When the Claude tier is added, what's the inner-loop shape and outer retry budget? Current state: inner = 3 attempts × 1 vendor (cursor preferred, never both); outer = 5 retries in run_evaluate_failure.
- **Resolution**: Inner = 1 attempt × 3 tiers (Cursor → Codex → Claude), outer = 3 retries. Total worst-case = 9 attempts (3 cursor + 3 codex + 3 claude) per phase. This brings run_ci_fix_vendor structurally in line with run_recovery_waterfall and explicitly reduces the outer budget from 5 to 3.
- **Source**: user

## Hard constraints carried into Step 2a
- Post-vendor-success path (token-record append, dirty-path capture, lint-fix loop, git add/commit/push, refresh-run-logs) MUST remain unchanged — only the recovery loop body is in scope.
- The new code must continue to use existing helpers: failure_capture_path, record_failure, append-token-record.sh, capture_tracked_dirty_paths, run_checks_with_lint_fix_loop, git-commit.sh, git-push.sh, refresh-run-logs.sh.
- Outer-loop detached-HEAD guard and jittered backoff (run_evaluate_failure:1340-1361) stay in place.
- Exit_stall codes 10-max-retries / 12-max-retries must continue to trigger when the outer budget exhausts.
- The launch-claude-ci.sh, launch-cursor-ci.sh --failure-log argv, launch-codex-ci.sh --failure-log argv, and local-reproduction invariant prompt text from #2395 are usable building blocks (since baseline = post-#2395).
