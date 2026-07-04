### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:30-42
- **Concern**: The prior red-green finding is still incomplete: the planned direct test can pass on the current unfixed `_summarize`. Scenario: Current code already gives the reappearing target `end` equal to its reappear value via `reappearing_targets`, and already gives a finally removed accumulated target `end=0` and removal delta via `snapshot_values.get(target, 0)`, so an implementation could leave the in-loop absent-target advance in place and still pass the described assertions
- **Proposed resolution**: Add a mandatory assertion or hand-crafted `_summarize` case that fails while `accumulator.advance(..., current=snapshot_values.get(target, 0))` remains, such as an accumulated target absent from an intermediate snapshot and present later without a reappearing reset, then pin `raises` or `largest_raise_delta` so the synthetic 0-to-current raise is caught; keep the existing partial-skip/no-post-loop check too

### FINDING_2:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/tests/lint/test_skill_closure_ledger.py:new test
- **Concern**: Prior accepted gap-test fix remains incomplete because the planned assertions can still pass on current _summarize. Scenario: With valid reappear data where previous=None, current code already resets the accumulator via reappearing_targets and returns end equal to the reappear value. The permanent-removal assertions also pass today because current in-loop absent advance already drives the target to 0. The new test can pass with no gap-skip fix.
- **Proposed resolution**: Revise the planned direct _summarize test so one assertion fails on current code and passes only when absent targets are skipped. Pin a full SummaryRow for a hand-crafted gap case where the synthetic 0 changes raises, largest_raise_delta, or delta, and keep the final-removal assertion for the post-loop.

### FINDING_3:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/tests/lint/test_skill_closure_ledger.py:planned test
- **Concern**: The planned direct regression test still does not prove the in-loop absent-target skip.. Scenario: This is the accepted prior gap in a new form: current `_summarize` can already satisfy the planned `end` and final-removal `delta` assertions because `reappearing_targets` resets the accumulator on reappear and current final absence already advances to `0`. An implementation could leave `snapshot_values.get(target, 0)` in the per-revision loop and still pass the specified assertions.
- **Proposed resolution**: Add a red-green assertion that fails with the current absent-target advance, such as instrumenting `_SummaryAccumulator.advance` in the focused unit test and asserting the gap target is not advanced at the absent intermediate revision, while still asserting the final-removal post-loop advances the permanently removed target to `0`.

### FINDING_4:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:30-42
- **Concern**: Prior accepted test-fidelity fix is incomplete: the planned direct test still does not prove the in-loop absent-target skip. Scenario: Current _summarize already returns the reappear target end value through reappearing_targets reset and already returns end=0 for final removals through the old in-loop zero advance, so the planned assertions can pass before the skip fix
- **Proposed resolution**: Require the new focused _summarize test to fail on current code by observing that no advance to current=0 happens on an intermediate gap, for example with a small spy around _SummaryAccumulator.advance, while keeping the final-removal post-loop assertion
