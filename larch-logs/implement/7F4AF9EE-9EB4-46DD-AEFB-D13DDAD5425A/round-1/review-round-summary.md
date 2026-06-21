# Review Round 1

- Mode: `diff`
- 4 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Duplicate WARN replay from captured loop stdout
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-warn-replay-output.txt
- **Severity**: important
- **Concern**: Stage 1 selected-source WARN replay and Stage 2 stdout overlay WARN replay can both read the same captured loop stdout (empty regular `.step3-review-result.env` with only non-allowlisted content, quiet-load failure with `primary_regular` still true, or fallback stdout as `selected_source`). That emits duplicate `WARN=` lines before the canonical KV envelope; retired Bash emitted once. Breaks the two-stage no-double-replay contract and orchestrator stdout ordering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Skip Stage 2 WARN overlay when selected_source equals stdout_file, or restrict Stage 2 WARN replay to cases where selected_source is the primary result-env file.
  - From codex-specialist-correctness-output.txt: Pass selected_source into the overlay helper and skip overlay WARN replay when selected_source is the stdout file.
  - From cursor-specialist-edge-cases-output.txt: Skip Stage 2 WARN overlay when selected_source equals stdout_file, or run Stage 2 WARN overlay only after successful quiet load (rc == 0).
  - From dyn-warn-replay-output.txt: Track whether env was loaded from the primary result env (quiet `rc == 0` and `selected_source` is the primary path). Gate Stage 2 overlay `WARN=` on that flag, or skip overlay replay when `selected_source` resolves to the same path as `--stdout-file`.


### FINDING_2: Missing escalation-evidence failure normalizer test
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-required regression coverage for `step3_record_report_evidence` / `_step3_record_report_evidence_quiet` failure is absent. A regression could reintroduce pre-envelope `WARN=` leakage or break stderr-only warning contract without CI detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add subprocess or monkeypatched test forcing step3_record_report_evidence failure and assert stdout/stderr contract.
  - From cursor-specialist-testing-output.txt: Add a pytest that mocks _step3_record_report_evidence_quiet to return 1 for an evidence status, runs normalize-status, asserts no pre-envelope WARN= on stdout, canonical KVs still print, and stderr has the failed-to-record-escalation-evidence warning only.


### FINDING_5: Primary-file WARN/ERROR dropped when regular env has no allowlisted keys
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-warn-replay-output.txt
- **Severity**: important
- **Concern**: When `.step3-review-result.env` is a regular file but has no allowlisted keys (only `WARN=`/`ERROR=` or other non-allowlisted lines), `_step3_read_result_env_quiet` binds `selected_source` to captured loop stdout. Stage 1 replays only that fallback, so machine `WARN=`/`ERROR=` that lived only on the primary file never reach wrapper stdout. Orchestrators and hooks consuming pre-envelope machine warnings can miss degradation signals.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Keep selected_source as primary whenever primary_regular; use fallback only when primary is missing/symlink/non-regular.
  - From dyn-warn-replay-output.txt: In Stage 1, mirror `read_result_env_main`'s `write_pairs` ordering: when `primary_kind == "regular"`, call `_replay_warn_error` on the primary path first, then replay `selected_source` only if it differs from primary.


### FINDING_6: mkstemp allocation failure changes post-loop exit semantics
- **Reviewer(s)**: dyn-step3-contracts-output.txt
- **Severity**: important
- **Concern**: `_step3_normalize_load_env` folds `tempfile.mkstemp` failures into the same `except OSError` path as read failures, emits the read-recovery warning (`could not read step3 review result env`), and continues with stdout fallback instead of aborting. Retired Bash printed `**⚠ Step 3: could not allocate safe step3 review result env; aborting plan review**` and exited `1` before status mapping or KV emission. That changes post-loop exit semantics on temp-file exhaustion and can return success-shaped envelopes when captured loop stdout is usable.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-step3-contracts-output.txt: Split mkstemp allocation from read failures; on allocation failure print the original abort message to stderr and return `1` immediately (or re-raise through a dedicated branch), matching the retired Bash contract.


