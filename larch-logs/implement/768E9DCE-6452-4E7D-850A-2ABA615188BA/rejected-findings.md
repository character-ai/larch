# Rejected Findings

## Round 1

### [rejected] FINDING_8

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_8: timing telemetry mark can write to cwd on malformed argv
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `timing_telemetry_mark_main` can treat an empty `--implement-tmpdir` value as `Path("")`, which resolves to cwd. Malformed argv can write step marks into the repo ledger and exit successfully.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0



## Round 2

### [rejected] FINDING_1

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_1: Timing JSON ignores since_last_mark
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `TimingReport.render_json` ignores `since_last_mark` and `mode`, so callers requesting only rows after the last mark still receive full `per_step` and `total_seconds` JSON.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_2: Domain-level --ledger is rejected before dispatch
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: The dispatcher rejects `token --ledger PATH ...` and `timing --ledger PATH ...` before subcommand parsers can preserve old flexible placement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_4: Snapshot replay ignores transcript-only source snapshots
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `token_report` skips snapshots that contain only `TRANSCRIPT_PATH`, then falls back to live transcript discovery and can fail or select the wrong concurrent transcript.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0



## Round 3

### [rejected] FINDING_6

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_6: parallel-tests misses pytest-backed Makefile targets
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `parallel-tests.py` discovery skips pytest-retargeted Makefile recipes introduced by this branch, so token and timing parity targets are omitted from filtered shard listings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0



## Round 4

6:FINDING_11_OUTCOME=rejected
9:FINDING_12_OUTCOME=rejected
22:FINDING_4_OUTCOME=rejected
25:FINDING_5_OUTCOME=rejected


