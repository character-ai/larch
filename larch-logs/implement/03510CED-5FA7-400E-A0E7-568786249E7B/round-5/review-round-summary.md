# Review Round 5

- Mode: `diff`
- 15 accepted, 2 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Mixed fixable/unfixable jobs pre-bail before Claude launch
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: When CI fails on both fixable jobs (e.g. python-lint) and unfixable jobs (e.g. gitleaks), the agentic delegate bails with `local-unfixable` before launching Claude. Fixable lint failures are never attempted, unlike the old `run_ci_fix` path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Only pre-bail when `not classified.fixable`; proceed with fixable jobs when both buckets are non-empty.


### FINDING_10: Partial conflict markers can be staged as resolved
- **Reviewer(s)**: codex-generic-output.txt, dyn-conflict-loop-output.txt
- **Severity**: important
- **Concern**: `_path_has_conflict_markers` only treats a file as conflicted when both `<<<<<<<` and `>>>>>>>` are present. A file with only a start marker, only `=======`, or other partial marker text is classified marker-free; `_stage_resolved_conflict_files` may `git add` it, `_unmerged_paths` can clear, and the rebase driver can continue with marker text committed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: For active conflict files, reject staging if any conflict-marker line remains: `<<<<<<<`, `=======`, or `>>>>>>>`. Update the regression test that currently expects partial markers to stage.
  - From dyn-conflict-loop-output.txt: Treat any conflict-marker signal as unresolved: require all three markers, or delegate to `git diff --check` / index unmerged state and refuse to `git add` until `_unmerged_paths` is empty for that path.


### FINDING_11: `make_conflict_launch_fn` log classification overrides semantic `other` failures
- **Reviewer(s)**: dyn-conflict-loop-output.txt
- **Severity**: important
- **Concern**: `make_conflict_launch_fn` always writes launcher output to `conflict-{tier}.fail.log` and sets `TierAttempt.failure_log`, but `_resolve_conflicts` classifies first-tier bailouts via `agents.effective_failure_class(attempt)`, which reads only `LAUNCHER_FAILURE_CLASS=` from that file and defaults to `"health"` when the KV is missing. That can override `classify_launch_failure(...)` already setting `attempt.failure.failure_class` to `"other"`, causing a Claude semantic failure to fall through to Codex/Cursor instead of first-tier short-circuit/handoff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-conflict-loop-output.txt: In the conflict loop, when `failure_log` exists but `parse_launcher_failure_class` returns the health default, fall back to `attempt.failure.failure_class` for the first-tier short-circuit decision; or have `make_conflict_launch_fn` always embed `LAUNCHER_FAILURE_CLASS=` in the written capture from the already-computed `failure`.


### FINDING_14: `test_run_lint_fix_codex_fail_cursor_success` does not assert Claude-first dispatch
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The test still expects codex then cursor only. Production with Claude available would dispatch Claude first; the test would not catch a reorder regression or missing Claude-first behavior required by plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add `claude_present` or which-probe and expect `claude` in `dispatch_calls` first.
  - From cursor-specialist-testing-output.txt: Pass `claude_present=True`, fail `_run_claude`, assert `dispatch_calls == ["claude", "codex", "cursor"]`.


### FINDING_15: Missing plan-required lint-fix dispatch coverage tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Missing explicit tests for all-three-tiers-fail and Claude-only-host dispatch. Lint-fix could skip Claude or mis-order fallbacks on Claude-only hosts without test failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add explicit tests for Claude-only dispatch and all-three-failed `main-agent-required` outcomes.


### FINDING_16: `_run_cycle` integration paths largely untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-required `_run_cycle` integration paths are largely untested because tests mock `_run_cycle`. Verify-failed push suppression, empty-delta handling, forbidden-path rollback, and `flush_logs_pre` threading could regress without CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add stub-runner tests that exercise `_run_cycle`/`main` without mocking the cycle body; assert push, rollback, and `stage_and_push` side effects.


### FINDING_17: Sixteen skipped agentic monitor tests lack replacements
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Sixteen agentic-skipped `evaluate_failure`/`monitor` tests lack equivalent replacements; only three new agentic tests exist. Terminal routing, monitor `goto_rebase`, and `FIX_ATTEMPTED` promotion could break while py-test stays green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Port skipped scenarios to agentic-delegate stubs or add tests for single delegate invocation, `--repo-root`/`cwd` threading, and no outer re-delegate on terminal statuses.


### FINDING_18: No assertion that `PrePushConflictHandoff` default message is generic
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: No test asserts the default `PrePushConflictHandoff` message is generic. A future edit could reintroduce non-bump wording without test failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Assert default `str(err)` is generic and contains no non-bump or version-file tokens.


### FINDING_2: `claude_present=None` skips Claude without binary probe
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-lint-claude-output.txt
- **Severity**: important
- **Concern**: `run_lint_fix` coerces `claude_present=None` to `False` without probing `shutil.which("claude")`. In-process callers that omit the flag on Claude-capable hosts return `main-agent-required` without attempting the new first-tier Opus fixer, inconsistent with CLI/`review_and_fix` `_binary_flag` behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Probe `shutil.which("claude")` when `claude_present is None` before the main-agent-required gate.
  - From dyn-lint-claude-output.txt: When `claude_present is None`, resolve it with the same `_binary_flag("CLAUDE_BINARY_FOUND", …, "claude")` helper used by `checks_lint_fix_main` and `review_and_fix.py`, instead of hard-coding `False`.


