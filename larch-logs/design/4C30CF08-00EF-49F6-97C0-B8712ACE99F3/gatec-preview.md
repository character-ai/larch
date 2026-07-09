## Final Design Plan

## Plan

## Approach

Fix the stale re-entry state at the shared Python cleanup point.

Add `bgjob/design-step3-review.result.env` and `bgjob/design-step4-tail.result.env` to `_step3_clear_downstream_sentinels()` in `python/larch/review/plan_review_loop.py`. This covers `--direct-review-entry`, `--direct-review-pause-hygiene`, and `--auto-continuation-entry` through one helper.

Do not change the Bash launchers. Their current rejoin-before-fresh-start behavior stays valid once re-entry clears stale result envs.

Do not add plan fingerprinting to `review_provenance()`. That is out of scope per the approved outline.

## Files to modify/create

### UPDATED: python/larch/review/plan_review_loop.py

In `_step3_clear_downstream_sentinels()`:

- Add unlink coverage for:
  - `bgjob/design-step3-review.result.env`
  - `bgjob/design-step4-tail.result.env`
- Keep `missing_ok=True`.
- Keep cleanup narrow. Do not remove registries, merge envs, live process state, or other bgjob files.

### UPDATED: python/tests/review/test_plan_review.py

Extend `_seed_step3_downstream()` so it:

- Creates `tmp_path / "bgjob"` with `mkdir(parents=True, exist_ok=True)` before writing any seeded result env files (fresh `tmp_path` fixtures have no `bgjob/` parent today).
- Seeds both stale bgjob result envs as regular files with minimal, assertable contents after creating `bgjob/`:
  - `bgjob/design-step3-review.result.env` — e.g. `BGJOB_RC=0\nNEXT_ACTION=step3b\n`
  - `bgjob/design-step4-tail.result.env` — e.g. `BGJOB_RC=0\nSKIP_APPROVE_REQUESTED_GATEC=false\n`

Update these existing tests to assert both seeded result env files are absent after cleanup:

- `test_step3_state_direct_review_entry_clears_restores_and_consumes`
- `test_step3_state_auto_continuation_clears_without_restore`

Also update `test_step3_state_direct_review_entry_noop_without_reentry` to assert both seeded result env files still exist when there is no `.step3-reentry` breadcrumb, so the no-op contract stays explicit.

Update `test_step3_state_pause_hygiene_clears_but_preserves_findings_and_reentry` to assert the same result env cleanup, since the shared helper applies there too.

## Edge cases

- Missing `bgjob/` directory should remain harmless during production cleanup (`unlink(missing_ok=True)`).
- Seeding must create `bgjob/` first; writing result env paths on a bare `tmp_path` without that parent raises `FileNotFoundError` and prevents the new assertions from running.
- Seeded result env files must exist before cleanup runs; otherwise absent-file assertions pass vacuously and do not prove stale state is removed.
- Existing stale result env files should be removed before the next launcher decides between `bgjob wait` and `bgjob start`.
- Direct review entry without `.step3-reentry` must stay a no-op and leave seeded result env files on disk.
- Auto-continuation must clear stale result envs without restoring upstream completion markers.
- Future-round review artifacts must remain preserved by the existing round cleanup rules.

## Failure modes

- If only Step 3 result env is cleared, Gate C can still reuse a stale Step 4 tail preview.
- If cleanup is added only to the Bash re-entry path, auto-continuation and pause hygiene can keep stale result envs.
- If the launcher rejoin logic is changed instead, it may break legitimate restarts where a completed bgjob result env is still authoritative.
- If `_seed_step3_downstream()` writes result envs without creating `bgjob/` first, focused regression tests fail at setup instead of exercising cleanup behavior.
- If tests assert absence without seeding the files first, cleanup regressions can pass vacuously while stale re-entry state survives in production.

## Testing strategy

Run the focused regression tests:

`python3 -m pytest python/tests/review/test_plan_review.py -k "step3_state_direct_review_entry_clears_restores_and_consumes or step3_state_direct_review_entry_noop_without_reentry or step3_state_auto_continuation_clears_without_restore or step3_state_pause_hygiene_clears_but_preserves_findings_and_reentry"`

Run lint for changed Python files using the repo's normal Python lint target or direct file-scoped tooling if available.

## Difficulty

This is workflow state cleanup for `/design` re-entry and bgjob reuse. The code change is small, but the behavior affects review provenance and Gate C preview freshness.

difficulty: MODERATE
diff_lines: 42
