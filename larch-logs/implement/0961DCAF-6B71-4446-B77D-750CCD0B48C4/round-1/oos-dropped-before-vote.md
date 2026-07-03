### OOS_1: [OUT_OF_SCOPE] Standalone review Step 4 needs an unconditional log root and RUN_ID validation
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing, dyn-dyn-transcript-flow
- **Severity**: important
- **Concern**: The Step 4 review capture and commit path only defines `review_log_root` inside the scout-manifest branch. Standalone runs can therefore capture to an empty or stale root, and `RUN_ID` is not being validated before path construction. That can make review artifacts non-durable and can stage them under the wrong local directory.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Add review_log_root="${LARCH_LOG_ROOT:-$REVIEW_TMPDIR/larch-logs}" before Step 4 log-phase and transcript capture prose.
  - From codex-specialist-correctness: `skills/review/SKILL.md:111` — Important. Plan-correctness, source: plan. The new standalone review capture uses `$review_log_root`, but the only explicit assignment is inside the skipped scout-manifest block at `skills/review/SKILL.md:82-84`. A normal standalone review with `SCOUT_STATUS=na` will expand an unset variable to empty, so `run-log capture-transcript` writes under a relative `review/<RUN_ID>/...` path because `python/larch/report/run_log_flush.py:811` uses `Path(args.log_root)` directly. **Suggested fix:** Define `review_log_root="${LARCH_LOG_ROOT:-$REVIEW_TMPDIR/larch-logs}"` unconditionally before all Step 4 log-phase, transcript capture, and commit calls, and pass that value to every review log command.
  - From cursor-specialist-edge-cases: Add unconditional review_log_root="${LARCH_LOG_ROOT:-$REVIEW_TMPDIR/larch-logs}" at Step 4 before capture and commit.
  - From codex-specialist-edge-cases: Initialize review_log_root="${LARCH_LOG_ROOT:-$REVIEW_TMPDIR/larch-logs}" unconditionally before all Step 4 log writes, guard transcript capture and commit on `[[ -z "${SESSION_ENV_PATH:-}" && -n "${RUN_ID:-}" ]]`, validate `RUN_ID` with the same slug contract before capture, and ideally add absolute `--log-root` plus slug validation inside `capture_transcript_main`.
  - From cursor-specialist-testing: Require review_log_root="${LARCH_LOG_ROOT:-$REVIEW_TMPDIR/larch-logs}" before standalone capture and commit when SESSION_ENV_PATH is empty.
  - From codex-specialist-testing: The new standalone review transcript command uses `$review_log_root`, but the only pinned assignment in this skill is inside the `SCOUT_STATUS` block at `skills/review/SKILL.md:82-106`. In a normal standalone review with no scout manifest, this can expand empty: `run-log capture-transcript` then stages under the current directory, while `run-log commit` rejects the empty log root via `python/larch/report/run_log_batch.py:219-226`, so the review transcript is not durable. **Suggested fix:** Set `review_log_root="${LARCH_LOG_ROOT:-$REVIEW_TMPDIR/larch-logs}"` unconditionally before all Step 4 log-phase, transcript capture, and commit calls, and add a no-scout standalone review coverage case.
  - From dyn-dyn-transcript-flow: Add a standalone Step 4 fence (or prose immediately before capture) that always sets `review_log_root="${LARCH_LOG_ROOT:-$REVIEW_TMPDIR/larch-logs}"` whenever `RUN_ID` is non-empty, independent of scout status; use that binding for all `review log-phase`, capture, and commit calls.

### OOS_2: [OUT_OF_SCOPE] Step 5c warning label should reflect pause and clarify publish paths
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: `_capture_design_transcript` hardcodes the 5c warning label even when `log_publish_main` is invoked for pause or clarify. That makes execution-issue warnings point to the wrong step and can confuse operators auditing capture gaps.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Thread warning_step_label through _TranscriptCaptureContext from log_publish_main --reason (final→5c, pause).

### OOS_3: [OUT_OF_SCOPE] Add a review Step 4 regression harness
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: Standalone review transcript capture lacks a dedicated offline harness or Python regression test, so future Step 4 changes could break the nested guard, source binding, or commit ordering without CI coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add thin review Step 4 harness covering capture argv, nested skip, and SESSION_UUID mismatch.

### OOS_4: [OUT_OF_SCOPE] Heatmap TSV consumers may need compatibility notes for the new sections
- **Reviewer(s)**: dyn-dyn-transcript-flow
- **Severity**: nit
- **Concern**: The heatmap TSV now includes extra `# transcript_coverage` and `# reference_heatmap` sections. Downstream parsers that still expect the legacy header shape could break.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-transcript-flow: Worth a short compatibility note if anything outside this repo consumes the artifact.

### OOS_5: [OUT_OF_SCOPE] Step 18 and teardown both flush execution issues
- **Reviewer(s)**: dyn-dyn-transcript-flow
- **Severity**: nit
- **Concern**: Step 18 finalize and `finalize.teardown` both run `execution-issues flush-safety-net`, which duplicates work on terminal runs even though the flush is append-only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-transcript-flow: Address the concern above.