### FINDING_3: Non-recoverable health failures burn full 20-cycle budget
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Quota and other non-auth launcher health failures map to `waterfall-failed` and the main loop retries up to 20 cycles. An Opus quota error on cycle 1 can trigger 19 more doomed Opus launches before `ci-fix-exhausted`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Short-circuit non-recoverable health failures to `first-fixer-non-health` or immediate `ci-fix-exhausted`.


### FINDING_4: CI-only path maps auth/binary health failures to Exit 3 instead of terminal delegate status
- **Reviewer(s)**: dyn-ci-delegate-output.txt
- **Severity**: important
- **Concern**: On the CI-only agentic path (no Codex/Cursor fallback), Claude launcher health failures with `reason in {"binary-missing", "auth"}` map to `first-fixer-non-health`, which still routes through ship-pr Exit 3 toward autonomous main-agent CI repair. Other health failures (quota/transient) continue cycling. This mismatches the Claude-only, no-tier-fallback policy.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-delegate-output.txt: For `role=fix`, map auth/binary-missing health failures to a terminal delegate status (`ci-fix-exhausted` or explicit `launcher-unavailable`) that `monitor()` maps to `NEEDS_USER_INPUT` without invoking the Exit 3 autonomous sub-procedure, matching the “Claude-only, no tier fallback” policy.


### FINDING_5: Post-push `ci wait` failure rolls local HEAD back to pre-cycle baseline
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, codex-generic-output.txt, dyn-ci-delegate-output.txt
- **Severity**: important
- **Concern**: After `stage_and_push` succeeds, a passive `ci wait` timeout or malformed output triggers `git reset --hard` / `_rollback()` to the pre-cycle `baseline_head` while the remote already contains the pushed fix. The next cycle runs from a stale local tree, which can re-apply fixes, push duplicate commits, hit non-fast-forward push failures (`push-failed` → `ci-fix-exhausted`), and burn cycle budget on self-inflicted divergence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Do not hard-reset to baseline after push; sync to remote tip or return terminal status without undoing pushed commits.
  - From codex-generic-output.txt: Once `stage_and_push` succeeds, do not roll back to `baseline_head` for passive-wait failures. Continue from the pushed head, or return/exhaust with the branch left at the pushed commit.
  - From dyn-ci-delegate-output.txt: After a confirmed push, never reset to the pre-cycle baseline on wait failure. Keep local HEAD at the pushed commit (or `git fetch`/`reset` to the remote tip), treat wait timeout/malformed output as “CI still red,” advance `run_id` when present, and continue the loop.


### FINDING_6: `_wait_for_ci` treats `ACTION=bail` as malformed output
- **Reviewer(s)**: dyn-ci-delegate-output.txt
- **Severity**: important
- **Concern**: `_wait_for_ci` only accepts a narrow set of `ACTION` values. `ci wait` poll-budget exhaustion emits `ACTION=bail` with `BAIL_REASON=CI_WAIT_BAIL_POLL_BUDGET_EXHAUSTED` (`python/ci_monitor.py:555-561`), which falls through to `ci-wait-malformed-output` and can route into the post-push rollback path instead of consuming a cycle as “CI not green yet.”
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-delegate-output.txt: Treat `ACTION=bail` (and optionally `CI_STATUS=pending` with elapsed ≥ timeout) as a non-fatal wait outcome: return parsed KV with no error, or a dedicated `wait-inconclusive` status that continues the agentic loop without rollback.


### FINDING_8: Parent delegate timeout ignores in-flight pushes
- **Reviewer(s)**: dyn-ci-delegate-output.txt
- **Severity**: important
- **Concern**: The parent wraps the entire delegate (up to 20 × (launcher + verify + push + 1800s wait)) in one `runner.run(..., timeout=_agentic_fix_delegate_timeout_sec())`. On `EXIT_TIMEOUT`, it returns `fix-exhausted: delegate-timeout` without checking whether a push already landed inside the child, leaving remote state changed while the parent assumes total failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-delegate-output.txt: Have the delegate write a cycle checkpoint KV/file after each successful push (commit SHA + `run_id`); on parent timeout, read that checkpoint and return `rebase-required` or `pushed` with `ci_fix_rebase_pending` instead of blind exhaustion, or shorten the outer timeout and let the delegate own per-cycle bounds only.


### FINDING_9: Dead unreachable `run_ci_fix` loop in `evaluate_failure`
- **Reviewer(s)**: dyn-ci-delegate-output.txt
- **Severity**: important
- **Concern**: When `ci_fix_rebase_pending=False`, `evaluate_failure` returns immediately via `_agentic_fix_result`. The `for attempt in range(...)` loop below is only reachable when `ci_fix_rebase_pending=True`, so the `run_ci_fix(..., ci_fix_rebase_pending=False)` block is dead on the active ship path. Future edits could re-enable the old multi-tier waterfall without noticing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-delegate-output.txt: Delete the unreachable non-pending loop body (keep only the early `ci_fix_rebase_pending` push-only branch), or guard it with an explicit `assert ci_fix_rebase_pending` and a comment that normal CI fix is exclusively agentic.


