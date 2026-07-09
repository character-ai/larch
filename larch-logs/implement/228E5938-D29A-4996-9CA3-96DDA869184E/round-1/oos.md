### FINDING_6: [OUT_OF_SCOPE] harness skip still lets CI go green without scenarios
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: minor
- **Concern**: The harness exits 0 on the identity/ps-probe skip path, so CI can look green without running any real-process bgjob scenarios in restricted environments.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Accept per plan; optionally emit a non-zero skip marker in harness-shard coverage if stricter gating is wanted later.
  - From cursor-specialist-testing: Plan accepts this; optional follow-up is fail-on-skip outside documented sandbox profiles


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_7: [OUT_OF_SCOPE] poll-interval invalid-env coverage
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing
- **Severity**: minor
- **Concern**: The invalid-env parser tests only cover the owner-grace override. Poll-interval invalid values need parallel coverage so a bad `LARCH_TEST_BGJOB_DAEMON_POLL_INTERVAL_S` value cannot regress unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Add a parallel parametrized test for ENV_TEST_BGJOB_DAEMON_POLL_INTERVAL_S.
  - From cursor-specialist-testing: Add parametrized invalid-env tests for ENV_TEST_BGJOB_DAEMON_POLL_INTERVAL_S mirroring owner-grace coverage
  - From codex-specialist-testing: Parameterize the invalid-env test over both test-only env constants, or add a second case for `_daemon_poll_interval_s()`.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### FINDING_8: [OUT_OF_SCOPE] allowlist comment still misdescribes the harness
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The allowlist comment still reads like a pytest-wrapper note, which can mislead maintainers about whether the real-process harness and `python/tests/bgjob` are already covered elsewhere.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Update comment to describe real-process harness plus python/tests/bgjob under py-test


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_11: [OUT_OF_SCOPE] terminate-path unit test still lacks a direct signal assertion
- **Reviewer(s)**: dyn-dyn-bgjob-process
- **Severity**: minor
- **Concern**: `python/tests/bgjob/test_reap.py` case 2 only checks that the terminate hook was invoked. It does not spy on `os.kill` / `os.killpg`, so branch fidelity for the real terminate path still depends entirely on the Bash scenario 5 integration test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-bgjob-process: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_12: [OUT_OF_SCOPE] `wait_done_rc` substring matching is too loose
- **Reviewer(s)**: dyn-dyn-bgjob-process
- **Severity**: minor
- **Concern**: `wait_done_rc` authorizes completion through substring matches on status and rc tokens, so malformed multi-line output could theoretically satisfy the checks without a clean single result envelope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-bgjob-process: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_13: [OUT_OF_SCOPE] baseline regen may have dropped tracked reads
- **Reviewer(s)**: dyn-dyn-bgjob-process
- **Severity**: minor
- **Concern**: The regenerated baseline removed more entries than the planned `_bg_wait_marker_context` row. If those reads are still expected, the regen may have silently dropped tracked debt rather than routing them through config constants.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-bgjob-process: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

