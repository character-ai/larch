## Proposed Design Outline

### Goals
- Fix 4 normative doc files that still cite retired script basenames (`check-plan-size.sh`, `revise-plan-with-waterfall.sh`).
- Wire `design-clarify.sh` and its harness into `relevant-checks.sh` so edits trigger `test-design-clarify`.
- Fix the `awaiting-continuation` success-path timing bug and add origin-fetch before idempotency checks in `design-log-publish.sh`.
- Strengthen SKILL.md fail-safe guard and test ordering for the Step 3 loop teardown.

### Non-goals
- Changing the awk library behavior or plan-size thresholds (the doc update is citation-only).
- Rewriting the test harness structure for `test-design-log-publish.sh` beyond the squash-simulation gap.
- Adding new features or flags to any modified surface.

### Approach sketch
- **Item 1**: Replace `check-plan-size.sh` and `revise-plan-with-waterfall.sh` references in 4 doc files with `python/cli.py plan check-size` and `python/cli.py plan revise-waterfall`.
- **Item 2**: Add a `case` arm in `relevant-checks.sh` for `design-clarify.sh|design-clarify.md|test-design-clarify.sh|test-design-clarify.md` → `append_target_once test-design-clarify`.
- **Item 3**: Add a guard in SKILL.md: before running the missing-row fail-safe, check if `.completed/step-2b` already exists; if so, skip the retained fence.
- **Item 4**: Add line-number ordering assertions in `test-design-structure.sh` for `wait "$_loop_pid"` before `kill -- -"$_pid"` in `design-step3-review.sh`.
- **Item 5**: Fix `review-design-step3-loop.sh` lines 786 and 655 to use `step3_loop_read_round_start_s` on success and panel-failed paths.
- **Item 6**: Call `design_publish_refresh_default_ref` before the idempotency check in `design-log-publish.sh`.
- **Item 7**: Add a test case that pushes log content to main without a live branch, then re-runs publish to confirm idempotency.

### Surfaces in scope
- `skills/design/scripts/lib-plan-optional-trailers.md`
- `skills/design/scripts/test-trailer-awk.md`
- `skills/design/scripts/test-design-postplan-emit.md`
- `docs/workflow-lifecycle.md`
- `scripts/relevant-checks.sh`
- `skills/design/SKILL.md`
- `scripts/test-design-structure.sh`
- `skills/design/scripts/review-design-step3-loop.sh`
- `scripts/design-log-publish.sh`
- `scripts/test-design-log-publish.sh`

### Open questions
- None.
