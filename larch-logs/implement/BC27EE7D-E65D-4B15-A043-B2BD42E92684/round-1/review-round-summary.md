# Review Round 1

- Mode: `diff`
- 3 accepted, 1 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Makefile voter shard targets run identical full pytest with no section filters
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-voter-contract-output.txt, dyn-stub-root-output.txt
- **Severity**: important
- **Concern**: All eight `test-dispatch-code-voters-*` Makefile targets (lines ~850–872) run the full `python/test_agent_voters.py` module with no `-k` section filters. The retired `scripts/test-dispatch-code-voters.sh --section …` harness mapped each target to a distinct slice (happy, edge-and-r3-claude, retry-claude, retry-codex-success, retry-cursor, retry-codex-fail-and-fallback, regressions-r1-r2, regressions-r3-codex). CI shards 3/6/7/9/12/15/17/19 now invoke differently named targets but execute the same small suite, losing shard isolation and implying broader coverage than exists. Once full pytest coverage is added, the same suite cost may be paid eight times.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-voter-contract-output.txt: restore per-target `-k` filters or collapse to one Makefile target and rebalance shards
  - From dyn-stub-root-output.txt: Restore per-target `-k` filters (or equivalent pytest markers) matching the retired harness sections, and keep one umbrella target only if shard tables are updated deliberately.


### FINDING_2: Pytest port omits most retired bash harness regression coverage
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-voter-contract-output.txt, dyn-stub-root-output.txt
- **Severity**: important
- **Concern**: The deleted ~1081-line `scripts/test-dispatch-code-voters.sh` harness is replaced by ~9–10 focused pytest cases in `python/test_agent_voters.py`. Plan-required acceptance scenarios are largely absent: #3704 parallel-dispatch ordering (waterfall launch before Claude wait completes), parse-rate `NOT_SUBSTANTIVE` retry success/failure for all voters, first-pass sidecar preservation, harness env-isolation, round parity, symlink diff, wait usage/config errors, production-shape parse-rate append, and late-sentinel delay paths. Stub-`CLAUDE_PLUGIN_ROOT` subprocess integration via delegating `python/cli.py` is not exercised end-to-end. Regressions in `agent_voters.py` KV/sentinel/parse-rate behavior can ship while `make py-test` stays green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Port retired section scenarios into pytest with stub plugin-root delegation.
  - From codex-specialist-correctness-output.txt: Port the missing harness scenarios into python/test_agent_voters.py or keep the retired harness until equivalent pytest coverage exists.
  - From cursor-specialist-edge-cases-output.txt: Port remaining bash harness scenarios into pytest with stub-plugin integration tests and harness_review_tmpdir under test_agent_voters.*
  - From cursor-specialist-edge-cases-output.txt: Add test asserting waterfall launch occurs before Claude wait completes
  - From cursor-specialist-testing-output.txt: Port retired harness sections into pytest with REAL_CLI-delegating stub plugin roots, harness_review_tmpdir under test_agent_voters.*, and assertions for sidecars, NOT_SUBSTANTIVE, and parallel waterfall-vs-Claude ordering.
  - From codex-specialist-testing-output.txt: Add pytest cases for the omitted sections, using stub plugin roots and real CLI delegation where needed.
  - From dyn-voter-contract-output.txt: Port the missing retired-harness scenarios into `python/test_agent_voters.py` (including subprocess cases through a stub `CLAUDE_PLUGIN_ROOT`), restore per-target `-k` filters or collapse to one Makefile target and rebalance shards, and add an explicit #3704 ordering assertion that `dispatch-waterfall` runs before `claude_process.wait()`.
  - From dyn-stub-root-output.txt: Port the retired stub-plugin fixtures: set `CLAUDE_PLUGIN_ROOT` to a tree whose `python/cli.py` delegates selected verbs to `REAL_CLI`, invoke `python3 …/cli.py agent dispatch-voters` (not the module directly), and assert every child argv uses `$stub_root/python/cli.py` for late-sentinel, parallel-dispatch, and parse-rate-retry paths.


### FINDING_6: Existing tests do not assert `--plugin-root` value on parse-rate-retry argv
- **Reviewer(s)**: dyn-stub-root-output.txt
- **Severity**: important
- **Concern**: `test_child_argv_parity_timeout_context_and_parse_rate_args` (`python/test_agent_voters.py:170–201`) checks that `parse-rate-retry` argv includes `--plugin-root` but never asserts its value equals the resolved stub `CLAUDE_PLUGIN_ROOT` path. A regression hardcoding checkout `Path(__file__).parents[1]` into `--plugin-root` while routing other children through `_cli_argv()` would pass this test but break installed-plugin and stub-harness parse-rate relaunches (`voting.launch_voter_retry` at `python/voting.py:667–671` builds child CLI paths from `--plugin-root`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-stub-root-output.txt: Assert `_value_after(parse_call, "--plugin-root") == str(tmp_path / "stub-plugin")` (or the active stub root) in every stub-root test, including subprocess integration cases.


