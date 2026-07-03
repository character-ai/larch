# Review Round 2

- Mode: `diff`
- 3 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_1: PR-create regression misses the pin-triggered flush seam
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-testing, dyn-dyn-runlog-flush
- **Severity**: important
- **Concern**: The PR-create regression test seeds `execution-issues.md` before the normal postbump flush, so it can still pass if `_flush_guidelines_warning_before_pr` is removed or broken. It does not prove the warning is flushed by the pin-triggered seam before `ensure_pr`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Drive pin_warning_logged=True via real pin failure after postbump flush without pre-seeding execution-issues.md; assert ndjson is written by the pin-triggered flush before ensure_pr
  - From codex-specialist-correctness: Make the test force a real warning-triggered path, for example by making `_pin_and_load_guidelines_note` append the warning and return `(note, True)` after the postbump flush, then use real `flush_logs_pre` and assert `ensure_pr` sees the committed batch.
  - From cursor-specialist-testing: Stub pin to return warning_logged=True, skip postbump flush in the test, assert ndjson appears only via the warning-triggered pre-ensure_pr flush; add resume-path variant
  - From dyn-dyn-runlog-flush: Add a case that appends the warning only inside a mocked `pin_warning_logged=True` path after postbump flush is stubbed to no-op (or use an `open-pr` resume that skips postbump), then assert `execution-issues.ndjson` is populated before `ensure_pr`.


### FINDING_2: Stale guidelines note drops warning state on persist failure
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: important
- **Concern**: `_handle_stale_guidelines_note` returns `warning_logged=False` when persistence fails, so a dropped note does not trigger the pre-`ensure_pr` flush and can leave `execution-issues.md` empty.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Mirror `_invalidate_guidelines_note`: log persist-failed warning and accumulate warning_logged when should_persist and not persisted


### FINDING_3: CI-fix regression still mocks the real invalidate→flush→push path
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-testing, codex-specialist-testing, dyn-dyn-runlog-flush
- **Severity**: important
- **Concern**: The CI-fix regression still uses a mocked `stage_and_push`, so it only proves the callback wiring. It does not prove that a normal successful CI-fix push commits `execution-issues.ndjson` before the branch push.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Use real stage_and_push with pre_push_log_refresh calling _invalidate_guidelines_note on a durable note tmpdir without pre-seeded warnings; assert committed execution-issues.ndjson before push
  - From codex-specialist-correctness: Add an integration-style test for `_run_cycle` using the real `stage_and_push` seam, with commit/push helpers stubbed, and assert exactly one branch push plus committed `execution-issues.ndjson` content before `_wait_for_ci` returns clean.
  - From cursor-specialist-testing: Add offline _run_cycle test with real stage_and_push, seeded run-log manifest and durable note, one push, ndjson contains architectural-guidelines warning
  - From codex-specialist-testing: Add the planned CI-fix regression in `python/tests/implement/test_ci_agentic_fix.py` without mocking `stage_and_push`: seed a run log, trigger `_invalidate_guidelines_note`, run the successful CI-fix push path, and assert the branch push sees `larch-logs/implement/<run-id>/execution-issues.ndjson` containing the architectural-guidelines warning.
  - From dyn-dyn-runlog-flush: Add an integration test through `ci_agentic_fix._run_cycle` (or unmocked `stage_and_push` with a real durable guidelines note) on the non-rebase push path.


