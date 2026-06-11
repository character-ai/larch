# Review Round 5

- Mode: `diff`
- 8 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: `--terse` does not select terse report mode
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: The token and timing report CLIs parse `--terse` but do not set `mode = "terse"`, so `python3 python/cli.py token report --terse` and `timing report --terse` reach the missing report mode path instead of rendering terse output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_10: Timing task-kind path-trigger rule does not target a real path
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `.claude/rules/timing-task-kind-allowlist.md` uses non-path strings for `python/timing.py`, so edits to `TIMING_TASK_KINDS_ALLOWED` may not trigger the reminder to keep launcher task-kind literals in sync.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_11: Missing pytest coverage for `measure-*` migrations
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-required pytest coverage for `measure_md_cost` and `measure_realized_cost` is missing after bash harness deletion, leaving tiktoken subprocess behavior, TSV output, schema assertions, and tiktoken-absent behavior without regression tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_12: Vote-helper retirement is incomplete
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Shared vote-helper deletion appears half-applied. The Makefile still runs ballot and scoreboard shared harnesses whose `.md` siblings were deleted, while deleted tally-vote paths are absent from `python/migrated-scripts.tsv`, leaving contract and stale-reference lint coverage incomplete.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_2: `parallel-tests.py` skips pytest-retargeted Makefile recipes
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `parallel-tests.py` does not recognize direct pytest recipes introduced by Makefile retargeting, so filtered or parallel runs can omit migrated token, timing, cost, and clarify pytest coverage while still appearing green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_3: Invalid ledger paths can crash token and timing CLIs with tracebacks
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Several token and timing command handlers resolve explicit `--ledger` paths outside command-level `try/except` handling. Invalid, unsafe, FIFO, outside-root, or missing ledger values can raise uncaught `ValueError` and dump Python tracebacks instead of emitting concise stderr and returning compatible telemetry-safe statuses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_8: Empty `TMPDIR` resolves to the current directory
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Empty `TMPDIR` can resolve to the current directory instead of falling back to `/tmp`. With `TMPDIR=""` and an explicit relative ledger, token and timing ledger validation can accept paths under the repo, violating the intended `${TMPDIR:-/tmp}` containment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_9: Missing timing marks render as plausible empty markdown reports
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Missing or markless timing ledgers can render full markdown reports with a plausible empty table and total `00:00:00`, rather than indicating that timing data is unavailable.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


