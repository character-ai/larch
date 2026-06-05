### FINDING_1: Monitor push-failure test weakly pins vendor push-failure path
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-test-fixture-integrity-output.txt
- **Severity**: latent
- **Concern**: `test_monitor_push_failed_stalls` (python/test_ci_monitor.py:1238-1292) can pass with `Outcome.STALLED` without proving the vendor push-failure path on every outer `evaluate_failure` / `run_ci_fix` attempt. Sequential `git diff` / `rev-parse` queues are sized for roughly one fix waterfall; `monitor()` may retry up to `CI_MONITOR_FIX_WATERFALL_MAX_ATTEMPTS` (3) on `waterfall-failed`, so later attempts can hit empty delta, skip `git push`, and still stall because `stage_and_push` failures reuse `detail="push failed"` (python/ci_monitor.py:1014-1023). Unrelated failures (timeout, missing run id, head-changed, weak `launch_calls`) could also yield STALLED without exercising the push stub the test/docstring claim to pin.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Also assert git push was invoked and/or that result detail contains push failed (or another push-path-specific signal).
  - From cursor-specialist-correctness-output.txt: Extend sequential diff stubs for three outer attempts or assert git push appears in runner.calls.
  - From cursor-specialist-edge-cases-output.txt: Assert result.result.detail is push failed with max_attempts=1 or outer fix attempts exhausted after full outer loop.
  - From dyn-test-fixture-integrity-output.txt: For this test only, monkeypatch `CI_MONITOR_FIX_WATERFALL_MAX_ATTEMPTS` to `1`, or multiply the sequential diff/rev-parse entries by the outer cap (and add `assert sum(1 for c in runner.calls if c == ("git", "push", "origin", "feature")) == 1` so a regression that skips push cannot still pass).


