# Review Round 2

- Mode: `diff`
- 3 accepted, 2 rejected (2 neutral)

## Accepted Findings

### FINDING_1: Makefile harness shards reference non-existent fixture targets
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-generic-output.txt, dyn-rebalance-safety-output.txt
- **Severity**: blocking
- **Concern**: `test-harnesses-1` and `test-harnesses-2` depend on `test-b` and `test-a` from `_sample_harness_plan`, not real Makefile targets. `make test-harnesses-1` / `test-harnesses-2` (and CI harness shards) fail with missing-target errors. Real harnesses such as `test-fluff-analysis-corpus` and `test-dispatch-with-waterfall` are dropped from the partition. Fixture-driven harness edits must not be committed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Restore Makefile shard lines from main; do not commit fixture-driven harness edits.
  - From cursor-specialist-edge-cases-output.txt: Revert shards 1-2 to their real targets (test-fluff-analysis-corpus, test-dispatch-with-waterfall) or to outputs from an actual rebalance run; never commit test fixture names.
  - From cursor-specialist-testing-output.txt: Revert shard lines to valid targets (e.g. restore test-fluff-analysis-corpus and test-dispatch-with-waterfall) and never commit _sample_harness_plan fixture names.
  - From codex-generic-output.txt: Restore the real shard targets from `main` for `test-harnesses-1` and `test-harnesses-2`


### FINDING_2: `python/shard-assignments.json` contains fixture nodeids instead of empty seed
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, codex-generic-output.txt, dyn-rebalance-safety-output.txt
- **Severity**: blocking
- **Concern**: Checked-in assignments contain test-fixture nodeids instead of the planned empty `{}` seed. This breaks the acceptance contract. Harmless today because paths are fake, but wrong seed state and collision risk if similar nodeids appear later. Populate only via `/rebalance-tests` from CI data.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Restore file to {} plus trailing newline; populate only via /rebalance-tests from CI data.
  - From codex-generic-output.txt: reset `python/shard-assignments.json` to exactly `{}` plus one trailing newline.


### FINDING_4: `pytest_ci_timing` banner/attempt splitting fails on real CI pytest output
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-ci-timing-output.txt
- **Severity**: important
- **Concern**: Attempt splitting keys off the literal case-sensitive substring `"slowest durations"`, but pytest's terminal reporter emits a count between those words (e.g. `slowest 312 durations` with `--durations=0`). That form does not match, so the attempt counter never advances on real CI banners. Pre-banner duration rows are also forced into `attempt=1`, merging with the first duration section. `_split_pytest_shard_attempts` collapses multiple sections into one group, and `rows_latest_attempt_per_shard` / `shard_totals_per_run` can sum stale and retried output together. Baseline medians and verification totals are wrong whenever a `python-tests` log slice contains more than one duration report (matrix/job retry). Unit tests only use non-production banner text (`python/test_pytest_ci_timing.py:26,85-87`), so the mismatch is not caught.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Initialize attempts at 0 before the first banner per plan, or ignore duration rows until the first banner is seen.
  - From dyn-ci-timing-output.txt: Detect banners with a case-insensitive regex such as `slowest\s+(?:\d+\s+)?durations`, increment attempt from that match, and add fixtures using pytest's numbered banner (`slowest {N} durations`) plus a retry case where the second attempt's first `call` row has a different nodeid.
  - From dyn-ci-timing-output.txt: Use `re.search(r"slowest\s+(?:\d+\s+)?durations", content, re.IGNORECASE)` (or equivalent) for banner detection, and add a test with `Slowest Durations` / `slowest 5 durations` variants.


