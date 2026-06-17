# Review Round 1

- Mode: `diff`
- 14 accepted, 3 rejected (0 neutral)

## Accepted Findings

### FINDING_1: rebase conflict loop blind staging can commit conflict markers
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-conflict-loop-output.txt
- **Severity**: blocking
- **Concern**: After each tier attempt, `_resolve_conflicts` runs `git add` on all originally unmerged paths without requiring launcher success, without verifying conflict markers are removed, and before `paths_delta_revert` on failed tiers. `git add` can clear unmerged index state while `<<<<<<<` markers remain (staged or on disk). A no-op or partial tier with `launcher_exit == 0` can satisfy an empty unmerged-path probe, set `resolved = True`, and allow `git rebase --continue` to commit broken content. Failed-tier staging is often not reverted because conflict paths are in `baseline_tracked` and `paths_delta_revert` skips them, leaving later tiers with a partially resolved index instead of the original conflict state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-edge-cases-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.
  - From dyn-conflict-loop-output.txt: Gate staging on `launcher_exit == 0` and `wrapper_rc == 0`, and add `_stage_resolved_conflict_files` that `git add`s only paths that exist and no longer contain conflict markers; treat any still-marked path as unresolved and continue or hand off without calling `rebase --continue`.
  - From dyn-conflict-loop-output.txt: Do not stage unless the tier succeeded and marker checks pass; between tiers, reset conflict CSV paths explicitly (for example `git restore --staged` / `git checkout --merge -- <path>` for those paths) instead of relying on `paths_delta_revert` alone for baseline-tracked conflict files.
  - From dyn-conflict-loop-output.txt: After staging, require every path in the active conflict set to be marker-free on disk (and optionally index-clean) before setting `resolved = True`; if markers remain, revert that tier’s index/worktree changes and continue to the next tier or hand off.


### FINDING_10: write-capable Claude CI prompts lack untrusted-data framing
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Write-capable Claude CI fix prompts embed plan and failure context without explicit untrusted-data delimiters or instruction to ignore embedded directives. A malicious CI log could inject edit instructions into a model with Edit and Write tools.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_11: Exit 3 still routes ci-fix-exhausted to autonomous main-agent CI fix
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Exit 3 still lists `ci-fix-exhausted` in the autonomous main-agent CI-fix token set. After the Opus agentic delegate exhausts 20 cycles, the orchestrator can still run the 12-step autonomous main-agent CI-fix sub-procedure instead of Step 12d operator bail, contradicting stall-recovery and the plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_12: agentic CI fix integration lacks planned test coverage
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-ci-delegate-output.txt
- **Severity**: important
- **Concern**: The agentic CI fixer and parent integration surface have minimal automated validation: `test_ci_agentic_fix.py` covers only invalid `--repo-root`; most `evaluate_failure` / KV-mapping tests in `test_ci_monitor.py` are skipped without replacement. Regressions in verify-before-push, empty-delta handling, passive `ci wait`, HEAD gate, rebase-required mapping, `FIX_ATTEMPTED` promotion, cycle cap, delegate argv threading, parent timeout behavior, and KV mapping can ship with green CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.
  - From dyn-ci-delegate-output.txt: Add stub-runner tests for `_agentic_fix_result` and `ci_agentic_fix.main()` covering the plan’s KV matrix, parent timeout behavior, and the `ci_fix_rebase_pending=True` push-only branch, then un-skip or replace the skipped `evaluate_failure` tests.


