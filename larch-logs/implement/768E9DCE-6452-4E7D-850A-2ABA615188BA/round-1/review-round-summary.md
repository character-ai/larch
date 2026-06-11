# Review Round 1

- Mode: `diff`
- 8 accepted, 1 rejected (1 neutral)

## Accepted Findings

### FINDING_1: /design telemetry commands are quoted as one executable
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: /design token and timing mark commands quote `python3 ... cli.py ...` as one executable word. Bash fails to invoke the Python CLI, and `|| true` hides the failure, disabling design telemetry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_11: Plan-listed pytest coverage is missing
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-listed B2 pytest coverage for ledger reports, budget source lanes, and harness telemetry is largely absent. Regressions in the new `tokens.py` and `timing.py` surfaces may reach production undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_2: Null-id Claude transcript dedupe drops cache bucket detail
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Null-id Claude transcript fingerprints omit `cache_create_5m` and `cache_create_1h`. Distinct usage rows can collapse, undercounting tokens and cache-write cost.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_3: Timing summary counts vendor tasks by write time
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Timing summary mode counts vendor tasks by row write time instead of task end time. A task that ended before a mark but wrote after it can be included in the new summary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_4: Claude source snapshot accepts incomplete metadata
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `token claude-source` can exit successfully when snapshot metadata contains only `TRANSCRIPT_PATH`. Callers then miss `SESSION_DIR` and `SESSION_UUID`, so subagent transcripts may not be discovered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_5: run_logs still shells out for token and timing reports
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `run_logs.py` still invokes token and timing report rendering through subprocess CLI calls. This leaves the planned direct renderer integration unexercised, blocks hydrated-env assertions, and may leave lint failures such as an unused `tokens` import.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_6: Retargeted shell harnesses copy pseudo-paths
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Several retained harnesses copy literal command strings such as `python3 python/cli.py token` as filesystem paths. Fixtures can fail before exercising migrated Python CLI behavior, and stubbed commands may never run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_9: Token report marker replacement matches prose substrings
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Token report block replacement matches sentinels by substring and lost lone-marker recovery. A prose mention of a marker can be mistaken for structure and rewrite or discard unrelated content.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


