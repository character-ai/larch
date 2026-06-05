Reviewing the cited test and monitor code to validate merges and severity.
Structured aggregator output (plain text for `aggregator-output.txt`):

### FINDING_1: Monitor push-failure test weakly pins vendor push-failure path
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-test-fixture-integrity-output.txt
- **Severity**: latent
- **Concern**: `test_monitor_push_failed_stalls` (python/test_ci_monitor.py:1238-1292) can pass with `Outcome.STALLED` without proving the vendor push-failure path on every outer `evaluate_failure` / `run_ci_fix` attempt. Sequential `git diff` / `rev-parse` queues are sized for roughly one fix waterfall; `monitor()` may retry up to `CI_MONITOR_FIX_WATERFALL_MAX_ATTEMPTS` (3) on `waterfall-failed`, so later attempts can hit empty delta, skip `git push`, and still stall because `stage_and_push` failures reuse `detail="push failed"` (python/ci_monitor.py:1014-1023). Unrelated failures (timeout, missing run id, head-changed, weak `launch_calls`) could also yield STALLED without exercising the push stub the test/docstring claim to pin.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Also assert git push was invoked and/or that result detail contains push failed (or another push-path-specific signal).
  - From cursor-specialist-correctness-output.txt: Extend sequential diff stubs for three outer attempts or assert git push appears in runner.calls.
  - From cursor-specialist-edge-cases-output.txt: Assert result.result.detail is push failed with max_attempts=1 or outer fix attempts exhausted after full outer loop.
  - From dyn-test-fixture-integrity-output.txt: For this test only, monkeypatch `CI_MONITOR_FIX_WATERFALL_MAX_ATTEMPTS` to `1`, or multiply the sequential diff/rev-parse entries by the outer cap (and add `assert sum(1 for c in runner.calls if c == ("git", "push", "origin", "feature")) == 1` so a regression that skips push cannot still pass).

### FINDING_2: launch_calls does not prove vendor waterfall tier sequence
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: In python/test_ci_monitor.py:1238-1292, `assert launch_calls` is weaker than plan language that the vendor launcher ran through the waterfall: a stub that skips the waterfall but still returns STALLED could pass if any unrelated launch occurred.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Assert tier sequence or minimum launch count aligned with run_waterfall / _available_tiers().

### FINDING_3: Duplicate vendor push-failure stub maps across monitor and evaluate tests
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `test_evaluate_failure_vendor_only_push_failed_stalls` and `test_monitor_push_failed_stalls` (python/test_ci_monitor.py:973-1027 and 1238-1292) duplicate large response/stub maps; updating one test only can leave the other green while monitor and evaluate paths diverge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract _vendor_only_push_failure_responses(run_id=...) shared by both tests.

### FINDING_4: Document push-failure dirty-tree semantics in ci_monitor comment
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The new comment at python/ci_monitor.py:1014-1024 does not state that push-failure returns without `_rollback()`, leaving an unpushed local commit while the outer loop re-enters the full fix waterfall from a dirty tree—unlike bash `CI_FIX_REBASE_PENDING` push-only retry. Phase 7 readers may assume idempotent clean re-fix.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add one comment line: local commit retained on push failure; outer retries re-enter waterfall from dirty state; contrast with bash CI_FIX_REBASE_PENDING push-only retry.

### FINDING_5: Monitor test does not exercise post-commit HEAD advance on push failure
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: In python/test_ci_monitor.py:1275-1290, `git rev-parse HEAD` stays frozen at `baseline_head` after a mocked successful commit while push fails. Production may see head-changed or duplicate-commit on outer retry; the test would still pass while real recovery diverges.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Advance post-commit rev-parse stub to new SHA with push rc=1 or add test covering unpushed-commit outer-retry semantics.

### OOS_1: [OUT_OF_SCOPE] TierAttempt 0,0 exit codes with LaunchFailure may break if waterfall semantics change
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Vendor push tests use `TierAttempt(tier, 0, 0, LaunchFailure(...))` to force a winning tier without a real agent. If `run_waterfall` starts treating `LaunchFailure` as tier failure regardless of exit codes, these tests may fail before reaching push. Pre-existing pattern; only refactor if waterfall semantics change (not required for #3405).
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_2: [OUT_OF_SCOPE] Empty-delta and failed-push share detail="push failed"
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-test-fixture-integrity-output.txt
- **Severity**: latent
- **Concern**: `run_ci_fix` at python/ci_monitor.py:1014-1023 reports `detail="push failed"` whenever `stage_and_push` returns `pushed=False`, including the empty-delta shortcut that never runs `git push`. Retry with no delta still reports push failed though no push ran. Predates this branch; the new test’s outer retries rely on that wording but do not hit the push stub on attempts 2–3.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Split detail for empty delta vs push failure in a follow-up if operators need clearer diagnostics.

### OOS_3: [OUT_OF_SCOPE] No rollback on push failure (pre-existing; Phase 7)
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Pre-existing behavior: push failure does not roll back, so Phase 7 wiring may surface inconsistent local state during CI fix recovery. Not changed by this PR’s documentation focus; track on Phase 7 cutover, not here.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_4: [OUT_OF_SCOPE] Bash CI_FIX_REBASE_PENDING push-only retry not ported by design
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `scripts/ship-pr.sh:1618-1718` persisted push-only retry under `CI_FIX_REBASE_PENDING` is intentionally not ported to Python until `LARCH_SHIP_PR_IMPL=python`. Live implement path still uses bash; tracked via #3405 with no action on this PR.
- **Suggested revisions (informational for voters; coder decides)**:

---

**Merge notes (brief):** Input findings 1, 5, 9, and 12 describe the same test-fixture / assertion gap around outer retries and ambiguous `STALLED` + `push failed` detail. Findings 6 and 13 are the same production diagnostic quirk (OOS). In-scope comment request (input 7) stays separate from OOS no-rollback / bash-port items (input 10, 11). Input 8 stays separate from FINDING_1 because it targets rev-parse/HEAD semantics, not push-call counting or detail strings.
