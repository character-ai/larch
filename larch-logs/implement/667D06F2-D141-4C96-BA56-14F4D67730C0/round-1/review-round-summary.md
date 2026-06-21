# Review Round 1

- Mode: `diff`
- 3 accepted, 1 rejected (1 neutral)

## Accepted Findings

### FINDING_1: _run_activity_mtime ignores Step 5 review activity when ranking runs
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `_run_activity_mtime` ranks concurrent implement runs using only v1/mark row timestamps (or max wall-clock mark timestamp), not step depth or ongoing Step 5 review activity. Step 5 writes one mark at entry while vendor and round ledger rows update during multi-round review but are ignored. A younger stalled Step 0 run with a fresher mark timestamp (e.g., mark at T-4m vs active Step 5 mark at T-30m) can outrank an active long-running Step 5 session, so `/progress` may show Step 0 preflight instead of Step 5 Gantt/stats. The docstring implies marks advance every step/round, but Step 5 emits no per-round marks during review, so the liveness signal does not match the feature description.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_2: #4954 regression test misses stale-newer-mark failure mode
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The new #4954 test in `python/test_progress_report.py` only covers active-newer-mark (synthetic ts=20 vs ts=10) and does not exercise the production chronology: active Step 5 entered earlier with an older mark, stale Step 0 started later with a fresher mark, and ranking still selects the stale run. The test can pass while the live failure remains reproducible; false confidence on merge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_6: Raw diagram subprocess capture may persist secrets
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Raw unredacted diagram subprocess stderr/stdout is persisted to `code-flow-diagram.raw-failure.log`. A failed diagram subprocess can print an API key, bearer token, or rejected diagram body. The sanitized bounded log is safe, but the raw tmpdir sidecar remains and is not removed on later success.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


