# Review Round 1

- Mode: `diff`
- 24 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Invalid run-log CLI invocation in Step 7a
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Step 7a treats `python/cli.py run-log` as one executable path. Run-log write and pre-bump commit paths can fail or skip because that file does not exist.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_10: Verify-completeness check is too shallow
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `verify_completeness_main` checks only a small subset of the retired completeness conditions. Incomplete run logs can print OK despite missing required batches and summary artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_11: Transcript capture skips rendering and terminal warnings
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `capture_transcript_main` stages source data directly instead of rendering session transcripts and appending warning execution issues for terminal statuses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-edge-cases-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_12: Pre-commit staging is missing before run-log commits
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The shared pre-commit staging helper is absent or not wired into flush and refresh paths. Vendor diagnostics, execution issues, reports, and transcripts can be omitted from committed run logs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_13: Volatile-only cleanup can leave dirty tracked files
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `_commit_run` unlinks volatile files instead of restoring or cleaning them through the shared cleanup flow. Tracked volatile artifacts can become dirty deletions while returning volatile-only success.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_14: Refresh marks step9a1 complete unconditionally
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `refresh_run_logs_main` always sets `steps_ran.step9a1=true`. Forked or design-only runs can be marked as if Step 9a1 completed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_15: Write-round omits dynamic panel manifest archetype refs
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `write-round` does not update `panel-manifest.ndjson` with dynamic reviewer `archetype_ref` entries. Committed panel manifests can miss refs needed by dynamic reviewers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_16: Cursor launcher still uses deleted redaction helper
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `scripts/lib-cursor-launcher-common.sh` still pipes diagnostics through deleted `redact-secrets.sh`. Cursor launcher failure diagnostics can lose redaction.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_17: Issue creation redaction helper path is invalid
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `skills/issue/scripts/create-one.sh` sets `REDACT_HELPER` to an invalid spaced executable path. Issue body redaction can fail or ship unredacted content.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_18: Plan command capture can skip redaction
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `skills/design/scripts/validate-plan-commands.sh` treats `python/cli.py redact secrets` as one executable file. Tier-3 plan command capture may skip redaction.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_2: Invalid review-core logging helper defaults
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `skills/review/scripts/review-core.sh` defaults logging helpers to non-existent executable paths and gates them with `[[ -x ]]`. Review write-round logging and append-failure records can be silently skipped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_20: Internal manifest writers still emit legacy schema
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Internal run-log manifest writers still emit legacy v1 manifests. Recovered or internally initialized implement runs can commit manifests without required v2 fields.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_21: Deleted append-tool-failure helper in OOS prepare path
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `skills/design/scripts/design-step5b-prepare.sh` still calls deleted `append-tool-failure.sh` on OOS prepare failure. Tool failure entries and stderr forensics can be lost.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From codex-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_22: Quiet breadcrumbs are not staged into run logs
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `_commit_run` does not stage top-level larch-quiet breadcrumbs. Quiet-log-only diagnostics can be dropped or produce no flush delta.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_23: Phantom probes still call deleted execution-issue helper
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Runtime stale-helper references include phantom probes that still call deleted `append-execution-issue.sh`. Probe diagnostics can fail after helper deletion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_24: Shared pool copy deletes existing shared archetypes
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `_commit_run` deletes the existing `larch-logs/shared` tree during shared pool copy. New dynamic archetypes can remove previously committed shared archetypes and break older `panel-manifest` refs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_25: Migrated CLI coverage is missing
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-required subprocess CLI and harness coverage is largely missing. Tests can pass despite broken shell invocations and skeletal run-log refresh, capture, and completeness behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_3: Invalid run-log append invocation in execution-issue flush
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `skills/implement/scripts/flush-execution-issues.sh` uses the same broken spaced-path CLI invocation. Execution-issue NDJSON flushes can fail at Step 7a and Step 8 boundaries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_4: Invalid run-log invocation in review phase logging
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `skills/review/scripts/log-phase.sh` treats run-log subcommands as part of the executable path. Review phase log batches can fail to write.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_5: Invalid run-log manifest invocation in final report refresh
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `skills/implement/scripts/write-final-report.sh` invokes the run-log manifest command through a broken spaced executable path. Final-report refresh can fail to update `steps_ran`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_6: Deleted append-tool-failure helper in design abort cleanup
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `skills/design/scripts/design-step0-abort-cleanup.sh` still calls deleted `scripts/append-tool-failure.sh`. Design abort cleanup can lose tool-failure forensics or exit on a removed helper.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_7: Deleted append-tool-failure helper in design drafter fallback
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `skills/design/scripts/design-step2b-drafter.sh` still calls deleted `scripts/append-tool-failure.sh`. Drafter fallback warnings can be omitted from execution issues.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_8: Deleted run-log helpers in voting tally writes
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `python/voting.py` still subprocesses deleted `larch-log.sh` and append helpers. Tally batch writes and voter parse-rate warnings can fail after the helper deletion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-edge-cases-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_9: Refresh run-log flow is incomplete
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `refresh_run_logs_main` does not port the full retired refresh flow. Refresh commits can omit token reports, timing reports, final reports, transcripts, and execution issue batches.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.


