## Decision 1: Behavior on invalid detail log (non-oversize causes)
- **Question**: When `record-escalation` receives an invalid `--failure-detail-log`, should it record the escalation anyway (soft) or keep failing?
- **Resolution**: Keep failing (exit 1), but the recorded reason MUST name the SPECIFIC cause instead of the generic `failure-detail-log-invalid`. Applies to the structural causes: non-absolute, symlink, outside-tmpdir, non-regular-file. Each maps to a distinct token (e.g. `failure-detail-log-non-absolute`, `failure-detail-log-symlink`, `failure-detail-log-outside-tmpdir`, `failure-detail-log-not-regular-file`). The loud failure is retained as a signal of genuinely broken wiring; only the diagnosability is fixed.
- **Source**: user

## Decision 2: Oversize handling (the 64KiB optional-evidence cap)
- **Question**: When the detail log exceeds the 64KiB cap specifically, skip-with-reason or truncate-and-attach?
- **Resolution**: Truncate and attach. Oversize is the ONE rejection cause that must NOT fail the escalation. `record-escalation` truncates the detail log to the 64KiB cap and attaches it; the escalation records successfully. This carves oversize out of Decision 1's hard-fail set (oversize is an expected/benign condition for large lint logs, not broken wiring). Addresses Hypothesis A (most-likely observed cause).
- **Source**: user

## Decision 3: Fix scope — also align checks.py containment
- **Question**: Confine the fix to the reporting layer (`stall_recovery.py`) or also change `checks.py`?
- **Resolution**: Also align `python/checks.py`. In addition to the `stall_recovery.py` reporting-layer changes, align the lint-fix checks-log path root with the `--tmpdir` that `record-escalation` validates against (Hypothesis B), so the real lint-fix detail log resolves inside tmpdir and is not rejected as outside-tmpdir.
- **Source**: user

## Hard constraints / non-goals (carried into plan drafting)
- `validate_failure_detail_log` is SHARED: a second caller `_read_validated_failure_detail_log` (used by `classify`) and the `compose-report` evidence read path also depend on it. Changes must preserve the `classify` soft-skip behavior and not break existing tests' stderr assertions.
- The generic token `failure-detail-log-invalid` has NO active consumers (only historical committed run-log `final-summary.md` files). Specializing it is safe; nothing downstream parses it.
- The Step 2b plan must decide whether oversize-truncate is record-escalation-local or applies to the shared read/compose path, and must handle the test fallout for `test_classify_rejects_oversize_failure_detail_log` and `test_compose_report_tier_a_skips_oversize_detail_log` accordingly.
- Non-goal: renaming or backfilling historical tokens in already-committed run logs.
- Non-goal: changing the unrelated `classify` command's contract beyond what the shared validation helper requires.
