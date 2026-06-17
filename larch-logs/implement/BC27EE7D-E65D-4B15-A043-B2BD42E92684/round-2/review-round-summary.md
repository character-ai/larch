# Review Round 2

- Mode: `diff`
- 3 accepted, 2 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Wait-barrier and sentinel-barrier pytest coverage gap
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Retired bash harness wait-barrier and sentinel-barrier scenarios (delayed external `.done`, `delayed_done_race`, launcher-owned Voter 1 delayed `.done`, external wait-timeout, nonzero `.done` exit codes, voter1 delayed/missing `.done`) are not invoked by pytest despite stub support in `python/test_agent_voters.py`. CI can stay green while a wait-barrier regression mis-classifies voters as launched before `.done` sentinels exist, mis-classifies failed externals, or backfills `.done` sentinels incorrectly, breaking post-wait voter status / degraded-panel logic and tally in production `/review` vote panels.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add pytest cases for `LARCH_WAIT_BARRIER_MODE=delayed`/`nonzero_done` and Voter-1 delayed-launcher stub, mirroring `main:scripts/test-dispatch-code-voters.sh` blocks ~485-622.
  - From cursor-specialist-testing-output.txt: Add subprocess pytest cases using existing wait-barrier stub modes, mirroring deleted `scripts/test-dispatch-code-voters.sh` assertions.


### FINDING_2: `_run_parse_rate_retry` ignores subprocess failure
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-voter-contract-output.txt
- **Severity**: important
- **Concern**: `_run_parse_rate_retry` (`python/agent_voters.py:315-331`) ignores `result.returncode` and treats the last stdout line as the parse-rate status even when the child CLI exits non-zero or prints nothing. Under retired bash `set -e`, a failing `voting parse-rate-retry` subprocess would abort dispatch; here dispatch continues with `parse_rate_status=""`, and `_effective_judges` (`python/agent_voters.py:345`) counts that slot as effective (`"" != "NOT_SUBSTANTIVE"`). That can suppress `DEGRADED_PANEL_WARNING` and let tally proceed with an overstated judge count after a parse-rate helper failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Check `result.returncode`; on failure set an explicit failure parse-rate status and treat the slot as non-effective in `_effective_judges`.
  - From dyn-voter-contract-output.txt: Fail the slot (or the whole dispatch) when `parse-rate-retry` returns non-zero or emits no recognized status token; at minimum treat non-zero rc as `NOT_SUBSTANTIVE` or `failed` instead of an empty status.


### FINDING_5: Missing subprocess stub-root integration test for voter-1 delayed launcher `.done`
- **Reviewer(s)**: dyn-stub-root-output.txt
- **Severity**: important
- **Concern**: The retired bash harness exercised voter-1 delayed launcher-owned `.done` through a subprocess stub plugin tree (`CLAUDE_PLUGIN_ROOT=$voter1_plugin`, `LARCH_VOTER1_DONE_DELAY=1`, invoking dispatch via the stub root). That case is not ported as a subprocess integration test in `python/test_agent_voters.py:277-305`. Current coverage is only `FakeHarness` unit tests (`test_successful_voter1_without_launcher_done_gets_local_sentinel_after_wait`), which monkeypatch `proc.run`/`Popen`. Subprocess paths like `test_parallel_dispatch_concurrent_waterfall_and_claude` set `plugin_root=plugin` but never assert child argv targets `$stub/python/cli.py`. A regression that hardcodes checkout `python/cli.py` on one child in the launch→wait chain could slip through CI even though `agent_voters.py` child CLI resolution is currently consistent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-stub-root-output.txt: Add a subprocess test mirroring retired `happy-voter1-delayed-done`: stub `python/cli.py` under a fake plugin root (delay async write of `claude-vote-output.txt.done`), set `CLAUDE_PLUGIN_ROOT`, invoke `python/cli.py agent dispatch-voters` from the checkout entrypoint, assert all intercepted child argv use `$stub/python/cli.py`, wait duration ≥ delay, and `VOTER_1_STATUS=launched`.


