### [rejected] FINDING_2

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_2: bgjob no-progress test never enters a live WAIT
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-correctness, cursor-specialist-testing, codex-specialist-testing, dyn-dyn-bgjob-proc
- **Severity**: minor
- **Concern**: The `scripts/test-hook-no-progress-guard.sh` bgjob case seeds only a static result environment and never drives an actual live wait, so regressions where repeated Stop turns increment the counter would stay undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Seed a live bgjob registry row run Stop while the job is in WAIT and assert no-progress counter stays zero
  - From cursor-specialist-edge-cases: Seed live registry/child; assert Stop during WAIT does not bump counter
  - From codex-specialist-correctness: Feed the hook the actual bgjob wait event shape, not just a prewritten result env.
  - From cursor-specialist-testing: Start a real bgjob or seed a live registry row, exercise repeated Stop during bgjob wait, and assert counter stays 0
  - From codex-specialist-testing: Reproduce the actual WAIT path with an active marker and the hook event that would be miscounted, then assert the counter and block sidecars stay unchanged
  - From dyn-dyn-bgjob-proc: Seed a live bgjob registry row (or run `bgjob start` with a long child), invoke the hook during an in-flight wait, and assert the counter/breaker stay idle; keep the legacy-marker cases separate.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** dismissed (0 YES)

### FINDING_5: poll-guard test misses documented bgjob wait forms
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: major
- **Concern**: The `scripts/test-hook-bg-poll-guard.sh` coverage relies on a tmpdir-path loophole instead of the documented wait shape, so the current denied form and related allow behavior are not covered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Add explicit bgjob wait allow matcher; test documented tmpdir variable forms


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** dismissed (0 YES)

### FINDING_7: identity-probe skip can falsely green bgjob harness
- **Reviewer(s)**: dyn-dyn-bgjob-proc
- **Severity**: major
- **Concern**: When identity probes are unavailable, the `scripts/test-bgjob.sh` harness reports success without running assertions, which can falsely green CI or local runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-bgjob-proc: On identity-probe skip, exit non-zero (or mark the harness skipped in a way that fails the Makefile target), and only treat individual cases as skippable when the plan explicitly allows it.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** dismissed (0 YES)

### FINDING_8: owner-death harness bypasses public bgjob CLI
- **Reviewer(s)**: dyn-dyn-bgjob-proc
- **Severity**: minor
- **Concern**: The `scripts/test-bgjob.sh` owner-death case exercises daemon internals directly instead of the public `bgjob start` / `bgjob wait` CLI flow, so CLI owner-PID and orphan signaling regressions could pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-bgjob-proc: Run owner death through the public `bgjob start`/`bgjob wait` CLI with a disposable owner subprocess (or documented `--owner-pid`), and assert `BGJOB_RC=orphaned` via wait stdout and `$TMPDIR/bgjob/<step>.result.env`.
Vote tally: YES=0 NO=2 JUDGE_ERROR=1

