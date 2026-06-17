### FINDING_2: Agentic delegate omits repo working-tree cwd contract
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: `evaluate_failure` spawns `ci agentic-fix` without passing the parent process working directory (`cwd=repo_root`) or an explicit `--cwd`/`--repo-root` flag. `RunContext.repo` is the GitHub slug, not a filesystem path, so git reads, `launch_tier`, `verify_job_locally`, and `stage_and_push` inside the delegate can run against the wrong directory when the parent `cwd` differs from the repo root.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Document and implement that `evaluate_failure` passes the parent `cwd` into the subprocess invocation (or add `--repo-root` to `ci agentic-fix` and thread it through every git call)
  - From Cursor-Pragmatic: Add --cwd (or --repo-root) to the ci agentic-fix CLI surface, thread evaluate_failure's cwd into the subprocess invocation, and assert in test_ci_monitor.py that runner.run uses the same cwd the in-process path used today.


### FINDING_4: local-unfixable drops fix-exhausted promotion parity
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: Replacing `run_ci_fix` with agentic KV mapping drops the `code_fix_attempted_on_ready_log` to fix-exhausted promotion for local-unfixable outcomes. Today, when fixers run but jobs are later deemed unfixable (toolchain/prepare_python_toolchain path), `evaluate_failure` returns fix-exhausted with the `ci-fix-exhausted` detail prefix; the plan maps agentic `STATUS=local-unfixable` straight to `NEEDS_USER_INPUT`, changing operator routing and stall detail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Either emit a distinct agentic status (or DETAIL flag) when fix was attempted before local-unfixable, or have evaluate_failure promote local-unfixable to fix-exhausted using the same code_fix_attempted_on_ready_log rule; extend test_ci_monitor.py to cover post-attempt unfixable parity with evaluate_failure_exhausted_routes_needs_user_input.


### FINDING_5: Agentic cycle omits delta path computation before stage_and_push
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The plan captures baseline tracked/untracked sets and calls `ci_monitor.stage_and_push` after verification, but never computes changed paths via `ci_monitor._delta_paths` (or equivalent). `stage_and_push` only commits when `delta_paths` is non-empty, so a successful Opus edit plus passing local verify would still return push failed with no commit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: After verification passes, compute delta_paths from the pre-cycle baselines (same contract as ci_monitor.run_ci_fix today), pass them into stage_and_push with commit_label claude, and treat empty delta as a no-progress cycle outcome


