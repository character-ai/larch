## Plan

## Approach

Fix both failure paths.

1. In review core coverage, separate "coverage satisfied" from "collector success".
   - Keep `collector_success` limited to `OK` and `cap_hit`.
   - Add slug-level handling for `NOT_SUBSTANTIVE`.
   - Treat a static archetype as coverage-satisfied when every returned reviewer for that archetype is `NOT_SUBSTANTIVE` and there is no mixed real failure for that archetype.
   - Do not change threshold counting. `NOT_SUBSTANTIVE` still contributes to `FAILED_SLOTS` and `NOT_SUBSTANTIVE_SLOTS`.

2. In Step 5 wrapper recovery, stop replaying cached stall results.
   - Keep cached `complete` result env reuse.
   - Treat cached `stall` result envs like restartable stale state when no live registry row exists.
   - With a live registry row, still rejoin the live bgjob. Clear any non-`complete` canonical result env before waiting.

3. Update direct wrapper contract docs and harness expectations so they no longer say cached stall envs are terminal-reused.

## Files to modify/create

### UPDATED: python/larch/review/review_core_body.py

- Update `_static_coverage_reason`.
- Track returned static reviewer statuses by archetype slug.
- Add a coverage set for all-`NOT_SUBSTANTIVE` archetypes.
- Keep `_tool_absent_excused_static_slugs` behavior unchanged by leaving `collector_success` as only `OK` and `cap_hit`.
- Preserve the existing missing-archetype reason string.

### UPDATED: python/tests/review/test_review_pipeline.py

- Add a direct unit test for `_static_coverage_reason` where an expected static archetype has only `STATUS=NOT_SUBSTANTIVE` collector records and returns no missing coverage reason.
- Add or extend a negative case so mixed `NOT_SUBSTANTIVE` plus real failure for the same archetype still reports that archetype missing.
- Keep existing threshold tests unchanged, especially assertions that `NOT_SUBSTANTIVE` counts as failed for the slot-failure gate.

### UPDATED: skills/implement/scripts/step-5-review.sh

- Change the cached result env branch so only `result_env_state=complete` returns through `bgjob wait`.
- Treat `result_env_state=stall` the same as stale for fresh-start purposes.
- In the live-registry branch, clear the canonical result env unless it is `complete`, then rejoin via `bgjob wait`.
- Keep symlink and non-regular-file guards unchanged.

### UPDATED: skills/implement/scripts/test-step-5-review.sh

- Rewrite the canonical stall result test.
- Seed a valid stall result env, run the wrapper with no live registry, and assert:
  - stdout is the fresh bgjob start line,
  - `bgjob-start-argv.txt` exists,
  - the old canonical result env was removed before start.
- Keep the canonical completed result test as cached-reuse coverage.
- Keep live-registry rejoin tests unchanged.

### UPDATED: skills/implement/scripts/test-step-5-review.md

- Update the harness description so it says cached completed results are reused and cached stall results are cleared for a fresh review.
- Remove stale references to old detach or reattach behavior if the paragraph still describes retired wrapper behavior.

### UPDATED: skills/implement/scripts/step-5-review.md

- Update the KV grammar and invariants.
- State that a valid stall envelope from an active or final wait remains terminal for the current run, but a cached canonical stall result env is restartable recovery state.
- State that only `BGJOB_RC=0` plus required Step 5 KVs is reused from a prior canonical result env.

### UPDATED: skills/implement/references/step5-review-branches.md

- Update the same-step re-entry paragraph.
- Preserve live-registry rejoin behavior.
- Replace cached stall reuse with cached stall clearing and fresh start for `step5-review` recovery.
- Keep MAV and main-agent handoff branch language unchanged.

### MAY_UPDATE: scripts/test-implement-structure.sh

- Update pinned prose literals only if the doc edits remove or materially change existing required substrings.
- Prefer preserving broad required phrases where they still describe live wait stall handling.

## Edge cases

- A single TRIVIAL static reviewer returning `NOT_SUBSTANTIVE` should satisfy static archetype coverage.
- A pair-shape archetype with one `NOT_SUBSTANTIVE` reviewer and one real failure should not satisfy coverage.
- Tool-absent excusal must still require a surviving `OK` or `cap_hit` collector result.
- A stale cached stall result with required KVs must not block recovery.
- A live Step 5 bgjob must never be replaced by a second daemon.

## Failure modes

- If `NOT_SUBSTANTIVE` is added to `collector_success`, tool-absent excusal may become too broad.
- If cached stall envs are only removed from the non-live branch, a live rejoin may read stale terminal state.
- If docs keep saying cached stall envs are reused, future fixes may reintroduce the retry no-op.
- If the shell harness expects `bgjob wait` for cached stalls, it will pin the defect.

## Testing strategy

Run only changed-file checks:

- `python3 -m pytest python/tests/review/test_review_pipeline.py -k 'static_coverage_reason or reviewer_failure_threshold or review_core_panel_failed_on_missing_static_archetype'`
- `bash skills/implement/scripts/test-step-5-review.sh`
- `make test-step-5-review`
- `python3 python/cli.py checks run-relevant` if available for the changed files.

## Acceptance

Run only changed-file checks:

- `python3 -m pytest python/tests/review/test_review_pipeline.py -k 'static_coverage_reason or reviewer_failure_threshold or review_core_panel_failed_on_missing_static_archetype'`
- `bash skills/implement/scripts/test-step-5-review.sh`
- `make test-step-5-review`
- `python3 python/cli.py checks run-relevant` if available for the changed files.

review_status: complete
rounds_completed: 1
difficulty: MODERATE
diff_added: 70
diff_deleted: 25
mechanical_churn: false
diff_lines: 95