### FINDING_13: lint-fix Claude-first waterfall lacks plan-required tests
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `test_checks.py` lint-fix tests do not assert Claude-first dispatch. Codex-first ordering or missing Claude dispatch in `run_lint_fix` could regress without failing CI, including on Claude-only hosts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_14: rebase explicit conflict loop lacks plan-required tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The explicit per-tier rebase conflict loop lacks plan-required tests; prepass tests are skipped/renamed. Conflict resolution revert, short-circuit, and staging semantics are unverified against current implementation behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_2: conflict launcher health classification ignores launcher envelope
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Conflict-resolution tier health classification drops the launcher KV envelope and classifies from a missing failure log or sidecars. Claude binary/auth/quota/transient failures can emit `LAUNCHER_FAILURE_CLASS=health` but be treated as `other`, short-circuiting the explicit loop before Codex/Cursor instead of falling through per health-tier policy.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_3: parent subprocess timeout can kill agentic CI fix mid-cycle
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-ci-delegate-output.txt
- **Severity**: important
- **Concern**: `_agentic_fix_result` runs the full `ci agentic-fix` delegate under `SUBPROCESS_DEFAULT_TIMEOUT_SEC` (1800s), while each cycle can spend up to `CI_WAIT_TIMEOUT_SEC` (1800s) in passive `ci wait` plus Claude launch and local verification. One successful cycle can consume the entire parent budget; the parent kills the delegate mid-loop, yielding malformed or partial KV (`malformed agentic-fix output`), routing to `STALLED` instead of bounded `ci-fix-exhausted` operator bail, and potentially leaving ambiguous repo state if killed after push or mid-edit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-ci-delegate-output.txt: Remove or greatly raise the outer delegate timeout (for example `timeout=None`, or a dedicated budget derived from `CI_AGENTIC_FIX_MAX_CYCLES * (CI_WAIT_TIMEOUT_SEC + launcher budget)`). Treat subprocess exit `124` / non-zero as a first-class terminal outcome with explicit cleanup and operator routing, not as generic malformed output.


### FINDING_4: Claude health-class CI fix failures retry to cycle exhaustion
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-ci-delegate-output.txt
- **Severity**: important
- **Concern**: Health-class Claude launcher failures (missing binary, auth, quota, transient infra) return per-cycle `waterfall-failed` / `claude-health`, and `main()` retries until the 20-cycle cap instead of terminating immediately. That can burn many identical Opus launches on an unrecoverable health fault and delays the operator-facing `first-fixer-non-health` path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From dyn-ci-delegate-output.txt: Treat first-cycle Claude `failure_class == "health"` as an immediate terminal status (`first-fixer-non-health` or a dedicated health KV). Map that in `_agentic_fix_result` to the same `NEEDS_USER_INPUT` routing the ship driver already uses for `first-fixer-non-health`.


### FINDING_5: review-and-fix lint-fix omits claude_present
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-lint-claude-output.txt
- **Severity**: important
- **Concern**: `_run_lint_fix_loop` calls `checks.run_lint_fix` without `claude_present`, so `run_lint_fix` defaults it to `False` and never dispatches `launch-claude-lint-fix`. On Claude-present or Claude-only hosts, `/review-and-fix` Step 5 lint-fix violates the required Claude/Opus-first policy that `checks_lint_fix_main` already follows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-edge-cases-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.
  - From dyn-lint-claude-output.txt: Thread `claude_present=_binary_flag("CLAUDE_BINARY_FOUND", implement_tmpdir, "claude")` through `_run_lint_fix_loop`, matching `checks_lint_fix_main`.


### FINDING_6: HEAD-change guard leaves unauthorized model commits
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: If Claude runs `git commit` during agentic CI fix, the delegate returns `head-changed` but leaves the unauthorized commit on the branch instead of restoring baseline HEAD.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_7: rebase conflicts during CI-fix push mapped to generic push failure
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Rebase conflicts during push preparation (`rebase_push`) are aborted and returned with `pending=false` or mapped to `waterfall-failed` / push-failed instead of preserving a `rebase-required` / `CI_FIX_REBASE_PENDING=true` handoff. A valid Claude CI fix that conflicts while rebasing routes to exhaustion instead of the planned pending push-only retry path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_8: post-commit push failures retried without terminal or reset
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: If `git push` fails after `stage_and_push` commits, later agentic cycles start from the unpushed commit and may add more commits before exhaustion instead of treating post-commit push failure as terminal or resetting to pre-cycle HEAD.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_9: ci-fix-exhausted detail omits redacted CI log tail
- **Reviewer(s)**: dyn-ci-delegate-output.txt
- **Severity**: important
- **Concern**: When the agentic delegate exhausts cycles, it emits `ci-fix-exhausted` with `DETAIL` set to the last cycle token (for example `verify-failed:…`, `empty-delta`, `push-failed`) and does not include the redacted CI log tail. The parent maps that straight through and no longer calls `_fix_exhausted_detail()`, breaking the Step 12d operator-bail diagnostic contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-delegate-output.txt: Before terminal emission, capture the last redacted failure log (or delegate `_fix_exhausted_detail()` into the parent mapper) so `fix-exhausted` detail keeps the same diagnostic contract ship/Step 12d expects.


