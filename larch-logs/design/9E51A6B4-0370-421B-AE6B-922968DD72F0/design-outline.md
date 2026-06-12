## Proposed Design Outline

### Goals
- Prevent `phase_driver_write_result_env` failures in `step3_loop_persist_envelope` from being silently swallowed by `|| true`.
- Sanitize KV values that may contain newlines/CRs before they reach `phase_driver_write_result_env`, so the primary write succeeds instead of relying on fallback guards.

### Non-goals
- Changing `lib-phase-driver.sh`'s newline guard (it is correct and intentional).
- Changing `design-step3-review.sh` (the Fix C guard at lines 203–206 is already present).
- Adding a shared `sanitize_for_kv_value` helper — inline stripping is sufficient for the two affected variables.

### Approach sketch
- Strip `$'\n'` and `$'\r'` from `PLAN_REVIEW_CONTINUE_REASON` and `SCOPE_ANCHOR_FILE` in `step3_loop_persist_envelope` before building the `kvs` array.
- Replace `|| true` with a conditional warning block that emits to the quiet channel (FD 3) so the failure is visible in execution issues.
- Update `review-design-step3-loop.md` to document the sanitization contract.
- Add a test case to `test-review-design-step3-loop.sh` that injects a newline into `PLAN_REVIEW_CONTINUE_REASON` and asserts the result env is written correctly.

### Surfaces in scope
- `skills/design/scripts/review-design-step3-loop.sh` (primary fix: sanitize + warn)
- `skills/design/scripts/review-design-step3-loop.md` (sibling doc update)
- `skills/design/scripts/test-review-design-step3-loop.sh` (regression test)
- `skills/design/scripts/test-review-design-step3-loop.md` (test sibling doc)

### Open questions
- None.
