### OOS_1: [OUT_OF_SCOPE] Duplicate flush on stalled round-failed path
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing
- **Severity**: nit
- **Concern**: `_flush_review_batches_for_result` runs twice on the unknown-status `round-failed-*` stall path, causing duplicate I/O; this is harmless and pre-existing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Keep a single flush call on the stall exit path.
  - From cursor-specialist-testing: Keep a single flush call on the stall exit path.

### OOS_2: [OUT_OF_SCOPE] Missing terminal flush at handoff exits
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: latent
- **Concern**: `main-agent-vote-required` and `coder-main-agent-required` handoff exits still return without a terminal batch flush; only a later resumed `complete`/`cap-hit` would flush. This is pre-existing mid-loop semantics outside the terminal-success scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: No change unless product wants run-root tallies at handoff boundaries.

### OOS_3: [OUT_OF_SCOPE] Silent skip paths still bypass warning
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: latent
- **Concern**: `flush_review_batches` can soft-skip on empty `run_id` or compose failure and return `True` without raising; the wrapper only surfaces exceptions, so those silent skip paths stay unreported.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Out of scope here; consider warnings on `False`/skip returns separately.

### OOS_4: [OUT_OF_SCOPE] `effective_cap` is re-parsed from args
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: `_finish_step5_terminal_success` derives `effective_cap` from `int(str(args.round_cap))` instead of reusing the loop-local `round_cap`, so a future mismatch could emit the wrong `EFFECTIVE_ROUND_CAP` or raise `ValueError`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Pass effective_cap=round_cap (or add an effective_cap: int parameter) into _finish_step5_terminal_success instead of re-parsing args.round_cap.

### OOS_5: [OUT_OF_SCOPE] Missing unmocked terminal artifact assertion
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: The plan-required on-disk run-root assertions were replaced with a mocked flush-call test, so wiring or compose regressions could still slip through while final summaries remain `N/A`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add one unmocked step5 terminal test that seeds minimal round artifacts and asserts code-review-tally.json and review-findings-full.jsonl exist under larch-logs/implement/<run-id>/.

### OOS_6: [OUT_OF_SCOPE] Cap-hit flush-failure coverage is missing
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: Flush-failure containment is exercised only for `complete`, not `cap-hit`, so a cap-hit-specific regression in the failure handler would be uncovered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Parametrize the warning test for cap-hit (fix-applied + gate_status=cap-hit) with the same rc/stderr/execution-issues assertions.

### OOS_7: [OUT_OF_SCOPE] Resume-past-cap flush metadata may be stale
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: `mav-resume-past-cap` still flushes with `rounds_completed=0` and `result=None`, which can make run-root tally metadata incomplete on resume-past-cap runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Revisit flush kwargs for mav-resume-past-cap if calibration needs accurate round metadata.

### OOS_8: [OUT_OF_SCOPE] flush False returns still stay silent
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: `flush_review_batches` returning `False` still produces no warning, so soft compose/skip failures can continue to yield silent `N/A` final-report lines.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Log a warning when flush returns False without changing Step 5 terminal status.

